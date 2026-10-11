"""Independent synthetic rule/arithmetic, costed engine and persistence gates."""
import base64
import copy
from decimal import Decimal as D
from fractions import Fraction as F
import hashlib
from pathlib import Path
import tempfile
import threading
import unittest

from terminal.archives import ArchiveManager, CHUNK
from terminal.daily_rules import RULES
from terminal.experiments import warmup_bars, parameter_fields
from terminal.graph import GraphEvaluator, GraphError, validate_graph
from terminal.jobs import JobManager
from terminal.library import catalog, prepare, create_copy
from terminal.library_batches import LibraryBatchManager
from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest
from terminal.storage import RunStore

DAY=86400
IDS=('double-seven-reversion','improved-r2-reversion')


def bars(prices):
    # Deliberately heterogeneous wicks: close extrema must not become Donchian.
    return [Candle(i*DAY,p,p+10+i%11,max(1,p-20-i%7),p,100) for i,p in enumerate(prices)]


def independent_rsi(prices,period=2):
    gain=loss=F(0);out=[]
    for i,price in enumerate(prices):
        change=F(price)-F(prices[i-1]) if i else F(0)
        gain=((period-1)*gain+max(change,0))/period
        loss=((period-1)*loss+max(-change,0))/period
        out.append(None if i+1<period else F(100) if loss==0 else 100*gain/(gain+loss))
    return out


def graph(entry,parameters=None):
    return prepare(entry,1,1440,parameters or {})['document']['graph']


def evaluate(g,prices):
    e=GraphEvaluator(g)
    return [e([bar],bar.time+DAY,True) for bar in bars(prices)]


def cost_profile():
    return Profile(primary_minutes=1440,execution_minutes=1440,version=2,
                   allocation='100',fee_rate='.001',slippage='.01',tick_size='.5',quantity_step='.1',min_quantity='.1')


class DailyNodeTests(unittest.TestCase):
    def test_extrema_current_inclusion_ties_null_slots_and_bounds(self):
        g=graph(IDS[0],{'trend_period':3,'window':3})
        result=evaluate(g,[12,11,10,10,11,12,13])
        self.assertEqual([r['values']['minimum.value'] for r in result],[None,None,10,10,10,10,11])
        self.assertEqual([r['values']['maximum.value'] for r in result],[None,None,12,11,11,12,13])
        for kind,key in [('rolling_min','period'),('rolling_max','period'),('lag','bars')]:
            node=dict(id='probe',type=kind,inputs={'source':'close.value'},params={key:1})
            test=copy.deepcopy(g);test['nodes'].append(node)
            validate_graph(test)
            for invalid in [0,1001,1.5,True,'2',float('inf')]:
                node['params'][key]=invalid
                with self.assertRaises(GraphError):validate_graph(test)
            node['params'][key]=1000;validate_graph(test)
        one=evaluate(graph(IDS[0],{'trend_period':2,'window':1}),[12,9])
        self.assertEqual([r['values']['minimum.value'] for r in one],[12,9])
        self.assertEqual([r['values']['maximum.value'] for r in one],[12,9])
        # A null SMA input occupies a rolling-window slot, never compressed.
        for node in g['nodes']:
            if node['type'] in ('rolling_min','rolling_max'):node['inputs']['source']='trend.value';node['params']['period']=2
        result=evaluate(g,[10,11,12,13])
        self.assertEqual([r['values']['minimum.value'] for r in result],[None,None,None,11])

    def test_lag_closed_slots_forming_replacement_and_duplicate_commit(self):
        g={'version':1,'nodes':[
            dict(id='close',type='price',inputs={},params={'field':'close'}),
            dict(id='mean',type='sma',inputs={'source':'close.value'},params={'period':2}),
            dict(id='lag',type='lag',inputs={'source':'mean.value'},params={'bars':2})],
            'outputs':dict(entry_long=None,exit_long=None,entry_short=None,exit_short=None)}
        self.assertEqual([r['values']['lag.value'] for r in evaluate(g,[9,11,11,13])],[None,None,None,10])
        self.assertEqual(warmup_bars(g),4)
        self.assertEqual(next(f['type'] for f in parameter_fields(g) if f['key']=='node.lag.bars'),'integer')
        e=GraphEvaluator(g)
        e([Candle(0,9,9,9,9,1)],DAY,True)
        for at,p in [(DAY+10,500),(DAY+20,700),(2*DAY,11)]:
            e([Candle(DAY,p,p,p,p,1)],at,at==2*DAY)
        e([Candle(2*DAY,11,11,11,11,1)],3*DAY,True)
        out=e([Candle(3*DAY,13,13,13,13,1)],4*DAY,True)
        self.assertEqual(out['values']['lag.value'],10)
        with self.assertRaisesRegex(GraphError,'committed twice'):
            e([Candle(3*DAY,13,13,13,13,1)],4*DAY+1,True)
        self.assertEqual(len(e.states['lag']),2)
        # A middle null remains a completed slot; current null may expose a valid lag.
        nullable=copy.deepcopy(g);nullable['nodes'][0].update(type='position_size',params={})
        nullable['nodes']= [nullable['nodes'][0],dict(id='lag',type='lag',inputs={'source':'close.value'},params={'bars':1})]
        e=GraphEvaluator(nullable);out=[]
        for i,value in enumerate([10,None,12]):
            e.position_context={'position_size':value}
            out.append(e([Candle(i*DAY,10,10,10,10,1)],(i+1)*DAY,True)['values']['lag.value'])
        self.assertEqual(out,[None,10,None])

    def test_rolling_forming_state_and_causal_future(self):
        g=graph(IDS[0],{'trend_period':3,'window':3});e=GraphEvaluator(g)
        for bar in bars([10,11]):e([bar],bar.time+DAY,True)
        for at,p in [(2*DAY+10,99),(2*DAY+20,1),(3*DAY,12)]:
            value=e([Candle(2*DAY,p,p,p,p,1)],at,at==3*DAY)['values']
            self.assertEqual(value['minimum.value'],min(10,11,p))
        out=e([Candle(3*DAY,13,13,13,13,1)],4*DAY,True)
        self.assertEqual(out['values']['minimum.value'],11)
        self.assertEqual(out['values']['maximum.value'],13)
        for ident in IDS:
            prices=[100]*200+[120,118,116,114,112,130,131]
            self.assertEqual(evaluate(graph(ident),prices)[:205],evaluate(graph(ident),prices[:205]+[1,2])[:205])


