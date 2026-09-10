"""Hand-derived H1 expectations, independently of the candidate engine."""
import unittest
from nautilus_trader.indicators import SimpleMovingAverage
from terminal.series import Candle, PartialBars


def evaluate(prices, intrabar=True):
    frames = PartialBars(60)
    output = []
    for i, price in enumerate(prices):
        _, complete = frames.update(Candle(i*60, price, price, price, price, 1))
        if not intrabar and not complete:
            continue
        # Rebuild from primary bars, never from minute samples.
        indicator = SimpleMovingAverage(2)
        for bar in frames.snapshot():
            indicator.update_raw(bar.close)
        output.append((i, indicator.value if indicator.initialized else None,
                       indicator.initialized and indicator.value > 110))
    return output, frames


class CausalProbeTests(unittest.TestCase):
    def test_signal_exists_inside_hour_and_disappears_at_close(self):
        prices = [100]*60 + [130]*30 + [90]*30
        partial, frames = evaluate(prices)
        closed, _ = evaluate(prices, False)
        self.assertEqual(partial[60], (60, 115, True))
        self.assertEqual(partial[90], (90, 95, False))
        self.assertEqual(closed, [(59, None, False), (119, 95, False)])
        self.assertEqual(len(frames.closed), 2)
        self.assertEqual(frames.closed[1].volume, 60)
        self.assertEqual(frames.closed[1].high, 130)

    def test_future_perturbations_cannot_change_earlier_values(self):
        baseline, _ = evaluate([100]*60 + [130]*30 + [90]*30)
        changed, _ = evaluate([100]*60 + [130]*30 + [999]*30)
        self.assertEqual(baseline[:90], changed[:90])

    def test_missing_minutes_do_not_form_complete_hour(self):
        frames = PartialBars(60)
        for i in range(60):
            if i != 30:
                frames.update(Candle(i*60, 100, 100, 100, 100, 1))
        self.assertEqual(frames.closed, [])
        self.assertEqual(frames.snapshot(), [])
        self.assertEqual(frames.gaps, [(1800, 1860)])

    def test_duplicate_or_out_of_order_data_fails(self):
        frames = PartialBars()
        bar = Candle(0, 100, 100, 100, 100, 1)
        frames.update(bar)
        with self.assertRaises(ValueError):
            frames.update(bar)
