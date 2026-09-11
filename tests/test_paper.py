from dataclasses import replace
import unittest

from terminal.paper import PaperEngine
from terminal.profile import Profile, dec


class PaperTests(unittest.TestCase):
    def engine(self,**fields):
        engine=PaperEngine(Profile(primary_minutes=1,allocation='100',**fields))
        self.addCleanup(engine.close)
        return engine

    def test_spot_fees_independently_expected(self):
        e=self.engine()
        opened=e.observe(60_000_000_000,'100',signals={'entry_long':True})
        self.assertEqual(dec(opened['cash']),dec('899.90'))
        self.assertEqual(dec(opened['equity']),dec('999.90'))
        closed=e.observe(120_000_000_000,'110',signals={'exit_long':True})
        self.assertEqual(closed['equity'],'1009.79')
        self.assertIsNone(closed['position'])

    def test_perpetual_short_fees_and_funding(self):
        e=self.engine(market='linear',leverage='2')
        opened=e.observe(60_000_000_000,'100',mark='100',signals={'entry_short':True})
        self.assertEqual(opened['position']['quantity'],'2.000')
        paid=e.observe(120_000_000_000,'100',mark='100',funding_rate='.01')
        self.assertEqual(dec(paid['cash']),dec('1001.80'))  # +2 funding, -.20 entry fee
        closed=e.observe(180_000_000_000,'90',mark='90',signals={'exit_short':True})
        self.assertEqual(closed['equity'],'1021.62')  # +20 price PnL, +2 funding, -.38 fees

    def test_stop_uses_first_observed_price_not_invented_threshold(self):
        e=self.engine(stop_loss='.05',fee_rate='0')
        e.observe(60_000_000_000,'100',signals={'entry_long':True})
        closed=e.observe(61_000_000_000,'80',signals={'entry_long':True})
        self.assertEqual(closed['fills'][0]['price'],'80.00')
        self.assertEqual(closed['fills'][0]['reason'],'stop_loss')
        self.assertEqual(dec(closed['equity']),dec('980.00'))
        self.assertIsNone(closed['position'])

    def test_short_take_adverse_slippage_and_mark_liquidation(self):
        e=self.engine(market='linear',take_profit='.05',slippage='.01',fee_rate='0')
        e.observe(60_000_000_000,'100',mark='100',signals={'entry_short':True})
        closed=e.observe(61_000_000_000,'90',mark='90')
        self.assertEqual(closed['fills'][0]['price'],'90.90')
        self.assertEqual(closed['fills'][0]['reason'],'take_profit')
        liquid=self.engine(market='linear',capital='100',leverage='10',fee_rate='0')
        liquid.observe(60_000_000_000,'100',mark='100',signals={'entry_long':True})
        result=liquid.observe(61_000_000_000,'100',mark='80')
        self.assertEqual(result['fills'][0]['reason'],'liquidation')
        self.assertEqual(result['fills'][0]['price'],'100.00')

    def test_reconstruction_matches_and_shutdown_does_not_close_position(self):
        observations=[(60_000_000_000,'100',{'entry_long':True}),(61_000_000_000,'110',None)]
        a,b=self.engine(),self.engine()
        for time,price,signals in observations:
            self.assertEqual(a.observe(time,price,signals=signals),b.observe(time,price,signals=signals))
        self.assertIsNotNone(a.snapshot()['position'])
        before=list(a.strategy.fills);a.close();self.assertEqual(a.strategy.fills,before)
        with self.assertRaises(ValueError):b.observe(60_000_000_000,'100')
