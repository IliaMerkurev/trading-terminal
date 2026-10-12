"""Read-only clock metadata for saved trade review; never changes accounting."""
from datetime import datetime, timezone

NANOSECONDS = 1_000_000_000


def clock(value, seconds):
    """Associate exact integer nanoseconds before a JSON number can round them."""
    if not isinstance(value, dict):
        return None
    ns = value.get('time_ns')
    if type(ns) is not int or ns < 0 or type(seconds) is not int or seconds <= 0:
        return None
    whole, fraction = divmod(ns, NANOSECONDS)
    source_open = whole // seconds * seconds
    try:
        utc = datetime.fromtimestamp(whole, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    except (OverflowError, OSError, ValueError):
        return None
    return dict(time_ns=str(ns), utc=f'{utc}.{fraction:09d} UTC',
                source_open=source_open, source_close=source_open + seconds,
                available_through=whole, interval_seconds=seconds)


def decorate(trade, profile):
    """Add a transport-only view; saved rows and decimal values stay untouched."""
    minutes = profile.get('execution_minutes', 1)
    seconds = minutes * 60 if type(minutes) is int and minutes > 0 else None
    events = trade.get('events')
    return {**trade, 'review': dict(
        entry=clock(trade.get('entry'), seconds),
        exit=clock(trade.get('exit'), seconds),
        events=[clock(event, seconds) for event in events] if isinstance(events, list) else [],
    )}
