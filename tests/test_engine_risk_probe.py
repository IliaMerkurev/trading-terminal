"""Prove a public simulation-module extension, not built-in funding/liquidation."""
from decimal import Decimal
import unittest

from nautilus_trader.backtest.modules import SimulationModule
from nautilus_trader.backtest.config import SimulationModuleConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig
from nautilus_trader.accounting.margin_models import StandardMarginModel
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money, Price, Quantity
from test_engine_probe import instrument, RoundTrip
from terminal.risk_gateway import RiskGateway


class RiskProbe(SimulationModule):
    """Single-instrument cross-margin, explicit scheduled synthetic mark/funding."""
    def __init__(self, strategy, mark="100", funding="0", liquidate=False):
        super().__init__(SimulationModuleConfig())
        self.strategy=strategy
        self.mark=Decimal(mark)
        self.rate=Decimal(funding)
        self.liquidate=liquidate
        self.applied=False
        self.events=[]

    def process(self, ts_now):
        if self.applied or ts_now < 2_000_000_000:
            return
        self.applied=True
        positions=self.exchange.cache.positions_open()
        for p in positions:
            qty=p.quantity.as_decimal()
            signed=qty if p.is_long else -qty
            amount=-signed*self.mark*self.rate
            self.exchange.adjust_account(Money(amount,USDT))
            balance=self.exchange.get_account().balance_total(USDT).as_decimal()
            equity=balance+p.unrealized_pnl(Price(float(self.mark),2)).as_decimal()
            maintenance=qty*self.mark*Decimal("0.05")
            self.events.append({"funding":amount,"equity":equity,"maintenance":maintenance})
            if self.liquidate and equity <= maintenance:
                self.strategy.close_all_positions(p.instrument_id)
                self.events.append({"liquidation":True})

    def log_diagnostics(self, logger):
        pass

    def reset(self):
        self.applied=False
        self.events=[]


def run_risk(side=OrderSide.BUY, capital=1000, mark="100", rate="0", liquidation=False, guarded=True):
    asset=instrument(True,fee="0")
    strategy=RoundTrip(asset.id,side)
    module=RiskProbe(strategy,mark,rate,liquidation)
    engine=BacktestEngine(BacktestEngineConfig(logging=LoggingConfig(bypass_logging=True)))
    engine.add_venue(Venue("TEST"),OmsType.NETTING,AccountType.MARGIN,[Money(capital,USDT)],
                     base_currency=USDT,default_leverage=Decimal(10),
                     margin_model=StandardMarginModel(),modules=[module],use_message_queue=False)
    engine.add_instrument(asset)
    guard = RiskGateway(engine, asset, leverage=Decimal(10), perpetual=True) if guarded else None
    engine.add_strategy(strategy)
    data=[QuoteTick(asset.id,Price.from_str("100.00"),Price.from_str("100.00"),
                    Quantity.from_str("100.000"),Quantity.from_str("100.000"),i*1_000_000_000,i*1_000_000_000)
          for i in range(1,5)]
    engine.add_data(data)
    try:
        engine.run()
        if guard:
            guard.assert_supported()
        return engine.cache.account_for_venue(Venue("TEST")).balance_total(USDT).as_decimal(),module.events,strategy.fills
    finally:
        engine.dispose()


class EngineRiskExtensionTests(unittest.TestCase):
    def test_funding_debits_long_and_credits_short_once(self):
        # 1 BTC * mark 100 * 1% = 1 USDT. Flat execution prices isolate funding.
        for side,expected in [(OrderSide.BUY,"999"),(OrderSide.SELL,"1001")]:
            with self.subTest(side=side):
                balance,events,fills=run_risk(side,rate="0.01")
                self.assertEqual(balance,Decimal(expected))
                self.assertEqual(len(events),1)
                self.assertEqual(len(fills),2)

    def test_mark_triggers_long_liquidation_with_unchanged_trade_price(self):
        # Equity=20+(80-100)=0; maintenance=80*5%=4. Mark triggers closure;
        # liquidation executes against the last-price book at 100, not at mark.
        balance,events,fills=run_risk(capital=20,mark="80",liquidation=True)
        self.assertEqual(events[0]["equity"],Decimal("0"))
        self.assertEqual(events[0]["maintenance"],Decimal("4"))
        self.assertEqual(events[1],{"liquidation":True})
        self.assertEqual(len(fills),2)
        self.assertEqual(balance,Decimal("20"))

    def test_mark_triggers_short_liquidation(self):
        balance,events,fills=run_risk(OrderSide.SELL,capital=20,mark="120",liquidation=True)
        self.assertEqual(events[0]["equity"],Decimal("0"))
        self.assertEqual(events[0]["maintenance"],Decimal("6"))
        self.assertEqual(events[1],{"liquidation":True})
        self.assertEqual(len(fills),2)

    def test_insufficient_initial_margin_rejects_entry(self):
        # Initial margin is 10; a capital of 5 cannot support this position.
        balance,events,fills=run_risk(capital=5)
        self.assertEqual(balance,Decimal("5"))
        self.assertEqual(fills,[])
        self.assertEqual(events,[])

    def test_upstream_margin_account_does_not_enforce_collateral(self):
        # Regression evidence for why the adapter guard is mandatory.
        _, _, fills = run_risk(capital=5, guarded=False)
        self.assertEqual(len(fills), 2)


if __name__ == "__main__":
    unittest.main()
