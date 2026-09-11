"""Verify a previously downloaded snapshot offline; no network call is made."""
import argparse
import json
from pathlib import Path

from terminal.data import DatasetStore,metadata_profile_fields,run_manifest
from terminal.graph import GraphEvaluator,example_graph
from terminal.profile import Profile
from terminal.simulation import run_backtest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("dataset")
    args=parser.parse_args()
    store=DatasetStore(".local-data/datasets")
    manifest,*_=store.load(args.dataset)
    fields=metadata_profile_fields(manifest)
    profile=Profile(**fields,leverage="3" if manifest["market"]=="linear" else "1",evaluation="intrabar")
    _,trade,marks,funding=store.for_run(args.dataset,profile)
    strategy=example_graph()
    snapshot=run_manifest(strategy,profile,manifest)
    a=run_backtest(trade,profile,GraphEvaluator(strategy),marks=marks,funding=funding)
    b=run_backtest(trade,profile,GraphEvaluator(strategy),marks=marks,funding=funding)
    if a!=b: raise AssertionError("Offline repeat differs")
    print(json.dumps({"dataset":args.dataset,"snapshot":snapshot["snapshot_sha256"],"identical":True,
                      "metrics":a["metrics"]},indent=2))


if __name__=="__main__":
    main()
