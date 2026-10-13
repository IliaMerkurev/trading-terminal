# ADR 0056: Passive observed local indicator-alert runtime

Date: 2026-10-12

Status: Implemented bounded backend reconstruction on the verified frozen core.
Service/runtime only; UI, historical scans, native and provider acceptance remain
separate. Product remains 0.6-dev, without a dependency or formula change.

## Decision and alternatives

Use a dedicated passive `MarketObserver` rather than an ordinary `MarketFeed`.
The ordinary feed owns a strategy-consumer slot, blocks source changes, and
excludes coarse `display_candle` inputs. Altering it would risk strategy/order
behavior. The passive observer neither opens nor retains a connection, counts
as a strategy consumer, requests history, nor acquires a provider. Existing
strategy-consumer behavior and coarse-candle filtering are unchanged.

Hub observations retain three queued native confirmations per observer, matching
the three cached native rows. Receipts are detached copies with source, market,
symbol, interval, monotonically ordered local sequence, Hub epoch, connection
generation, raw candle and separate UTC-second/monotonic observation clocks.
Only confirmed `candle`/`display_candle` envelopes enter this path. Consecutive
exact duplicates coalesce before sequence allocation; changed duplicates are
never hidden. A fourth pending distinct receipt fails the observer closed.
Overflow, source replacement, reconnect and shutdown require fresh explicit Arm.

## Arm and evaluation

The exact strict Service contract is in [ALERT_RUNTIME_API](../ALERT_RUNTIME_API.md).
A frontend initializes a new session and explicitly registers visible Market
context. Every newer context revision fences previous work, including A → B → A.
A new frontend session sets null context and pauses prior work. Losing a browser
tab cannot itself stop a local Service; the future UI must explain explicit Pause.

Create captures a reviewed applied settings revision/hash and always stays paused.
Explicit Arm supplies saved revision/hash, session/context revision, request ID
and `reviewed:true`. The complete ARMING/ARMED definition set must fit the core's
256 KiB budget before admission. A single background worker replays only full
origin cached confirmed rows through the existing frozen core/display engine.
It establishes the latest already-observed native baseline without inserting
historical hits. No cached or recovered close becomes a delivery receipt.

A baseline may have been legitimately observed earlier within its still-current
native interval: its age is bounded by native width plus 15 seconds, while Hub
ticker/book freshness remains mandatory. This permits healthy five-minute and
coarser sources to Arm between closes. Baseline observation must not precede
its native close. Subsequent receipts must be processed within 15 monotonic
seconds, be after their confirmed close, and advance exactly one native interval.
Only genuinely observed subsequent contiguous confirmations can commit events.
Source, client, visibility, native interval, Hub epoch/generation, history epoch,
full-prefix raw hash, explicit provenance, cache conflicts, definition revision,
cursor token and freshness are checked again before publication. A periodic
poll checks stale source/native close and changed cache even without new candles.

Keep only a raw-prefix hash per armed rule, rather than retaining a full candle
tape for every definition. Each replay reads at most 10,000 full-origin rows and
uses the core's combined formula/evidence work estimate. This is bounded causal
full replay, not a second incremental formulas implementation or an unlimited
history monitor. Exceeding any work/queue budget pauses visibly, without trimming
origins, fetching replacement history, reseeding or auto-resuming.

Applied settings saves synchronously check active dependencies. Surviving
parameter/type/contract changes persist a reviewed-rebind requirement; reverting
parameters or restarting cannot bypass it. Hidden/deleted originals, appearance
and layout changes preserve the frozen definition and do not reseed its origin.

## Durable writes and uncertain replies

The existing atomic immutable event/cursor transaction and durable at-most-once
banner claim remain the sole write/delivery boundaries. No banner, system toast,
sound, email or Telegram dispatch is performed by this backend. `observed_at`
is actual receipt UTC seconds; raw open, native confirmed close and divergence
pivot/availability clocks remain the core's unmodified evidence.

An additive constant-size request ledger makes create and accepted Arm identities
durable. Create and its request mapping commit in the same transaction; a retry
with the same identity/content returns the same rule. A read-only request lookup
allows reconciliation without writing. An old accepted Arm request can report
current state after Pause/restart, but cannot re-enable monitoring. Rule edits
retain optimistic metadata revisions; uncertain replies require GET/inspection
before a fresh edit. Request identities are not a saved-rule count quota.
A separate additive table persists the reviewed-rebind requirement. No authentic
previous missing-alert database exists, so legacy schema compatibility is not
claimed.

Pause sets cancellation and invalidates durable cursor capabilities. Worker
publication checks cancellation while holding the same runtime/context fence.
Shutdown joins the worker before closing history/display/Service dependencies.
If the bounded join times out, shutdown reports incomplete and retains those
dependencies and workspace ownership for a later successful close.

## Verification boundaries

Actual AppService envelopes and actual MarketHub stream fanout are exercised by
independently authored synthetic native candles, with provider, PAPER, trading
and external notification entry points guarded. Initial true/no-backlog,
false→true, equality crossing, five-minute clocks, coarse Arm between closes,
duplicates/conflicts, lost create/Arm replies, context/restart/reconnect,
parameter rebind, queue overflow and stale-without-candle behavior are checked.
Tests inject timing and controlled failures; they do not establish live provider,
Windows/native, actual GUI or owner acceptance. The focused command/results and
retained nearest-regression evidence are recorded in STATUS, not represented as
a full product suite or remote CI pass.
