"""Single-position historical profile executed by NautilusTrader.

Quotes follow an explicit synthetic minute path. Strategies see a minute bar
only after its close. Funding, mark checks and protections precede that signal.
"""
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from dataclasses import asdict

from nautilus_trader.accounting.margin_models import StandardMarginModel
from nautilus_trader.backtest.config import SimulationModuleConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.modules import SimulationModule
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig, StrategyConfig
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import Bar, BarType, QuoteTick
from nautilus_trader.model.enums import AccountType, CurrencyType, OmsType, OrderSide
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import CurrencyPair, CryptoPerpetual
from nautilus_trader.model.objects import Currency, Money, Price, Quantity
from nautilus_trader.trading.strategy import Strategy

from terminal.profile import Profile, dec
from terminal.risk_gateway import RiskGateway, ProfileViolation
from terminal.series import Candle, PartialBars
from terminal.signals import SignalStream

VENUE = Venue("RESEARCH")
NS = 1_000_000_000


def precision(step):
    return max(0, -dec(step).normalize().as_tuple().exponent)


def make_instrument(profile):
    base = profile.symbol[:-4]
    currency = Currency(base, 8, 0, base, CurrencyType.CRYPTO)
    pp, qp = precision(profile.tick_size), precision(profile.quantity_step)
    fields = dict(instrument_id=InstrumentId.from_str(f"{profile.symbol}.RESEARCH"),
        raw_symbol=Symbol(profile.symbol), base_currency=currency, quote_currency=USDT,
        price_precision=pp, size_precision=qp,
        price_increment=Price(float(profile.tick_size), pp), size_increment=Quantity(float(profile.quantity_step), qp),
        min_quantity=Quantity(float(profile.min_quantity), qp), max_quantity=Quantity(float(profile.max_quantity), qp), min_notional=Money(profile.min_notional, USDT),
        maker_fee=dec(profile.fee_rate), taker_fee=dec(profile.fee_rate), ts_event=0, ts_init=0)
    if profile.market == "linear":
        return CryptoPerpetual(**fields, settlement_currency=USDT, is_inverse=False,
            margin_init=1/dec(profile.leverage), margin_maint=dec(profile.maintenance_rate))
    return CurrencyPair(**fields)


class ProfileStrategy(Strategy):
    def __init__(self, asset, profile, candles, evaluator, progress,trade_start=None):
        super().__init__(StrategyConfig(order_id_tag="001"))
        self.asset, self.profile = asset, profile
        self.bar_type = BarType.from_str(f"{asset.id}-1-MINUTE-LAST-EXTERNAL")
        self.candles = candles
        self.evaluator = evaluator
        self.progress, self.seen = progress, 0
        self.signal_stream = SignalStream(evaluator, profile.primary_minutes, profile.evaluation)
        self.fills, self.diagnostics, self.indicators = [], [], []
        self.reason = "entry"
        self.protections = None
        self.trade_start=trade_start

    def on_start(self):
        self.subscribe_bars(self.bar_type)

    def close(self, reason):
        self.reason = reason
        self.close_all_positions(self.asset.id)

    def on_bar(self, bar):
        self.seen += 1
        if self.seen == 1 or self.seen % 256 == 0 or self.seen == len(self.candles):
            self.progress(self.seen/len(self.candles))
        candle = self.candles[bar.ts_init]
        result = self.signal_stream.update(candle)
        if result is None:
            return
        if self.trade_start is not None and candle.time<self.trade_start:return
        signals = result.get("signals", {})
        self.indicators.append({"time":candle.time + 60, "values":result.get("values", {}), "signals":signals})
        if self.protections.exit_minute == candle.time:
            return
        positions = self.cache.positions_open(instrument_id=self.asset.id)
        if positions:
            position = positions[0]
            if signals.get("exit_long" if position.is_long else "exit_short", False):
                self.close("signal")
            return  # Entries cannot scale, reverse, or reenter after a same-step exit.
        long, short = bool(signals.get("entry_long")), bool(signals.get("entry_short"))
        if long and short:
            self.diagnostics.append({"time":candle.time+60, "message":"Simultaneous long/short entries skipped"})
            return
        if not long and not short:
            return
        if short and self.profile.market == "spot":
            self.diagnostics.append({"time":candle.time+60, "message":"Spot short signal ignored: unleveraged market"})
            return
        account = self.cache.account_for_venue(VENUE)
        quote = self.cache.quote_tick(self.asset.id)
        price = quote.ask_price if long else quote.bid_price
        quantity = self.profile.size(account.balance_total(USDT).as_decimal(), price.as_decimal())
        if not quantity:
            self.diagnostics.append({"time":candle.time+60, "message":"Entry skipped: capital or minimum size constraint"})
            return
        self.reason = "entry"
        self.submit_order(self.order_factory.market(self.asset.id, OrderSide.BUY if long else OrderSide.SELL,
                                                   Quantity(float(quantity), self.asset.size_precision)))

    def record_order_event(self, event):
        if not isinstance(event, OrderFilled):
            return
        self.fills.append({"time_ns":event.ts_event, "side":"buy" if event.order_side == OrderSide.BUY else "sell",
            "quantity":str(event.last_qty), "price":str(event.last_px),
            "fee":str(event.commission.as_decimal()), "reason":self.reason})

    def on_stop(self):
        self.close("end_of_run")


