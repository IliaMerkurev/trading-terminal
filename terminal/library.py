"""Versioned, non-executing library templates. Native consent stays in the existing workflow."""
import copy
import hashlib
import importlib.metadata
from pathlib import Path

from terminal.data import digest
from terminal.graph import validate_graph
from terminal.native import preview
from terminal.profile import Profile, dec

TIMEFRAMES = [1, 3, 5, 15, 30, 60, 120, 240, 360, 720, 1440]
NAUTILUS_COMMIT = '27a8e54e7ac3c57d6cbf8891f0283dfbaee97317'
LEAN_COMMIT = '985ef30ad3ac774218c5ac516b4cb0aa2655730f'
EMA_HASH = 'cfdc26b76d03df6cc481d47327d64dd6c23b356236cd061bb87c691b7918d13b'

ENTRIES = [
    dict(id='historical-return',version=1,name='Historical return direction',family='momentum',kind='Adapted',
         author='QuantConnect Corporation; independent terminal graph adaptation',license='Apache-2.0',
         source_url=f'https://github.com/QuantConnect/Lean/blob/{LEAN_COMMIT}/Algorithm.Framework/Alphas/HistoricalReturnsAlphaModel.py',
         source_commit=LEAN_COMMIT,source_version_date='2026-09-18T14:03:24Z',source_sha256='43004946edfd02dbcb0010a6bde405ac9f65b3fbcfaed82c2065911300bee5d9',
         source_default_minutes=1440,author_recommended_minutes=None,local_default_minutes=1440,
         timeframe_evidence='Source constructor defaults to daily with lookback 1; no author recommendation inferred.',
         markets=['spot','linear'],directions=['long'],modes=['historical_closed'],timeframes=TIMEFRAMES,
         parameters={'lookback':dict(type='integer',default=1,min=1,max=1000)},dependencies={},
         adaptation='Long-only graph follows the sign of close-to-close historical return over lookback bars: enter positive, exit nonpositive. Omits short insights, insight expiry/magnitude allocation and multi-symbol portfolio framework; flat insight cancellation maps to exiting. Profile controls sizing/costs. No source annualization string is used.',
         review='Pinned Apache source reviewed statically. Framework history/consolidator/insight APIs are not loaded; no copied module, direct file/process/credential access, unsafe dynamic execution or future indexing.',
         compatibility='Confirmed selected bars; lookback + 1 bars initialize fractional ROC. Zero denominator fails visibly. Not an EMA/MACD parameter variant.',
         availability='verified',verification='Independent fractional ROC/warmup/causality and nontrivial 1m/3m trade checks passed; cached BTCUSDT spot at 1m/5m completed with both passive baselines. Losses retained; no profitability claim.'),
    dict(id='macd-tolerance',version=1,name='MACD normalized momentum',family='momentum',kind='Adapted',
         author='QuantConnect Corporation; independent terminal graph adaptation',license='Apache-2.0',
         source_url=f'https://github.com/QuantConnect/Lean/blob/{LEAN_COMMIT}/Algorithm.Python/MACDTrendAlgorithm.py',
         source_commit=LEAN_COMMIT,source_version_date='2026-09-18T14:03:24Z',source_sha256='ea86a2c14af9bd1b2ae2081d6004ac0a400f69a858b3c3d87f0da2db3d476fc0',
         source_default_minutes=1440,author_recommended_minutes=None,local_default_minutes=1440,
         timeframe_evidence='Source subscribes daily SPY and evaluates once per day; daily is a source default, not an author recommendation.',
         markets=['spot','linear'],directions=['long'],modes=['historical_closed'],timeframes=TIMEFRAMES,
         parameters={'fast':dict(type='integer',default=12,min=1,max=1000),'slow':dict(type='integer',default=26,min=2,max=1000),
                     'signal':dict(type='integer',default=9,min=1,max=1000),'tolerance':dict(type='number',default=.0025,min=0,max=.5)},
         dependencies={'nautilus_trader':'1.231.0'},
         adaptation='Long-only graph preserves histogram/fast-EMA tolerance logic: enter histogram > tolerance * fast EMA; exit histogram < -tolerance * fast EMA. Existing causal Nautilus EMA initialization replaces Lean initialization. Evaluates each confirmed selected bar rather than an equity daily callback; profile sizing/costs replace full SPY allocation. No short entry.',
         review='Pinned source reviewed statically; AlgorithmImports/portfolio/plot APIs are not loaded. No copied module or extra dependencies, dynamic execution or future-bar access.',
         compatibility='Single confirmed primary timeframe; warmup slow + signal bars. Numeric multiplication preserves source tolerance without division.',
         availability='verified',verification='Independent normalized MACD trade/causality and 1m/3m checks passed; cached BTCUSDT spot at 1m/5m completed with both passive baselines. Legitimate no-trade outcomes retained; no profitability claim.'),
    dict(id='bb-rsi-reversion',version=1,name='Bollinger RSI reversion',family='mean_reversion',kind='Adapted',
         author='Nautech Systems Pty Ltd; independent terminal graph adaptation',license='LGPL-3.0',
         source_url=f'https://github.com/nautechsystems/nautilus_trader/blob/{NAUTILUS_COMMIT}/nautilus_trader/examples/strategies/bb_mean_reversion.py',
         source_commit=NAUTILUS_COMMIT,source_version_date='2026-08-02T11:26:46Z',source_sha256='e4c9dca50146b34f68185f78822dbcbba5d0b08d20370dd36fbdc4a1550cf089',
         source_default_minutes=None,author_recommended_minutes=None,local_default_minutes=60,
         timeframe_evidence='Source requires a bar_type and recommends no interval; 60m is a local convenience.',
         markets=['spot','linear'],directions=['long'],modes=['historical_closed'],timeframes=TIMEFRAMES,
         parameters={'bb_period':dict(type='integer',default=20,min=2,max=1000),'deviations':dict(type='number',default=2,min=.01,max=10),
                     'rsi_period':dict(type='integer',default=14,min=2,max=1000),'lower':dict(type='number',default=30,min=0,max=100)},
         dependencies={'nautilus_trader':'1.231.0'},
         adaptation='Long-only graph: enter close <= lower Bollinger band AND Wilder RSI < lower threshold; exit close >= middle band. Close-only bands replace native bar-price input. Source shorts/reversals are omitted; profile sizing/protection/costs replace fixed quantity. Source RSI 0.30 maps to graph 30 on its 0–100 scale.',
         review='Pinned installed source reviewed statically: engine-only bar callbacks, no direct network/file/process/credential access or dynamic execution. No upstream module copied or loaded by this graph.',
         compatibility='Single confirmed primary timeframe; warmup max(bb_period,rsi_period+1). No additional feeds.',
         availability='verified',verification='Independent confluence/trade/causality and 1m/3m checks passed; cached BTCUSDT spot at 1m/5m completed with both passive baselines. No profitability claim.'),
    dict(id='native-ema-cross', version=2, name='Native EMA trend', family='trend', kind='Native',
         author='Nautech Systems Pty Ltd', license='LGPL-3.0',
         source_url=f'https://github.com/nautechsystems/nautilus_trader/blob/{NAUTILUS_COMMIT}/nautilus_trader/examples/strategies/ema_cross.py',
         source_commit=NAUTILUS_COMMIT,source_version_date='2026-08-02T11:26:46Z', source_sha256=EMA_HASH,
         source_default_minutes=None, author_recommended_minutes=None, local_default_minutes=60,
         timeframe_evidence='Source requires a bar_type; it recommends no interval. 60m is a local convenience, not author guidance.',
         markets=['linear'], directions=['long','short'], modes=['historical_closed'], timeframes=TIMEFRAMES,
         parameters={'fast':dict(type='integer',default=10,min=1,max=1000), 'slow':dict(type='integer',default=20,min=2,max=1000),
                     'quantity':dict(type='decimal',default='0.001',min='0.00000001',max='1000000')},
         dependencies={'nautilus_trader':'1.231.0'},
         adaptation='Native subclass of the unchanged installed implementation. A reviewed temporal adapter suppresses on_bar decisions before the evaluation start while registered EMAs warm up. Disable historical requests/tick subscriptions by config; retain fixed quantity, reversal and stop-close semantics. Spot is excluded because the source opens shorts.',
         review='Static source reviewed; read-only source hash guard before module import. Explicit user trust required. No strategy loading during browse/copy.',
         compatibility='Declared external closed bars only; native profile version 1. Reviewed window adapter permits preceding warmup without trades. Historical only; not Live-compatible.',
         availability='verified', verification='Synthetic native trade/fee and 1m/3m warmup checks passed; finite cached BTCUSDT linear batch at 1m/5m with actual spot alternatives passed. Historical integration evidence, not a profitability claim.'),
    dict(id='rsi-threshold', version=1, name='RSI threshold reversion', family='mean_reversion', kind='Adapted',
         author='QuantConnect Corporation; independent terminal graph adaptation', license='Apache-2.0',
         source_url=f'https://github.com/QuantConnect/Lean/blob/{LEAN_COMMIT}/Algorithm.Framework/Alphas/RsiAlphaModel.py',
         source_commit=LEAN_COMMIT,source_version_date='2026-09-18T14:03:24Z', source_sha256='5cba110dc89dffe8ef6f4c386a25ce25c896e04d4616a4809041604652294c15',
         source_default_minutes=1440, author_recommended_minutes=None, local_default_minutes=1440,
         timeframe_evidence='RsiAlphaModel constructor defaults to Resolution.DAILY; no author recommendation inferred.',
         markets=['spot','linear'], directions=['long'], modes=['historical_closed'], timeframes=TIMEFRAMES,
         parameters={'period':dict(type='integer',default=14,min=2,max=1000), 'lower':dict(type='number',default=30,min=0,max=100),
                     'upper':dict(type='number',default=70,min=0,max=100)}, dependencies={'nautilus_trader':'1.231.0'},
         adaptation='Visual long-only threshold adaptation: enter below lower RSI, exit above upper RSI. Uses existing Wilder RSI scaled 0–100. Omits insight expiry, 35/65 hysteresis, multi-symbol allocation and short insights; not equivalent to Lean portfolio behavior. Profile controls sizing/costs.',
         review='Pinned source reviewed statically. No external source copied or executed; existing bounded graph nodes only.',
         compatibility='Single primary timeframe, confirmed bars; warmup period + 1 bars. No additional feeds.',
         availability='verified', verification='Independent RSI signals/trades and 1m/3m batch parity passed; finite cached BTCUSDT linear batch at 1m/5m with actual spot alternatives passed. Historical integration evidence, not a profitability claim.'),
]


