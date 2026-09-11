"""Private worker entrypoint: stdin gate before engine/native imports."""
import json
import os
from pathlib import Path
import sys


def main():
    # Parent attaches the Windows Job Object before sending the bounded request.
    line=sys.stdin.buffer.readline(1024*1024+1)
    if len(line)>1024*1024: raise ValueError("Worker input exceeds budget")
    request=json.loads(line)
    if request.get("version")!=1 or request.get("command")!="run": raise ValueError("Invalid worker command")
    from terminal.data import DatasetStore,canonical,digest,write_new,runtime_snapshot
    from terminal.graph import GraphEvaluator
    from terminal.profile import Profile
    from terminal.simulation import run_backtest
    from terminal.storage import identifier,RunStore
    root=Path(request["root"]).resolve()
    directory=root/"runs"/identifier(request["run_id"])
    snapshot=json.loads((directory/"snapshot.json").read_bytes())
    if digest({k:v for k,v in snapshot.items() if k!="snapshot_sha256"})!=snapshot["snapshot_sha256"]:
        raise ValueError("Worker snapshot checksum mismatch")
    def progress(value):
        # Append-only progress avoids Windows rename/read sharing races.
        with (directory/"progress.jsonl").open("ab") as stream:
            stream.write(canonical({"version":1,"type":"progress","fraction":value})+b"\n")
    try:
        if runtime_snapshot()!=snapshot["runtime"]:
            raise ValueError("Runtime changed after the run snapshot was prepared")
        profile=Profile(**snapshot["profile"])
        _,bars,marks,funding=DatasetStore(root/"datasets").for_run(snapshot["dataset"]["id"],profile)
        strategy=snapshot["strategy"]
        window=snapshot.get('research',{}).get('window')
        if window:
            from terminal.experiments import validate_range
            validate_range([window['start'],window['end']],snapshot['dataset']['range'],'Trading window')
            if type(window['warmup_start']) is not int or window['warmup_start']%60 or not snapshot['dataset']['range'][0]<=window['warmup_start']<=window['start']:raise ValueError('Invalid warmup range')
            bars=[b for b in bars if window['warmup_start']<=b.time<window['end']]
            marks={t:c for t,c in marks.items() if window['warmup_start']<=t<window['end']}
            funding={t:r for t,r in funding.items() if window['start']<=t<window['end']}
        if strategy.get("engine")=="nautilus_trader":
            from terminal.native import trust_identity,load_trusted
            if not RunStore(root).is_trusted(trust_identity(strategy)):
                raise ValueError("Native source has no recorded explicit trust")
            result=run_backtest(bars,profile,None,marks=marks,funding=funding,progress=progress,
                native_factory=lambda asset:load_trusted(strategy,directory,asset.id),native_timeframes=strategy["bar_minutes"])
        else:
            result=run_backtest(bars,profile,GraphEvaluator(strategy),marks=marks,funding=funding,progress=progress,trade_start=window['start'] if window else None)
        result["manifest_sha256"]=snapshot["snapshot_sha256"]
        if snapshot.get('research',{}).get('experiment'):
            result['candles_reference']={'dataset_id':snapshot['dataset']['id'],'range':[window['start'],window['end']]}
            result['candles']=[]  # The immutable dataset is shared by all combinations.
        write_new(directory/"worker-result.json",canonical(result))
    except Exception as exc:
        write_new(directory/"worker-error.json",canonical({"version":1,"type":"error","message":str(exc)[:2000]}))
        raise


if __name__=="__main__":
    main()
