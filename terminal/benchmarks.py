"""Passive intent schedules and saved-result metrics; execution remains in simulation.py."""
import calendar
from datetime import datetime, timezone
from decimal import Decimal
import math

from terminal.data import digest, runtime_snapshot
from terminal.profile import Profile, dec

VERSION = 1
SPOT_EXECUTION_FIELDS = ('fee_rate', 'slippage', 'tick_size', 'quantity_step',
                         'min_quantity', 'max_quantity', 'min_notional', 'max_notional')


def execution_assumptions(value):
    fields = {'version', 'fee_source', 'fee_note', 'slippage_source', 'precision_source', 'precision_note'}
    if not isinstance(value, dict) or set(value) != fields or type(value['version']) is not int or value['version'] != 1:
        raise ValueError('Invalid spot execution assumptions')
    if value['fee_source'] not in ('explicit_spot', 'explicit_shared') or value['slippage_source'] not in ('explicit_spot', 'explicit_shared'):
        raise ValueError('Spot costs must be explicitly reviewed')
    if value['precision_source'] not in ('dataset_metadata', 'reviewed_manual'):
        raise ValueError('Spot precision must have an explicit modeling source')
    for key in ('fee_note', 'precision_note'):
        if not isinstance(value[key], str) or not value[key].strip() or len(value[key]) > 1000 or '\x00' in value[key]:
            raise ValueError('Spot assumption notes must contain 1–1000 characters')
    return dict(value)


def independent_spot(value, strategy):
    """Validate reviewed inputs without inheriting linear fees or instrument limits."""
    if not isinstance(value, dict) or set(value) != {'version', 'profile', 'assumptions'} or type(value['version']) is not int or value['version'] != 1:
        raise ValueError('Spot benchmark N/A: an independently specified spot execution profile and explicit spot fee assumption are required')
    raw = value['profile']
    if not isinstance(raw, dict) or any(key not in raw for key in (*SPOT_EXECUTION_FIELDS, 'market', 'symbol', 'capital')):
        raise ValueError('Spot benchmark N/A: explicitly supply all spot costs, precision and order limits')
    if 'tier_assumption' in raw and not isinstance(raw['tier_assumption'],str):
        raise ValueError('Spot tier assumption must be text')
    p = Profile(**raw)
    if (p.market != 'spot' or p.symbol != strategy.symbol or dec(p.capital) != dec(strategy.capital)
            or p.execution_minutes != strategy.execution_minutes or p.version != 1 or dec(p.leverage) != 1
            or p.position_management is not None or dec(p.stop_loss) or dec(p.take_profit)):
        raise ValueError('Independent spot settings must match symbol, capital and resolution without leverage or protection')
    # Passive scheduling owns deployment. These fixed account conventions cannot
    # acquire strategy sizing, funding or maintenance policies by accident.
    p = Profile(**{**p.snapshot(), 'primary_minutes':p.execution_minutes, 'sizing':'percent', 'allocation':'100',
                   'evaluation':'closed', 'funding_mode':'assumed_zero', 'mark_mode':'last_proxy',
                   'maintenance_rate':'0', 'gap_policy':'reject', 'tier_assumption':'Unleveraged passive spot account; no funding or margin'})
    assumptions = execution_assumptions(value['assumptions'])
    return {'version':1, 'profile':p.snapshot(), 'assumptions':assumptions}


def validate_document(document, profile, dataset, runtime=None):
    if not isinstance(document,dict) or set(document)-{'execution_assumptions'}!={'benchmark','version','start','end','interval'} or document['benchmark']!='passive' or type(document['version']) is not int or document['version']!=VERSION:
        raise ValueError('Invalid benchmark document')
    if 'execution_assumptions' in document:execution_assumptions(document['execution_assumptions'])
    if profile.version != 1:
        raise ValueError('Passive execution requires profile version 1')
    return contract(profile,dataset,document['start'],document['end'],document['interval'],runtime,document.get('execution_assumptions'))


def start_or_reuse(jobs, profile, dataset_id, start, end, interval='weekly', owner=None, execution_assumptions=None):
    if not isinstance(profile,Profile):profile=Profile(**profile)
    document=dict(benchmark='passive',version=VERSION,start=start,end=end,interval=interval)
    if execution_assumptions is not None:document['execution_assumptions']=execution_assumptions
    frozen=validate_document(document,profile,jobs.datasets.describe(dataset_id))
    jobs.datasets.check_profile(jobs.datasets.describe(dataset_id),profile)
    with jobs.lock:
        # Existing results remain immutable even when source history is no longer available.
        # Only a completed result for this exact frozen contract is reusable.
        with jobs.store.connect() as db:
            row=db.execute("SELECT id FROM runs WHERE status='completed' AND json_extract(summary,'$.origin')='local' AND json_extract(manifest,'$.research.benchmark_contract')=? ORDER BY created_at,id LIMIT 1",(frozen['contract_sha256'],)).fetchone()
        if row:
            jobs.store.result(row['id'])  # Check saved result integrity before exposing it.
            return {'run_id':row['id'],'reused':True,'contract':frozen}
        ident=jobs.start(document,profile,dataset_id,research={'benchmark_contract':frozen['contract_sha256']},owner=owner)
        return {'run_id':ident,'reused':False,'contract':frozen}


