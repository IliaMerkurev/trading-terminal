"""One bounded Linux/HTTP supported-load pass on disposable synthetic workspaces.

Predeclared local goals: start/status/cancel acknowledgement <=2 s; cancellation
quiescence <=5 s. These are development targets, not a cross-platform guarantee.
Every admitted dimension is tested separately; never shrink archive limits.
"""
import argparse
import base64
import hashlib
import http.client
import json
from pathlib import Path
import sys
import threading
import time
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from terminal.browser_host import BrowserServer
from terminal.archives import CHUNK
from tests.archive_receipt_fixtures import documents


def rss_tree(pid):
    # Some procfs implementations omit task/*/children. Derive the owned tree
    # from PPid instead; inaccessible samples are reported as missing, not zero.
    processes={}
    for path in Path('/proc').glob('[0-9]*/status'):
        try:
            fields={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in path.read_text().splitlines() if ':' in line}
            processes[int(path.parent.name)]=(int(fields['PPid']),int(fields.get('VmRSS','0 kB').split()[0])*1024)
        except (OSError,ValueError,KeyError):continue
    if pid not in processes:return None
    owned={pid}
    while True:
        more={child for child,(parent,_) in processes.items() if parent in owned}-owned
        if not more:break
        owned|=more
    return sum(processes[child][1] for child in owned)


