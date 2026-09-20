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
    dict(id='native-ema-cross', version=1, name='Native EMA trend', family='trend', kind='Native',
         author='Nautech Systems Pty Ltd', license='LGPL-3.0',
         source_url=f'https://github.com/nautechsystems/nautilus_trader/blob/{NAUTILUS_COMMIT}/nautilus_trader/examples/strategies/ema_cross.py',
         source_commit=NAUTILUS_COMMIT, source_sha256=EMA_HASH,
         source_default_minutes=None, author_recommended_minutes=None, local_default_minutes=60,
         timeframe_evidence='Source requires a bar_type; it recommends no interval. 60m is a local convenience, not author guidance.',
         markets=['linear'], directions=['long','short'], modes=['historical_closed'], timeframes=TIMEFRAMES,
         parameters={'fast':dict(type='integer',default=10,min=1,max=1000), 'slow':dict(type='integer',default=20,min=2,max=1000),
                     'quantity':dict(type='decimal',default='0.001',min='0.00000001',max='1000000')},
         dependencies={'nautilus_trader':'1.231.0'},
         adaptation='Unchanged installed implementation. Disable historical requests and tick subscriptions using native config; retain fixed quantity, reversal and stop-close semantics. Spot is excluded because the source opens shorts.',
         review='Static source reviewed; read-only source hash guard before module import. Explicit user trust required. No strategy loading during browse/copy.',
         compatibility='Declared external closed bars only; native profile version 1. Later-period warmup is not supported yet.',
         availability='preview', verification='Full library integration and benchmark verification pending; no performance claim.'),
    dict(id='rsi-threshold', version=1, name='RSI threshold reversion', family='mean_reversion', kind='Adapted',
         author='QuantConnect Corporation; independent terminal graph adaptation', license='Apache-2.0',
         source_url=f'https://github.com/QuantConnect/Lean/blob/{LEAN_COMMIT}/Algorithm.Framework/Alphas/RsiAlphaModel.py',
         source_commit=LEAN_COMMIT, source_sha256='5cba110dc89dffe8ef6f4c386a25ce25c896e04d4616a4809041604652294c15',
         source_default_minutes=1440, author_recommended_minutes=None, local_default_minutes=1440,
         timeframe_evidence='RsiAlphaModel constructor defaults to Resolution.DAILY; no author recommendation inferred.',
         markets=['spot','linear'], directions=['long'], modes=['historical_closed'], timeframes=TIMEFRAMES,
         parameters={'period':dict(type='integer',default=14,min=2,max=1000), 'lower':dict(type='number',default=30,min=0,max=100),
                     'upper':dict(type='number',default=70,min=0,max=100)}, dependencies={'nautilus_trader':'1.231.0'},
         adaptation='Visual long-only threshold adaptation: enter below lower RSI, exit above upper RSI. Uses existing Wilder RSI scaled 0–100. Omits insight expiry, 35/65 hysteresis, multi-symbol allocation and short insights; not equivalent to Lean portfolio behavior. Profile controls sizing/costs.',
         review='Pinned source reviewed statically. No external source copied or executed; existing bounded graph nodes only.',
         compatibility='Single primary timeframe, confirmed bars; warmup period + 1 bars. No additional feeds.',
         availability='preview', verification='Full library integration and benchmark verification pending; no performance claim.'),
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
                  "from nautilus_trader.examples.strategies.ema_cross import EMACross, EMACrossConfig\n")
        document = dict(version=1,engine='nautilus_trader',engine_version='1.231.0',source=source,
            class_name='EMACross',config_class='EMACrossConfig',bar_minutes=[minutes],dependencies=entry['dependencies'],
            provenance=f"{entry['source_url']} SHA256 {EMA_HASH}; LGPL-3.0; imported installed source, not copied.",
            config=dict(instrument_id='$instrument',bar_type=f'$bar:{minutes}',trade_size=values['quantity'],
                        fast_ema_period=values['fast'],slow_ema_period=values['slow'],request_bars=False,
                        subscribe_trade_ticks=False,subscribe_quote_ticks=False,close_positions_on_stop=True))
        preview(document)
        profile = Profile(market='linear',primary_minutes=minutes).snapshot()
        kind = 'native'; warmup = values['slow']
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


def create_copy(store, **request):
    prepared = prepare(**request)
    ident = store.save_strategy(prepared['name']+' copy',prepared['kind'],prepared['document'],None,profile=prepared['profile'])
    return {'strategy_id':ident,'contract':prepared['contract']}
