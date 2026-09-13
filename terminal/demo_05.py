"""Prepare small synthetic 0.5 examples in a NEW, separate data root."""
import argparse
import json
from pathlib import Path
import time

from terminal.graph import example_graph
from terminal.profile import Profile
from terminal.series import Candle
from terminal.service import AppService


def prepare(root):
    root=Path(root).resolve()
    ordinary=Path(__file__).resolve().parents[1]/'.local-data'
    if root==ordinary or root.exists():
        raise ValueError('Use a new isolated data directory; existing data is never replaced')
    service=AppService(root)
    def wait():
        deadline=time.monotonic()+180
        while service.experiments.active is not None:
            if time.monotonic()>deadline:raise RuntimeError('Demonstration phase exceeded 180 seconds')
            time.sleep(.1)
    try:
        config={'max_entries':4,'repeated_entry':'scale','scale_allocation_percent':'10',
                'dca':[{'distance':'.02','allocation_percent':'10'}],
                'partial_take':[{'distance':'.03','fraction':'.25'},{'distance':'.06','fraction':'.75'}]}
        profile=Profile(version=2,primary_minutes=1,fee_rate='.001',position_management=config).snapshot()
        graph=example_graph()
        strategy=service.store.save_strategy('Synthetic 0.5: managed position experiments','graph',{'graph':graph,'layout':{}},profile=profile)
        live_profile=Profile(version=2,primary_minutes=60,position_management=config).snapshot()
        live_strategy=service.store.save_strategy('0.5 public H1 monitoring / manual PAPER example','graph',{'graph':graph,'layout':{}},profile=live_profile)
        start=1735689600
        bars=[Candle(start+i*60,100+i%12,103+i%12,97+i%12,100+i%12,100) for i in range(240)]
        dataset=service.datasets.save('spot','BTCUSDT',start,start+240*60,bars,[],{},metadata={},provenance=[],source='Synthetic 0.5 fixtures; not exchange history')
        experiment=service.experiments.start(strategy_id=strategy,dataset_id=dataset['id'],profile=profile,
            is_range=[start+30*60,start+150*60],oos_range=[start+180*60,start+240*60],
            axes=[{'key':'pm.scale_allocation_percent','values':['5','10']}])['experiment_id']
        wait()
        result=service.experiments.get(experiment)
        if result['status']!='completed' or any(row['status']!='completed' for row in result['rows']):
            raise RuntimeError('A synthetic demonstration run failed')
        frozen=service.experiments.freeze(experiment,0)
        service.experiments.validate(frozen['validation_id']);wait()
        validation=service.experiments.get(experiment)['validations'][0]
        if validation['status']!='completed':raise RuntimeError('Synthetic later-period validation failed')
        report={'source':'Synthetic fixtures; no exchange history or owner data',
                'strategy_id':strategy,'live_strategy_id':live_strategy,'experiment_id':experiment,
                'combinations':2,'predeclared_candidate_ordinal':0,'validation_run_id':validation['run_id']}
        (root/'synthetic-05-demo.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        return report
    finally:service.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,required=True)
    args=parser.parse_args()
    if not args.data_root.is_absolute():parser.error('--data-root must be absolute')
    print(json.dumps(prepare(args.data_root),indent=2))
