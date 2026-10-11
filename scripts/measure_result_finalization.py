"""Serialized HTTP finalization acceptance on NEW synthetic-only workspaces.

Targets: ordinary request <=2 s; cancellation is separately fault-tested <=5 s.
A normalized input is an independently authored persistence fixture, never a
calculation. --engine executes one admitted M1 graph row through the normal API.
"""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time
from unittest.mock import Mock
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from terminal.browser_host import BrowserServer
from terminal.data import canonical,runtime_snapshot
from terminal import result_finalization as finalization
from scripts.measure_archive_import import rss_tree
from tests.archive_receipt_fixtures import documents


class MeasuredLock:
    def __init__(self,lock):self.lock=lock;self.local=threading.local();self.maximum=0.;self.samples=[]
    def __enter__(self):
        self.lock.acquire()
        depth=getattr(self.local,'depth',0)
        if not depth:self.local.start=time.monotonic()
        self.local.depth=depth+1
        return self
    def __exit__(self,*args):
        self.local.depth-=1
        if not self.local.depth:
            elapsed=time.monotonic()-self.local.start;self.maximum=max(self.maximum,elapsed);self.samples.append(elapsed)
        self.lock.release()


def sha(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(256*1024),b''):value.update(chunk)
    return value.hexdigest()


def measure(destination,source,engine=False):
    destination.mkdir(parents=True,exist_ok=False);workspace=destination/'workspace'
    if engine:shutil.copytree(source/'datasets',workspace/'datasets')
    dist=destination/'dist';dist.mkdir();(dist/'index.html').write_text('<title>Synthetic finalization acceptance</title>')
    server=BrowserServer(workspace,dist);thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01});thread.start()
    headers={'Origin':server.origin,'Sec-Fetch-Site':'same-origin','Content-Type':'application/json','X-Terminal-Session':server.token}
    samples={};timeline=[];peak=0;stop=threading.Event();jobs=server.service.jobs
    lock=MeasuredLock(jobs.lock);jobs.lock=lock
    output={'synthetic_only':True,'kind':'actual_engine' if engine else 'independent_normalized_fixture','runtime':runtime_snapshot(),
        'targets_seconds':{'ordinary_request':2,'ordinary_cancel_quiescence':5},'memory_scope':'50ms sampled summed Linux RSS, parent test client/service plus managed descendants; shared pages may be counted more than once'}
    def call(command,params=None):
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=20);began=time.monotonic()
        try:
            conn.request('POST','/api/request',json.dumps({'version':1,'id':command,'command':command,'params':params or {}}),headers)
            response=conn.getresponse();reply=json.loads(response.read())
            if response.status!=200 or reply['type']!='result':raise RuntimeError(str(reply))
            return reply['result']
        finally:samples.setdefault(command,[]).append({'elapsed':time.monotonic()-began,'at':time.monotonic()});conn.close()
    def sample():
        nonlocal peak
        while not stop.wait(.05):
            value=rss_tree(os.getpid())
            if value is not None:peak=max(peak,value)
    sampler=threading.Thread(target=sample)
    writer_id=None
    try:
        project,_=documents(1)
        if engine:
            inputs=json.loads((source/'preview_inputs.json').read_text())
            frozen=server.service.library_batches.prepare(**inputs)
            assert frozen['modeled_source_candles']==2000000 and all(not row['error'] for row in frozen['rows'])
            output['preview_modeled_source_candles']=frozen['modeled_source_candles'];output['preview_workload_breakdown']=frozen['workload_breakdown']
            row=frozen['rows'][0]
            manifest=jobs.datasets.describe(inputs['dataset_id'])
            assert manifest['metadata'].get('synthetic') is True and any(p.get('kind')=='synthetic' for p in manifest['provenance'])
            assert manifest.get('interval_seconds',60)==60
            params={'strategy':row['document']['graph'],'profile':row['profile'],'dataset_id':inputs['dataset_id'],
                    'window':{'start':inputs['start'],'end':inputs['end'],'warmup_start':row['dataset']['range'][0]}}
            output['executed_row']=row['selection'];output['source_rows']=manifest['coverage']['trade']['count'];output['evaluation_rows']=(inputs['end']-inputs['start'])//60
            output['synthetic_provenance']=manifest['provenance'];output['source_physical_hashes']=manifest['files_sha256']
            output['source_dataset']=row['dataset'];sampler.start();began=time.monotonic()
            ident=call('start_window_run',params)['run_id']
        else:
            snapshot=json.loads((source/'snapshot.json').read_text());key=uuid.uuid4().hex
            assert 'synthetic' in snapshot['dataset']['source'].lower()
            output['synthetic_provenance']=snapshot['dataset']['source']
            ident=jobs.store.create(snapshot)
            with jobs.store.connect() as db:finalization.register(db,ident,key,snapshot['snapshot_sha256'])
            jobs.store.status(ident,'running');shutil.copyfile(source/'result.json',jobs.store.directory(ident)/'worker-result.json')
            output['input_result_bytes']=(source/'result.json').stat().st_size;output['input_result_sha256']=sha(source/'result.json')
            process=Mock(wait=Mock(return_value=0),poll=Mock(return_value=0))
            active={'id':ident,'generation':key,'process':process,'job':Mock(),'cancelled':False,'phase':'computing'}
            monitor=threading.Thread(target=jobs._monitor,args=(ident,process,active['job'],Mock(is_alive=Mock(return_value=False))),daemon=True)
            active['monitor']=monitor;jobs.active=active;sampler.start();began=time.monotonic();monitor.start()
        output['run_id']=ident
        while True:
            status=call('run_status',{'run_id':ident});control=status.get('finalization') or {};phase=control.get('phase',status['status'])
            point={'phase':phase,'elapsed':time.monotonic()-began,'staged_rows':control.get('staged_rows',0),'staged_bytes':control.get('staged_bytes',0),'status':status['status'],'worker_active':status['worker_active']}
            timeline.append(point)
            call('scheduler_status')
            writer_id=call('save_graph',{'name':'Synthetic foreground writer','graph':project['strategy']['document']['graph'],'layout':{},'strategy_id':writer_id,'profile':project['profile']})['strategy_id']
            if not status['worker_active']:break
            if time.monotonic()-began>900:raise TimeoutError('Synthetic calculation/finalizer exceeded acceptance window')
            time.sleep(.2)
        assert status['status']=='completed' and status['storage_failure'] is None,status
        output['elapsed_seconds']=time.monotonic()-began;output['timeline']=timeline
        stop.set();sampler.join(5)  # Postmeasurement full verification is separate.
        directory=jobs.store.directory(ident);record=jobs.store.get(ident)
        output['worker_result_sha256']=sha(directory/'worker-result.json');output['result_sha256']=sha(directory/'result.json')
        assert output['worker_result_sha256']==output['result_sha256']==record['result_hash']
        output['result_bytes']=(directory/'result.json').stat().st_size;output['summary']=record['summary'];assert record['summary']['origin']=='local'
        with jobs.store.connect() as db:
            output['series_counts']={r[0]:r[1] for r in db.execute('SELECT kind,count(*) FROM series WHERE run_id=? GROUP BY kind',(ident,))}
            output['batch_statistics']=dict(db.execute('SELECT count(*) AS batches,max(row_count) AS max_rows,max(encoded_bytes) AS max_bytes,sum(encoded_bytes) AS total_bytes FROM local_finalization_batches WHERE run_id=?',(ident,)).fetchone())
            output['native_trust_count']=db.execute('SELECT count(*) FROM native_trust').fetchone()[0]
            output['integrity']=db.execute('PRAGMA integrity_check').fetchone()[0];output['foreign_keys']=[tuple(r) for r in db.execute('PRAGMA foreign_key_check')]
            output['local_evidence']=[tuple(r) for r in db.execute('SELECT kind,route,provenance FROM research_evidence WHERE run_id=?',(ident,))]
        output['finalization']=status['finalization'];output['max_owned_lock_seconds']=lock.maximum
        output['lock_samples']=len(lock.samples);output['max_write_attempt_seconds_including_connection_and_lock_wait']=max(json.loads(line)['max_write_seconds'] for line in (directory/'finalization-timings.jsonl').read_text().splitlines())
        output['peak_parent_client_descendants_rss_bytes']=peak
        expected=json.loads((directory/'worker-result.json').read_bytes())
        with jobs.store.connect() as db:
            cursor=iter(db.execute('SELECT kind,row_index,value FROM series WHERE run_id=? ORDER BY kind,row_index',(ident,)))
            for kind in sorted(finalization.SERIES):
                assert output['series_counts'].get(kind,0)==len(expected[kind])
                for index,value in enumerate(expected[kind]):
                    actual=next(cursor,None)
                    assert actual is not None and tuple(actual)==(kind,index,canonical(value).decode())
            assert next(cursor,None) is None
        output['independent_full_normalized_verification']=True
        output['postmeasurement_verification_excluded_from_runtime_memory']=True
        output['requests']={name:{'count':len(values),'max':max(r['elapsed'] for r in values),'p95':sorted(r['elapsed'] for r in values)[min(len(values)-1,int(.95*len(values)))],'samples':values} for name,values in samples.items()}
        output['request_target_passed']=all(v['max']<=2 for v in output['requests'].values())
        assert output['request_target_passed'] and output['integrity']=='ok' and not output['foreign_keys'] and output['native_trust_count']==0
    finally:
        stop.set()
        if sampler.ident is not None:sampler.join(5)
        try:
            server.shutdown();thread.join(10);server.server_close()
        finally:
            output['closed']=not thread.is_alive() and jobs.instance_file.closed
            (destination/'measurement.json').write_text(json.dumps(output,indent=2)+'\n')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('destination',type=Path);parser.add_argument('source',type=Path);parser.add_argument('--engine',action='store_true');args=parser.parse_args()
    result=measure(args.destination,args.source,args.engine)
    print(json.dumps({key:result[key] for key in ('kind','run_id','elapsed_seconds','result_bytes','series_counts','max_write_attempt_seconds_including_connection_and_lock_wait','max_owned_lock_seconds','peak_parent_client_descendants_rss_bytes','request_target_passed','closed')},indent=2))
