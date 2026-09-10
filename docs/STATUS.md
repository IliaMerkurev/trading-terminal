# Implementation status

## Available

- Product specification and acceptance requirements.
- Proposed component architecture.
- Engine decision and Windows evidence in [ADR 0001](adr/0001-engine.md).
- Synthetic execution, risk, partial-H1 causality, native example and worker-tree cancellation checks.
- Initial risk gateway and causal minute-to-primary aggregation components.
- [Simulation profile](adr/0002-simulation-profile.md): unborrowed spot, single-position cross-margin perpetuals, sizing, fee/slippage/funding effects, mark liquidation, protections, explicit minute path and normalized metrics.
- [Strategy IR and adapter](adr/0003-strategy-ir.md): typed acyclic graphs, all V1 indicators, comparisons/crossings/boolean logic, shared signal outputs and causal partial-primary evaluation with recorded indicator values.

## Not implemented or verified

There is no runnable desktop application, user-facing trusted import workflow, historical data pipeline, chart UI, persistence/comparison/export workflow, or installer. Forty-eight Windows tests pass; these are calculation foundations, not V1 acceptance. Historical Bybit tier coverage and data-download integration remain unverified. No market data has been downloaded by these tests. A seven-day synthetic intrabar fixture measured 1.464s and 260.5 MiB peak working set on Windows.

## Next milestone

Implement historical data coverage and immutable dataset/run manifests (ILI-8), then persistent results and managed workers (ILI-9). [PROJECT.md](../PROJECT.md) remains the authoritative scope.
