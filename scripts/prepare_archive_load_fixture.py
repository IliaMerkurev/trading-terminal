"""Stream independently authored semantic normalized series near archive limits.

Engineering fixtures only. No market acquisition, strategy execution or source
padding. Output must be outside the repository and the destination must be new.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from terminal.data import canonical,digest
from tests.archive_receipt_fixtures import documents


def file_hash(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(256*1024),b''):value.update(chunk)
    return value.hexdigest()


def result_file(path,result,target,wide,entropy=False):
    rows=0;largest=0
    names=['s_'+base64.urlsafe_b64encode(hashlib.sha256(f'synthetic indicator {i}'.encode()).digest()[:16]).decode().rstrip('=') for i in range(4096)] if entropy else []
    with path.open('wb') as out:
        out.write(b'{')
        for ordinal,key in enumerate(sorted(result)):
            if ordinal:out.write(b',')
            out.write(canonical(key)+b':')
            if key!='indicators':out.write(canonical(result[key]));continue
            out.write(b'[')
            if wide:
                out.write(b'{"time":60,"values":{');index=0;start=out.tell()
                while out.tell()<target-8192:
                    if index:out.write(b',')
                    value=((index*1664525+1013904223)%4294967296)/1024
                    out.write(canonical(f'synthetic_{index:07d}')+b':'+canonical(value));index+=1
                out.write(b'}}');rows=1;largest=out.tell()-start+22
            else:
                while (rows<71 if entropy else out.tell()<target-8192):
                    if rows:out.write(b',')
                    point={'time':(rows+1)*60,'values':{f'synthetic_{i:02d}':((rows*1664525+i*1013904223)%4294967296)/1024 for i in range(32)}}
                    if entropy:point['values']={name:int.from_bytes(hashlib.sha256(f'synthetic value {result["manifest_sha256"]} {rows} {index}'.encode()).digest()[:7],'big')>>4 for index,name in enumerate(names)}
                    raw=canonical(point);out.write(raw);rows+=1;largest=max(largest,len(raw))
            out.write(b']')
        out.write(b'}')
    return rows,largest


def prepare(root,mode):
    runs=8 if mode in ('zip','expanded','export') else 1
    target=(63*1024*1024 if mode=='zip' else 127*1024*1024 if mode=='expanded' else 64*1024*1024-65536)//runs
    project,docs=documents(runs);parts=root/mode;parts.mkdir()
    manifest={};points=0;largest=0;counts={}
    for name,doc in docs.items():
        if name=='project.json':continue
        path=parts/name;path.parent.mkdir(parents=True,exist_ok=True)
        if name.endswith('/result.json'):
            count,row=result_file(path,doc,target,mode=='row',mode=='export');points+=count;largest=max(largest,row);counts[name.split('/')[1]]=count
        else:path.write_bytes(canonical(doc))
        manifest[name]=file_hash(path)
    for source,count in counts.items():
        snapshot=docs[f'runs/{source}/snapshot.json']
        previous=snapshot['snapshot_sha256']
        snapshot['dataset']['range']=[0,max(count+1,3)*60]
        snapshot['dataset']['coverage']['trade']['count']=max(count,2)
        snapshot['snapshot_sha256']=digest({key:value for key,value in snapshot.items() if key!='snapshot_sha256'})
        snapshot_path=parts/f'runs/{source}/snapshot.json';snapshot_path.write_bytes(canonical(snapshot))
        result_path=parts/f'runs/{source}/result.json'
        with result_path.open('r+b') as stream:
            start=max(0,result_path.stat().st_size-8192);stream.seek(start);tail=stream.read()
            old=b'"manifest_sha256":"'+previous.encode()+b'"'
            new=b'"manifest_sha256":"'+snapshot['snapshot_sha256'].encode()+b'"'
            assert tail.count(old)==1
            stream.seek(start);stream.write(tail.replace(old,new))
        manifest[f'runs/{source}/snapshot.json']=file_hash(snapshot_path)
        manifest[f'runs/{source}/result.json']=file_hash(result_path)
    project['files']=manifest;(parts/'project.json').write_bytes(canonical(project))
    output=root/f'{mode}.ttproject.zip'
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED if mode=='zip' else zipfile.ZIP_DEFLATED,compresslevel=None if mode=='zip' else 6) as zipped:
        for path in sorted(parts.rglob('*.json')):zipped.write(path,path.relative_to(parts).as_posix())
    with zipfile.ZipFile(output) as zipped:
        entries=zipped.infolist();expanded=sum(e.file_size for e in entries)
        assert output.stat().st_size<=64*1024*1024 and expanded<=128*1024*1024 and max(e.file_size for e in entries)<=64*1024*1024
    return {'mode':mode,'filename':output.name,'sha256':file_hash(output),'zip_bytes':output.stat().st_size,'expanded_bytes':expanded,'maximum_entry_bytes':max(e.file_size for e in entries),'indicator_rows':points,'maximum_normalized_row_bytes':largest,'runs':runs,'expected_normalized_rows':points+2*runs,'description':'Deterministic invented numeric indicator values and equity; no market or financial calculation evidence'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('destination',type=Path);parser.add_argument('--mode',choices=['zip','expanded','entry','row','export']);args=parser.parse_args()
    args.destination.mkdir(parents=True,exist_ok=False)
    rows=[prepare(args.destination,mode) for mode in ([args.mode] if args.mode else ('zip','expanded','entry','row'))]
    (args.destination/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(rows,indent=2))
