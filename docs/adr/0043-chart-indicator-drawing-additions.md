# ADR 0043: Explicit display indicator seeds and custom Fibonacci levels

Date: 2026-10-11. Status: implemented; focused and frozen full automated checks
and bounded fixed-H4 offline browser acceptance passed. Exact evidence and
remaining live/native/Windows limits are in STATUS.md.

## Scope

Extend the existing cache-only chart presentation with ATR, Stochastic and OBV,
plus a bounded Fib ratio editor and optional drawing names. No new dependencies,
market acquisition, graph nodes, strategy/execution changes, Pine runtime or
third-party scripts. The existing six display formulas remain unchanged. These
are independently authored MIT application features. No cross-platform/Pine
numerical parity is claimed; recorded IR continues to show actual run values.

## Explicit formulas and seeds

Each new indicator consumes confirmed native candles, in native timeframe order,
from the persisted source/market/symbol/interval origin. A missing timestamp or
unconfirmed candle resets all states; conflicted confirmation refuses replay.
The viewport is only an output filter. Existing origin contract strings remain
unchanged so legacy saved origins are not invalidated or silently reanchored.
These additive per-kind formulas define the new kinds, rather than changing the
old engine-seed contract. Defaults: ATR period 14; Stochastic period 14, smooth 3,
signal 3; OBV no parameters. Integer periods remain bounded to 1–1000.

- ATR: TR = max(high-low, abs(high-previous close), abs(low-previous close)).
  First segment TR is high-low. First output at bar N is the arithmetic mean of
  N TR values; later ATR = ((N-1)*previous ATR + TR)/N. Values are price units.
  The UI names this `ATR · Wilder, SMA seed`. This intentionally differs from
  the existing graph engine's first-TR recursive seed. For TR [2,4,3,1], period 3,
  display outputs [null,null,3,7/3]; unchanged graph first-ready output is 25/9.
  This is display analysis, never a substitute for recorded graph ATR.
- Stochastic: raw = 100*(close-lowest low)/(highest high-lowest low), using the
  last N bars. A flat high/low range explicitly yields 0. K = SMA(raw, smooth),
  D = SMA(K, signal); neither smoothing stage emits partial-window means.
  First K is at N+smooth-1 bars, first D at N+smooth+signal-2 (up to 2998 bars).
  Percent pane is 0–100 with 20/80 guides; no signal/trading interpretation.
- OBV: first confirmed valid-volume candle of a segment yields 0, ignoring its
  volume for the seed. Later rising closes add the current native volume,
  falling closes subtract it, unchanged closes add zero. Numeric zero volume
  is valid. Missing/nonfinite/negative/boolean volume yields null and resets only
  OBV; next valid candle seeds 0. Absolute OBV depends on this origin/offset and
  is not comparable to differently seeded tools. Units remain source-native:
  OKX spot base currency, OKX derivatives contracts; Bybit retains its existing
  explicitly unverified native-unit disclosure. No contract/base conversion.

All three stay unavailable before the persisted origin. In particular,
Stochastic does not reuse the existing 999-bar finite-window prefix, which is
insufficient for its maximum smoothing warmup. Existing SMA/BB/volume pre-origin
behavior is unchanged. The 10,000-bar replay, 1,800-output and transport budgets,
cancellation, source segregation, revision keys and explicit reanchor remain.
Each new kind has a normal automatic auxiliary pane even under logarithmic
price. Multiple instances of a kind share that pane. Negative OBV remains valid.

Primary formula references, consulted without copying implementation:
[StockCharts ATR](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-true-range-atr),
[TradingView Stochastic](https://www.tradingview.com/support/solutions/43000502332-stochastic-stoch/),
[StockCharts OBV](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/on-balance-volume-obv).
OBV's chosen zero seed and Stochastic flat-window convention are explicit local
contracts, not claims that all cited tools initialize identically.

## Drawing compatibility and limits

Version-1 drawings accept optional `name` (up to 80 printable characters), and
Fib-only optional `levels` (1–20 unique finite numeric ratios, inclusive -5–5).
Boolean ratios, empty tokens, duplicates and nonfinite values are rejected.
Legacy documents retain their bytes/fields on read; omitted levels render the
original [0,.236,.382,.5,.618,.786,1]. Only an explicit save changes revision.
The input uses comma-separated ratios with inline validation; Apply saves all
ratios atomically, Reset saves defaults, and normal undo/redo applies. Names
appear in the existing selector, including hidden/locked objects; no reordering
or broad object-manager rewrite. Lock also protects ratio/name editing.

Each level uses A.price + ratio*(B.price-A.price), preserving anchor orientation;
then priceToCoordinate projects the result, including under logarithmic price.
Ratio and price labels remain visible. Equal-price anchors are safe. Derived
nonpositive/nonfinite prices are not drawable and are omitted, rather than
clamped or passed into logarithmic projection; saved ratios remain unchanged.
No logarithmic-price interpolation mode, per-level colors, custom label text,
multi-select, drawing export or order/alert linkage is added.

## Verification

Independent handwritten expected values cover true-range gaps and seeds,
Stochastic smoothing/flat windows/maximal warmup, OBV equal-close/zero/missing
volume, future perturbation, unconfirmed/conflicted candles, gaps, persisted
origins/reopen and source isolation. Backend tests preserve old drawing shapes,
strict bounds and atomic revision failure. Frontend tests cover addition/settings,
normal auxiliary scales under log price, negative OBV, custom ratios/labels,
legacy read, invalid input, reset/undo and names. Mocks do not establish browser
pointer, layout or Windows/native acceptance. No live provider probe is implied.
