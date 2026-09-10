# Implementation status

## Available

- Product specification and acceptance requirements.
- Proposed component architecture.
- Engine decision and Windows evidence in [ADR 0001](adr/0001-engine.md).
- Synthetic execution, risk, partial-H1 causality, native example and worker-tree cancellation checks.
- Initial risk gateway and causal minute-to-primary aggregation components.

## Not implemented or verified

There is no runnable desktop application, user-facing trusted import workflow, historical data pipeline, complete simulation profile, chart UI, persistence/comparison/export workflow, or installer. Sixteen initial Windows tests pass; these are foundation/engine experiments, not V1 acceptance. Historical Bybit tiers and funding/mark integration remain unverified. No market data has been downloaded by these tests.

## Next milestone

Implement the explicit single-position cross-margin simulation profile, precision/sizing rules, full event ordering and independent regression fixtures (ILI-6), then the complete graph adapter (ILI-7). [PROJECT.md](../PROJECT.md) remains the authoritative scope.
