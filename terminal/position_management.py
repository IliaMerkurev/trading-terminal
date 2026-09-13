"""Versioned position policy and projection of actual engine fills.

This module never invents fills, debits an account, or connects to an exchange.
Nautilus owns execution and cash. The lifecycle projection provides decisions,
cost attribution and an independently reconcilable view of that engine history.
"""
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING

from terminal.profile import dec

ZERO = Decimal(0)


@dataclass(frozen=True)
class PositionConfig:
    version: int = 1  # Position policy schema, independent of product version.
    repeated_entry: str = 'ignore'
    scale_allocation_percent: str = '10'
    max_entries: int = 1
    max_allocation_percent: str = '100'
    max_position_notional: str = '1000000'
    max_leverage: str = '10'
    dca: tuple = ()
    partial_take: tuple = ()
    trailing_activation: str = '0'
    trailing_distance: str = '0'
    break_even_activation: str = '0'
    atr_period: int = 14
    atr_stop_multiplier: str = '0'
    atr_trailing_multiplier: str = '0'

    def __post_init__(self):
        if type(self.version) is not int or self.version != 1:
            raise ValueError('Unsupported Position Management schema')
        if self.repeated_entry not in ('ignore', 'scale'):
            raise ValueError('Invalid repeated entry policy')
        if type(self.max_entries) is not int or not 1 <= self.max_entries <= 32:
            raise ValueError('Maximum entries must be between 1 and 32')
        if type(self.atr_period) is not int or not 2 <= self.atr_period <= 200:
            raise ValueError('ATR period must be between 2 and 200')
        for field in ('scale_allocation_percent', 'max_allocation_percent'):
            if not 0 < dec(getattr(self, field)) <= 100:
                raise ValueError(f'{field} must be in (0, 100]')
        if dec(self.max_position_notional) <= 0 or not 1 <= dec(self.max_leverage) <= 100:
            raise ValueError('Positive notional and leverage between 1 and 100 required')
        for field in ('trailing_activation', 'trailing_distance', 'break_even_activation'):
            if not 0 <= dec(getattr(self, field)) < 1:
                raise ValueError(f'{field} must be a fraction in [0, 1)')
        if dec(self.trailing_activation) and not dec(self.trailing_distance):
            raise ValueError('Trailing activation requires a positive distance')
        for field in ('atr_stop_multiplier', 'atr_trailing_multiplier'):
            if not 0 <= dec(getattr(self, field)) <= 100:
                raise ValueError(f'{field} must be between 0 and 100')
        # Copy mutable input into immutable numeric tuples. Unknown fields fail.
        for field, second in (('dca', 'allocation_percent'), ('partial_take', 'fraction')):
            rows = getattr(self, field)
            if not isinstance(rows, (list, tuple)) or len(rows) > 8:
                raise ValueError(f'{field} supports at most eight steps')
            normalized = []
            previous = ZERO
            for row in rows:
                if isinstance(row, dict):
                    if set(row) != {'distance', second}: raise ValueError(f'Invalid {field} fields')
                    distance, amount = dec(row['distance']), dec(row[second])
                elif isinstance(row, tuple) and len(row) == 2:
                    distance, amount = map(dec, row)
                else:
                    raise ValueError(f'Invalid {field} step')
                if not previous < distance < 1 or not 0 < amount <= (100 if field == 'dca' else 1):
                    raise ValueError(f'{field} requires increasing fractional distances and bounded sizes')
                normalized.append((str(distance), str(amount)))
                previous = distance
            if field == 'partial_take' and sum((dec(r[1]) for r in normalized), ZERO) > 1:
                raise ValueError('Partial take fractions exceed the complete position')
            object.__setattr__(self, field, tuple(normalized))

    def snapshot(self):
        result = asdict(self)
        result['dca'] = [{'distance':d, 'allocation_percent':a} for d,a in self.dca]
        result['partial_take'] = [{'distance':d, 'fraction':a} for d,a in self.partial_take]
        return result


