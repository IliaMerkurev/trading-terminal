"""Execute an installed LGPL example without copying or rewriting its source."""
from decimal import Decimal
import unittest

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig
from nautilus_trader.examples.strategies.ema_cross import EMACross, EMACrossConfig
from nautilus_trader.model.data import Bar, BarType, QuoteTick
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.model.currencies import USDT
from terminal.risk_gateway import RiskGateway
from test_engine_probe import instrument


class NativeProbeTests(unittest.TestCase):
    def test_installed_native_example_runs_unchanged(self):
        asset = instrument(fee="0")
        bar_type = BarType.from_str("BTCUSDT.TEST-1-MINUTE-LAST-EXTERNAL")
        strategy = EMACross(EMACrossConfig(instrument_id=asset.id, bar_type=bar_type,
            trade_size=Decimal(1), fast_ema_period=2, slow_ema_period=3,
            request_bars=False, subscribe_trade_ticks=False, close_positions_on_stop=True))
        engine = BacktestEngine(BacktestEngineConfig(logging=LoggingConfig(bypass_logging=True)))
        engine.add_venue(Venue("TEST"), OmsType.NETTING, AccountType.CASH,
                         [Money(1000, USDT)], bar_execution=False, use_message_queue=False)
        engine.add_instrument(asset)
        guard = RiskGateway(engine, asset)
        engine.add_strategy(strategy)
        for i, price in enumerate([100, 102, 104, 106, 108], 1):
            ts = i * 60_000_000_000
            px = Price(price, 2)
            engine.add_data([QuoteTick(asset.id, px, px, Quantity(100, 3), Quantity(100, 3), ts, ts)])
            engine.add_data([Bar(bar_type, Price(price-1, 2), Price(price+1, 2), Price(price-2, 2),
                                 px, Quantity(100, 3), ts, ts)])
        try:
            engine.run()
            guard.assert_supported()
            self.assertEqual(guard.denials, [])
            positions = engine.cache.positions_closed()
            self.assertEqual(len(positions), 1)
            # EMA(2) > EMA(3) at third sample: buy 104, close at last quote 108.
            self.assertEqual(positions[0].realized_pnl.as_decimal(), Decimal(4))
            self.assertEqual(engine.cache.account_for_venue(Venue("TEST")).balance_total(USDT).as_decimal(), Decimal(1004))
        finally:
            engine.dispose()
