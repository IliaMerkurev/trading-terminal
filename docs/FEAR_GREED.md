# Latest daily BTC sentiment

## Approved scope and acceptance plan

Add a compact, collapsible semicircular Fear & Greed gauge to the upper-left
of the main Market chart workspace. Reserve its own layout space so it cannot
cover candles, axes, drawings or controls. Keep the latest source date visible
in expanded and collapsed states, including while browsing historical candles
or another instrument. Label the index **Latest · BTC · daily**.

The source is [Alternative.me](https://alternative.me/crypto/fear-and-greed-index/),
using the public [latest-value API](https://api.alternative.me/fng/?limit=1).
Display a noticeable adjacent Alternative.me attribution link in every state.
The provider permits commercial display with this attribution. This is a
BTC-focused sentiment index, not an instrument-specific score, probability,
strategy signal or trading recommendation. No strategies, alerts, backtests,
agreement weights, paid service, account or security changes are included.

## Data and lifecycle contract

- Validate the response/error envelope, finite integer 0–100 value, source Unix
  timestamp, authoritative category and bounded update countdown. Source record
  time is not a fetch/publication timestamp. Reject future or malformed records.
- Keep only a validated last-good record and its date in a bounded local cache.
  Show loading, unavailable, invalid, offline and outdated states honestly.
  Failed reads never synthesize 0, 50 or a new date.
- Fetch independently of chart prices and timeframe/source navigation. A slow
  or unavailable external service must not block the local dispatcher or chart.
- Schedule daily reads from the advisory `time_until_update`, with bounded
  timeout, retry/backoff and concurrent-request deduplication. No minute polling.
- Preserve collapse preference consistently with existing local UI preferences.
  Cancel view timers on exit; fence obsolete replies and shutdown writes.

## Planned verification

Independent synthetic checks will cover value/date/envelope validation, category
preservation, scheduling, concurrency, cache/restart, stale/error/offline states,
cancel/exit/reopen, and rendering without a fabricated value. Existing tests stay
unchanged. New regression files, additive patch, exact commands/results and final
runtime hashes will be stored in a private version-linked archive outside Git.

TypeScript and production build will be checked, plus focused neighboring chart
regressions. Actual own-cloud browser acceptance will inspect normal/narrow/focus
layouts, keyboard collapse, historical navigation and the node panel. Synthetic
fixtures will be labeled; real API runtime access will be reported separately.
No Windows/native, full-product, live-exchange or owner acceptance is implied.

Status: plan checkpoint; implementation and acceptance are not yet complete.
