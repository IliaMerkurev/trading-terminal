"""Version-pinned Nautilus risk endpoint adapter for a single-position profile.

This is a simulation rule layer, not an exchange connection or Python sandbox.
The original risk engine still processes accepted commands. Unsupported native
features are recorded as fatal profile violations, never reported as valid runs.
"""
from decimal import Decimal

from nautilus_trader.core.uuid import UUID4
from nautilus_trader.execution.messages import SubmitOrder, SubmitOrderList
from nautilus_trader.model.enums import OrderSide, OrderType
from nautilus_trader.model.events import OrderDenied


class ProfileViolation(ValueError):
    pass


class RiskGateway:
    def __init__(self, engine, instrument, *, leverage=Decimal(1), perpetual=False,
                 max_notional=Decimal("1000000")):
        self.engine = engine
        self.instrument = instrument
        self.leverage = Decimal(leverage)
        self.perpetual = perpetual
        self.max_notional = Decimal(max_notional)
        if self.leverage < 1 or (not perpetual and self.leverage != 1):
            raise ValueError("Invalid leverage for market")
        self.denials = []
        self.violations = []
        self.original = engine.kernel.risk_engine.execute
        self.bus = engine.kernel.msgbus
        self.bus.deregister("RiskEngine.execute", self.original)
        self.bus.register("RiskEngine.execute", self.execute)

    def deny(self, order, reason, *, fatal=False):
        self.denials.append(reason)
        if fatal:
            self.violations.append(reason)
        cache = self.engine.cache
        if not cache.order_exists(order.client_order_id):
            cache.add_order(order)
        event = OrderDenied(order.trader_id, order.strategy_id, order.instrument_id,
                            order.client_order_id, reason, UUID4(),
                            self.engine.kernel.clock.timestamp_ns())
        self.bus.send("ExecEngine.process", event)

    def execute(self, command):
        if isinstance(command, SubmitOrderList):
            for order in command.order_list.orders:
                self.deny(order, "Order lists are outside the V1 market-order profile", fatal=True)
            return
        if not isinstance(command, SubmitOrder):
            self.original(command)
            return
        order = command.order
        if order.instrument_id != self.instrument.id or order.order_type != OrderType.MARKET:
            self.deny(order, "Only one instrument and simple market orders are supported", fatal=True)
            return
        cache = self.engine.cache
        pending = cache.orders_open(instrument_id=order.instrument_id) + cache.orders_inflight(instrument_id=order.instrument_id)
        if any(o.client_order_id != order.client_order_id for o in pending):
            self.deny(order, "Concurrent orders are outside the single-position profile", fatal=True)
            return
        positions = cache.positions_open(instrument_id=order.instrument_id)
        if positions:
            position = positions[0]
            opposite = (position.is_long and order.side == OrderSide.SELL) or (position.is_short and order.side == OrderSide.BUY)
            if not opposite or order.quantity != position.quantity:
                self.deny(order, "Scaling, partial exits and reversal are unsupported", fatal=True)
                return
            # A native opposite order for exactly the position quantity is a full exit.
            self.original(command)
            return
        if order.is_reduce_only:
            self.deny(order, "No position available for reduction")
            return
        if not self.perpetual and order.side == OrderSide.SELL:
            self.deny(order, "Unleveraged spot cannot open a short", fatal=True)
            return
        quote = cache.quote_tick(order.instrument_id)
        if quote is None:
            self.deny(order, "An executable quote is required")
            return
        price = quote.ask_price if order.side == OrderSide.BUY else quote.bid_price
        notional = order.quantity.as_decimal() * price.as_decimal()
        if notional > self.max_notional:
            self.deny(order, "Order exceeds the declared risk tier")
            return
        account = cache.account_for_venue(order.instrument_id.venue)
        available = account.balance_total(self.instrument.quote_currency).as_decimal()
        initial = notional / self.leverage
        commission = notional * self.instrument.taker_fee
        if initial + commission > available:
            self.deny(order, "Insufficient initial margin including entry fee")
            return
        self.original(command)

    def assert_supported(self):
        if self.violations:
            raise ProfileViolation("; ".join(dict.fromkeys(self.violations)))