class NativeController:
    """Observe an unchanged native Strategy; no graph signal/size conversion."""
    def __init__(self,asset,profile,native):
        self.asset,self.profile,self.native=asset,profile,native
        self.reason="native"
        self.fills,self.indicators=[],[]
        self.diagnostics=[{"message":"Native source/config controls signals, sizing and exits. Graph sizing controls are not applied; simulation capital, fees, funding and margin limits still apply."}]

    record_order_event=ProfileStrategy.record_order_event

    def close(self,reason):
        self.reason=reason
        self.native.close_all_positions(self.asset.id)
        self.reason="native"

    def capture(self,ts_now):
        values={}
        for index,indicator in enumerate(self.native.registered_indicators):
            if index>=128: raise ValueError("Native registered indicator count exceeds the result budget")
            for field in ("value","upper","middle","lower"):
                if hasattr(indicator,field):
                    values[f"{type(indicator).__name__}_{index}.{field}"]=float(getattr(indicator,field)) if indicator.initialized else None
        if not values: return
        point={"time":(ts_now+1)//NS,"values":values,"signals":{}}
        if self.indicators and self.indicators[-1]["time"]==point["time"]: self.indicators[-1]=point
        else: self.indicators.append(point)


class Protections(SimulationModule):
    def __init__(self, profile, strategy, samples, funding, progress=lambda _:None):
        super().__init__(SimulationModuleConfig())
        self.profile, self.strategy, self.samples, self.funding = profile, strategy, samples, funding
        self.sample = None
        self.last_applied = None
        self.events, self.equity = [], []
        self.exit_minute = None
        self.progress,self.processed=progress,0

    def pre_process(self, data):
        if isinstance(data, QuoteTick):
            self.sample = self.samples[data.ts_init]
            self.processed+=1
            if isinstance(self.strategy,NativeController) and (self.processed==1 or self.processed%1024==0 or self.processed==len(self.samples)):
                self.progress(self.processed/len(self.samples))

    def balance_and_equity(self):
        cash = self.exchange.get_account().balance_total(USDT).as_decimal()
        equity = cash
        for position in self.exchange.cache.positions_open():
            mark = dec(self.sample["mark"])
            if self.profile.market == "linear":
                equity += position.unrealized_pnl(Price(float(mark), self.strategy.asset.price_precision)).as_decimal()
            else:
                equity += position.quantity.as_decimal() * dec(self.sample["price"])
        return cash, equity

    def process(self, ts_now):
        if self.sample is None:
            return
        if self.last_applied != ts_now:
            self.last_applied = ts_now
            mark = dec(self.sample["mark"])
            trade = dec(self.sample["price"])
            positions = self.exchange.cache.positions_open()
            for position in positions:
                quantity = position.quantity.as_decimal()
                side = Decimal(1) if position.is_long else Decimal(-1)
                if self.profile.market == "linear":
                    rate = self.funding.get(ts_now)
                    if rate is not None:
                        amount = -side * quantity * mark * dec(rate)
                        money = Money(amount, USDT)
                        self.exchange.adjust_account(money)
                        self.events.append({"time_ns":ts_now, "type":"funding", "amount":str(money.as_decimal())})
                    _, equity = self.balance_and_equity()
                    maintenance = quantity * mark * dec(self.profile.maintenance_rate)
                    if quantity * mark > dec(self.profile.max_notional):
                        raise ProfileViolation("Mark notional exceeds the declared constant risk tier")
                    close_fee = quantity * mark * dec(self.profile.fee_rate)
                    if equity <= maintenance + close_fee or self.sample.get('trigger')=='liquidation':
                        self.events.append({"time_ns":ts_now, "type":"liquidation", "equity":str(equity), "maintenance":str(maintenance)})
                        self.strategy.close("liquidation")
                        self.exit_minute = self.sample["minute"]
                        continue
                entry = dec(position.avg_px_open)
                movement = side * (trade-entry) / entry
                reason = self.sample.get('trigger')
                if dec(self.profile.stop_loss) and movement <= -dec(self.profile.stop_loss):
                    reason = "stop_loss"
                elif dec(self.profile.take_profit) and movement >= dec(self.profile.take_profit):
                    reason = "take_profit"
                if reason:
                    self.strategy.close(reason)
                    self.exit_minute = self.sample["minute"]
        cash, equity = self.balance_and_equity()
        initial = Decimal(0)
        maintenance = Decimal(0)
        if self.profile.market == "linear":
            for position in self.exchange.cache.positions_open():
                initial += position.quantity.as_decimal()*dec(position.avg_px_open)/dec(self.profile.leverage)
                maintenance += position.quantity.as_decimal()*dec(self.sample["mark"])*dec(self.profile.maintenance_rate)
        available = equity-initial if self.profile.market == "linear" else cash
        point = {"time_ns":ts_now, "cash":str(cash), "equity":str(equity),
                 "initial_margin":str(initial), "maintenance_margin":str(maintenance), "available":str(available)}
        if self.equity and self.equity[-1]["time_ns"] == ts_now:
            self.equity[-1] = point
        else:
            self.equity.append(point)
        if isinstance(self.strategy,NativeController): self.strategy.capture(ts_now)

    def log_diagnostics(self, logger):
        pass

    def reset(self):
        self.sample = self.last_applied = self.exit_minute = None
        self.events, self.equity = [], []


def run_backtest(candles, profile, evaluator, *, marks=None, funding=None, progress=lambda _:None,
                 native_factory=None,native_timeframes=(1,),trade_start=None):
    if not candles:
        raise ValueError("No minute history available")
    if not isinstance(profile, Profile):
        profile = Profile(**profile)
    if trade_start is not None and (native_factory is not None or type(trade_start) is not int or trade_start%60 or not candles[0].time<=trade_start<=candles[-1].time):
        raise ValueError('Invalid visual-strategy trading window')
    if native_factory is not None and profile.version!=1:raise ValueError('Native strategies retain execution profile version 1; profile 2 protections apply to visual graphs')
    if native_factory is not None and (dec(profile.stop_loss) or dec(profile.take_profit) or profile.evaluation!="closed"):
        raise ValueError("Native strategies require their own protection/signal semantics; graph intrabar and stop/take controls are unavailable")
    if any(b.time % 60 for b in candles) or any(b.time <= a.time for a,b in zip(candles, candles[1:])):
        raise ValueError("History must be sorted, unique UTC minute candles")
    gaps = [(a.time+60, b.time) for a,b in zip(candles,candles[1:]) if b.time != a.time+60]
    if gaps and (profile.gap_policy == "reject" or profile.evaluation == "intrabar"):
        raise ValueError("Missing minute history: intrabar requires continuous finer data; gaps are never filled")
    if profile.market == "linear":
        if profile.mark_mode == "history" and (marks is None or any(b.time not in marks for b in candles)):
            raise ValueError("Complete separate mark history is required, or explicitly select last-price proxy")
        if profile.funding_mode == "history" and funding is None:
            raise ValueError("Funding history coverage is required, or explicitly select assumed zero funding")
    asset = make_instrument(profile)
    bar_type = BarType.from_str(f"{asset.id}-1-MINUTE-LAST-EXTERNAL")
    quotes, bars, samples, candle_map = [], [], {}, {}
    tick, slip = dec(profile.tick_size), dec(profile.slippage)
    fields = ("open", "low", "high", "close") if profile.path == "OLHC" else ("open", "high", "low", "close")
    aggregators={period:PartialBars(period) for period in sorted(native_timeframes)} if native_factory else {}
    for candle in candles:
        mark = marks[candle.time] if profile.market == "linear" and profile.mark_mode == "history" else candle
        for field, offset in zip(fields, (0, 20*NS, 40*NS, 60*NS-1)):
            timestamp = candle.time*NS + offset
            price = dec(getattr(candle, field))
            bid = (price*(1-slip)/tick).to_integral_value(rounding=ROUND_FLOOR)*tick
            ask = (price*(1+slip)/tick).to_integral_value(rounding=ROUND_CEILING)*tick
            if bid <= 0:
                raise ValueError("Price too small for precision/slippage profile")
            quotes.append(QuoteTick(asset.id, Price(float(bid), asset.price_precision), Price(float(ask), asset.price_precision),
                                   Quantity(1_000_000_000, asset.size_precision), Quantity(1_000_000_000, asset.size_precision), timestamp, timestamp))
            samples[timestamp] = {"minute":candle.time, "price":price, "mark":dec(getattr(mark, field))}
        ts = (candle.time+60)*NS-1
        candle_map[ts] = candle
        if native_factory:
            for period,aggregator in aggregators.items():
                primary,complete=aggregator.update(candle)
                if complete:
                    native_type=BarType.from_str(f"{asset.id}-{period}-MINUTE-LAST-EXTERNAL")
                    bars.append(Bar(native_type,*(Price(float(getattr(primary,k)),asset.price_precision) for k in ("open","high","low","close")),
                                    Quantity(float(primary.volume),asset.size_precision),ts,ts))
        else:
            bars.append(Bar(bar_type, *(Price(float(getattr(candle,k)),asset.price_precision) for k in ("open","high","low","close")),
                            Quantity(float(candle.volume),asset.size_precision), ts, ts))
    if not bars: raise ValueError("No complete native bars available for declared timeframes")
    native = native_factory(asset) if native_factory else None
    strategy = NativeController(asset,profile,native) if native else ProfileStrategy(asset, profile, candle_map, evaluator, progress,trade_start)
    funding_ns = {int(t)*NS:rate for t,rate in (funding or {}).items()} if profile.funding_mode == "history" else {}
    protection = Protections(profile, strategy, samples, funding_ns, progress)
    strategy.protections = protection
    engine = BacktestEngine(BacktestEngineConfig(logging=LoggingConfig(bypass_logging=True)))
    engine.add_venue(VENUE, OmsType.NETTING, AccountType.MARGIN if profile.market == "linear" else AccountType.CASH,
        [Money(profile.capital,USDT)], base_currency=USDT if profile.market == "linear" else None,
        default_leverage=dec(profile.leverage), margin_model=StandardMarginModel(), modules=[protection],
        use_message_queue=False, bar_execution=False)
    engine.add_instrument(asset)
    guard = RiskGateway(engine,asset,leverage=dec(profile.leverage),perpetual=profile.market=="linear",max_notional=dec(profile.max_notional))
    data_guard=None
    if native:
        from terminal.native import NativeDataGateway
        data_guard=NativeDataGateway(engine,asset.id,[str(b.bar_type) for b in bars])
    engine.add_strategy(native or strategy)
    # Observe the engine event stream, including fills emitted while on_stop runs.
    engine.kernel.msgbus.subscribe("events.order.*", strategy.record_order_event)
    try:
        if profile.version==2 and not native:
            from terminal.execution_v2 import first_crossing
            def consume(items):
                engine.add_data(items)
                engine.run(start=items[0].ts_init,end=items[-1].ts_init+1,streaming=True)
                engine.clear_data()
            for i,candle in enumerate(candles):
                minute_quotes=quotes[i*4:i*4+4]
                # The observed open applies gaps, funding and liquidation first.
                consume([minute_quotes[0]])
                for index in range(1,4):
                    previous,current=minute_quotes[index-1],minute_quotes[index]
                    positions=engine.cache.positions_open(instrument_id=asset.id)
                    crossing=first_crossing(samples[previous.ts_init],samples[current.ts_init],positions[0] if positions else None,
                        profile,engine.cache.account_for_venue(VENUE).balance_total(USDT).as_decimal())
                    chunk=[]
                    if crossing:
                        timestamp=previous.ts_init+max(1,min(current.ts_init-previous.ts_init-1,int((crossing.pop('fraction')*(current.ts_init-previous.ts_init)).to_integral_value(rounding=ROUND_CEILING))))
                        price=crossing['price']
                        bid=(price*(1-slip)/tick).to_integral_value(rounding=ROUND_FLOOR)*tick
                        ask=(price*(1+slip)/tick).to_integral_value(rounding=ROUND_CEILING)*tick
                        samples[timestamp]=crossing
                        chunk.append(QuoteTick(asset.id,Price(float(bid),asset.price_precision),Price(float(ask),asset.price_precision),
                            Quantity(1_000_000_000,asset.size_precision),Quantity(1_000_000_000,asset.size_precision),timestamp,timestamp))
                    chunk.append(current)
                    if index==3:chunk.append(bars[i])
                    consume(chunk)
            engine.end()
        else:
            engine.add_data(quotes)
            engine.add_data(bars)
            engine.run()
        guard.assert_supported()
        if data_guard: data_guard.assert_supported()
        engine_artifacts=[{"instrument":str(order.instrument_id),"side":order.side.name,
                           "type":order.order_type.name,"status":order.status.name,
                           "quantity":str(order.quantity),"filled_quantity":str(order.filled_qty),
                           "average_price":order.avg_px,"submitted_ns":order.ts_init}
                          for order in engine.cache.orders()]
        final_cash, final_equity = protection.balance_and_equity()
        if engine.cache.positions_open():
            raise RuntimeError("End-of-run close failed; result is incomplete")
        fills = strategy.fills
        if len(fills) % 2:
            raise RuntimeError("Incomplete fill pairs; result cannot be marked completed")
        trades = []
        for entry, exit_fill in zip(fills[::2], fills[1::2]):
            side = Decimal(1) if entry["side"] == "buy" else Decimal(-1)
            gross = side * (dec(exit_fill["price"])-dec(entry["price"])) * dec(entry["quantity"])
            fees = dec(entry["fee"])+dec(exit_fill["fee"])
            cashflow = sum((dec(e["amount"]) for e in protection.events if e["type"] == "funding" and entry["time_ns"] < e["time_ns"] <= exit_fill["time_ns"]),Decimal(0))
            trades.append({"entry":entry, "exit":exit_fill, "gross_pnl":str(gross), "fees":str(fees), "funding":str(cashflow), "net_pnl":str(gross-fees+cashflow)})
        points = [p for p in protection.equity if trade_start is None or p['time_ns']>=trade_start*NS]
        final_point = {"time_ns":quotes[-1].ts_init, "cash":str(final_cash), "equity":str(final_equity),
                       "initial_margin":"0", "maintenance_margin":"0", "available":str(final_cash)}
        if points and points[-1]["time_ns"] == final_point["time_ns"]:
            points[-1] = final_point
        else:
            points.append(final_point)
        peak, drawdown = dec(profile.capital), Decimal(0)
        for point in points:
            equity = dec(point["equity"])
            peak = max(peak,equity)
            drawdown = max(drawdown,(peak-equity)/peak if peak else Decimal(0))
        return {"schema_version":1, "status":"completed", "profile":profile.snapshot(),
            "engine":"nautilus_trader", "engine_version":"1.231.0", "metric_version":1,
            "strategy_format":"native" if native else "graph",
            "metrics":{"final_equity":str(final_equity), "net_pnl":str(final_equity-dec(profile.capital)),
                "max_drawdown":str(drawdown), "trade_count":len(trades),
                "win_rate":sum(dec(t["net_pnl"])>0 for t in trades)/len(trades) if trades else None,
                "fees":str(sum((dec(f["fee"]) for f in fills),Decimal(0))),
                "funding":str(sum((dec(e["amount"]) for e in protection.events if e["type"]=="funding"),Decimal(0)))},
            "fills":fills, "trades":trades, "events":protection.events, "equity":points, "engine_orders":engine_artifacts,
            "indicators":strategy.indicators, "diagnostics":strategy.diagnostics + [{"message":d} for d in guard.denials],
            "gaps":[g for g in gaps if trade_start is None or g[1]>=trade_start], "candles":[asdict(c) for c in candles if trade_start is None or c.time>=trade_start]}
    finally:
        engine.dispose()
