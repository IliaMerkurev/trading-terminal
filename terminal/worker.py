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
    from terminal.storage import identifier
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
        result=run_backtest(bars,profile,GraphEvaluator(snapshot["strategy"]),marks=marks,funding=funding,progress=progress)
        result["manifest_sha256"]=snapshot["snapshot_sha256"]
        write_new(directory/"worker-result.json",canonical(result))
    except Exception as exc:
        write_new(directory/"worker-error.json",canonical({"version":1,"type":"error","message":str(exc)[:2000]}))
        raise


if __name__=="__main__":
    main()
