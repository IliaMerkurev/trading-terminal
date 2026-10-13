# ADR 0049: Advanced display indicators and exact-boundary VWAP

Historical count-limit references below are superseded by [ADR 0051](0051-uncapped-indicator-instances.md). Other contracts remain.

## Status and scope

Implemented in an isolated integration checkpoint; browser geometry and native
acceptance remain separate gates. Extends the 21-kind display catalog to 29 kinds
with DMI/ADX, Supertrend, Stochastic RSI, HMA, Bollinger %B, Bollinger bandwidth,
VWAP and local Parabolic SAR. Ichimoku is not part of this checkpoint.
These are display-only additions, not strategy IR nodes or trading signals.

## Contracts and presentation

The frontend uses the validated Python formula contracts and never recalculates
indicator values. Existing raw-candle inputs, confirmed-close rules, saved origins,
HA presentation and source/timeframe namespaces remain unchanged.

- DMI exposes plus_di, minus_di and adx in a 0–100 auxiliary pane. Stochastic RSI
  exposes k/d in its own 0–100 pane with 20/80 guides.
- Supertrend renders only up/down ports on the price pane. Inactive ports retain
  whitespace. Because the pinned library filters whitespace before rendering,
  the last finite point before an inactive gap carries a transparent outgoing
  segment color, preventing connections across reversals. Direction is a textual +1 up / −1
  down readout; it never participates in price autoscale. Down uses the existing
  red convention. These signs are explicitly not Pine direction signs.
- HMA uses raw-price coordinates. Bollinger %B is a dimensionless, unbounded
  auxiliary ratio; bandwidth is an auxiliary percentage, not fixed to 0–100.
- SAR follows backend plot_style=dots using Lightweight Charts 5.2.1 LineSeries
  point markers with its connecting stroke disabled. The existing local causal
  initialization/reversal contract is disclosed; platform parity is not claimed.
- VWAP offers explicit UTC-day (midnight reset) and fixed UTC anchor modes. The
  datetime picker is interpreted as UTC, regardless of the device timezone.
  Anchors refer to candle opens, whereas chart labels refer to interval ends.
  Validation requires native-timeframe alignment. Day mode serializes anchor 0;
  fixed mode stores integer UTC seconds without presenting the epoch as the UI.
  Complete confirmed native history must begin at the exact boundary. No automatic
  history fetching or backfill is introduced. Missing boundary, interrupted
  coverage, pre-anchor candles and zero cumulative volume have readable reasons.
  Diagnostic status is labelled latest evaluated candle, not historical cursor
  status; historical missing values remain unavailable without invented reasons.

The catalog retains nine-item pages, bounded type-only favorites and search.
Eight instances (including hidden ones), atomic Apply, Collapse retention and
Cancel remain unchanged. Scalar defaults remain examples, not recommendations.
No dependencies or licenses are added.

## Verification

Focused Linux/component verification:

- ChartIndicators, indicatorReadout, MarketChartNavigation and chartWindow:
  72 tests passed together. One subsequently added MarketChart integration test
  for VWAP diagnostics and Supertrend readout passed independently (24 unchanged
  tests skipped in that invocation).
- test_display_formula_catalog, test_advanced_display_formulas and
  test_boundary_display_formulas: 27 tests passed. Integrated registry assertion
  is 29 rather than the earlier isolated six-formula checkpoint's 27.
- scripts/frontend.mjs build: TypeScript and production build passed. Existing
  large-chunk warning remains.

Mocked rendering tests verify exact ports, pane assignments, bounded/unbounded
axes, SAR marker options and Supertrend whitespace. They do not prove actual
chart-library pixels or native Windows behavior. Browser/narrow-layout acceptance,
independent integration review and any publication are separate coordinator gates.

## Actual-renderer and UTC editing correction

Real-browser inspection found two presentation defects in the initial candidate:
LineSeries connected Supertrend finite points across inactive whitespace, and a
controlled datetime-local value erased the native segmented editor during partial
year entry. The focused correction uses the installed library's verified
left-point color ownership to make only outgoing gap bridges transparent. Values,
timestamps, direction and active regime strokes are unchanged. Isolated one-point
regimes have no connecting stroke; numeric readout remains available.

The UTC picker now keeps native segmented editing independent of numeric draft
serialization, consumes both input and change events with deduplication, and
converts only complete timestamp text. Incomplete input disables Apply; completed
aligned edits survive Collapse/reopen and remain atomic with the other settings.
The browser's transient incomplete date segments are not persisted across closing
the editor; completed timestamps and invalid draft state are retained.

Focused regression: 31 tests passed, including execution of the actual installed
LWC 5.2.1 simple-line walker against the produced finite points, plus UTC input,
incomplete/complete, alignment and Collapse tests. TypeScript and production build
passed. Browser correction acceptance remains a separate gate.

A subsequent period-one boundary review found that raw-window clipping removes
backend synthetic gap slots. Supertrend now also hides outgoing segments when
neighboring retained timestamps differ from the native timeframe width. Market
render/update paths supply that width explicitly. An actual-renderer regression
covers the filtered missing-candle case at both one and five minutes without
adding timestamps. Both renderer tests and TypeScript/build passed; earlier
31-test evidence remains applicable to the unchanged UTC editor and controls.

## Bounded browser acceptance

The correction was accepted by actual-App browser checks: `6cca6bb` passed native
UTC year editing, 5m anchor alignment rejection, disabled invalid Apply,
Collapse/reopen retention, saved VWAP rendering and Cancel restoration. Final
source `e4d35a0` passed Supertrend regime-break, SAR-dot and three-curve DMI visual
smoke; independent review accepted the additional missing-raw-candle fix. The UTC
editor is unchanged between those sources. These checks complete this bounded
browser milestone only, with the limitations above retained.