class DailyRuleTests(unittest.TestCase):
    def test_default_contracts_honest_hashes_and_constraints(self):
        for candidate,ident in zip(('C12','C13'),IDS):
            entry=next(e for e in catalog() if e['id']==ident);p=prepare(ident,1,1440,{})
            self.assertEqual(p['contract']['warmup_bars'],200)
            self.assertEqual(entry['source_sha256'],hashlib.sha256(RULES[candidate].encode()).hexdigest())
            self.assertIsNone(entry['source_commit']);self.assertIn('not upstream',entry['source_hash_basis'])
            self.assertEqual(entry['empirical_validation'],'not_performed')
            self.assertEqual(entry['availability'],'implementation_verified')
            self.assertEqual(entry['markets'],['spot']);self.assertEqual(entry['timeframes'],[1440])
            self.assertEqual(p['profile']['version'],2);self.assertIsNone(p['profile'].get('position_management'))
            self.assertEqual(p['document']['graph']['outputs']['entry_short'],None)
            with self.assertRaisesRegex(ValueError,'timeframe'):prepare(ident,1,60,{})
        with self.assertRaisesRegex(ValueError,'at least'):prepare(IDS[1],1,1440,{'trend_period':5,'rsi_period':3})
        self.assertEqual(prepare(IDS[0],1,1440,{'window':300})['contract']['warmup_bars'],300)

    def test_c12_independent_rules_tie_and_trend_equality(self):
        prices=[100]*194+[120,119,118,117,116,115]+[115,116,114,113,120]
        result=evaluate(graph(IDS[0]),prices)
        for i,row in enumerate(result):
            ready=i>=199
            enter=ready and F(prices[i])>sum(map(F,prices[i-199:i+1]))/200 and prices[i]==min(prices[max(0,i-6):i+1])
            leave=i>=6 and prices[i]==max(prices[i-6:i+1])
            self.assertEqual(row['signals']['entry_long'],enter,i)
            self.assertEqual(row['signals']['exit_long'],leave,i)
        self.assertTrue(result[200]['signals']['entry_long'])  # tied minimum
        self.assertFalse(result[201]['signals']['entry_long'])
        self.assertFalse(evaluate(graph(IDS[0]),[100]*201)[-1]['signals']['entry_long'])

    def test_c13_independent_ohlc_rsi_and_strict_signal_boundaries(self):
        prices=[100]*200+[120,118,116,114,112,130,131]
        expected=independent_rsi(prices);rows=evaluate(graph(IDS[1]),prices)
        self.assertEqual(expected[200:206],[F(100),F(250,3),F(125,2),F(125,3),F(25),F(3725,41)])
        for i,row in enumerate(rows):
            actual=row['values']['rsi.value']
            if expected[i] is None:self.assertIsNone(actual)
            else:self.assertAlmostEqual(actual,float(expected[i]),places=10)
            entry=i>=199 and all(v is not None for v in expected[max(0,i-2):i+1]) and expected[i-2]<65 and expected[i-1]<expected[i-2] and expected[i]<expected[i-1] and F(prices[i])>sum(map(F,prices[i-199:i+1]))/200
            self.assertEqual(row['signals']['entry_long'],entry,i)
        self.assertTrue(rows[204]['signals']['entry_long']);self.assertTrue(rows[205]['signals']['exit_long'])
        # Independently inject RSI only to isolate strict comparisons. OHLC recurrence is tested above.
        g=graph(IDS[1],{'trend_period':5})
        node=next(n for n in g['nodes'] if n['id']=='rsi');node.update(type='price',inputs={},params={'field':'volume'})
        for sequence,want in [([60,50,40],True),([65,50,40],False),([60,60,40],False),([60,50,50],False)]:
            e=GraphEvaluator(g)
            for i,rsi in enumerate([100]*5+sequence):
                p=100 if i<5 else 120
                row=e([Candle(i*DAY,p,p,p,p,rsi)],(i+1)*DAY,True)
            self.assertEqual(row['signals']['entry_long'],want)
        for value,want in [(75,False),(75.01,True)]:
            e=GraphEvaluator(g);row=e([Candle(0,100,100,100,100,value)],DAY,True)
            self.assertEqual(row['signals']['exit_long'],want)

    def test_independently_costed_entries_exits_prefix_and_future(self):
        cases=[(IDS[0],[100]*194+[120,119,118,117,116,115]+[114,113,120,121],200,[D('115.5'),D('118.5')],D('.1872'),D('2.2128')),
               (IDS[1],[100]*200+[120,118,116,114,112,130,131],200,[D('113.5'),D('128.5')],D('.1936'),D('11.8064'))]
        for ident,prices,start,fills,fees,pnl in cases:
            result=run_backtest(bars(prices),cost_profile(),GraphEvaluator(graph(ident)),trade_start=start*DAY)
            self.assertEqual([D(f['price']) for f in result['fills']],fills)
            self.assertEqual([D(f['quantity']) for f in result['fills']],[D('.8'),D('.8')])
            self.assertEqual(D(result['metrics']['fees']),fees);self.assertEqual(D(result['metrics']['net_pnl']),pnl)
            self.assertEqual(len(result['trades']),1)
            self.assertTrue(all(f['time_ns']>=start*DAY*10**9 for f in result['fills']))
            entry_index=200 if ident==IDS[0] else 204
            self.assertEqual(result['fills'][0]['time_ns'],(entry_index+1)*DAY*10**9-1)
            changed=run_backtest(bars(prices[:entry_index+1]+[200]*(len(prices)-entry_index-1)),cost_profile(),GraphEvaluator(graph(ident)),trade_start=start*DAY)
            self.assertEqual(result['fills'][0],changed['fills'][0])
            self.assertEqual(result['indicators'][:entry_index+1-start],changed['indicators'][:entry_index+1-start])

    def test_final_costed_flatten_and_no_same_step_reentry(self):
        # C12 plateau: low=high=close, but old lows keep SMA below it.
        prices=[100]*193+[120]*9
        result=run_backtest(bars(prices),cost_profile(),GraphEvaluator(graph(IDS[0])),trade_start=200*DAY)
        self.assertEqual(len(result['fills']),2)
        self.assertEqual([f['time_ns'] for f in result['fills']],[(201*DAY)*10**9-1,(202*DAY)*10**9-1])
        for ident,prices,start,entry,exit,fees,pnl in [
            (IDS[0],[100]*194+[120,119,118,117,116,115]+[114,113],200,'115.5','111.5','.1816','-3.3816'),
            (IDS[1],[100]*200+[120,118,116,114,112,111],200,'113.5','109.5','.1784','-3.3784')]:
            result=run_backtest(bars(prices),cost_profile(),GraphEvaluator(graph(ident)),trade_start=start*DAY)
            self.assertEqual([D(f['price']) for f in result['fills']],[D(entry),D(exit)])
            self.assertEqual(D(result['metrics']['fees']),D(fees));self.assertEqual(D(result['metrics']['net_pnl']),D(pnl))
            self.assertEqual(len(result['trades']),1)