def catalog():
    return copy.deepcopy(ENTRIES)


def prepare(entry_id, version, minutes, parameters):
    entry = next((e for e in ENTRIES if e['id'] == entry_id and e['version'] == version), None)
    if entry is None or type(version) is not int:
        raise ValueError('Unknown library entry version')
    if type(minutes) is not int or minutes not in entry['timeframes']:
        raise ValueError('Unsupported strategy timeframe')
    if not isinstance(parameters, dict) or set(parameters) - entry['parameters'].keys():
        raise ValueError('Unknown library parameters')
    values = {}
    for name, field in entry['parameters'].items():
        value = parameters.get(name, field['default'])
        if isinstance(value, bool) or field['type'] == 'integer' and type(value) is not int:
            raise ValueError(f'Invalid {name} type')
        number = dec(value)
        if not dec(field['min']) <= number <= dec(field['max']):
            raise ValueError(f'{name} outside reviewed bounds')
        values[name] = int(number) if field['type'] == 'integer' else str(number) if field['type'] == 'decimal' else float(number)
    if entry_id == 'native-ema-cross':
        if values['fast'] >= values['slow']:
            raise ValueError('Fast EMA must be below slow EMA')
        path = importlib.metadata.distribution('nautilus_trader').locate_file('nautilus_trader/examples/strategies/ema_cross.py')
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != EMA_HASH:
            raise ValueError('Reviewed native dependency source changed; review required')
        source = ("import hashlib\nimport importlib.metadata\nfrom pathlib import Path\n"
                  "_source = importlib.metadata.distribution('nautilus_trader').locate_file('nautilus_trader/examples/strategies/ema_cross.py')\n"
                  f"if hashlib.sha256(Path(_source).read_bytes()).hexdigest() != '{EMA_HASH}':\n    raise ValueError('Reviewed native source changed')\n"
                  "from nautilus_trader.examples.strategies.ema_cross import EMACross, EMACrossConfig\n"
                  "\nclass WindowEMACrossConfig(EMACrossConfig, frozen=True):\n    evaluation_start: int = 0\n"
                  "\nclass WindowEMACross(EMACross):\n"
                  "    def on_bar(self, bar):\n"
                  "        if bar.ts_event < self.config.evaluation_start * 1000000000:\n            return\n"
                  "        super().on_bar(bar)\n")
        document = dict(version=1,engine='nautilus_trader',engine_version='1.231.0',source=source,
            class_name='WindowEMACross',config_class='WindowEMACrossConfig',bar_minutes=[minutes],dependencies=entry['dependencies'],
            provenance=f"{entry['source_url']} SHA256 {EMA_HASH}; LGPL-3.0; imported installed source, not copied.",
            config=dict(instrument_id='$instrument',bar_type=f'$bar:{minutes}',trade_size=values['quantity'],
                        fast_ema_period=values['fast'],slow_ema_period=values['slow'],request_bars=False,
                        subscribe_trade_ticks=False,subscribe_quote_ticks=False,close_positions_on_stop=True,evaluation_start=0))
        preview(document)
        profile = Profile(market='linear',primary_minutes=minutes).snapshot()
        kind = 'native'; warmup = values['slow']
    elif entry_id=='historical-return':
        nodes=[dict(id='close',type='price',inputs={},params={'field':'close'}),
               dict(id='return',type='roc',inputs={'source':'close.value'},params={'period':values['lookback']}),
               dict(id='zero',type='constant',inputs={},params={'value':0}),
               dict(id='entry',type='compare',inputs={'left':'return.value','right':'zero.value'},params={'operator':'>'}),
               dict(id='exit',type='compare',inputs={'left':'return.value','right':'zero.value'},params={'operator':'<='})]
        graph=dict(version=1,nodes=nodes,outputs=dict(entry_long='entry.value',exit_long='exit.value',entry_short=None,exit_short=None))
        validate_graph(graph);document={'graph':graph,'layout':{}}
        profile=Profile(primary_minutes=minutes,version=2).snapshot();kind='graph';warmup=values['lookback']+1
    elif entry_id=='macd-tolerance':
        if values['fast']>=values['slow']:raise ValueError('MACD fast period must be below slow period')
        nodes=[dict(id='close',type='price',inputs={},params={'field':'close'}),
               dict(id='fast',type='ema',inputs={'source':'close.value'},params={'period':values['fast']}),
               dict(id='macd',type='macd',inputs={'source':'close.value'},params={k:values[k] for k in ('fast','slow','signal')})]
        for name,sign,operator in [('entry',1,'>'),('exit',-1,'<')]:
            nodes.extend([dict(id=name+'Tolerance',type='constant',inputs={},params={'value':sign*values['tolerance']}),
                          dict(id=name+'Threshold',type='multiply',inputs={'left':'fast.value','right':name+'Tolerance.value'},params={}),
                          dict(id=name,type='compare',inputs={'left':'macd.histogram','right':name+'Threshold.value'},params={'operator':operator})])
        graph=dict(version=1,nodes=nodes,outputs=dict(entry_long='entry.value',exit_long='exit.value',entry_short=None,exit_short=None))
        validate_graph(graph);document={'graph':graph,'layout':{}}
        profile=Profile(primary_minutes=minutes,version=2).snapshot();kind='graph';warmup=values['slow']+values['signal']
    elif entry_id=='bb-rsi-reversion':
        nodes=[dict(id='close',type='price',inputs={},params={'field':'close'}),
               dict(id='bands',type='bb',inputs={'source':'close.value'},params={'period':values['bb_period'],'deviations':values['deviations']}),
               dict(id='rsi',type='rsi',inputs={'source':'close.value'},params={'period':values['rsi_period']}),
               dict(id='threshold',type='constant',inputs={},params={'value':values['lower']}),
               dict(id='belowBand',type='compare',inputs={'left':'close.value','right':'bands.lower'},params={'operator':'<='}),
               dict(id='oversold',type='compare',inputs={'left':'rsi.value','right':'threshold.value'},params={'operator':'<'}),
               dict(id='entry',type='and',inputs={'left':'belowBand.value','right':'oversold.value'},params={}),
               dict(id='exit',type='compare',inputs={'left':'close.value','right':'bands.middle'},params={'operator':'>='})]
        graph=dict(version=1,nodes=nodes,outputs=dict(entry_long='entry.value',exit_long='exit.value',entry_short=None,exit_short=None))
        validate_graph(graph);document={'graph':graph,'layout':{}}
        profile=Profile(primary_minutes=minutes,version=2).snapshot();kind='graph'
        warmup=max(values['bb_period'],values['rsi_period']+1)
    else:
        if values['lower'] >= values['upper']:
            raise ValueError('Lower RSI must be below upper RSI')
        nodes = [dict(id='close',type='price',inputs={},params={'field':'close'}),
                 dict(id='rsi',type='rsi',inputs={'source':'close.value'},params={'period':values['period']})]
        for name, operator in [('lower','<'),('upper','>')]:
            nodes.extend([dict(id=name,type='constant',inputs={},params={'value':values[name]}),
                dict(id=name+'Signal',type='compare',inputs={'left':'rsi.value','right':name+'.value'},params={'operator':operator})])
        graph = dict(version=1,nodes=nodes,outputs=dict(entry_long='lowerSignal.value',exit_long='upperSignal.value',entry_short=None,exit_short=None))
        validate_graph(graph)
        document = {'graph':graph,'layout':{}}
        profile = Profile(primary_minutes=minutes,version=2).snapshot()
        kind = 'graph'; warmup = values['period'] + 1
    contract = dict(entry_id=entry_id,version=version,source_sha256=entry['source_sha256'],minutes=minutes,parameters=values,
                    document_sha256=digest(document),warmup_bars=warmup)
    return dict(name=entry['name'],kind=kind,document=document,profile=profile,contract=contract)


