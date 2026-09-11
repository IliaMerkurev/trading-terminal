"""Development commands; no trading or credential handling."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path

from terminal.data import BybitClient,DatasetStore,prepare_dataset


def utc(value):
    parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    if parsed.tzinfo is None:
        parsed=parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    download=commands.add_parser("download")
    download.add_argument("--market",choices=("spot","linear"),required=True)
    download.add_argument("--symbol",required=True)
    download.add_argument("--start",type=utc,required=True,help="Inclusive ISO UTC time")
    download.add_argument("--end",type=utc,required=True,help="Exclusive ISO UTC time")
    inspect=commands.add_parser("dataset")
    inspect.add_argument("id")
    args=parser.parse_args()
    root=Path(".local-data")
    store=DatasetStore(root/"datasets")
    if args.command=="download":
        manifest=prepare_dataset(BybitClient(root/"http-cache"),store,args.market,args.symbol,args.start,args.end)
    else:
        manifest,*_=store.load(args.id)
    print(json.dumps({"id":manifest["id"],"market":manifest["market"],"symbol":manifest["symbol"],
                      "range":manifest["range"],"coverage":manifest["coverage"]},indent=2))


if __name__=="__main__":
    main()
