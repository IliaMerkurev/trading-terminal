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

## Implemented contract and initial verification

The optional service owns one fetch at a time in a background thread. A short-
lived subprocess performs the fixed HTTPS GET with a 32 KiB response bound,
redirect rejection and an eight-second parent deadline. A nine-second child
watchdog also bounds a surviving child after parent failure. Graceful shutdown
cancels, joins and fences cache writes; current Windows behavior is not verified.

The next attempt follows the advisory countdown plus 60 seconds, with a
15-minute minimum; a failed attempt backs off one hour. Explicit user refresh
is throttled to once per minute. The mounted view briefly observes in-flight
local status at 500 ms (at most 25 reads), then sleeps until due. These local
reads do not repeat the external request. Exiting cancels view timers and fences
obsolete replies. Reopening/source changes reuse the independent service cache.

A record is outdated after the advisory update time plus five minutes, or after
36 hours of source age, whichever occurs first. Source category text controls
the label and known-category color; the continuous dial gradient is illustrative,
not a claim about provider classification thresholds. Unknown categories retain
their text with a neutral color. Failed cache persistence is visible. A corrupt
or deeply nested cache degrades this widget without preventing app startup.

Initial focused checks passed 22 backend (17 new and five shutdown regressions)
and 50 frontend (10 new and 40 chart neighbors), TypeScript and production build.
Three existing route-allowlist assertions require the new read-only sentiment
endpoint in the external test patch; tracked repository tests remain unchanged.
The existing bundle-size advisory remains. The application fetch worker obtained
69 / Greed, source date 2026-10-12, from the real endpoint in the own-cloud runtime;
an earlier request was temporarily unreachable. This is not a provider uptime
or platform-wide guarantee. Review corrections passed 18 focused backend and 12 focused frontend checks:
HTTP 403 is distinguished from 503/429; reactivation immediately ages the date;
manual refresh is fenced while pending and its one-minute cooldown is visible.
These totals overlap the initial pass and are not additive unique-test totals.

Actual production-browser acceptance is blocked in the current own-cloud
control environment: Chromium cannot reach the exec-launched loopback host,
and the documented native terminal input route does not enter commands.
No network/security changes or alternate Chromium launch were attempted.
No actual layout, keyboard, node-panel, narrow/focus, restart/reopen GUI or
screenshot acceptance is claimed. The in-flow gauge reserves its own layout
space before the plot; its actual visual fit still needs inspection. The private
version-linked test archive is pending at this checkpoint.
