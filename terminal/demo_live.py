"""Small independent synthetic journals; never exchange history or user data."""
import argparse
import json
from pathlib import Path

from terminal.data import canonical
from terminal.graph import example_graph
from terminal.live_store import LiveSession
from terminal.paper_journal import PaperJournal
from terminal.profile import Profile
from terminal.series import Candle
from terminal.service import AppService


def prepare(root):
    root=Path(root).resolve()
    ordinary=Path(__file__).resolve().parents[1]/'.local-data'
    if root==ordinary:raise ValueError('Use a separate synthetic demonstration data root')
    marker=root/'synthetic-live-demo.json'
    if marker.exists():return json.loads(marker.read_text(encoding='utf8'))
    service=AppService(root)
    report=[]
    try:
        cases=[('Synthetic: observed paper golden',Profile(primary_minutes=1),[100,100,110,120,90,90],2,[(180,'entry_long'),(300,'exit_long')]),
               ('Synthetic: forming H1 signals',Profile(primary_minutes=60,evaluation='intrabar'),[100]*60+[110]*30+[90]*30,60,[(3660,'entry_long'),(5460,'exit_long')]),
               ('Synthetic: closed H1 signals',Profile(primary_minutes=60),[100]*60+[110]*30+[90]*30,60,[(7200,'exit_long')])]
        for index,(name,profile,prices,warmup,expected) in enumerate(cases):
            graph=example_graph()
            strategy=service.store.save_strategy(name,'graph',{'graph':graph,'layout':{}},profile=profile.snapshot())
            sid=service.live.journal.create(graph,profile,strategy,name)
            with service.store.connect() as db:db.execute('INSERT INTO live_options VALUES(?,?)',(sid,canonical({'paper':index==0,'channels':[],'warmup_minutes':max(100,warmup)}).decode()))
            session=LiveSession(service.live.journal,sid)
            paper=PaperJournal(service.store,sid,profile,None) if index==0 else None
            try:
                for minute,price in enumerate(prices):
                    session.ingest(Candle(minute*60,price,price,price,price,1),(minute+1)*60000,'warmup' if minute<warmup else 'recovered')
                    if paper and minute>=warmup:
                        observed=[100,105,110,110][minute-warmup]
                        paper.append({'provider_ms':(minute+1)*60000+500,'observed_ms':(minute+1)*60000+500,'price':str(observed),'mark':None},session.latest['signals'])
                        paper.process()
                events=list(reversed(service.live.journal.events(sid)))
                actual=[(e['time'],e['type']) for e in events]
                if actual!=expected:raise AssertionError(f'Synthetic signal mismatch: {name}')
                replay=session.verify_replay()
                if not replay['match']:raise AssertionError('Synthetic live/replay mismatch')
                result={'name':name,'session_id':sid,'expected_events':[list(e) for e in expected],'replay':replay}
                if paper:
                    result['paper_equity']=paper.snapshot()['equity']
                    if result['paper_equity']!='1009.79':raise AssertionError('Independent spot account golden mismatch')
                report.append(result)
                service.live.journal.state(sid,'PAUSED','Synthetic recorded fixture; no market connection was opened')
            finally:
                if paper:paper.close()
        marker.write_text(json.dumps(report,indent=2),encoding='utf8')
        return report
    finally:service.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,required=True)
    args=parser.parse_args()
    if not args.data_root.is_absolute():parser.error('An absolute isolated data root is required')
    print(json.dumps(prepare(args.data_root),indent=2))


if __name__=='__main__':main()
