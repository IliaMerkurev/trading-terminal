import unittest
from terminal.display_events import EventCollector


class EventCollectorTests(unittest.TestCase):
    def collector(self, start=0, end=300):
        return EventCollector([dict(id='cipher', type='vmc_cipher_b')], 1, start, end)

    def event(self, **kw):
        return dict(kind='regular_bullish', oscillator='wt', pivot_time=180,
            confirmed_at=300, previous_pivot_time=60, value=-40., previous_value=-60.,
            index=5, pivot_index=3, **kw)

    def test_end_conversion_once_and_stable_identity(self):
        a = self.collector(); b = self.collector(start=120)
        e = self.event()
        for collector in (a, b):
            collector.observe('cipher', [e, e], 0)
        ea, eb = (c.result()['instances']['cipher'] for c in (a, b))
        self.assertEqual(ea, eb)
        self.assertEqual(len(ea), 1)
        self.assertEqual(ea[0]['confirmed_at'], 360)
        self.assertEqual(ea[0]['pivot_time'], 240)
        self.assertEqual(ea[0]['previous_pivot_time'], 120)
        self.assertNotIn('index', ea[0]); self.assertNotIn('pivot_index', ea[0])
        self.assertEqual(e['confirmed_at'], 300)

    def test_no_future_confirmation_even_if_pivot_in_window(self):
        for end in (180, 240):
            c = self.collector(end=end); c.observe('cipher', [self.event()], 0)
            self.assertEqual(c.result()['instances']['cipher'], [])

    def test_viewport_bounded_and_no_cross_gap_connector(self):
        c = self.collector(start=360, end=600)
        c.observe('cipher', [self.event()], 0)
        self.assertEqual(c.result()['instances']['cipher'], [])
        with self.assertRaisesRegex(ValueError, 'segment'):
            self.collector().observe('cipher', [self.event()], 120)

    def test_reject_invalid_event_values_clock_and_oscillator(self):
        for change in ({'value': float('nan')}, {'confirmed_at': 180.0},
                       {'pivot_time': 360}, {'oscillator': 'price'},
                       {'previous_pivot_time': 180}):
            e = self.event(); e.update(change)
            with self.assertRaises(ValueError): self.collector().observe('cipher', [e], 0)

    def test_multiple_same_bar_events_remain_distinct(self):
        c = self.collector(); e = self.event(); other = dict(e, kind='divergence_buy_dot')
        c.observe('cipher', [e, other], 0)
        self.assertEqual(len(c.result()['instances']['cipher']), 2)
