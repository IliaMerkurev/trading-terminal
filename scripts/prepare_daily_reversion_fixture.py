"""New-only synthetic/local daily histories for C12/C13 browser acceptance.

Invented OHLCV and cost constraints; no exchange connection or automatic run.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from terminal.library import create_copy
from terminal.profile import Profile
from terminal.series import Candle
from terminal.service import AppService


def create_fixture(root):
    root=Path(root)
    if not root.is_absolute():raise ValueError('Use an absolute new fixture directory')
    root.mkdir(parents=True,exist_ok=False)
    service=AppService(root)
    try:
        day=86400;base=1704067200
        profile=Profile(primary_minutes=1440,execution_minutes=1440,version=2,
            allocation='100',fee_rate='.001',slippage='.01',tick_size='.5',quantity_step='.1',min_quantity='.1',
            tier_assumption='Invented synthetic/local cost and precision assumptions; no venue or profitability evidence').snapshot()
        metadata={'synthetic':True,'instrument':{'symbol':'BTCUSDT','priceFilter':{'tickSize':'0.5'},
            'lotSizeFilter':{'basePrecision':'0.1','minOrderQty':'0.1','minOrderAmt':'1',
                            'maxMarketOrderQty':'1000000000','maxOrderQty':'1000000000','maxOrderAmt':'1000000'}}}
        windows=[]
        for candidate,ident,prices,expected in [
            ('C12','double-seven-reversion',[100]*194+[120,119,118,117,116,115]+[114,113,120,121],
             {'fills':['115.5','118.5'],'quantity':'0.8','fees':'0.1872','net_pnl':'2.2128'}),
            ('C13','improved-r2-reversion',[100]*200+[120,118,116,114,112,130,131],
             {'fills':['113.5','128.5'],'quantity':'0.8','fees':'0.1936','net_pnl':'11.8064'})]:
            bars=[Candle(base+i*day,p,p+10+i%11,max(1,p-20-i%7),p,100) for i,p in enumerate(prices)]
            manifest=service.datasets.save('spot','BTCUSDT',base,base+len(bars)*day,bars,[],{},minutes=1440,
                metadata=metadata,source=f'Synthetic/local {candidate}: invented daily rule fixture (not market data)',
                provenance=[{'synthetic':True,'generator':'scripts/prepare_daily_reversion_fixture.py','version':1}])
            selection=dict(entry_id=ident,version=1,minutes=1440,parameters={})
            saved=create_copy(service.store,profile=profile,**selection)
            note=service.observations.save(None,0,manifest['id'],base+200*day,base+len(bars)*day,
                f'Synthetic/local {candidate} engineering fixture only. Expected one costed long/flat lifecycle.',
                'Any mismatch with independently specified prices, costs or signal dates fails this fixture.')
            windows.append(dict(candidate=candidate,dataset_id=manifest['id'],strategy_id=saved['strategy_id'],
                observation_id=note['id'],start=base+200*day,end=base+len(bars)*day,selection=selection,expected=expected))
        result=dict(synthetic=True,profile=profile,windows=windows,initial_runs=0,initial_batches=0,
                    warning='Synthetic/local engineering verification only; empirical validation not performed.')
        (root/'synthetic-daily-reversion-fixture.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        return result
    finally:service.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path)
    print(json.dumps(create_fixture(parser.parse_args().root),indent=2))
