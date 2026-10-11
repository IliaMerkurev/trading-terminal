# ADR 0050: Causal Ichimoku projections on the Market chart

## Decision

Complete the bounded 30-kind display catalog using the existing Lightweight
Charts 5.2.1 series primitive API. No dependency, strategy node, acquisition,
trading change or product-version bump is introduced. This integration is a
candidate pending independent integration review and actual-App browser checks.
The existing price-style selection remains transient and resets to Candles.

Tenkan and Kijun are ordinary raw-domain price series. Senkou A/B, cloud fill and
Chikou are an attached primitive on the populated raw-close carrier. Shifted
points never enter setData and never create shared-axis timestamps, candle slots,
volume slots, drawing anchors or recorded IR values. Displacement is 1–100 raw
bars; conversion/base/span_b windows are 1–1000. Defaults are 9/26/52/26.

Projection acceptance requires version/contract, exact raw interval-end domain,
source/market/symbol/timeframe, requested start/end, settings revision,
calculation origin/generation and horizon to match. The hook additionally tracks
the exact raw request snapshot, rejecting projections when a candle changes even
if timestamps do not. The backend result origin is compared with its projection
context; source/revision/window and hook epochs independently reject stale work.

The primitive clears synchronously before raw-window mutation and is detached on
instance/settings/source/timeframe/style/active changes and unmount. New accepted
transport is copied into owned geometry. Gaps and segment boundaries are not
bridged. Hover shows computed-at and plotted-at UTC separately, explicitly labels
estimated future dates and later-known Chikou. Raw OHLC remains unchanged.

Explicit Fit includes current primitive extents. Return continues to target the
last raw bar at retained width. The library cannot resolve primitive price
coordinates in an entirely projection-only right viewport without a populated
raw point. Therefore, while a visible Ichimoku instance is enabled, a pan wholly
past the last raw point is minimally translated to include that point with a
half-bar margin, preserving width. The UI discloses this constraint. No fake bars
or substitute price series values are created. Ordinary overlapping pans and
other indicator configurations are untouched. Cloud autoscale contributes only
when the price scale has autoScale enabled; manual and logarithmic conversion
remain the chart engine's responsibility.

## Evidence and remaining gates

- Focused frontend scope: ChartIndicators, indicatorReadout,
  chartIchimokuPrimitive, chartIchimokuIntegration, MarketChartNavigation and
  chartWindow. First pass: 99 passed, one new test used the wrong button label.
  Corrected test selector; the affected MarketChartNavigation suite passed all
  26 tests. Combined unique coverage is 100 passing tests.
- Backend existing formula scope: 27 passed. Ichimoku suite required its tests
  directory on PYTHONPATH; corrected invocation passed 13 tests. No formula
  correction was needed.
- TypeScript plus production build passed; existing large-chunk warning remains.
- No browser screenshots, real-library geometry or Windows/native acceptance is
  claimed by component/unit tests. Real-GUI Fit/pan/log/manual/style/blank-HA and
  lifecycle acceptance must be run against the frozen integration commit.

Reproduction:

    node node_modules/vitest/vitest.mjs run frontend/src/ChartIndicators.test.tsx frontend/src/indicatorReadout.test.ts frontend/src/chartIchimokuPrimitive.test.ts frontend/src/chartIchimokuIntegration.test.ts frontend/src/MarketChartNavigation.test.tsx frontend/src/chartWindow.test.ts
    PYTHONPATH=tests:. python -m unittest test_display_formula_catalog test_advanced_display_formulas test_boundary_display_formulas test_ichimoku_projection
    node scripts/frontend.mjs build

These are focused integration checks, not a full regression or release gate.

## Bounded browser acceptance

Actual-App checks on `5f52018` verified cloud-aware Fit, log/manual price scales,
projection-only pan guarding, raw Return, cloud retention with unavailable HA,
Line switching, source isolation and computed/plotted hover provenance. These
Ichimoku paths were unchanged by the later Supertrend/UTC corrections. Final
smoke on `e4d35a0` added Ichimoku, hid other overlays and verified the full forward
cloud after calculation readiness and Fit. Independent review and this bounded
browser milestone are complete; no platform parity, live-provider, native Windows
or owner-led unaided acceptance is asserted.
