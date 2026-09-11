# Implementation status

## Available

- Product specification and acceptance requirements.
- Proposed component architecture.
- Engine decision and Windows evidence in [ADR 0001](adr/0001-engine.md).
- Synthetic execution, risk, partial-H1 causality, native example and worker-tree cancellation checks.
- Initial risk gateway and causal minute-to-primary aggregation components.
- [Simulation profile](adr/0002-simulation-profile.md): unborrowed spot, single-position cross-margin perpetuals, sizing, fee/slippage/funding effects, mark liquidation, protections, explicit minute path and normalized metrics.
- [Strategy IR and adapter](adr/0003-strategy-ir.md): typed acyclic graphs, all V1 indicators, comparisons/crossings/boolean logic, shared signal outputs and causal partial-primary evaluation with recorded indicator values.
- [Historical datasets and manifests](adr/0004-data-manifests.md): public Bybit downloads, separate trade/mark/funding storage, gap reports, current-metadata assumptions, checksummed Parquet snapshots and offline replay.

## Not implemented or verified

There is no runnable desktop application, user-facing trusted import workflow, chart UI, run-history/comparison/export workflow, or installer. Fifty-nine Windows tests pass; these are calculation/data foundations, not V1 acceptance. Historical Bybit tier changes remain unknown. One real BTCUSDT day was downloaded for spot and perpetuals; both cached datasets produced identical repeated offline results. A seven-day synthetic intrabar fixture measured 1.464s and 260.5 MiB peak working set on Windows.

## Next milestone

Implement persistent run results, bounded IPC and managed workers (ILI-9), then explicitly trusted native import (ILI-10). [PROJECT.md](../PROJECT.md) remains the authoritative scope.