class DailyPersistenceTests(unittest.TestCase):
    def test_graph_copy_reopen_archive_roundtrip_and_profile_scope(self):
        with tempfile.TemporaryDirectory() as root:
            store=RunStore(Path(root)/'source');manager=ArchiveManager(store)
            for ident in IDS:
                copied=create_copy(store,entry_id=ident,version=1,minutes=1440,parameters={})
                saved=store.strategy(copied['strategy_id'])
                self.assertEqual(saved['document'],prepare(ident,1,1440,{})['document'])
                again=RunStore(Path(root)/'source').strategy(copied['strategy_id'])
                self.assertEqual(again,saved)
                info=manager.export({k:saved[k] for k in ('name','kind','document')},saved['profile'],[]);raw=(store.root/'exports'/info['filename']).read_bytes()
                dest=RunStore(Path(root)/ident);other=ArchiveManager(dest);upload=other.begin(len(raw))
                for offset in range(0,len(raw),CHUNK):other.append(upload['upload_id'],offset,base64.b64encode(raw[offset:offset+CHUNK]).decode())
                imported=other.finish(upload['upload_id'])
                self.assertEqual(dest.strategy(imported['strategy_id'])['document'],saved['document'])
                for changes in [{'market':'linear'},{'evaluation':'intrabar'},{'gap_policy':'skip'}]:
                    with self.assertRaises(ValueError):create_copy(store,entry_id=ident,version=1,minutes=1440,parameters={},profile={**saved['profile'],**changes})

    def test_historical_admission_exact_prefix_and_gap_failure(self):
        with tempfile.TemporaryDirectory() as root:
            jobs=JobManager(root);manager=LibraryBatchManager(jobs)
            try:
                prices=[100]*200+[120,118,116,114,112,130,131]
                def dataset(rows):return jobs.datasets.save('spot','BTCUSDT',0,len(prices)*DAY,rows,[],{},minutes=1440,metadata={'synthetic':True},provenance=[])
                full=dataset(bars(prices))
                request=dict(selections=[dict(entry_id=ident,version=1,minutes=1440,parameters={}) for ident in IDS],dataset_id=full['id'],profile=cost_profile().snapshot(),start=200*DAY,end=len(prices)*DAY,interval='daily',spot_dataset_id=None)
                short=manager.preview(**{**request,'start':199*DAY})
                self.assertTrue(all('warmup' in row['error'] for row in short['rows'][:2]))
                frozen=manager.prepare(**request)
                self.assertTrue(all(not row['error'] for row in frozen['rows'][:2]))
                active={'stop':threading.Event()}
                manager._preflight_data(active,frozen)
                skipped=manager.preview(**{**request,'profile':{**request['profile'],'gap_policy':'skip'}})
                self.assertTrue(all('rejected gaps' in row['error'] for row in skipped['rows'][:2]))
                # More than 200 total closed bars still cannot conceal a recent prefix gap.
                request['start']=204*DAY
                frozen=manager.prepare(**request)
                gapped=dataset([bar for i,bar in enumerate(bars(prices)) if i!=198])
                with self.assertRaisesRegex(ValueError,'coverage is incomplete'):
                    manager.prepare(**{**request,'dataset_id':gapped['id']})
                # Isolate the downstream prefix guard after verifying public admission.
                # An altered in-memory stage fixture is never submitted as an admitted batch.
                frozen['inputs']['dataset_id']=gapped['id']
                for row in frozen['rows']:row['dataset']=manager._dataset(gapped)
                with self.assertRaisesRegex(ValueError,'contiguous complete'):
                    manager._preflight_data(active,frozen)
                # Evaluation-period gaps are refused too, not silently skipped.
                evaluation_gap=dataset([bar for i,bar in enumerate(bars(prices)) if i!=205])
                with self.assertRaisesRegex(ValueError,'coverage is incomplete'):
                    manager.prepare(**{**request,'dataset_id':evaluation_gap['id']})
            finally:manager.close();jobs.close()

    def test_supported_worker_batch_and_saved_result_archive(self):
        from scripts.prepare_daily_reversion_fixture import create_fixture
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'new';fixture=create_fixture(root)
            with self.assertRaises(FileExistsError):create_fixture(root)
            jobs=JobManager(root);manager=LibraryBatchManager(jobs)
            try:
                for window in fixture['windows']:
                    params=dict(selections=[window['selection']],dataset_id=window['dataset_id'],profile=fixture['profile'],
                        start=window['start'],end=window['end'],interval='daily',spot_dataset_id=None)
                    preview=manager.preview(**params)
                    ident=manager.start(expected_contract=preview['contract_sha256'],**params)['batch_id']
                    manager.active['thread'].join(40);self.assertIsNone(manager.active)
                    report=manager.get(ident);self.assertEqual(report['status'],'completed',report)
                    result=jobs.store.result(report['rows'][0]['run_id'])
                    self.assertEqual([D(f['price']) for f in result['fills']],list(map(D,window['expected']['fills'])))
                    for field in ('fees','net_pnl'):self.assertEqual(D(result['metrics'][field]),D(window['expected'][field]))
                    saved=jobs.store.strategy(window['strategy_id']);archive=ArchiveManager(jobs.store)
                    info=archive.export({k:saved[k] for k in ('name','kind','document')},saved['profile'],[report['rows'][0]['run_id']])
                    from terminal.archives import read_archive,validate_snapshot
                    project,files=read_archive((jobs.store.root/'exports'/info['filename']).read_bytes())
                    snapshot=files[f"runs/{report['rows'][0]['run_id']}/snapshot.json"]
                    validate_snapshot(snapshot)
                    self.assertEqual(snapshot['research']['library']['contract']['candidate_id'],window['candidate'])
                    self.assertEqual(files[f"runs/{report['rows'][0]['run_id']}/result.json"]['fills'],result['fills'])
            finally:manager.close();jobs.close()

    def test_all_catalog_four_hour_default_keeps_daily_incompatible_rows(self):
        with tempfile.TemporaryDirectory() as root:
            jobs=JobManager(root);manager=LibraryBatchManager(jobs)
            try:
                # Synthetic H4 source supplies 200 complete UTC days before evaluation.
                rows=[Candle(i*14400,100,101,99,100,1) for i in range(6*207)]
                dataset=jobs.datasets.save('spot','BTCUSDT',0,207*DAY,rows,[],{},minutes=240,metadata={'synthetic':True},provenance=[])
                selections=[dict(entry_id=e['id'],version=e['version'],minutes=m,parameters={}) for e in catalog() for m in (240,1440)]
                params=dict(selections=selections,dataset_id=dataset['id'],profile=Profile(execution_minutes=240,primary_minutes=240).snapshot(),start=200*DAY,end=207*DAY,interval='daily',spot_dataset_id=None)
                self.assertEqual(manager.warmup(selections,dataset['id'])['start'],200*DAY)
                frozen=manager.prepare(**params)
                self.assertEqual(len(frozen['rows']),20)  # 9 templates x 2 intervals + 2 passive rows.
                for row in frozen['rows']:
                    if row.get('selection',{}).get('entry_id') in IDS:
                        if row['selection']['minutes']==240:
                            self.assertIn('supports [1440] minutes only',row['error']);self.assertIsNone(row['document'])
                        else:self.assertIsNone(row['error'])
                self.assertEqual(sum(bool(r['error']) for r in frozen['rows']),4)  # 2 native spot + 2 daily-only H4.
                manager._save('a'*32,frozen,'frozen')
                self.assertEqual(sum(r['status']=='incompatible' for r in manager.get('a'*32)['rows']),4)
            finally:manager.close();jobs.close()