class PositionLedger:
    """Average-cost lifecycle projection; actual commissions/funding are inputs."""
    def __init__(self, profile):
        self.profile = profile
        self.quantity = self.entry = self.anchor = ZERO
        self.side = 0
        self.entries = self.sequence = 0
        self.first_ns = None
        self.fees = self.funding = self.gross = ZERO
        self.open_entry_fees = self.open_funding = ZERO
        self.total_entered = self.peak_quantity = self.max_notional = ZERO
        self.events = []
        self.completed = []
        self.history_limit = None
        self.pending_events = None
        self.first_fill = self.last_fill = None

    def emit(self, event):
        self.events.append(event)
        if self.pending_events is not None: self.pending_events.append(event)
        if self.history_limit is not None: self.events = self.events[-self.history_limit:]

    def fill(self, side, quantity, price, fee, time_ns, reason):
        quantity, price, fee = map(dec, (quantity, price, fee))
        if side not in ('buy', 'sell') or quantity <= 0 or price <= 0 or fee < 0:
            raise ValueError('Invalid actual fill')
        direction = 1 if side == 'buy' else -1
        if not self.quantity:
            if direction < 0 and self.profile.market == 'spot': raise ValueError('Spot short unsupported')
            self.sequence += 1
            self.side, self.first_ns, self.entries = direction, time_ns, 0
            self.entry = self.anchor = price
            self.fees = self.funding = self.gross = ZERO
            self.open_entry_fees = self.open_funding = ZERO
            self.total_entered = self.peak_quantity = self.max_notional = ZERO
            self.events = []
        if direction != self.side and quantity > self.quantity:
            raise ValueError('A reduction cannot reverse a position')
        previous = self.quantity
        self.fees += fee
        gross = allocated_fee = allocated_funding = ZERO
        if direction == self.side:
            self.entry = (self.entry*self.quantity + price*quantity)/(self.quantity+quantity)
            self.quantity += quantity
            self.total_entered += quantity
            self.entries += 1
            self.open_entry_fees += fee
            event_type = 'entry' if not previous else 'scale'
        else:
            fraction = quantity/self.quantity
            allocated_fee = self.open_entry_fees*fraction
            allocated_funding = self.open_funding*fraction
            self.open_entry_fees -= allocated_fee
            self.open_funding -= allocated_funding
            gross = self.side*(price-self.entry)*quantity
            self.gross += gross
            self.quantity -= quantity
            event_type = 'exit' if not self.quantity else 'reduction'
        self.peak_quantity = max(self.peak_quantity, self.quantity)
        self.max_notional = max(self.max_notional, self.quantity*price)
        event = {'position_id':self.sequence, 'type':event_type, 'time_ns':time_ns,
                 'side':side, 'quantity':str(quantity), 'price':str(price), 'fee':str(fee),
                 'reason':reason, 'remaining_quantity':str(self.quantity), 'average_entry':str(self.entry),
                 'gross_pnl':str(gross), 'allocated_entry_fee':str(allocated_fee),
                 'allocated_funding':str(allocated_funding),
                 'reduction_net_pnl':str(gross-fee-allocated_fee+allocated_funding) if direction != self.side else None}
        self.emit(event)
        if event_type == 'entry': self.first_fill = event
        self.last_fill = event
        if not self.quantity:
            self.completed.append(self.summary())
            if self.history_limit is not None: self.completed = self.completed[-50:]
        return event

    def funding_cashflow(self, amount, time_ns):
        if not self.quantity: raise ValueError('Funding requires an open position')
        amount = dec(amount)
        self.funding += amount
        self.open_funding += amount
        self.emit({'position_id':self.sequence, 'type':'funding', 'time_ns':time_ns, 'amount':str(amount)})

    def summary(self):
        return {'position_id':self.sequence, 'side':'long' if self.side == 1 else 'short',
                'entry':self.first_fill, 'exit':self.last_fill if not self.quantity else None,
                'entry_count':self.entries, 'peak_quantity':str(self.peak_quantity),
                'max_notional':str(self.max_notional), 'gross_pnl':str(self.gross),
                'fees':str(self.fees), 'funding':str(self.funding),
                'net_pnl':str(self.gross-self.fees+self.funding), 'events':list(self.events)}

    def snapshot(self, price, mark=None):
        price = dec(price); mark = dec(mark if mark is not None else price)
        self.max_notional = max(self.max_notional, self.quantity*mark)
        unrealized = self.side*(mark-self.entry)*self.quantity
        margin = self.quantity*self.entry/dec(self.profile.leverage) if self.profile.market == 'linear' else ZERO
        return {'position_id':self.sequence, 'side':'long' if self.side == 1 else 'short',
                'quantity':str(self.quantity), 'entry':str(self.entry), 'entry_count':self.entries,
                'initial_margin':str(margin), 'allocated_capital':str(self.quantity*self.entry/dec(self.profile.leverage)),
                'maintenance_margin':str(self.quantity*mark*dec(self.profile.maintenance_rate)) if self.profile.market == 'linear' else '0',
                'notional':str(self.quantity*mark), 'unrealized_pnl':str(unrealized),
                'realized_gross_pnl':str(self.gross), 'fees':str(self.fees), 'funding':str(self.funding),
                'realized_net_pnl':str(self.gross-self.fees+self.funding),
                'net_pnl':str(self.gross-self.fees+self.funding+unrealized)}

    def break_even_price(self):
        """Observed trigger covering remaining entry costs and adverse exit costs."""
        if not self.quantity: return None
        fee, slip, tick = map(dec, (self.profile.fee_rate, self.profile.slippage, self.profile.tick_size))
        cost = self.open_entry_fees-self.open_funding
        if self.side == 1:
            rounding = ROUND_CEILING
            executable = ((self.entry+cost/self.quantity)/(1-fee)/tick).to_integral_value(rounding=rounding)*tick
            price = executable/(1-slip)
        else:
            rounding = ROUND_FLOOR
            executable = ((self.entry-cost/self.quantity)/(1+fee)/tick).to_integral_value(rounding=rounding)*tick
            price = executable/(1+slip)
        return (price/tick).to_integral_value(rounding=rounding)*tick


