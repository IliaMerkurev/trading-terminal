# ADR 0025: explicit historical resolution and immutable history reuse

The owner authorized a card-first backtest workflow, longer-horizon strategy research,
history reuse and faster calculations on 2026-09-30. Product version remains 0.6-dev.

## Decision

Retain NautilusTrader 1.231.0 and existing accounting. Add `execution_minutes` to
the simulation profile, omitting its default value of 1 from legacy snapshots.
Immutable datasets record their actual candle interval. Native Bybit 5m, 15m,
1h, 4h and daily candles can drive spot closed-bar graphs and passive benchmarks.
Primary strategy intervals must be divisible by the execution interval. Four
modeled quotes span each actual source candle; closed signals become available
at that candle's close. Profile 2 retains continuous stop/take crossing and gap
rules. Fees, slippage, precision and unused cash retain the existing engine path.

Coarse paths can produce different trades and drawdown from M1. They are explicit
approximations, never reconstructed minute or tick history. Finer execution,
perpetuals, intrabar evaluation, native Python and Position Management remain on
M1. Coarse perpetual funding/mark timelines, native adapters and policy ATR need
separate validation before expansion. Unsupported combinations fail visibly.
Live/Paper and parameter experiments retain M1; Library comparisons support coarse
research. Saved results and source contracts distinguish resolutions.

History preparation verifies compatible immutable snapshots, returns an exact
complete cache hit without network, and fetches missing trade/mark spans for an
extension. New snapshots reference reused dataset identities; old files are never
updated. Conflicting overlaps fail. Perpetual funding and current metadata are
refreshed when building an extended snapshot. Current precision/tier metadata is
still an explicit historical assumption. Chart caches remain separate.

The Library provides a backend-derived suggested evaluation start reserving full
preceding warmup. It retains the complete dataset prefix for exact EMA state;
trimming the prefix to a nominal lookback would change recursive indicators.
Workload budgets count source candles, retaining the existing 2,000,000 limit.
Charts page at most 480 source candles and use recorded availability times.

## Alternatives and evidence

Skipping M1 observations without changing the contract would silently change
execution, funding and risk semantics. A second vectorized accounting engine
would duplicate financial logic. Neither is used. No dependency was added.
The [official Bybit endpoint](https://bybit-exchange.github.io/docs/v5/market/kline)
documents native intervals, reverse pagination and the still-forming close field.
The client excludes unclosed candles using provider time.

Windows focused checks: seven new coarse/history/managed-batch tests passed in
4.271s. Of 55 neighboring tests, 54 passed; the M1 download cancellation fixture
exposed an optional-argument compatibility issue. Preserving the legacy M1 call
shape fixed it; the two download tests passed in 0.005s. Existing financial,
causality, native-import and benchmark checks in that pass passed unchanged.
Full combined acceptance and UI verification remain pending at this checkpoint.
