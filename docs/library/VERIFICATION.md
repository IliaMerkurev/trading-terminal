# Library integration evidence

These checks establish computation and wiring, not expected investment returns.
Source review is recorded separately in [SOURCES.md](SOURCES.md). Timeframe
variants count once per implementation. No author recommendation is inferred.

| Strategy | Kind / family | Timeframe evidence | Independent synthetic evidence | Finite cached public integration |
|---|---|---|---|---|
| Native EMA trend v2 | Native with temporal adapter / trend | Source requires interval; local default 60m; tested 1m/3m/5m | Buy 106, exit 108, quantity 1, fees 0.214, net 1.786; warmup has no fills; native batch/standalone parity | BTCUSDT linear, 1m/5m: 31/7 completed positions; actual spot alternatives; losses retained |
| RSI threshold reversion v1 | Adapted graph / mean reversion | Source default daily; tested 1m/3m/5m | RSI threshold and future-perturbation fixture; nontrivial trades, batch/standalone equality | BTCUSDT linear, 1m/5m: 2/1 completed positions; actual spot alternatives; losses retained |
| Bollinger RSI reversion v1 | Adapted graph / mean reversion | Source requires interval; local default 60m; tested 1m/3m/5m | Independent falling-band/RSI confluence, middle-band exit, future perturbation; buy 6, exit 10, no-fee net 66.664 on allocation 100 with 0.001 quantity step | BTCUSDT spot, 1m/5m: 7/2 completed positions; both passive alternatives completed; mixed returns retained |
| MACD normalized momentum v1 | Adapted graph / momentum | Source default daily; tested 1m/3m/5m | Independently calculated EMA/histogram/tolerance; buy 16, exit 8, allocation 100, no-fee net -50; future perturbation and finite multiplication guard | BTCUSDT spot, 1m/5m: legitimate no-trade outcomes; both passive alternatives completed |
| Historical return direction v1 | Adapted graph / momentum | Source default daily; tested 1m/3m/5m | Fractional ROC 0.2 and -1/11; warmup/partial-state/future checks; buy 12, exit 10, allocation 120, net -20 | BTCUSDT spot, 1m/5m: 180/36 completed positions; losses retained; both passive alternatives completed |

The shared finite market observation is 2026-09-01 12:00–24:00 UTC, with preceding
copied cached history for warmup. Each row starts with 1,000 USDT independently.
Costs, market metadata and native fixed quantity remain in each immutable run.
Spot alternatives are not leverage/risk-equivalent to perpetual strategies.
Weekly DCA has a single purchase in this short period; annualized return is N/A.
No tuning, selection of only winning runs, or new endurance test was performed.

Focused Bollinger integration: 5 tests passed in 0.460s, including library trust
regression. Existing numerical Bollinger/RSI indicator evidence is retained;
this candidate adds no indicator implementation. Close-only bands, long-only
direction and profile-controlled sizing are explicit differences from upstream.

Five implementations and three families are verified at this checkpoint.
Later-period Library workflow and final release acceptance remain open.

Focused MACD integration: 13 Python checks passed in 0.132s; 9 frontend editor/model checks passed. TypeScript/Vite and locked offline Windows/Rust build passed. Existing EMA/MACD calculations are reused; the new numeric multiplication node is typed and rejects nonfinite output.

Focused historical-return integration: 16 Python tests passed in 0.518s after one synthetic zero-denominator fixture correction (valid market OHLC is positive; the zero is supplied by a graph constant). Nine frontend editor/model tests passed after correcting the test runner working directory. No product logic correction or weakened assertion was needed. The initially malformed private public-run invocation was corrected; the bounded cached integration then completed.
