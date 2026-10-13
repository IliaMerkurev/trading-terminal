"""Independent, bounded latest daily BTC sentiment display; never strategy input."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

SOURCE_URL = 'https://alternative.me/crypto/fear-and-greed-index/'
API_URL = 'https://api.alternative.me/fng/?limit=1'
FIRST_TIMESTAMP = 1517443200  # Provider series begins in February 2018.
MAX_BYTES = 32768
TIMEOUT = 8
RETRY_SECONDS = 3600
STALE_SECONDS = 36 * 3600


def integer(value, low, high):
    if isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 12:
        value = int(value)
    if type(value) is not int or not low <= value <= high:
        raise ValueError('Invalid numeric field')
    return value


def validate(payload, now):
    """Normalize only provider-supplied data; never derive category thresholds."""
    if not isinstance(payload, dict) or not isinstance(payload.get('metadata'), dict):
        raise ValueError('Invalid provider response')
    if 'error' not in payload['metadata'] or payload['metadata']['error'] is not None:
        raise ValueError('Provider reported an error')
    data = payload.get('data')
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise ValueError('No valid latest record')
    item = data[0]
    value = integer(item.get('value'), 0, 100)
    timestamp = integer(item.get('timestamp'), FIRST_TIMESTAMP, int(now))
    category = item.get('value_classification')
    if not isinstance(category, str) or not 1 <= len(category) <= 40 or category.strip() != category or any(ord(c) < 32 for c in category):
        raise ValueError('Invalid provider category')
    # A missing advisory countdown falls back to the next UTC daily boundary.
    delay = (int(now) // 86400 + 1) * 86400 - int(now)
    if 'time_until_update' in item:
        delay = integer(item['time_until_update'], 0, 86400)
    return dict(value=value, category=category, timestamp=timestamp,
                fetched_at=int(now), next_update_at=int(now) + delay,
                next_attempt_at=int(now) + max(900, delay + 60))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Unexpected provider redirect')


def _fetch_child():
    """Child has a hard parent deadline, including DNS and slow response bodies."""
    try:
        request = Request(API_URL, headers={'Accept': 'application/json', 'User-Agent': 'TradingTerminal/0.6 sentiment-display'})
        with build_opener(NoRedirect).open(request, timeout=5) as response:
            if response.status != 200:
                raise ValueError('Unexpected provider status')
            body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError('Provider response exceeded limit')
        payload = json.loads(body)
        # Output only the bounded schema. Raw transport errors never reach the UI.
        record = validate(payload, time.time())
        return {'record': record}
    except HTTPError as exc:
        kind = 'access' if exc.code in (401, 403, 451) else 'rate_limit' if exc.code == 429 else 'provider'
        return {'error': kind, 'detail': f'Provider request failed (HTTP {exc.code}).'}
    except (URLError, OSError):
        return {'error': 'offline', 'detail': 'Could not reach Alternative.me. Check network or provider access.'}
    except (ValueError, TypeError, UnicodeError):
        return {'error': 'invalid', 'detail': 'Alternative.me returned no valid latest value.'}


def fetch_latest(cancel):
    process = subprocess.Popen([sys.executable, '-m', 'terminal.fear_greed', '--fetch'],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               cwd=str(Path(__file__).resolve().parents[1]),
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    deadline = time.monotonic() + TIMEOUT
    try:
        while not cancel.is_set() and time.monotonic() < deadline:
            try:
                output, _ = process.communicate(timeout=.2)
                if process.returncode != 0 or len(output) > MAX_BYTES:
                    raise ValueError('Sentiment worker failed')
                return json.loads(output)
            except subprocess.TimeoutExpired:
                continue
        return {'error': 'offline', 'detail': 'Alternative.me request timed out or was cancelled.'}
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()


def checked_record(record, now):
    if not isinstance(record, dict) or set(record) != {'value', 'category', 'timestamp', 'fetched_at', 'next_update_at', 'next_attempt_at'}:
        raise ValueError('Invalid cache record')
    stamp = integer(record['timestamp'], FIRST_TIMESTAMP, int(now))
    fetched = integer(record['fetched_at'], stamp, int(now))
    update = integer(record['next_update_at'], fetched, fetched + 86400)
    attempt = integer(record['next_attempt_at'], fetched + 900, fetched + 86460)
    normalized = validate({'metadata': {'error': None}, 'data': [{
        'value': record['value'], 'value_classification': record['category'],
        'timestamp': stamp, 'time_until_update': update - fetched}]}, fetched)
    if normalized['next_attempt_at'] != attempt:
        raise ValueError('Invalid cache schedule')
    return normalized


class FearGreed:
    """One fetch at a time, detached from chart reads and local IPC dispatch."""
    def __init__(self, root, *, fetcher=fetch_latest, clock=time.time):
        self.path = Path(root) / 'fear-greed-v1.json'
        self.fetcher, self.clock = fetcher, clock
        self.lock = threading.RLock()
        self.cancel = threading.Event()
        self.thread = None
        self.record = None
        self.error = None
        self.cache_warning = None
        self.next_attempt = 0
        self.last_attempt = -math.inf
        try:
            if self.path.exists():
                if self.path.stat().st_size > MAX_BYTES:
                    raise ValueError('Oversized cache')
                payload = json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(payload, dict) or type(payload.get('version')) is not int or payload.get('version') != 1:
                    raise ValueError('Invalid cache')
                self.record = checked_record(payload.get('record'), self.clock())
                self.next_attempt = self.record['next_attempt_at']
        except (ValueError, OSError, TypeError, RecursionError):
            self.cache_warning = 'Saved sentiment cache is unavailable or invalid.'

    def status(self, refresh=False):
        if type(refresh) is not bool:
            raise ValueError('Invalid refresh flag')
        with self.lock:
            now = self.clock()
            busy = bool(self.thread and self.thread.is_alive())
            due = now >= self.next_attempt or (refresh and now - self.last_attempt >= 60)
            if due and not busy and not self.cancel.is_set():
                self.last_attempt = now
                self.next_attempt = now + RETRY_SECONDS
                self.error = None
                self.thread = threading.Thread(target=self._run, name='daily-btc-sentiment', daemon=True)
                self.thread.start()
                busy = True
            record = dict(self.record) if self.record else None
            outdated = bool(record and (now - record['timestamp'] > STALE_SECONDS or now > record['next_update_at'] + 300))
            return dict(record=record, loading=busy, outdated=outdated, error=self.error,
                        cache_warning=self.cache_warning, closed=self.cancel.is_set(),
                        retry_after=max(0, int(self.next_attempt - now)),
                        refresh_after=max(0, math.ceil(60 - (now - self.last_attempt))) if math.isfinite(self.last_attempt) else 0)

    def _run(self):
        try:
            result = self.fetcher(self.cancel)
            now = self.clock()
            if not isinstance(result, dict):
                raise ValueError('Invalid worker result')
            if result.get('error'):
                error = result['error'] if result['error'] in ('access', 'offline', 'invalid', 'provider', 'rate_limit') else 'invalid'
                details = {'provider': 'Alternative.me could not supply an update; try again later.',
                           'rate_limit': 'Alternative.me rate-limited this request; the next automatic attempt is in one hour.',
                           'access': 'Alternative.me access was rejected; network or provider restrictions may apply.',
                           'offline': 'Could not reach Alternative.me; last saved value retained when available.',
                           'invalid': 'Alternative.me returned no valid latest value.'}
                with self.lock:
                    if not self.cancel.is_set():
                        self.error = dict(kind=error, detail=details[error])
                return
            record = checked_record(result.get('record'), now)
            with self.lock:
                if self.cancel.is_set():
                    return
                if self.record and record['timestamp'] < self.record['timestamp']:
                    raise ValueError('Older provider reply')
                self.record = record
                self.next_attempt = record['next_attempt_at']
                self.error = None
                try:
                    temporary = self.path.with_suffix('.tmp')
                    temporary.write_text(json.dumps({'version': 1, 'record': record}), encoding='utf-8')
                    os.replace(temporary, self.path)
                    self.cache_warning = None
                except OSError:
                    self.cache_warning = 'Latest value is visible but could not be saved for offline use.'
        except Exception:
            with self.lock:
                if not self.cancel.is_set():
                    self.error = dict(kind='invalid', detail='No valid latest value was accepted; previous data retained when available.')

    def close(self):
        with self.lock:
            self.cancel.set()
            thread = self.thread
        if thread:
            thread.join(TIMEOUT + 2)
            if thread.is_alive():
                raise RuntimeError('Sentiment worker is still stopping')


if __name__ == '__main__' and sys.argv[1:] == ['--fetch']:
    # A self-deadline also bounds an orphan if the supervising app crashes.
    watchdog = threading.Timer(TIMEOUT + 1, lambda: os._exit(2))
    watchdog.daemon = True
    watchdog.start()
    print(json.dumps(_fetch_child(), allow_nan=False))
    watchdog.cancel()
