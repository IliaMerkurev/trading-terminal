"""Observed-price paper adapter using the existing Nautilus account/risk engine.

No exchange execution client is constructed. Each quote is a real observation
with explicitly adverse slippage, not a synthetic historical intrabar segment.
The caller journals observations for deterministic reconstruction after restart.
"""
from decimal import ROUND_CEILING, ROUND_FLOOR

from nautilus_trader.accounting.margin_models import StandardMarginModel
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.objects import Money, Price, Quantity

from terminal.profile import Profile, dec
from terminal.risk_gateway import RiskGateway
from terminal.simulation import NS, VENUE, ProfileStrategy, Protections, make_instrument


class PaperStrategy(ProfileStrategy):
    def on_stop(self):
        # Closing the application must not invent an end-of-backtest fill.
        pass


class PaperEngine:
    MAX_ORDERS = 10000  # Retained engine cache has a finite session safety budget.

    def __init__(self, profile):
        self.profile = profile if isinstance(profile,Profile) else Profile(**profile)
        self.asset = make_instrument(self.profile)
        self.strategy = PaperStrategy(self.asset,self.profile,{},None,lambda _:None)
        self.samples, self.funding = {}, {}
        self.protection = Protections(self.profile,self.strategy,self.samples,self.funding)
        self.strategy.protections = self.protection
        self.engine = BacktestEngine(BacktestEngineConfig(logging=LoggingConfig(bypass_logging=True)))
        self.engine.add_venue(VENUE,OmsType.NETTING,AccountType.MARGIN if self.profile.market=='linear' else AccountType.CASH,
            [Money(self.profile.capital,USDT)],base_currency=USDT if self.profile.market=='linear' else None,
            default_leverage=dec(self.profile.leverage),margin_model=StandardMarginModel(),modules=[self.protection],
            use_message_queue=False,bar_execution=False)
        self.engine.add_instrument(self.asset)
        self.guard=RiskGateway(self.engine,self.asset,leverage=dec(self.profile.leverage),perpetual=self.profile.market=='linear',max_notional=dec(self.profile.max_notional))
        self.engine.add_strategy(self.strategy)
        self.engine.kernel.msgbus.subscribe('events.order.*',self.strategy.record_order_event)
        self.last_ns=None
        self.closed=False

    def observe(self,time_ns,price,*,mark=None,funding_rate=None,signals=None,signal_minute=None):
        if self.closed or type(time_ns) is not int or time_ns<0 or (self.last_ns is not None and time_ns<=self.last_ns):
            raise ValueError('Paper observations must have increasing timestamps in an open session')
        if len(self.engine.cache.orders())>=self.MAX_ORDERS:
            raise ValueError('Paper session order budget reached; pause and review before a new session')
        price=dec(price)
        if price<=0:
            raise ValueError('Paper observed price must be positive')
        if self.profile.market=='linear' and self.profile.mark_mode=='history' and mark is None:
            raise ValueError('Separate observed mark required for perpetual paper trading')
        mark=dec(mark if mark is not None else price)
        if mark<=0:
            raise ValueError('Paper mark must be positive')
        tick,slip=dec(self.profile.tick_size),dec(self.profile.slippage)
        bid=(price*(1-slip)/tick).to_integral_value(rounding=ROUND_FLOOR)*tick
        ask=(price*(1+slip)/tick).to_integral_value(rounding=ROUND_CEILING)*tick
        if bid<=0:
            raise ValueError('Price too small for precision/slippage profile')
        minute=time_ns//NS//60*60
        self.samples.clear();self.funding.clear()
        self.samples[time_ns]={'minute':minute,'price':price,'mark':mark}
        if funding_rate is not None:
            if self.profile.market!='linear' or self.profile.funding_mode!='history':
                raise ValueError('Funding supplied for a profile without observed funding')
            self.funding[time_ns]=dec(funding_rate)
        quote=QuoteTick(self.asset.id,Price(float(bid),self.asset.price_precision),Price(float(ask),self.asset.price_precision),
                        Quantity(1_000_000_000,self.asset.size_precision),Quantity(1_000_000_000,self.asset.size_precision),time_ns,time_ns)
        self.strategy.fills.clear();self.strategy.diagnostics.clear();self.protection.events.clear();self.protection.equity.clear()
        self.guard.denials.clear()
        self.engine.add_data([quote])
        self.engine.run(start=time_ns,end=time_ns+1,streaming=True)
        self.engine.clear_data()
        # Protections process the observed quote before signal orders. A close
        # here cannot reenter on the same observation, regardless of M1 latency.
        if signals is not None and self.protection.exit_minute!=minute:
            self.strategy.apply_signals(signals,minute if signal_minute is None else signal_minute)
        self.guard.assert_supported()
        self.last_ns=time_ns
        return self.snapshot()

    def snapshot(self):
        if self.last_ns is None:
            return {'cash':self.profile.capital,'equity':self.profile.capital,'position':None,'fills':[],'events':[],'diagnostics':[]}
        cash,equity=self.protection.balance_and_equity()
        positions=self.engine.cache.positions_open(instrument_id=self.asset.id)
        position=None
        if positions:
            p=positions[0]
            position={'side':'long' if p.is_long else 'short','quantity':str(p.quantity),
                      'entry':str(p.avg_px_open),'initial_margin':str(p.quantity.as_decimal()*dec(p.avg_px_open)/dec(self.profile.leverage)) if self.profile.market=='linear' else '0'}
        return {'time_ns':self.last_ns,'cash':str(cash),'equity':str(equity),
                'net_pnl':str(equity-dec(self.profile.capital)),'position':position,
                'fills':list(self.strategy.fills),'events':list(self.protection.events),'diagnostics':list(self.strategy.diagnostics)}

    def close(self):
        if not self.closed:
            self.engine.dispose()
            self.closed=True
