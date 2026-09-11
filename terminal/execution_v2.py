"""Causal crossings on the explicitly modeled continuous intraminute path.

Only an already open position can introduce a crossing sample. Minute boundaries
are discontinuous observations, even when the candles have adjacent timestamps.
"""
from decimal import Decimal
from terminal.profile import dec


def first_crossing(left,right,position,profile,cash):
    if position is None:return None
    side=Decimal(1) if position.is_long else Decimal(-1)
    entry=dec(position.avg_px_open);quantity=position.quantity.as_decimal()
    candidates=[]
    def crossing(field,level,reason,priority):
        a,b=dec(left[field]),dec(right[field])
        if a==b:return
        fraction=(level-a)/(b-a)
        if 0<fraction<1:candidates.append((fraction,priority,reason))
    if dec(profile.stop_loss):
        level=entry*(1-side*dec(profile.stop_loss))
        if side*(dec(right['price'])-dec(left['price']))<0:crossing('price',level,'stop_loss',1)
    if dec(profile.take_profit):
        level=entry*(1+side*dec(profile.take_profit))
        if side*(dec(right['price'])-dec(left['price']))>0:crossing('price',level,'take_profit',2)
    if profile.market=='linear':
        denominator=quantity*(side-dec(profile.maintenance_rate)-dec(profile.fee_rate))
        threshold=(side*quantity*entry-cash)/denominator
        if side*(dec(right['mark'])-dec(left['mark']))<0:crossing('mark',threshold,'liquidation',0)
    if not candidates:return None
    fraction,_,reason=min(candidates)
    return {**right,'price':dec(left['price'])+fraction*(dec(right['price'])-dec(left['price'])),
        'mark':dec(left['mark'])+fraction*(dec(right['mark'])-dec(left['mark'])),
        'trigger':reason,'fraction':fraction}