def rounded_reduction(profile, held, fraction):
    held, fraction = dec(held), dec(fraction)
    if not 0 < fraction <= 1: raise ValueError('Reduction fraction must be in (0, 1]')
    if fraction == 1: return held
    step = dec(profile.quantity_step)
    quantity = (held*fraction/step).to_integral_value(rounding=ROUND_FLOOR)*step
    if quantity < dec(profile.min_quantity) or held-quantity < dec(profile.min_quantity):
        return ZERO  # Never silently enlarge a partial exit or leave invalid dust.
    return quantity


def addition_rejection(profile, config, ledger, quantity, execution_price, cash, equity):
    """Return a stable diagnostic; never silently resize to pass a risk limit."""
    quantity, price, cash, equity = map(dec, (quantity, execution_price, cash, equity))
    leverage = dec(profile.leverage)
    if ledger.entries >= config.max_entries and ledger.quantity: return 'maximum entry count reached'
    if leverage > dec(config.max_leverage): return 'maximum leverage exceeded'
    if quantity <= 0 or quantity % dec(profile.quantity_step) or quantity < dec(profile.min_quantity) or quantity > dec(profile.max_quantity):
        return 'quantity precision or minimum/maximum size constraint'
    notional = quantity*price
    if notional < dec(profile.min_notional): return 'minimum notional constraint'
    if (ledger.quantity+quantity)*price > min(dec(config.max_position_notional), dec(profile.max_notional)):
        return 'maximum position notional reached'
    allocated = (ledger.quantity*ledger.entry+notional)/leverage
    if allocated > dec(profile.capital)*dec(config.max_allocation_percent)/100:
        return 'maximum position allocation reached'
    commission = notional*dec(profile.fee_rate)
    if profile.market == 'spot':
        if notional+commission > cash: return 'insufficient cash including entry fee'
    elif allocated+commission > equity:
        return 'insufficient initial margin including entry fee'
    return None