def for_window(prepared, start):
    prepared=copy.deepcopy(prepared)
    if prepared['kind']=='native':
        if type(start) is not int or start<0 or start%60:raise ValueError('Invalid native evaluation start')
        prepared['document']['config']['evaluation_start']=start
        prepared['contract']['document_sha256']=digest(prepared['document'])
        prepared['contract']['evaluation_start']=start
    return prepared


def native_window_document(document, start):
    """Only the exact reviewed temporal adapter can acquire a trading window."""
    try:
        config=document['config']
        prepared=prepare('native-ema-cross',2,document['bar_minutes'][0],
                         {'fast':config['fast_ema_period'],'slow':config['slow_ema_period'],'quantity':config['trade_size']})
        expected=for_window(prepared,config['evaluation_start'])['document']
        if document!=expected:raise ValueError('Native document differs from reviewed adapter')
        return for_window(prepared,start)['document']
    except (KeyError,IndexError,TypeError) as exc:
        raise ValueError('Native separate-window execution requires the reviewed library adapter') from exc


def create_copy(store, **request):
    prepared = prepare(**request)
    ident = store.save_strategy(prepared['name']+' copy',prepared['kind'],prepared['document'],None,profile=prepared['profile'])
    return {'strategy_id':ident,'contract':prepared['contract']}
