"""Versioned simulation parameters; rates are fractions, not percentages."""
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_FLOOR
import re


def dec(value):
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("Numeric parameters must be finite")
    return result


@dataclass(frozen=True)
class Profile:
    market: str = "spot"
    symbol: str = "BTCUSDT"
    capital: str = "1000"
    leverage: str = "1"
    sizing: str = "fixed"
    allocation: str = "100"
    fee_rate: str = "0.001"
    slippage: str = "0"
    stop_loss: str = "0"
    take_profit: str = "0"
    tick_size: str = "0.01"
    quantity_step: str = "0.001"
    min_quantity: str = "0.001"
    min_notional: str = "1"
    max_notional: str = "1000000"
    maintenance_rate: str = "0.005"
    primary_minutes: int = 60
    evaluation: str = "closed"
    path: str = "OLHC"
    funding_mode: str = "history"
    mark_mode: str = "history"
    gap_policy: str = "reject"
    tier_assumption: str = "Manual constant tier; historical risk tiers are not known"
    version: int = 1

    def __post_init__(self):
        if self.version != 1 or self.market not in ("spot", "linear"):
            raise ValueError("Unsupported profile version or market")
        if not re.fullmatch(r"[A-Z0-9]{1,24}USDT", self.symbol):
            raise ValueError("Expected an uppercase USDT symbol")
        for name in ("capital", "leverage", "allocation", "tick_size", "quantity_step", "min_quantity", "min_notional", "max_notional"):
            if dec(getattr(self, name)) <= 0:
                raise ValueError(f"{name} must be positive")
        for name in ("fee_rate", "slippage", "stop_loss", "take_profit", "maintenance_rate"):
            if not 0 <= dec(getattr(self, name)) < 1:
                raise ValueError(f"{name} must be a fraction in [0, 1)")
        if dec(self.leverage) < 1 or (self.market == "spot" and dec(self.leverage) != 1):
            raise ValueError("Spot is unleveraged; leverage must be at least one")
        if self.market == "linear" and dec(self.maintenance_rate) >= 1 / dec(self.leverage):
            raise ValueError("Maintenance rate must be below the initial margin rate")
        if self.sizing not in ("fixed", "percent") or (self.sizing == "percent" and dec(self.allocation) > 100):
            raise ValueError("Invalid sizing mode or percentage")
        if self.evaluation not in ("closed", "intrabar") or self.path not in ("OLHC", "OHLC"):
            raise ValueError("Unsupported bar evaluation/path")
        if self.funding_mode not in ("history", "assumed_zero") or self.mark_mode not in ("history", "last_proxy"):
            raise ValueError("Unsupported cost/mark assumption")
        if self.gap_policy not in ("reject", "skip") or not self.tier_assumption.strip():
            raise ValueError("Explicit gap and historical tier assumptions required")
        if self.primary_minutes not in (1,3,5,15,30,60,120,240,360,720,1440):
            raise ValueError("Unsupported primary timeframe")
        for step in (self.tick_size, self.quantity_step):
            if -dec(step).normalize().as_tuple().exponent > 8:
                raise ValueError("V1 supports at most eight price/quantity decimal places")

    def snapshot(self):
        return asdict(self)

    def size(self, available, execution_price):
        available, price = dec(available), dec(execution_price)
        amount = dec(self.allocation)
        if self.sizing == "percent":
            amount = available * amount / 100
        if amount > available or available <= 0:
            return Decimal(0)
        leverage = dec(self.leverage)
        # Reserve entry commission when the desired allocation uses all cash.
        notional = min(amount * leverage, available / (1/leverage + dec(self.fee_rate)))
        if notional > dec(self.max_notional):
            return Decimal(0)  # Do not silently resize to a different risk tier.
        step = dec(self.quantity_step)
        quantity = (notional / price / step).to_integral_value(rounding=ROUND_FLOOR) * step
        if quantity < dec(self.min_quantity) or quantity * price < dec(self.min_notional):
            return Decimal(0)
        return quantity
