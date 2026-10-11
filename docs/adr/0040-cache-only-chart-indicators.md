# ADR 0040: cache-only display indicators with durable origins

## Decision

Add separate chart-display SMA, EMA, Bollinger Bands, RSI, MACD and native volume.
These are presentation tools on the selected native chart timeframe, not recorded
Strategy IR, strategy evaluation, trading signals or paper execution. Recorded IR
retains its own selector and pane. No new dependencies, feeds or acquisition
commands are introduced. Existing market history controls retain their behavior.

Up to eight stable instances may be edited together, including multiple EMAs.
Periods are integers 1–1000; BB deviations are (0,10]; MACD fast is below slow.
Apply validates and saves the complete configuration atomically. Settings and
per-timeframe origins live in the existing workspace SQLite database, keyed by
market/symbol. They contain no candle payloads or secrets. Unknown/corrupt settings
produce a warning and safe empty configuration; failed reads/writes leave price
browsing available. Hidden instances retain settings, removed ones do not return.

## Numerical and time contract

The backend reuses `terminal.graph.indicator_for` / the pinned Nautilus primitives,
without changing financial-engine formula code. SMA uses a full trailing close
window. EMA uses alpha 2/(N+1), first-close seed and N-observation suppression.
BB uses close-only SMA and population standard deviation. RSI uses the existing
zero-difference Wilder initialization and 0–100 scale: flat input returns 100,
not 50; the display conservatively waits N+1 closes. MACD signal is seeded only
from initialized MACD values. Incomplete values are absent, never zero padded.
Volume is the returned native candle value, including genuine zero and missing
values; units remain explicitly unverified, with no BTC/USD conversion.

Both existing price candles and these indicators are plotted at UTC interval end:
interval-start seconds plus `minutes * 60`, exactly once. They are not shifted
relative to each other. Display intervals remain independent of strategy settings.

## Confirmation and segmentation

An additive confirmation table records the exact payload hash and provenance.
Existing rows are `legacy_unknown`; age alone never establishes confirmation.
Existing REST history acquisition can independently attest exact closed rows.
Explicit hub confirmations are persisted separately; forming values stay visible
on the price chart and in volume but never advance a recursive indicator.
Confirmed corrections persist a conflict and invalidate calculation instead of
rewriting accepted prices. Duplicate confirmations are idempotent; newer exact
duplicates advance only the provider watermark. Coarse display streams retain
three per-candle watermarks to admit delayed closes/corrections without accepting
unbounded old packets. Strategy feed semantics are unchanged.

Unknown inputs and time gaps reset the display segment and warmup. Whitespace
breaks plotted lines across gaps; no OHLCV is synthesized. Volume remains useful
for legacy history. The interface explains missing confirmed inputs and exposes
origin, generation, seed contract, gaps and warmup information.

## Bounded lifecycle

The initial origin is the oldest of at most 10,000 latest cached native bars.
It is persisted before use and never silently changes on paging, trimming,
Latest, Fit, configuration edits or reopening. Replay stops at the requested end;
a requested prefix over 10,000 input bars refuses visibly, without reseeding.
Before origin, bounded local prefixes support SMA/BB/volume; recursive outputs
remain unavailable. Explicit Recalculate with earlier cached history selects the
earliest cached origin and increments generation, with a warning that recursive
values may change. Over-budget reanchoring leaves the old origin intact.

One managed display thread owns one active replay and one coalesced latest pending
request. It checks cancellation every 32 input rows. Service dispatch never waits
for the numerical replay. Cache identity includes source, timeframe, origin,
configuration, candle revision and requested projection; two completed results
are retained. Forming-tick volume is projected after replay and cannot cancel or
reseed unchanged confirmed work. Stale frontend replies are ignored after source,
timeframe, visibility/configuration or navigation changes. Shutdown cancels and
joins the thread before releasing workspace ownership.

A maximum 1,800 displayed candles, 10,000 total replay/prefix inputs, eight
instances, bounded gap whitespace and 900 KiB response guard constrain work and
transport. These are bounds, not a guarantee of instantaneous worst-case BB
completion. There is no parallel job dashboard, candle localStorage or automatic
backfill. When history or settings are unavailable, price browsing survives.

## Evidence and limits

An independent standard-library Fraction oracle supplies nonlinear eight-close
SMA/EMA/RSI/MACD values and BB squared-band distances. Separate explicit goldens
cover first-close seeds, population deviation, flat/falling/rising RSI and MACD
readiness. Tests exercise viewport overlap/reopen/reanchor, metadata, corrections,
work caps, async coalescing, tick starvation avoidance and shutdown. Frontend
checks cover duplicate EMA controls, invalid draft preservation, panes, stale
responses and settings failure handling. Actual browser and Windows/native
acceptance are reported separately in status; neither follows from mocked DOM
or arithmetic tests. This slice does not change product version, license, original
research cohorts, native trust, market-data acquisition policy or execution rules.
