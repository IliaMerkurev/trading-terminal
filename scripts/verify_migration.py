"""Verify additive migrations on a new copy of a consistent local backup."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from terminal.service import AppService


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args();source=args.backup.resolve();destination=args.destination.resolve()
    if destination.exists():parser.error('Destination must be new; existing files are preserved')
    destination.mkdir(parents=True)
    with sqlite3.connect((source/'terminal.sqlite3').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(destination/'terminal.sqlite3') as dst:src.backup(dst)
    if (source/'runs').exists():shutil.copytree(source/'runs',destination/'runs')
    def rows(root):
        with sqlite3.connect((root/'terminal.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
            return {'runs':db.execute('SELECT * FROM runs ORDER BY id').fetchall(),'strategies':db.execute('SELECT * FROM strategies ORDER BY id').fetchall(),'trust':db.execute('SELECT * FROM native_trust ORDER BY identity').fetchall()}
    before=rows(source)
    service=AppService(destination)
    try:
        after=rows(destination)
        if before!=after:raise RuntimeError('Migration changed existing records')
        for run in service.store.recent():
            if run['status']=='completed':service.store.result(run['id'])
        with service.store.connect() as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('SQLite integrity check failed')
        report={'result':'passed','runs_preserved':len(before['runs']),'strategies_preserved':len(before['strategies']),'trust_records_preserved':len(before['trust']),'result_checksums':'verified','migration':'additive experiment tables'}
        (destination/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report))
    finally:service.close()


if __name__=='__main__':main()
