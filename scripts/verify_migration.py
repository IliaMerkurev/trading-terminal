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
    def rows(root,tables=None):
        with sqlite3.connect((root/'terminal.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
            names=tables or [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            result={}
            for name in names:
                quoted='"'+name.replace('"','""')+'"'
                checksum=hashlib.sha256();count=0
                for row in db.execute(f'SELECT * FROM {quoted} ORDER BY rowid'):
                    checksum.update(json.dumps(row,separators=(',',':'),default=str).encode());checksum.update(b'\n');count+=1
                result[name]={'rows':count,'sha256':checksum.hexdigest()}
            return result
    before=rows(source)
    service=AppService(destination)
    try:
        after=rows(destination,list(before))
        if before!=after:raise RuntimeError('Migration changed existing records')
        for run in service.store.recent():
            if run['status']=='completed':service.store.result(run['id'])
        with service.store.connect() as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('SQLite integrity check failed')
        report={'result':'passed','runs_preserved':before['runs']['rows'],'strategies_preserved':before['strategies']['rows'],'trust_records_preserved':before['native_trust']['rows'],'existing_tables_preserved':before,'result_checksums':'verified','migration':'additive research/live/paper tables'}
        (destination/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report))
    finally:service.close()


if __name__=='__main__':main()
