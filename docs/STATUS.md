# Implementation status

## Available

- Product specification and acceptance requirements.
- Proposed component architecture.
- Engine decision and Windows evidence in [ADR 0001](adr/0001-engine.md).
- Synthetic execution, risk, partial-H1 causality, native example and worker-tree cancellation checks.
- Initial risk gateway and causal minute-to-primary aggregation components.
- [Simulation profile](adr/0002-simulation-profile.md): unborrowed spot, single-position cross-margin perpetuals, sizing, fee/slippage/funding effects, mark liquidation, protections, explicit minute path and normalized metrics.

## Not implemented or verified

There is no runnable desktop application, user-facing trusted import workflow, historical data pipeline, complete graph adapter, chart UI, persistence/comparison/export workflow, or installer. Thirty-seven Windows tests pass; these are calculation foundations, not V1 acceptance. Historical Bybit tier coverage and live data-download integration remain unverified. No market data has been downloaded by these tests.

## Next milestone

Implement validated Strategy IR, all required indicators and the causal graph adapter (ILI-7), then historical data and immutable manifests (ILI-8). [PROJECT.md](../PROJECT.md) remains the authoritative scope.