def measure(source,entry,destination):
    root=destination/entry['mode'];root.mkdir();dist=root/'dist';dist.mkdir();(dist/'index.html').write_text('<title>Synthetic import load</title>')
    server=BrowserServer(root/'workspace',dist);thread=threading.Thread(target=server.serve_forever);thread.start()
    durations={};peak=0;stop=threading.Event();progress=[];started=time.monotonic();out={**entry,'targets_seconds':{'request':2,'quiescence':5}}
    import os
    def sample():
        nonlocal peak
        while not stop.wait(.05):
            sampled=rss_tree(os.getpid())
            if sampled is not None:peak=max(peak,sampled)
    sampler=threading.Thread(target=sample);sampler.start()
    def call(command,params=None):
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=20);tick=time.monotonic()
        try:
            conn.request('POST','/api/request',json.dumps({'version':1,'id':command,'command':command,'params':params or {}}),headers)
            reply=json.loads(conn.getresponse().read())
            if reply['type']!='result':raise RuntimeError(reply['error']['message'])
            return reply['result']
        finally:
            durations.setdefault(command,[]).append(time.monotonic()-tick);conn.close()
    try:
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
        conn.request('GET','/api/session',headers={'Sec-Fetch-Site':'same-origin','X-Terminal-Bootstrap':'1'})
        token=json.loads(conn.getresponse().read())['token'];conn.close()
        headers={'Origin':server.origin,'Sec-Fetch-Site':'same-origin','Content-Type':'application/json','X-Terminal-Session':token}
        op=call('archive_begin',{'size':entry['zip_bytes']})['operation_id'];out['operation_id']=op
        with (source/entry['filename']).open('rb') as stream:
            offset=0
            while chunk:=stream.read(CHUNK):
                call('archive_append',{'upload_id':op,'offset':offset,'data':base64.b64encode(chunk).decode()});offset+=len(chunk)
        call('archive_import_start',{'operation_id':op});deadline=time.monotonic()+300;cancelled=False;resumed=False;write_id=None
        project,_=documents(0)
        while time.monotonic()<deadline:
            status=call('archive_import_status',{'operation_id':op});control=status['execution']
            progress.append({key:control[key] for key in ('phase','state','staged_rows','total_rows')})
            call('scheduler_status');call('list_runs')
            # Exercise a foreground writer through the deliberately serialized host.
            write_id=call('save_graph',{'name':'Synthetic load navigation sentinel','graph':project['strategy']['document']['graph'],'layout':{},'strategy_id':write_id,'profile':project['profile']})['strategy_id']
            if entry['mode']=='expanded' and not cancelled and control['phase']=='staging' and control['staged_rows']>0:
                mark=time.monotonic();cancel=call('archive_import_cancel',{'operation_id':op,'attempt_key':control['attempt_key']});out['cancel_ack']=cancel['status'];cancelled=True
                while server.service.archives.worker.active and time.monotonic()-mark<10:time.sleep(.01)
                out['cancel_quiescence_seconds']=time.monotonic()-mark
                status=call('archive_import_status',{'operation_id':op});out['cancel_outcome']=status['outcome'];out['reserved_ids_before_resume']=[item['destination_id'] for item in status['items']]
                call('archive_import_resume',{'operation_id':op,'expected_revision':status['revision'],'attempt_key':uuid.uuid4().hex});resumed=True
            elif control['state']=='terminal' and server.service.archives.worker.active is None:
                out['outcome']=status['outcome'];out['termination_reason']=control['termination_reason'];out['reserved_ids']=[item['destination_id'] for item in status['items']];break
            time.sleep(.05)
        else:raise TimeoutError('Bounded 300-second import observation expired')
        with server.service.store.connect() as db:
            out['integrity_check']=db.execute('PRAGMA integrity_check').fetchone()[0];out['foreign_key_check']=[list(row) for row in db.execute('PRAGMA foreign_key_check')]
            out['native_trust_count']=db.execute('SELECT count(*) FROM native_trust').fetchone()[0]
            out['normalized_rows']=db.execute('SELECT count(*) FROM series').fetchone()[0]
        out['published_hashes']={}
        for item in status['items']:
            if item['kind']=='run' and item['publication_state']=='published':
                file=server.service.store.directory(item['destination_id'])/'result.json';h=hashlib.sha256()
                with file.open('rb') as stream:
                    for chunk in iter(lambda:stream.read(CHUNK),b''):h.update(chunk)
                out['published_hashes'][item['destination_id']]=h.hexdigest();assert h.hexdigest()==item['expected_result_sha256']
        out['max_write_transaction_seconds']=max([json.loads(line)['max_write_seconds'] for path in (root/'workspace'/'imports').glob('*.timings.jsonl') for line in path.read_text().splitlines()] or [0])
        out['assertions']={'completed':out['outcome']=='completed','rows_match':out['normalized_rows']==entry['expected_normalized_rows'],'same_ids_after_resume':not resumed or out['reserved_ids']==out['reserved_ids_before_resume'],'memory_measured':out.get('peak_parent_and_descendants_rss_bytes',peak)>0,'request_target':all(max(durations.get(command,[0]))<=2 for command in ('archive_import_start','archive_import_resume','archive_import_status','archive_import_cancel','save_graph','list_runs','scheduler_status')),'quiescence_target':out.get('cancel_quiescence_seconds',0)<=5}
    except Exception as exc:out['failure']=type(exc).__name__+': '+str(exc)
    finally:
        stop.set();sampler.join();server.shutdown();thread.join(10);server.server_close()
        out['total_seconds']=time.monotonic()-started;out['peak_parent_and_descendants_rss_bytes']=peak
        out['latencies_seconds']={key:{'samples':len(values),'max':max(values)} for key,values in durations.items()}
        out['progress_observed']=progress[::max(1,len(progress)//20)]
        (root/'measurement.json').write_text(json.dumps(out,indent=2)+'\n')
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('fixtures',type=Path);parser.add_argument('destination',type=Path);args=parser.parse_args()
    args.destination.mkdir(parents=True,exist_ok=False)
    results=[]
    for entry in json.loads((args.fixtures/'manifest.json').read_text()):
        result=measure(args.fixtures,entry,args.destination);results.append(result)
        (args.destination/'measurement.json').write_text(json.dumps(results,indent=2)+'\n')
        print(json.dumps({k:result.get(k) for k in ('mode','outcome','failure','assertions','total_seconds','peak_parent_and_descendants_rss_bytes','max_write_transaction_seconds','latencies_seconds')}),flush=True)
        if result.get('failure') or not all(result.get('assertions',{}).values()):break
