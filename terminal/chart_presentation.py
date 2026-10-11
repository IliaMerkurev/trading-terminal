"""Pure chart-price projection. Synthetic prices never enter engine inputs."""
import math

PRICE_CONTRACT = 'heikin-ashi-midpoint-seed-v1'
NATIVE_CONTRACT = 'native-ohlc-v1'
CONFIRMED = frozenset(('closed_rest', 'provider_confirmed', 'synthetic_closed'))


def metadata(style):
    if type(style) is not str or style not in ('candles', 'heikin_ashi'):
        raise ValueError('Unsupported chart price style')
    return dict(price_style=style,
                price_contract=PRICE_CONTRACT if style == 'heikin_ashi' else NATIVE_CONTRACT,
                price_metadata=dict(synthetic=style == 'heikin_ashi', time_basis='utc_interval_end',
                                    seed_policy='segment_midpoint' if style == 'heikin_ashi' else 'native',
                                    forming_policy='last_contiguous_confirmed_or_provisional_midpoint'
                                    if style == 'heikin_ashi' else 'native'))


def unavailable(row, width, reason):
    return dict(time=row['time'] + width, status='unavailable', seed=None, reason=reason)


def _bar(row, width, style, state, forming=False):
    values = [row[k] for k in ('open', 'high', 'low', 'close')]
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError('Non-finite chart price input')
    opening, high, low, close = values
    seed = None
    if style == 'heikin_ashi':
        contiguous = state is not None and state[0] + width == row['time']
        # Divide each term before addition to avoid intermediate overflow.
        ha_close = opening / 4 + high / 4 + low / 4 + close / 4
        opening = state[1] / 2 + state[2] / 2 if contiguous else opening / 2 + close / 2
        close = ha_close
        high, low = max(high, opening, close), min(low, opening, close)
        seed = 'previous_confirmed' if contiguous else 'provisional_midpoint' if forming else 'midpoint'
    return dict(time=row['time'] + width, open=opening, high=high, low=low, close=close,
                status='forming' if forming else 'confirmed', seed=seed)


def replay(candles, style, minutes, start, end, cancel=None, before_origin=False):
    """Return visible prices plus private terminal (time, HA open, HA close).

    Only confirmed input advances recurrence; missing/unknown input breaks it.
    A viewport is solely an output filter. No caller-visible state is modified.
    """
    metadata(style)
    width = minutes * 60
    state = None
    output = []
    for index, row in enumerate(candles):
        if index % 32 == 0 and cancel and cancel.is_set():
            raise InterruptedError('Price calculation superseded')
        confirmation = row.get('confirmation')
        if confirmation == 'conflict':
            raise ValueError('Confirmed candle conflict; calculation invalidated')
        closed = confirmation in CONFIRMED
        if style == 'heikin_ashi' and (before_origin or not closed):
            bar = unavailable(row, width, 'before_origin' if before_origin else 'unconfirmed_history')
            state = None
        else:
            bar = _bar(row, width, style, state)
            if closed:
                state = (row['time'], bar['open'], bar['close'])
            else:
                state = None
                bar['status'] = 'unconfirmed_history'
        if start <= row['time'] <= end:
            output.append(bar)
    return output, state


def preview(row, style, minutes, state):
    """Project one current forming observation, never advance confirmed state."""
    return _bar(row, minutes * 60, style, state, forming=True)
