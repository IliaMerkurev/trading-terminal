"""New-only synthetic displayed-period acceptance, never ordinary user data."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.prepare_observation_fixture import create_fixture as observation_fixture
from terminal.service import AppService


def create_fixture(root):
    root=Path(root)
    fixture=observation_fixture(root)  # Refuses an existing root.
    service=AppService(root)
    try:
        params={k:fixture[k] for k in ('dataset_id','profile','selections','start','end')}
        params.update(interval='daily',spot_dataset_id=None)
        manager=service.library_batches
        batch=manager.start(expected_contract=manager.preview(**params)['contract_sha256'],**params)['batch_id']
        thread=manager.active['thread'];thread.join(60)
        if thread.is_alive():raise RuntimeError('Synthetic acceptance worker did not finish within 60 seconds')
        report=manager.get(batch)
        if report['status']!='completed' or any(row['status']!='completed' for row in report['rows']):
            raise RuntimeError('Synthetic acceptance comparison did not complete')
        fixture.update(batch_id=batch,run_id=report['rows'][0]['run_id'],
            never_run_range=[fixture['end'],fixture['end']+24*3600],
            immutable_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('runs/*/*.json')})
        with service.store.connect() as db:
            fixture['initial_counts']={table:db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('runs','library_batches','observations','observation_revisions','observation_batches')}
            fixture['initial_evidence']={r['kind']:r['n'] for r in db.execute('SELECT kind,count(*) AS n FROM research_evidence GROUP BY kind')}
            fixture['batch_snapshot_sha256']=hashlib.sha256(db.execute('SELECT snapshot FROM library_batches WHERE id=?',(batch,)).fetchone()[0].encode()).hexdigest()
        fixture['expected'].update(initial_runs=fixture['initial_counts']['runs'],initial_batches=fixture['initial_counts']['library_batches'])
        (root/'synthetic-display-fixture.json').write_text(json.dumps(fixture,indent=2)+'\n')
        return fixture
    finally:service.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path)
    print(json.dumps(create_fixture(parser.parse_args().root),indent=2))
