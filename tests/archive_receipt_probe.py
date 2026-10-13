"""Deterministic crash barriers, only for isolated test workspaces."""
import json
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from terminal.archive_receipts import ArchiveReceipts
from terminal.data import write_new
from terminal.jobs import JobManager
from tests.archive_receipt_fixtures import archive


def main():
    root,stage = sys.argv[1:]
    jobs = JobManager(root);ledger = ArchiveReceipts(jobs.store)
    raw,project,docs = archive();operation = 'f'*32
    def barrier():
        print(json.dumps({'operation_id':operation,'stage':stage,'receipt':ledger.status(operation)}),flush=True)
        sys.stdin.buffer.read(1)
        raise RuntimeError('The parent should terminate this fixture')
    ledger.begin(operation,len(raw));ledger.claim(operation);ledger.reserve(operation,raw,project,docs)
    if stage=='reserved':barrier()
    def write(path,data):
        write_new(path,data)
        if stage=='snapshot' and Path(path).name=='snapshot.json':barrier()
    with patch('terminal.archive_receipts.write_new',side_effect=write):
        for ordinal,source in enumerate(project['runs']):
            ledger.publish_run(operation,ordinal,docs[f'runs/{source}/snapshot.json'],docs[f'runs/{source}/result.json'])
            if ordinal==0 and stage=='first_run':barrier()
    ledger.publish_strategy(operation,project['strategy'],project['profile'])
    if stage=='completed':barrier()


if __name__=='__main__':main()
