# Market chart expansion plan

Date: 2026-10-11. Scope: the authorized free-compatible Market chart workspace,
using the installed Lightweight Charts 5.2.1. This is not a proprietary chart
product, a Pine runtime, script marketplace or TradingView parity claim. Keep
application MIT and existing chart attribution; do not add dependencies, paid
services, subscriptions, trading behavior or a product-version change.

## Delivery order and gates

### 1. Toolbar, catalog and individual editor — complete bounded UI phase

- Symbol/source/market, supported native timeframes and Indicators share a compact
  toolbar. Return remains visible; scale, Fit and Recorded IR use Chart options.
  Narrow screens use the native timeframe selector instead of duplicate buttons.
- Searchable categorized catalog exposes only the nine implemented types: SMA,
  EMA, Bollinger Bands, ATR, RSI, MACD, Stochastic, Volume and OBV.
- Favorites persist only bounded recognized type identifiers in a UI preference.
  Invalid/unavailable browser storage cannot block browsing or indicator edits.
- One selected instance editor owns inputs/style; the complete draft still saves
  atomically with its original revision. Hidden instances count toward eight.
  Collapse/Escape retain drafts; Cancel explicitly discards. No plot overlay,
  dialog trap, new market-settings persistence or namespace change.
- Focused component/keyboard, persistence-failure, cap/validation, source-race,
  chart/navigation/drawing checks and TypeScript/build passed. Corrected frozen
  source `1fd6a51` passed actual-App browser checks at 1094×757, 729×505 and
  625×432, including native-selector focus, editor-only legend entry, eight-
  instance cap, filtering, outer scrolling and visible Exit. Earlier `f22e5c1`
  supplies scoped save-error/retry/reload/favorite evidence. See STATUS.md for
  exact runs, source hashes, limits and remaining platform/owner acceptance.

### 2. Candles, Heikin Ashi and line — integrated candidate

Implemented Candles, Heikin Ashi and raw-close Line under [ADR 0048](adr/0048-chart-price-styles-and-formula-batch.md). Bounded actual-App browser acceptance passed on corrected source `7086f36`; independent review and platform/owner acceptance are tracked separately. Price style is transient and resets to Candles on reload. HA uses
an explicit, stable cache-derived origin shared with the display calculation
worker, not the moving viewport's first candle. An optional price_style on
chart_indicator_read can carry display output without changing the raw candle
feed, provider acquisitions or schema. Independent fixtures must establish seed,
gap/unconfirmed reset, warmup, paging/Return/timeframe stability, timestamps,
forming updates and bounded cache behavior. Label HA as synthetic prices. Line
uses raw close. Indicator inputs, raw OHLC readouts, price levels, trading,
strategy and immutable recorded IR remain unchanged. Drawing price-coordinate
semantics must stay explicit, and unsupported modes must never be dead controls.

### 3. First formula batches, 21 total types — integrated candidate

The catalog now exposes twelve reviewed additions to the nine-kind baseline, with nine entries per page:

- Trend: WMA, RMA, VWMA
- Channels and volatility: Donchian, Keltner, standard deviation
- Momentum: ROC, Momentum, CCI, Williams %R
- Volume: MFI, CMF

Each type requires one explicit calculation contract covering input fields,
parameters and valid bounds, output ports, units, seeds/warmup, zero denominator,
missing volume, confirmation/gaps, and origin causality. Independent numeric
fixtures and future-perturbation checks precede frontend metadata/rendering.
Expose catalog entries only after backend validation, settings roundtrip and
series integration agree. Preserve existing formulas and source-native units.

### 4. Advanced formula batches, 30 total types — bounded milestone complete

The finite target adds nine further types (DMI/ADX counts as one three-output
kind): DMI/ADX, Supertrend, Stochastic RSI, HMA, anchored/session VWAP, Parabolic
SAR, Ichimoku, Bollinger %B and Bollinger Bandwidth.

Define special contracts before implementation: recursive seed and reversal rules
for DMI/ADX, Supertrend and SAR; compound warmup/rounding for Stochastic RSI/HMA;
UTC-day or explicit UTC anchor and native volume units for VWAP; causal shifted
output timestamps and future whitespace without future input for Ichimoku; zero-
width bands and units for %B/Bandwidth. Do not promise cross-vendor equality or
strategy support. All nine are now exposed in the integrated candidate under
[ADR 0049](adr/0049-advanced-display-indicator-integration.md) and
[ADR 0050](adr/0050-ichimoku-market-integration.md). Ichimoku projections use a
raw-coordinate primitive without adding timestamps; Fit includes projections,
Return targets raw history, and a disclosed projection-only pan guard retains
the last populated raw candle. Independent review and bounded synthetic actual-App
acceptance passed through corrected source `e4d35a0`; see the dated STATUS record
for reused unchanged evidence and final checks. The finite 30-type implementation
and browser milestone is complete. Whole-product, platform-parity, live-provider,
Windows/native and owner-led unaided acceptance are not implied. Earlier phase
acceptance remains valid only for its tested surface.

## Acceptance and boundaries

At each integrated checkpoint: verify source isolation, atomic settings/revisions,
failed-save recovery, multiple/hidden instances, pane/overlay scales, stable
origins, focus/Return, toolbar/editor dismissal and accessible narrow layout.
Use one focused pass and one correction/recheck when needed, per AGENTS.md.
Retain runnable checkpoints and record actual evidence in STATUS.md. Browser
fixtures are synthetic; they cannot establish live-provider, Windows/native or
owner-led unaided acceptance. No automatic main merge, release or publication is
implied by this plan.
