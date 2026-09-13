"""Exact path crossings and lifecycle accounting through the retained engine."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest
from terminal.paper import PaperEngine
from test_simulation import flat, signal_map


class ManagedExecutionTests(unittest.TestCase):
    def profile(self, **config):
        return Profile(version=2, market='linear', leverage='2', primary_minutes=1, allocation='100', fee_rate='0',
                       mark_mode='last_proxy', funding_mode='assumed_zero', position_management={'max_entries':4, **config})

    def test_dca_then_full_exit_reconciles_and_is_repeatable(self):
        profile = self.profile(dca=[{'distance':'.2','allocation_percent':'10'}])
        data = [Candle(0,100,100,100,100,100),Candle(60,100,100,75,100,100)]
        a = run_backtest(data,profile,signal_map({60:{'entry_long':True}}))
        b = run_backtest(data,profile,signal_map({60:{'entry_long':True}}))
        # Initial 2*100; add 2.5*80; exit 4.5*100 => +50.
        self.assertEqual(a,b)
        self.assertEqual(D(a['metrics']['net_pnl']),D(50))
        self.assertEqual([D(fill['price']) for fill in a['fills']], [D(100),D(80),D(100)])
        self.assertEqual(a['metrics']['trade_count'],1)
        self.assertEqual(a['trades'][0]['entry_count'],2)

    def test_three_partial_thresholds_in_one_segment(self):
        profile = replace(self.profile(partial_take=[{'distance':'.03','fraction':'.25'},
            {'distance':'.06','fraction':'.25'},{'distance':'.1','fraction':'.5'}]),allocation='200',path='OHLC')
        data = [Candle(0,100,100,100,100,100),Candle(60,100,112,100,112,100)]
        result = run_backtest(data,profile,signal_map({60:{'entry_long':True}}))
        self.assertEqual([D(f['quantity']) for f in result['fills']], [D(4),D(1),D(1),D(2)])
        self.assertEqual([D(f['price']) for f in result['fills']], [D(100),D(103),D(106),D(110)])
        self.assertEqual(D(result['metrics']['net_pnl']),D(29))
        self.assertEqual(result['metrics']['trade_count'],1)

    def test_stop_crossing_prevents_later_dca_and_same_step_reentry(self):
        profile = replace(self.profile(dca=[{'distance':'.2','allocation_percent':'10'}]),stop_loss='.15')
        data = [Candle(0,100,100,100,100,100),Candle(60,100,100,70,90,100)]
        result = run_backtest(data,profile,signal_map({60:{'entry_long':True}}))
        self.assertEqual([f['reason'] for f in result['fills']], ['entry','stop_loss'])
        self.assertEqual(D(result['fills'][1]['price']),D(85))
        self.assertEqual(D(result['metrics']['net_pnl']),D(-30))

    def test_funding_after_scaling_and_reduction_reconciles_actual_cash(self):
        profile = replace(self.profile(repeated_entry='scale',partial_take=[{'distance':'.1','fraction':'.5'}]),funding_mode='history')
        data = flat([100,100,100,110,110])
        # 2 entry, then 2 add. Funding 4*110*1%=4.4 at t=180,
        # applied at the newly observed boundary price before the partial exit.
        # Partial at 110 realizes 20 on two, final realizes another 20;
        # second funding charges remaining 2*110*1%=2.2 at t=240.
        result = run_backtest(data,profile,signal_map({60:{'entry_long':True},180:{'entry_long':True}}),funding={180:'.01',240:'.01'})
        self.assertEqual(D(result['metrics']['funding']),D('-6.6'))
        self.assertEqual(D(result['metrics']['net_pnl']),D('33.4'))
        self.assertEqual([D(f['quantity']) for f in result['fills']],[D(2),D(2),D(2),D(2)])

    def test_liquidation_after_scale_uses_total_quantity_and_mark(self):
        profile = replace(self.profile(repeated_entry='scale',scale_allocation_percent='40'),capital='100',allocation='40',
                          leverage='10',maintenance_rate='.05',mark_mode='history')
        data = flat([100,100,100,100])
        marks = {c.time:c for c in flat([100,100,100,85])}
        result = run_backtest(data,profile,signal_map({60:{'entry_long':True},180:{'entry_long':True}}),marks=marks)
        # Quantity=8, mark loss=120, equity=-20, maintenance=34.
        # Observed last remains 100, so the liquidation fill realizes zero.
        self.assertEqual([f['reason'] for f in result['fills']],['entry','repeated_entry','liquidation'])
        self.assertEqual(D(result['fills'][-1]['quantity']),D(8))
        self.assertEqual(D(result['metrics']['final_equity']),D(100))

    def test_confirmed_atr_warmup_and_future_perturbation(self):
        profile = self.profile(atr_period=2,atr_stop_multiplier='2')
        data = [Candle(0,100,102,98,100,100),Candle(60,100,102,98,100,100),Candle(120,100,101,85,95,100)]
        result = run_backtest(data,profile,signal_map({60:{'entry_long':True},120:{'entry_long':True}}))
        self.assertEqual(result['fills'][0]['time_ns'],120*10**9-1)
        self.assertEqual(D(result['fills'][1]['price']),D(92))
        self.assertEqual(result['fills'][1]['reason'],'atr_stop')
        changed = run_backtest([*data,Candle(180,95,1000,90,900,100)],profile,signal_map({60:{'entry_long':True},120:{'entry_long':True}}))
        self.assertEqual(result['fills'],changed['fills'])

    def test_observed_paper_scaling_partial_funding_and_restart_replay(self):
        profile = replace(self.profile(repeated_entry='scale'),fee_rate='.001',funding_mode='history')
        inputs = [dict(time_ns=10**9,price='100',signals={'entry_long':True}),
                  dict(time_ns=2*10**9,price='100',signals={'entry_long':False}),
                  dict(time_ns=3*10**9,price='100',signals={'entry_long':True}),
                  dict(time_ns=4*10**9,price='110',funding_rate='.01',manual_action='reduce_25'),
                  dict(time_ns=5*10**9,price='120',manual_action='close')]
        recordings = []
        for _ in range(2):
            paper = PaperEngine(profile)
            try: recordings.append([paper.observe(**value) for value in inputs])
            finally: paper.close()
        self.assertEqual(recordings[0],recordings[1])
        results = recordings[0]
        self.assertEqual(D(results[2]['position']['quantity']),D(4))
        self.assertEqual(D(results[3]['position']['quantity']),D(3))
        self.assertEqual(D(results[3]['position']['initial_margin']),D(150))
        # Gross=10+60=70; fees=.2+.2+.11+.36=.87; funding=-4.4.
        self.assertEqual(D(results[-1]['cash']),D('1064.73'))
        self.assertIsNone(results[-1]['position'])
        events = [e for result in results for e in result['lifecycle_events']]
        self.assertEqual({e['position_id'] for e in events},{1})
        self.assertEqual([e['type'] for e in events],['entry','scale','funding','reduction','exit'])

    def test_paper_observed_gap_executes_observed_price_not_historical_threshold(self):
        profile = replace(self.profile(),stop_loss='.05')
        paper = PaperEngine(profile)
        try:
            paper.observe(10**9,100,manual_action='buy')
            result = paper.observe(2*10**9,80)
            self.assertEqual(result['fills'][0]['reason'],'stop_loss')
            self.assertEqual(D(result['fills'][0]['price']),D(80))
            self.assertEqual(D(result['net_pnl']),D(-40))
        finally: paper.close()

    def test_manual_cannot_override_a_same_quote_protective_exit(self):
        paper = PaperEngine(replace(self.profile(),stop_loss='.05'))
        try:
            paper.observe(10**9,100,manual_action='buy')
            result = paper.observe(2*10**9,90,manual_action='buy')
            self.assertEqual(len(result['fills']),1)
            self.assertIsNone(result['position'])
        finally: paper.close()


if __name__ == '__main__': unittest.main()
