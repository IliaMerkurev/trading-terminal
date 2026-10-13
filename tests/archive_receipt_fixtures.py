"""Small independently authored archive documents; no calculations or downloads."""
import io
import zipfile
from terminal.data import canonical, digest
from terminal.graph import example_graph
from terminal.profile import Profile
from terminal.storage import SERIES


def documents(count=2):
    profile = Profile(primary_minutes=1).snapshot()
    strategy = {'name':'Independent receipt fixture','kind':'graph','document':{'graph':example_graph(),'layout':{}}}
    docs = {}; ids = [f'{i+1:032x}' for i in range(count)]
    for i, ident in enumerate(ids):
        snapshot = {'schema_version':1,'strategy':example_graph(),'profile':profile,
            'dataset':{'id':f'{i+1:064x}','content_sha256':f'{i+17:064x}','range':[0,120],
                       'source':'Independent synthetic receipt fixture','coverage':{'trade':{'count':2,'complete':True}}},
            'runtime':{'fixture':'independently authored','case':i}}
        snapshot['snapshot_sha256'] = digest(snapshot)
        result = {kind:[] for kind in SERIES}
        result.update(schema_version=1,status='completed',manifest_sha256=snapshot['snapshot_sha256'],profile=profile,
            engine='nautilus_trader',engine_version='1.231.0',metric_version=1,history_omitted=True,
            metrics={'final_equity':str(1000+i),'net_pnl':str(i),'max_drawdown':'0','trade_count':0,'win_rate':None,'fees':'0','funding':'0'},
            equity=[{'time_ns':60_000_000_000,'equity':str(1000+i)},{'time_ns':120_000_000_000,'equity':str(1000+i)}],
            indicators=[{'time':60,'values':{'fixture':i+1}},{'time':120,'values':{'fixture':i+2}}])
        docs[f'runs/{ident}/snapshot.json'] = snapshot
        docs[f'runs/{ident}/result.json'] = result
    project = {'schema_version':1,'strategy':strategy,'profile':profile,'runs':ids,'files':{name:digest(value) for name,value in docs.items()},'history_included':False}
    docs['project.json'] = project
    return project, docs


def archive(count=2, *, compression=zipfile.ZIP_STORED):
    project, docs = documents(count)
    output = io.BytesIO()
    with zipfile.ZipFile(output,'w',compression=compression) as zipped:
        for name,value in docs.items():
            zipped.writestr(name,canonical(value))
    return output.getvalue(),project,docs


def sentinels(store):
    project,docs = documents(1)
    ident = store.create(docs[f"runs/{project['runs'][0]}/snapshot.json"])
    store.status(ident,'running');store.complete(ident,docs[f"runs/{project['runs'][0]}/result.json"])
    strategy = store.save_strategy('Prior saved strategy','graph',project['strategy']['document'],profile=project['profile'])
    return ident,strategy
