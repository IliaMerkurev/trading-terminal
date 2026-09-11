"""Prepare independently checked synthetic demonstrations without network access."""
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import time

from terminal.data import DatasetStore,canonical,runtime_snapshot,write_new
from terminal.jobs import JobManager
from terminal.profile import Profile
from terminal.series import Candle


def node(name,kind,inputs=None,**params):return {'id':name,'type':kind,'inputs':inputs or {},'params':params}
def graph(nodes,**outputs):return {'version':1,'nodes':nodes,'outputs':{k:outputs.get(k) for k in ('entry_long','exit_long','entry_short','exit_short')}}


def prepare(root):
    manager=JobManager(root)
    try:
        runtime=runtime_snapshot();record=manager.store.root/'demos'/f"{runtime['implementation_sha256']}.json"
        if record.exists():return json.loads(record.read_bytes())
        start=1704067200  # 2024-01-01 00:00:00 UTC, independent synthetic input.
        def dataset(prices,market='spot'):
            bars=[Candle(start+i*60,p,p,p,p,100) for i,p in enumerate(prices)]
            return manager.datasets.save(market,'BTCUSDT',start,start+len(bars)*60,bars,[],{},metadata={},provenance=[],source='Synthetic V1 verification fixture')['id']
        causal=graph([node('p','price',field='close'),node('s','sma',{'source':'p.value'},period=2),node('k','constant',value=110),node('above','compare',{'left':'s.value','right':'k.value'},operator='>'),node('below','compare',{'left':'s.value','right':'k.value'},operator='<')],entry_long='above.value',exit_long='below.value')
        simple=graph([node('p','price',field='close'),node('entry','constant',value=100),node('exit','constant',value=110),node('enter','compare',{'left':'p.value','right':'entry.value'},operator='>='),node('leave','compare',{'left':'p.value','right':'exit.value'},operator='>=')],entry_long='enter.value',exit_long='leave.value')
        short=graph([node('p','price',field='close'),node('entry','constant',value=100),node('exit','constant',value=90),node('enter','compare',{'left':'p.value','right':'entry.value'},operator='>='),node('leave','compare',{'left':'p.value','right':'exit.value'},operator='<=')],entry_short='enter.value',exit_short='leave.value')
        causal_data=dataset([100]*60+[130]*30+[90]*30)
        base=Profile(fee_rate='0')
        cases=[('Synthetic: forming H1 condition',causal,replace(base,evaluation='intrabar'),causal_data,'-30.760',1),
               ('Synthetic: closed H1 condition',causal,base,causal_data,'0',0),
               ('Synthetic: spot fees golden case',simple,Profile(primary_minutes=1),dataset([100,100,110]),'9.790',1),
               ('Synthetic: perpetual short golden case',short,Profile(market='linear',primary_minutes=1,leverage='2',allocation='50',mark_mode='last_proxy',funding_mode='assumed_zero'),dataset([100,100,90],'linear'),'9.810',1)]
        results=[]
        for name,strategy,profile,dataset_id,pnl,count in cases:
            strategy_id=manager.store.save_strategy(name,'graph',{'graph':strategy,'layout':{}},profile=profile.snapshot())
            run_id=manager.start(strategy,profile,dataset_id)
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                status=manager.status(run_id)
                if status['status'] in ('completed','failed','cancelled'):break
                time.sleep(.05)
            else:raise RuntimeError('Synthetic demo exceeded its bounded execution deadline')
            if status['status']!='completed':raise RuntimeError(f"Demo failed: {status['error']}")
            metrics=status['summary']['metrics']
            if Decimal(metrics['net_pnl'])!=Decimal(pnl) or metrics['trade_count']!=count:raise AssertionError('Independent demo golden result does not match')
            results.append({'name':name,'strategy_id':strategy_id,'run_id':run_id,'dataset_id':dataset_id,'expected_net_pnl':pnl,'expected_trades':count,'actual_metrics':metrics})
        result={'schema_version':1,'source':'Synthetic fixtures, not exchange history','runtime':runtime,'cases':results}
        write_new(record,canonical(result));return result
    finally:manager.close()


if __name__=='__main__':
    result=prepare(Path(__file__).resolve().parents[1]/'.local-data')
    print(json.dumps({'source':result['source'],'cases':[{'name':c['name'],'run_id':c['run_id'],'metrics':c['actual_metrics']} for c in result['cases']]},indent=2))