def schedule(start, end, interval):
    if type(start) is not int or type(end) is not int or start % 60 or end % 60 or start >= end:
        raise ValueError('Benchmark range must be increasing UTC minute boundaries')
    if interval not in ('once','daily','weekly','monthly'):
        raise ValueError('Unsupported benchmark schedule')
    dates = []; stamp = start; index = 0
    origin = datetime.fromtimestamp(start, timezone.utc)
    while stamp < end:
        dates.append(stamp)
        if len(dates) > 10000:
            raise ValueError('Benchmark schedule exceeds 10,000 purchases')
        if interval == 'once': break
        index += 1
        if interval in ('daily','weekly'):
            stamp = start + index * (86400 if interval == 'daily' else 7*86400)
        else:
            year, month = divmod(origin.year*12 + origin.month-1 + index, 12)
            month += 1
            stamp = int(origin.replace(year=year,month=month,day=min(origin.day,calendar.monthrange(year,month)[1])).timestamp())
    return dates


def contract(profile, dataset, start, end, interval='weekly', runtime=None, assumptions=None):
    if not isinstance(profile, Profile): profile = Profile(**profile)
    if profile.market != 'spot' or dataset['market'] != 'spot' or dataset['symbol'] != profile.symbol:
        raise ValueError('Passive alternatives require actual matching spot history')
    if profile.position_management is not None or dec(profile.stop_loss) or dec(profile.take_profit):
        raise ValueError('Passive benchmarks exclude strategy position/protection policies')
    if not dataset['range'][0] <= start < end <= dataset['range'][1]:
        raise ValueError('Benchmark range outside source history')
    dates = schedule(start,end,interval)
    seconds=profile.execution_minutes*60
    if start%seconds or end%seconds or any(t%seconds for t in dates):
        raise ValueError('Benchmark schedule and range must align to execution candles')
    if dataset.get('interval_seconds',60)!=seconds:raise ValueError('Benchmark dataset resolution differs')
    value = dict(version=VERSION,metric_version=VERSION,execution='retained-nautilus',source=dataset['source'],
        dataset_id=dataset['id'],content_sha256=dataset['content_sha256'],symbol=profile.symbol,
        profile=profile.snapshot(),start=start,end=end,schedule=interval,purchases=dates,
        end_treatment='full_close_with_costs',cash_yield='0',external_cashflows=False,runtime=runtime if runtime is not None else runtime_snapshot())
    if assumptions is not None:value['execution_assumptions']=execution_assumptions(assumptions)
    return {**value,'contract_sha256':digest(value)}


def metrics(result, start, end):
    if type(start) is not int or type(end) is not int or end <= start:
        raise ValueError('Invalid metric evaluation period')
    if result.get('status') != 'completed':
        raise ValueError('Only completed results have performance metrics')
    capital = dec(result['profile']['capital']); equity = dec(result['metrics']['final_equity'])
    pnl = equity-capital; days = Decimal(end-start)/Decimal(86400)
    annualized = None; reason = 'Period shorter than 365 days'
    if equity <= 0: reason = 'Nonpositive final equity'
    elif days >= 365:
        try: candidate = math.expm1(math.log(float(equity/capital))*365/float(days))
        except (OverflowError,ValueError): candidate = math.inf
        if math.isfinite(candidate): annualized=candidate; reason=None
        else: reason='Annualized result outside numeric range'
    return dict(version=VERSION,net_pnl=str(pnl),period_return=str(pnl/capital),final_equity=str(equity),
        max_drawdown=result['metrics']['max_drawdown'],completed_positions=result['metrics']['trade_count'],
        win_rate=result['metrics']['win_rate'],fees=result['metrics']['fees'],funding=result['metrics']['funding'],
        annualized_geometric_return=annualized,annualized_unavailable_reason=reason,
        annualization_convention='365-day geometric; no external cashflows; N/A below 365 days')


def delta(strategy, baseline):
    return {'usdt':str(dec(strategy['net_pnl'])-dec(baseline['net_pnl'])),
            'percentage_points':str(100*(dec(strategy['period_return'])-dec(baseline['period_return'])))}


def run(candles, profile, start, end, interval='weekly', progress=lambda _:None):
    """Trusted internal entrypoint; no native code, deposits or alternative fill model."""
    from terminal.simulation import run_backtest
    if not isinstance(profile, Profile): profile = Profile(**profile)
    if profile.market != 'spot' or profile.version != 1 or profile.position_management is not None or dec(profile.stop_loss) or dec(profile.take_profit):
        raise ValueError('Passive execution requires spot profile 1 without position/protection policies')
    dates = schedule(start,end,interval)
    bars = [bar for bar in candles if start <= bar.time < end]
    result = run_backtest(bars,profile,None,progress=progress,benchmark={'dates':dates,'start':start,'end':end})
    result['benchmark'] = dict(version=VERSION,schedule=interval,purchases=dates,start=start,end=end,
                               end_treatment='full_close_with_costs',cash_yield='0',external_cashflows=False)
    result['research_metrics'] = metrics(result,start,end)
    return result
