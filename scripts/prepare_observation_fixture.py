"""New-only independently synthetic history for the manual observation workflow.

Creates no strategy runs, opens no network connection, never reuses user data.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from terminal.service import AppService
from terminal.series import Candle
from terminal.data import metadata_profile_fields
from terminal.profile import Profile


def create_fixture(root):
    root=Path(root)
    if not root.is_absolute():raise ValueError('Use an absolute new fixture directory')
    root.mkdir(parents=True,exist_ok=False)
    service=AppService(root)
    try:
        base=1704067200;hour=3600
        metadata={'synthetic':True,'instrument':{'symbol':'BTCUSDT','priceFilter':{'tickSize':'0.01'},
            'lotSizeFilter':{'basePrecision':'0.000001','minOrderQty':'0.000001','minOrderAmt':'1',
                            'maxMarketOrderQty':'100','maxOrderQty':'100','maxOrderAmt':'1000000'}}}
        bars=[Candle(base+i*hour,100+i%24,102+i%24,99+i%24,100.5+i%24,10) for i in range(900)]
        def save(rows,label):
            return service.datasets.save('spot','BTCUSDT',base,base+900*hour,rows,[],{},minutes=60,
                metadata=metadata,source=label,provenance=[{'synthetic':True,'generator':'scripts/prepare_observation_fixture.py','version':1}])
        full=save(bars,'Synthetic TT16: independently invented hourly cycle')
        gaps=save([bar for i,bar in enumerate(bars) if i!=24],'Synthetic TT16: missing hour 24')
        start=base+600*hour;end=base+624*hour
        note=service.observations.save(None,0,full['id'],start,end,
            'The invented 24-hour cycle rises from 100.5 to 123.5 before resetting.',
            'An observed close differs from the independently specified hourly sequence.')
        profile=Profile(**{**metadata_profile_fields(full),'execution_minutes':60,'primary_minutes':60,'capital':'1000',
                           'sizing':'percent','allocation':'95','fee_rate':'0.001','slippage':'0.0005'}).snapshot()
        result=dict(synthetic=True,dataset_id=full['id'],gapped_dataset_id=gaps['id'],observation_id=note['id'],
            start=start,end=end,profile=profile,selections=[dict(entry_id='rsi-threshold',version=1,minutes=60,parameters={'period':2})],
            expected={'full_candles':900,'first_page_candles':500,'second_page_candles':400,
                      'gapped_first_page_candles':499,'missing_timestamp':base+24*hour,
                      'observation_first_close':100.5,'observation_last_close':123.5,
                      'initial_runs':0,'initial_batches':0,'initial_observation_revision':1},
            bad_warmup_range=[base,base+24*hour])
        (root/'synthetic-observation-fixture.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    finally:service.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path)
    print(json.dumps(create_fixture(parser.parse_args().root),indent=2))
