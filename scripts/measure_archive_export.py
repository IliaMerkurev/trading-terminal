"""Actual serialized HTTP export/transfer acceptance on isolated synthetic data.

Targets: ordinary requests <=2 s, cancellation quiescence <=5 s. Measurements
include local test-client memory in parent RSS; browser Blob memory is separate.
Existing workspaces are never modified: either import a synthetic archive into a
new destination, or copy an explicitly supplied closed synthetic workspace.
"""
import argparse
import base64
import gc
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import threading
import time
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from terminal.browser_host import BrowserServer
from terminal.archive_export import CHUNK_BYTES
from scripts.measure_archive_import import rss_tree
from tests.archive_receipt_fixtures import documents


def measure(destination,source=None,workspace=None):
    destination.mkdir(parents=True,exist_ok=False)
    if workspace:shutil.copytree(workspace,destination/'workspace')
    dist=destination/'dist';dist.mkdir();(dist/'index.html').write_text('<title>Synthetic export acceptance</title>')
    server=BrowserServer(destination/'workspace',dist);thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01});thread.start()
    headers={'Origin':server.origin,'Sec-Fetch-Site':'same-origin','Content-Type':'application/json','X-Terminal-Session':server.token}
    samples={};phases=[];peak=0;stop=threading.Event();writer_id=None
    out={'targets_seconds':{'request':2,'quiescence':5},'synthetic_only':True,'measurement_includes_local_http_client_memory':True}
    def post(path,payload,label):
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=20);tick=time.monotonic()
        try:
            conn.request('POST',path,json.dumps(payload),headers);response=conn.getresponse();raw=response.read()
            if response.status!=200:raise RuntimeError(f'{label} returned HTTP {response.status}')
            return raw
        finally:samples.setdefault(label,[]).append(time.monotonic()-tick);conn.close()
    def call(command,params=None):
        reply=json.loads(post('/api/request',{'version':1,'id':command,'command':command,'params':params or {}},command))
        if reply['type']!='result':raise RuntimeError(reply['error']['message'])
        return reply['result']
    def probe():
        nonlocal writer_id
        scheduler=call('scheduler_status')
        result=call('save_graph',{'name':'Synthetic foreground writer','graph':project['strategy']['document']['graph'],'layout':{},'strategy_id':writer_id,'profile':project['profile']})
        writer_id=result['strategy_id'];return scheduler
    def sample():
        nonlocal peak
        while not stop.wait(.05):
            current=rss_tree(os.getpid())
            if current is not None:peak=max(peak,current)
    sampler=threading.Thread(target=sample)
    try:
        project,_=documents()
        if source:
            upload=call('archive_begin',{'size':source.stat().st_size})
            with source.open('rb') as stream:
                offset=0
                while raw:=stream.read(upload['chunk_bytes']):
                    call('archive_append',{'upload_id':upload['upload_id'],'offset':offset,'data':base64.b64encode(raw).decode()});offset+=len(raw)
            call('archive_import_start',{'operation_id':upload['operation_id']})
            while server.service.archives.worker.active:time.sleep(.2)
            receipt=call('archive_import_status',{'operation_id':upload['operation_id']});assert receipt['outcome']=='completed',receipt
            out['source_archive_sha256']=receipt['archive_sha256'];out['source_archive_bytes']=source.stat().st_size
        with server.service.store.connect() as db:
            before={row['id']:row['result_hash'] for row in db.execute("SELECT id,result_hash FROM runs WHERE status='completed'")}
            normalized=db.execute('SELECT count(*) FROM series').fetchone()[0]
            out['import_receipts_before']=[tuple(row) for row in db.execute('SELECT operation_id,phase,outcome,archive_sha256 FROM archive_imports ORDER BY operation_id')]
        params={'strategy':project['strategy'],'profile':project['profile'],'run_ids':list(before)}
        samples.clear();gc.collect();sampler.start();started=time.monotonic()
        cancel_id=uuid.uuid4().hex;call('archive_export_start',{'request_id':cancel_id,**params});time.sleep(.15);probe()
        cancel_tick=time.monotonic();call('archive_export_cancel',{'export_id':cancel_id})
        while server.service.exports.active and time.monotonic()-cancel_tick<5:
            call('archive_export_status',{'export_id':cancel_id});time.sleep(.02)
        out['cancellation_quiescence_seconds']=time.monotonic()-cancel_tick
        assert server.service.exports.active is None
        assert call('archive_export_status',{'export_id':cancel_id})['status']=='cancelled'
        ident=uuid.uuid4().hex;call('archive_export_start',{'request_id':ident,**params})
        assert call('archive_export_start',{'request_id':ident,**params})['export_id']==ident
        while True:
            status=call('archive_export_status',{'export_id':ident})
            if not phases or phases[-1]['phase']!=status['phase']:phases.append({'phase':status['phase'],'elapsed_seconds':time.monotonic()-started})
            probe()
            if status['status'] not in ('running','cancel_requested'):break
            time.sleep(.2)
        assert status['status']=='completed',status
        d=status['descriptor'];out['descriptor']=d;out['phases']=phases;out['export_total_seconds']=time.monotonic()-started
        output=destination/'verified-download.ttproject.zip';digest=hashlib.sha256();download_tick=time.monotonic()
        with output.open('xb') as stream:
            for offset in range(0,d['bytes'],CHUNK_BYTES):
                size=min(CHUNK_BYTES,d['bytes']-offset);raw=post('/api/export/chunk',{'export_id':ident,'filename':d['filename'],'offset':offset,'size':size},'chunk')
                assert len(raw)==size and hashlib.sha256(raw).hexdigest()==d['chunk_sha256'][offset//CHUNK_BYTES]
                stream.write(raw);digest.update(raw)
                if offset//CHUNK_BYTES%8==0:probe()
        assert output.stat().st_size==d['bytes'] and digest.hexdigest()==d['sha256']
        out['download_seconds']=time.monotonic()-download_tick
        get=server.get_request
        def small_send_buffer():
            connection,address=get();connection.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,4096);return connection,address
        server.get_request=small_send_buffer
        stalled=socket.socket();stalled.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,1024);stalled.connect(('127.0.0.1',server.server_port))
        body=json.dumps({'export_id':ident,'filename':d['filename'],'offset':0,'size':min(CHUNK_BYTES,d['bytes'])}).encode()
        lines=''.join(f'{key}: {value}\r\n' for key,value in headers.items())
        stalled.sendall((f'POST /api/export/chunk HTTP/1.1\r\nHost: 127.0.0.1:{server.server_port}\r\n'+lines+f'Content-Length: {len(body)}\r\n\r\n').encode()+body)
        time.sleep(.1);tick=time.monotonic();probe();out['stalled_receiver_probe_seconds']=time.monotonic()-tick;stalled.close();server.get_request=get
        out['peak_parent_client_and_descendants_rss_bytes']=peak
        with server.service.store.connect() as db:
            after={row['id']:row['result_hash'] for row in db.execute("SELECT id,result_hash FROM runs WHERE status='completed'")}
            out['integrity_check']=db.execute('PRAGMA integrity_check').fetchone()[0];out['foreign_key_check']=[tuple(row) for row in db.execute('PRAGMA foreign_key_check')]
            out['native_trust_count']=db.execute('SELECT count(*) FROM native_trust').fetchone()[0]
            receipts=[tuple(row) for row in db.execute('SELECT operation_id,phase,outcome,archive_sha256 FROM archive_imports ORDER BY operation_id')]
            assert before==after and db.execute('SELECT count(*) FROM series').fetchone()[0]==normalized and receipts==out['import_receipts_before']
        out['run_hashes_unchanged']=after;out['normalized_rows_unchanged']=normalized
        out['latencies_seconds']={key:{'samples':len(values),'max':max(values),'p95':sorted(values)[min(len(values)-1,int(len(values)*.95))],'values':values} for key,values in samples.items()}
        out['assertions']={'request_target':all(max(values)<=2 for values in samples.values()),'quiescence_target':out['cancellation_quiescence_seconds']<=5,'stalled_receiver_target':out['stalled_receiver_probe_seconds']<=2,'exact_count_and_hash':True,'immutable_results_and_receipts':True,'memory_sampled':peak>0}
        assert all(out['assertions'].values()),out['assertions']
    finally:
        stop.set()
        if sampler.ident is not None:sampler.join()
        server.shutdown();thread.join();server.server_close()
    (destination/'measurement.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({key:value for key,value in out.items() if key not in ('descriptor','latencies_seconds','run_hashes_unchanged')},indent=2))
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('destination',type=Path);source=parser.add_mutually_exclusive_group(required=True);source.add_argument('--archive',type=Path);source.add_argument('--workspace',type=Path);args=parser.parse_args()
    measure(args.destination,args.archive,args.workspace)
