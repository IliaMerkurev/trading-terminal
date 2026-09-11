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
- [Managed workers and persistence](adr/0005-workers-storage.md): one test at a time, immutable snapshots, versioned local pipe IPC, cancellation, SQLite run history and bounded result pages.
- [Trusted native import](adr/0006-native-import.md): AST-only preview, source-bound consent, unchanged native Strategy/Config execution in workers, declared multiple bar timeframes and visible compatibility failures.

## Not implemented or verified

There is no runnable desktop application, chart UI, comparison/export workflow, or installer. Seventy-one Windows regression tests have passed; these are calculation/data/service foundations, not V1 acceptance. Desktop import/trust controls remain to integrate. Historical Bybit tier changes remain unknown. One real BTCUSDT day was downloaded for spot and perpetuals; both cached datasets produced identical repeated offline results. A seven-day synthetic intrabar fixture measured 1.464s and 260.5 MiB peak working set on Windows.

## Next milestone

Implement the desktop graph editor (ILI-11), integrated Backtest/Results workflow (ILI-12), comparison/export (ILI-13) and Windows demonstration/acceptance checks (ILI-14). [PROJECT.md](../PROJECT.md) remains the authoritative scope.
