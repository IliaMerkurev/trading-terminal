"""Create a new, isolated offline A2 review fixture; never overwrite a workspace."""
import argparse
import json
from pathlib import Path

from terminal.jobs import JobManager
from terminal.library_batches import LibraryBatchManager
from terminal.profile import Profile
from terminal.series import Candle


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,required=True)
    root=parser.parse_args().data_root.resolve()
    if root.exists() and any(root.iterdir()):raise ValueError('Use a new empty synthetic data directory')
    jobs=JobManager(root);manager=LibraryBatchManager(jobs)
    try:
        start=1735689600
        bars=[Candle(start+i*60,100,100,100,100,100) for i in range(180)]
        metadata={'synthetic':True,'instrument':{'priceFilter':{'tickSize':'.5'},'lotSizeFilter':{
            'minOrderQty':'.1','basePrecision':'.1','minOrderAmt':'1','maxMarketOrderQty':'20','maxOrderAmt':'2000'}}}
        spot=jobs.datasets.save('spot','BTCUSDT',start,start+10800,bars,[],{},metadata=metadata,provenance=['Independently invented offline A2 fixture'])
        linear_metadata={'synthetic':True,'instrument':{'priceFilter':{'tickSize':'1'},'lotSizeFilter':{
            'minOrderQty':'1','qtyStep':'1','minNotionalValue':'150','maxMktOrderQty':'5'}},
            'current_risk_tiers':[{'isLowestRisk':1,'maintenanceMargin':'.005','riskLimitValue':'500'}]}
        linear=jobs.datasets.save('linear','BTCUSDT',start,start+10800,bars,[],{},metadata=linear_metadata,provenance=['Independently invented offline A2 fixture'])
        # A separate complete source supports the Lab's default history policies.
        # The original proxy/zero-cost source and saved reports stay immutable.
        complete_metadata={**linear_metadata,'instrument':{**linear_metadata['instrument'],'fundingInterval':1}}
        complete_linear=jobs.datasets.save('linear','BTCUSDT',start,start+10800,bars,bars,{b.time:'0' for b in bars},
            metadata=complete_metadata,provenance=['Independently invented complete mark/funding A2 fixture'])
        profile=Profile(market='linear',capital='1000',leverage='2',primary_minutes=1,fee_rate='.02',slippage='.02',
            tick_size='1',quantity_step='1',min_quantity='1',max_quantity='5',min_notional='150',max_notional='500',
            funding_mode='assumed_zero',mark_mode='last_proxy')
        settings={'version':1,'profile':Profile(capital='1000',primary_minutes=1,fee_rate='.01',slippage='.01',tick_size='.5',
            quantity_step='.1',min_quantity='.1',max_quantity='20',min_notional='1',max_notional='2000').snapshot(),
            'assumptions':{'version':1,'fee_source':'explicit_spot','fee_note':'Synthetic independent 1% fee and 1% slippage; not an exchange quote.',
            'slippage_source':'explicit_spot','precision_source':'dataset_metadata',
            'precision_note':'Invented synthetic precision and size limits for offline testing; not current or historical exchange metadata'}}
        params=dict(selections=[dict(entry_id='rsi-threshold',version=1,minutes=1,parameters={'period':2})],
            dataset_id=linear['id'],profile=profile.snapshot(),start=start+720,end=start+3600,
            interval='daily',spot_dataset_id=spot['id'],spot_benchmark=settings)
        ident=manager.start(expected_contract=manager.preview(**params)['contract_sha256'],**params)['batch_id']
        thread=manager.active['thread'];thread.join(40)
        if thread.is_alive():raise ValueError('Fixture exceeded bounded deadline')
        report=manager.get(ident)
        if report['status']!='completed':raise ValueError('Synthetic A2 fixture failed; inspect isolated saved status')
        manager.save_metadata(ident,'A2 independent spot controls','Synthetic flat prices. Linear costs 2%; independent spot costs 1%. Passive final equity 960.8 USDT; strategy has no signals.',0)
        frozen=manager.freeze_validation(ident,0,linear['id'],start+5400,start+10800,spot['id'])
        manager.save_metadata(frozen['batch_id'],'A2 frozen later-period review','Original independent spot assumptions retained. Frozen only; not executed.',0)
        print(json.dumps({'selection_batch_id':ident,'frozen_later_batch_id':frozen['batch_id'],
            'spot_dataset_id':spot['id'],'linear_dataset_id':linear['id'],'complete_linear_dataset_id':complete_linear['id'],'selection_range':[params['start'],params['end']]}))
    finally:manager.close();jobs.close()


if __name__=='__main__':main()
