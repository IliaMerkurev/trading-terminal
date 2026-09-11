from dataclasses import replace
from decimal import Decimal as D
import unittest
from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest


class ExecutionV2Tests(unittest.TestCase):
    def run_case(self,profile,bars,side='long',**kwargs):
        return run_backtest(bars,profile,lambda bars,time,complete:{'signals':{f'entry_{side}':time==60},'values':{}},**kwargs)

    def test_independent_stop_take_paths_for_both_sides_and_legacy(self):
        bars=[Candle(0,100,100,100,100,100),Candle(60,100,120,80,100,100)]
        for side in ('long','short'):
            for path in ('OLHC','OHLC'):
                p=Profile(version=2,primary_minutes=1,market='linear',mark_mode='last_proxy',funding_mode='assumed_zero',fee_rate='0',stop_loss='.05',take_profit='.05',path=path)
                r=self.run_case(p,bars,side)
                expected=95 if path=='OLHC' else 105
                reason='stop_loss' if (side=='long')==(path=='OLHC') else 'take_profit'
                self.assertEqual(D(r['fills'][1]['price']),expected)
                self.assertEqual(r['fills'][1]['reason'],reason)
                self.assertEqual(D(r['metrics']['net_pnl']),D(expected-100)*(1 if side=='long' else -1))
                legacy=self.run_case(replace(p,version=1),bars,side)
                self.assertEqual(D(legacy['fills'][1]['price']),80 if path=='OLHC' else 120)

    def test_opening_gap_is_not_a_continuous_segment(self):
        p=Profile(version=2,primary_minutes=1,fee_rate='0',stop_loss='.05')
        bars=[Candle(0,100,100,100,100,100),Candle(60,80,100,70,90,100)]
        result=self.run_case(p,bars)
        self.assertEqual(D(result['fills'][1]['price']),80)

    def test_levels_are_inactive_before_entry_and_costs_follow_crossing(self):
        p=Profile(version=2,primary_minutes=1,fee_rate='.001',stop_loss='.05',slippage='.01')
        bars=[Candle(0,100,120,60,100,100),Candle(60,100,100,80,90,100)]
        result=self.run_case(p,bars)
        # Entry=101, qty=.990; stop=95.95, adverse sell=94.9905 rounded down=94.99.
        self.assertEqual(D(result['fills'][0]['price']),101)
        self.assertEqual(D(result['fills'][1]['price']),D('94.99'))
        self.assertGreater(result['fills'][1]['time_ns'],60_000_000_000)
        self.assertEqual(D(result['metrics']['fees']),D('0.1940301'))

    def test_continuous_mark_liquidation_and_funding_precede_trade_protection(self):
        p=Profile(version=2,primary_minutes=1,market='linear',capital='20',allocation='10',leverage='10',maintenance_rate='.05',fee_rate='0',stop_loss='.05')
        bars=[Candle(0,100,100,100,100,100),Candle(60,100,100,90,100,100)]
        # With one unit and cash 20, liquidation mark is 80/.95; separate mark
        # reaches it before the trade path reaches 95. No fabricated mark fill.
        marks={0:bars[0],60:Candle(60,100,100,50,100,100)}
        r=self.run_case(p,bars,marks=marks,funding={})
        self.assertEqual(r['fills'][1]['reason'],'liquidation')
        self.assertEqual(D(r['fills'][1]['price']),D('96.84'))
        funded=self.run_case(p,bars,marks=marks,funding={60:'.16'})
        self.assertEqual([e['type'] for e in funded['events']],['funding','liquidation'])
        self.assertEqual(D(funded['fills'][1]['price']),100)

    def test_partial_h1_remains_causal_in_version_two(self):
        from terminal.graph import GraphEvaluator,example_graph
        def history(prices):return [Candle(i*60,p,p,p,p,100) for i,p in enumerate(prices)]
        baseline=history([100]*60+[130]*30+[90]*30)
        changed=history([100]*60+[130]*30+[999]*30)
        p=Profile(version=2,primary_minutes=60,evaluation='intrabar',fee_rate='0')
        a=run_backtest(baseline,p,GraphEvaluator(example_graph()))
        b=run_backtest(changed,p,GraphEvaluator(example_graph()))
        self.assertEqual(a['fills'][0]['time_ns'],3660*10**9-1)
        self.assertEqual(a['indicators'][0]['values']['mean.value'],None)
        self.assertEqual(next(x for x in a['indicators'] if x['time']==3660)['values']['mean.value'],115)
        self.assertEqual([x for x in a['indicators'] if x['time']<=5400],[x for x in b['indicators'] if x['time']<=5400])
        self.assertEqual([x for x in a['fills'] if x['time_ns']<5400*10**9],[x for x in b['fills'] if x['time_ns']<5400*10**9])
        closed=run_backtest(baseline,replace(p,evaluation='closed'),GraphEvaluator(example_graph()))
        self.assertEqual(closed['metrics']['trade_count'],0)
