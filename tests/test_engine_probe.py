"""Independent synthetic execution checks for the candidate engine, not live trading."""
from decimal import Decimal
import unittest

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.models import FillModel
from nautilus_trader.accounting.margin_models import StandardMarginModel
from nautilus_trader.model.enums import PositionSide
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig, StrategyConfig
from nautilus_trader.model.currencies import BTC, USDT
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import CurrencyPair, CryptoPerpetual
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.trading.strategy import Strategy


def instrument(perpetual=False, fee="0.001"):
    """Invented TEST venue/instrument; no historical exchange metadata is implied."""
    common = dict(
        instrument_id=InstrumentId.from_str("BTCUSDT.TEST"),
        raw_symbol=Symbol("BTCUSDT"), base_currency=BTC, quote_currency=USDT,
        price_precision=2, size_precision=3,
        price_increment=Price.from_str("0.01"), size_increment=Quantity.from_str("0.001"),
        maker_fee=Decimal(fee), taker_fee=Decimal(fee), ts_event=0, ts_init=0,
    )
    if perpetual:
        return CryptoPerpetual(**common, settlement_currency=USDT, is_inverse=False,
                               margin_init=Decimal("0.1"), margin_maint=Decimal("0.05"))
    return CurrencyPair(**common)


class RoundTrip(Strategy):
    def __init__(self, instrument_id, side, quantity="1.000"):
        super().__init__(StrategyConfig(order_id_tag="001"))
        self.instrument_id = instrument_id
        self.side = side
        self.quantity = Quantity.from_str(quantity)
        self.seen = 0
        self.fills = []

    def on_start(self):
        self.subscribe_quote_ticks(self.instrument_id)

    def on_quote_tick(self, tick):
        self.seen += 1
        if self.seen == 1:
            self.submit_order(self.order_factory.market(self.instrument_id, self.side, self.quantity))
        elif self.seen == 3:
            self.close_all_positions(self.instrument_id)

    def on_order_filled(self, event):
        self.fills.append((str(event.order_side), str(event.last_px), str(event.commission)))


def run_round_trip(perpetual=False, side=OrderSide.BUY, fee="0.001", slipped=False):
    asset = instrument(perpetual, fee)
    engine = BacktestEngine(BacktestEngineConfig(logging=LoggingConfig(bypass_logging=True)))
    engine.add_venue(Venue("TEST"), OmsType.NETTING,
                     AccountType.MARGIN if perpetual else AccountType.CASH,
                     [Money(1000, USDT)], base_currency=USDT if perpetual else None,
                     default_leverage=Decimal(10 if perpetual else 1),
                     fill_model=FillModel(prob_slippage=1.0 if slipped else 0.0))
    engine.add_instrument(asset)
    strategy = RoundTrip(asset.id, side)
    engine.add_strategy(strategy)
    quotes=[]
    for i, price in enumerate(["100.00", "100.00", "110.00", "110.00"], 1):
        quotes.append(QuoteTick(asset.id, Price.from_str(price), Price.from_str(price),
                                Quantity.from_str("100.000"), Quantity.from_str("100.000"),
                                i*1_000_000_000, i*1_000_000_000))
    engine.add_data(quotes)
    try:
        engine.run()
        balance=engine.cache.account_for_venue(Venue("TEST")).balance_total(USDT).as_decimal()
        return balance, strategy.fills
    finally:
        engine.dispose()


class EngineExecutionTests(unittest.TestCase):
    def test_explicit_margin_model_uses_notional_without_double_leverage(self):
        asset=instrument(True)
        model=StandardMarginModel()
        quantity=Quantity.from_str("1.000")
        price=Price.from_str("100.00")
        self.assertEqual(model.calculate_margin_init(asset,quantity,price,Decimal(10)).as_decimal(),Decimal("10"))
        self.assertEqual(model.calculate_margin_maint(asset,PositionSide.LONG,quantity,price,Decimal(10)).as_decimal(),Decimal("5"))

    def test_spot_net_cash_after_round_trip(self):
        # Buy 1 at 100, sell at 110, commissions 0.10 + 0.11 => 1009.79.
        balance, fills=run_round_trip()
        self.assertEqual(len(fills), 2, fills)
        self.assertEqual(balance, Decimal("1009.79"))

    def test_perpetual_long_and_short(self):
        for side, expected in [(OrderSide.BUY,"1009.79"),(OrderSide.SELL,"989.79")]:
            with self.subTest(side=side):
                balance,fills=run_round_trip(True,side)
                self.assertEqual(len(fills),2,fills)
                self.assertEqual(balance,Decimal(expected))

    def test_fees_change_balance(self):
        self.assertEqual(run_round_trip(fee="0")[0],Decimal("1010"))

    def test_one_tick_slippage_changes_fills_and_balance(self):
        # Adverse one-tick fills: 100.01 and 109.99; fees total 0.21000.
        balance,fills=run_round_trip(slipped=True)
        self.assertEqual(balance,Decimal("1009.77"),fills)


if __name__ == "__main__":
    unittest.main()
