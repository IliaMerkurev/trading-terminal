# ADR 0052: VuManChu display formulas and confirmed events

Date: 2026-10-11. Integrated development candidate; bounded offline actual-App checks passed.

## Decision and scope

Extend the 30-type display catalog to 33 types with `vmc_cipher_b`,
`vmc_cipher_a` and `vmc_swing`. Cipher B provides Core + confirmed divergences
in an auxiliary pane; Cipher A provides an eight-EMA price ribbon; Swing provides
a transparent Range Filter on price. Typed settings include explicit boolean,
source and numeric controls. Canonical defaults and validation come from the
source-derived formula module. These are cache-only native-timeframe chart
annotations, not graph/recorded IR, strategy signals, alerts or order logic.

Use raw OHLC under Candles, Heikin Ashi and Line. Synthetic HA prices never enter
VMC calculations. Numeric ports, events, regimes, raw source/window identity,
settings revision and saved origin belong to one immutable checksummed snapshot.
Same-timestamp raw corrections clear stale numeric and event outputs together.
An uncertain save quarantines calculations and preserves the draft until an
authoritative reload; obsolete replies cannot restore prior geometry.

## Event meaning and geometry

The formula module consumes confirmed contiguous candles with OPEN timestamps.
Its confirmation and pivot OPEN timestamps become chart interval-END timestamps
exactly once in the display adapter. Events appear at the confirmation candle;
a five-bar divergence pivot becomes available two bars after its pivot, never
retroactively as a tradable signal. Hover details distinguish confirmation,
pivot and previous pivot. Native source time, market, symbol, timeframe, window,
settings revision, origin/generation and confirmation horizon must all agree.

Stable event identities omit replay-local indexes. Identical duplicates are
removed while distinct same-bar events remain. Unknown/forming rows and gaps
reset causal state and have null regimes. Connectors require closed contiguous
raw support in the same segment; an unavailable predecessor keeps details but
omits unverifiable geometry. Event rendering creates no new candle timestamps.
Hidden instances persist but neither calculate nor render. B scale is independent
of price manual/log settings; A/Swing share price geometry without replacing raw
candles. Recorded IR remains separate.

## Accurate labels and deliberate omissions

**Fast WT (WT1−WT2)** is a WaveTrend difference, not volume-weighted VWAP.
**VMC flow (candle-body proxy)** uses neither volume nor standard MFI.
Cipher B omits Sommi flags/diamonds, lookahead higher-timeframe candles,
higher-timeframe MACD colors and optional Schaff. No MTF feature, Pine runtime,
TradingView numerical/runtime parity or proprietary Market Cipher, Morpheus or
Scalper equivalence is claimed. Warmup, missing values, confirmation delay and
saved-origin effects remain visible rather than filled with invented values.

## Resources and licensing

ADR 0051 remains authoritative: no fixed instance-count limits, including hidden
instances, and no replacement 32/128 quota. Unchanged limits are 10,000 replay
input bars, 1,800 viewport bars, 64 MiB serialized settings/results, 64 KiB
transport pages and an estimated 256 MiB working-memory preflight. VMC estimates
include numeric ports, regimes and retained event objects. Resource refusal is
explicit and atomic; no settings or events are silently truncated. The estimate
is not a measured allocator hard bound or unlimited-hardware promise. Additional
input-history/checkpoint scope is deferred.

`terminal/vumanchu_indicators.py` is an MPL-2.0-covered derived translation;
the rest of the project remains MIT unless separately noticed. Exact original
publication versions, source byte hashes, author/contributor credits and links
are in [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md); the complete
[Mozilla license](../../licences/MPL-2.0.txt) accompanies the readable source.
Any binary distribution must make the corresponding source for that exact
version available under MPL. This source milestone does not approve distribution.

## Evidence and limits

Independent formula, backend and frontend reviews cover causal arithmetic,
typed parameters, saved origin, corrections/gaps, multi-page atomicity and stale
responses. The two blocking frontend issues found in review, raw-snapshot
mismatch and uncertain-save resurrection, were corrected before integration.
See [STATUS](../STATUS.md) for the final integrated targeted test/build results.
The offline actual-App fixture generates events through the real formulas;
it is distinct from live-provider, Windows/native and owner-led unaided
acceptance. No dependency, provider access, product version, release or main
merge is added. Existing chunk-size build advisory remains.