@dataclass(frozen=True)
class PositionAction:
    side: str
    quantity: Decimal
    reason: str


class PositionManager:
    """Deterministic decisions over observed prices and confirmed actual fills."""
    def __init__(self, profile):
        self.profile = profile
        self.config = PositionConfig(**(profile.position_management or {}))
        self.ledger = PositionLedger(profile)
        self.stop = None
        self.stop_reason = None
        self.favorable = ZERO
        self.atr = None
        self.initial_atr = None
        self.dca_attempted = set()
        self.take_attempted = set()
        self.take_basis = None
        self.last_signals = {}
        self.diagnostics = []
        self.blocked_ns = None
        from terminal.graph import GraphEvaluator
        from terminal.signals import SignalStream
        graph = {'version':1, 'nodes':[{'id':'protection_atr', 'type':'atr', 'inputs':{}, 'params':{'period':self.config.atr_period}}],
                 'outputs':{name:None for name in ('entry_long','exit_long','entry_short','exit_short')}}
        self.atr_stream = SignalStream(GraphEvaluator(graph), profile.primary_minutes, 'closed')

    def observe_candle(self, candle):
        result = self.atr_stream.update(candle)
        if result is not None:
            value = result['values']['protection_atr.value']
            self.atr = dec(value) if value is not None else None
        return self.atr

    def first_crossing(self, left, right, cash):
        """Crossings only along a declared historical segment, never a live gap."""
        p = self.ledger
        if not p.quantity: return None
        candidates = []
        def add(field, level, priority, reason, direction):
            a,b = dec(left[field]),dec(right[field])
            if direction*(b-a) <= 0: return
            fraction = (level-a)/(b-a)
            if 0 < fraction < 1: candidates.append((fraction,priority,reason))
        if self.profile.market == 'linear':
            denominator = p.quantity*(p.side-dec(self.profile.maintenance_rate)-dec(self.profile.fee_rate))
            level = (p.side*p.quantity*p.entry-dec(cash))/denominator
            add('mark',level,0,'liquidation',-p.side)
        if self.stop is not None: add('price',self.stop,1,self.stop_reason,-p.side)
        if dec(self.profile.take_profit): add('price',p.entry*(1+p.side*dec(self.profile.take_profit)),2,'take_profit',p.side)
        for index,(distance,_) in enumerate(self.config.partial_take):
            if index not in self.take_attempted: add('price',p.entry*(1+p.side*dec(distance)),3,'partial_take',p.side)
        for index,(distance,_) in enumerate(self.config.dca):
            if index not in self.dca_attempted: add('price',p.anchor*(1-p.side*dec(distance)),4,'dca',-p.side)
        if not candidates: return None
        fraction,_,reason = min(candidates)
        return {**right, 'price':dec(left['price'])+fraction*(dec(right['price'])-dec(left['price'])),
                'mark':dec(left['mark'])+fraction*(dec(right['mark'])-dec(left['mark'])),
                'trigger':reason, 'fraction':fraction}

    def diagnostic(self, time_ns, reason):
        item = {'time_ns':time_ns, 'message':reason}
        self.diagnostics.append(item)
        self.diagnostics = self.diagnostics[-200:]
        if self.ledger.quantity:
            self.ledger.emit({'position_id':self.ledger.sequence, 'type':'rejection', **item})
        return None

    def fill(self, side, quantity, price, fee, time_ns, reason):
        opening = not self.ledger.quantity
        event = self.ledger.fill(side, quantity, price, fee, time_ns, reason)
        if opening:
            self.stop = self.stop_reason = None
            self.favorable = dec(price)
            self.initial_atr = self.atr
            self.dca_attempted.clear(); self.take_attempted.clear()
            self.take_basis = None
        if event['type'] in ('reduction', 'exit'): self.blocked_ns = time_ns
        if self.ledger.quantity: self.ratchet(dec(price), time_ns)
        return event

    def ratchet(self, price, time_ns):
        p, c = self.ledger, self.config
        if not p.quantity: return
        side = p.side
        self.favorable = max(self.favorable,price) if side == 1 else min(self.favorable,price)
        candidates = []
        if dec(self.profile.stop_loss): candidates.append((p.entry*(1-side*dec(self.profile.stop_loss)), 'stop_loss'))
        if self.initial_atr is not None and dec(c.atr_stop_multiplier):
            candidates.append((p.entry-side*self.initial_atr*dec(c.atr_stop_multiplier), 'atr_stop'))
        movement = side*(self.favorable-p.entry)/p.entry
        if dec(c.trailing_distance) and movement >= dec(c.trailing_activation):
            candidates.append((self.favorable*(1-side*dec(c.trailing_distance)), 'trailing_stop'))
        if dec(c.break_even_activation) and movement >= dec(c.break_even_activation):
            candidates.append((p.break_even_price(), 'break_even'))
        if self.atr is not None and dec(c.atr_trailing_multiplier):
            candidates.append((self.favorable-side*self.atr*dec(c.atr_trailing_multiplier), 'atr_trailing'))
        tick = dec(self.profile.tick_size)
        for level, reason in candidates:
            # A protective stop rounds toward the position, never further away.
            level = (level/tick).to_integral_value(rounding=ROUND_CEILING if side == 1 else ROUND_FLOOR)*tick
            if level > 0 and (self.stop is None or side*(level-self.stop) > 0):
                self.stop, self.stop_reason = level, reason
                p.emit({'position_id':p.sequence, 'type':'stop_change', 'time_ns':time_ns,
                                 'price':str(level), 'reason':reason})

    def close_action(self, reason, quantity=None):
        p = self.ledger
        return PositionAction('sell' if p.side == 1 else 'buy', p.quantity if quantity is None else quantity, reason)

    def protective_action(self, price, mark, equity, time_ns):
        p, c = self.ledger, self.config
        if not p.quantity: return None
        price, mark, equity = map(dec, (price,mark,equity))
        p.max_notional = max(p.max_notional, p.quantity*mark)
        if self.profile.market == 'linear' and equity <= p.quantity*mark*(dec(self.profile.maintenance_rate)+dec(self.profile.fee_rate)):
            return self.close_action('liquidation')
        # Existing stop is tested before a favorable update changes protection.
        if self.stop is not None and p.side*(price-self.stop) <= 0:
            return self.close_action(self.stop_reason)
        self.ratchet(price,time_ns)
        if self.stop is not None and p.side*(price-self.stop) <= 0:
            return self.close_action(self.stop_reason)
        if dec(self.profile.take_profit) and p.side*(price-p.entry)/p.entry >= dec(self.profile.take_profit):
            return self.close_action('take_profit')
        for index, (distance,fraction) in enumerate(c.partial_take):
            if index in self.take_attempted or p.side*(price-p.entry)/p.entry < dec(distance): continue
            self.take_attempted.add(index)
            if self.take_basis is None: self.take_basis = p.quantity
            cumulative = sum((dec(row[1]) for row in c.partial_take[:index+1]), ZERO)
            quantity = p.quantity if cumulative == 1 else min(p.quantity, rounded_reduction(self.profile,self.take_basis,fraction))
            if not quantity or (quantity < p.quantity and (p.quantity-quantity < dec(self.profile.min_quantity) or quantity*price < dec(self.profile.min_notional))):
                self.diagnostic(time_ns, f'Partial take {index+1} rejected: minimum size or residual dust')
                continue
            return self.close_action(f'partial_take_{index+1}', quantity)
        return None

    def addition(self, side, price, cash, equity, time_ns, reason, allocation_percent=None):
        p = self.ledger
        if self.blocked_ns == time_ns: return None
        if p.quantity and (1 if side == 'buy' else -1) != p.side:
            return self.diagnostic(time_ns, 'Entry rejected: opposite direction cannot reverse an open position')
        if side == 'sell' and self.profile.market == 'spot':
            return self.diagnostic(time_ns, 'Entry rejected: spot cannot open a short')
        if (dec(self.config.atr_stop_multiplier) or dec(self.config.atr_trailing_multiplier)) and self.atr is None:
            return self.diagnostic(time_ns, 'Entry rejected: confirmed primary ATR is not ready')
        price = dec(price)
        if allocation_percent is None:
            quantity = self.profile.size(cash, price)
        else:
            amount = dec(self.profile.capital)*dec(allocation_percent)/100
            step = dec(self.profile.quantity_step)
            quantity = (amount*dec(self.profile.leverage)/price/step).to_integral_value(rounding=ROUND_FLOOR)*step
        rejected = addition_rejection(self.profile, self.config, p, quantity, price, cash, equity)
        if rejected: return self.diagnostic(time_ns, f'{"Scale" if p.quantity else "Entry"} rejected: {rejected}')
        return PositionAction(side, quantity, reason)

    def signals(self, signals, bid, ask, cash, equity, time_ns):
        p = self.ledger
        transitions = {name for name,value in signals.items() if value is True and not self.last_signals.get(name,False)}
        self.last_signals = dict(signals)
        if self.blocked_ns == time_ns: return None
        if p.quantity:
            if signals.get('exit_long' if p.side == 1 else 'exit_short'):
                return self.close_action('signal')
            if self.config.repeated_entry == 'scale' and ('entry_long' if p.side == 1 else 'entry_short') in transitions:
                return self.addition('buy' if p.side == 1 else 'sell', ask if p.side == 1 else bid,
                                     cash,equity,time_ns,'repeated_entry', self.config.scale_allocation_percent)
            return None
        long, short = signals.get('entry_long') is True, signals.get('entry_short') is True
        if long and short: return self.diagnostic(time_ns, 'Simultaneous long/short entries skipped')
        if not long and not short: return None
        return self.addition('buy' if long else 'sell', ask if long else bid, cash,equity,time_ns,'entry')

    def dca_action(self, price, bid, ask, cash, equity, time_ns):
        p = self.ledger
        if not p.quantity or self.blocked_ns == time_ns: return None
        for index, (distance, allocation) in enumerate(self.config.dca):
            if index in self.dca_attempted or -p.side*(dec(price)-p.anchor)/p.anchor < dec(distance): continue
            self.dca_attempted.add(index)  # One attempt per step, including explicit rejection.
            action = self.addition('buy' if p.side == 1 else 'sell', ask if p.side == 1 else bid, cash,equity,time_ns,
                                   f'dca_{index+1}', allocation)
            if action: return action
        return None

    def manual(self, action, bid, ask, cash, equity, time_ns):
        p = self.ledger
        if self.blocked_ns == time_ns: return self.diagnostic(time_ns, 'Manual action skipped after a same-observation reduction')
        if action in ('close','reduce_25','reduce_50'):
            if not p.quantity: return self.diagnostic(time_ns, 'Manual reduction rejected: no position')
            quantity = rounded_reduction(self.profile, p.quantity, {'close':'1','reduce_25':'.25','reduce_50':'.5'}[action])
            if not quantity or (quantity < p.quantity and quantity*dec(bid if p.side == 1 else ask) < dec(self.profile.min_notional)):
                return self.diagnostic(time_ns, 'Manual reduction rejected: minimum size or residual dust')
            return self.close_action('manual_'+action, quantity)
        if action == 'add':
            if not p.quantity: return self.diagnostic(time_ns, 'Manual add rejected: no position')
            return self.addition('buy' if p.side == 1 else 'sell', ask if p.side == 1 else bid, cash,equity,time_ns,
                                 'manual_add',self.config.scale_allocation_percent)
        if action not in ('buy','sell'): raise ValueError('Unsupported manual paper action')
        if p.quantity: return self.diagnostic(time_ns, 'Manual entry rejected: use Add for the existing position')
        return self.addition(action,ask if action == 'buy' else bid,cash,equity,time_ns,'manual_'+action)
