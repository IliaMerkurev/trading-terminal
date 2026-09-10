# Proposed architecture

Status: component proposal with initial engine foundations; not an implemented application. [PROJECT.md](../PROJECT.md) is the authoritative specification; [ADR 0001](adr/0001-engine.md) selects the first runtime and records measured limitations.

| Component | Baseline | Responsibility |
| --- | --- | --- |
| Desktop host | Tauri 2 | Window lifecycle and bounded IPC |
| Interface | React, TypeScript, Vite | Strategy / Backtest / Results |
| Graph editor | React Flow | Layout and visual editing, independent of trading IR |
| Charts | Lightweight Charts | Display values from completed/active run data |
| Application layer | Python and Pydantic | Validation, projects, data, worker orchestration |
| Storage | SQLite and Parquet | Metadata and reproducible historical datasets |
| Strategy representation | Versioned JSON IR plus native Python | Two distinct strategy inputs |
| Runtime | NautilusTrader 1.231.0 with simulation adapter | Calculation in a cancellable worker |
| Environment | uv and pinned dependencies | Reproducible Python setup |

The UI never independently computes financial results. The worker receives an immutable run snapshot and returns normalized results with engine artifacts and assumptions. Protocol output is isolated from native strategy stdout. Messages, errors, cancellation, and schema versions are explicit. Large table payloads are bounded.

A separate REST server is not required. Runtime selection must precede a large interface implementation. Changes to the baseline require an ADR with evidence and preserved product behavior. Exact versions and installation requirements remain unverified.

See [engine evaluation](ENGINE_SELECTION.md) and [development guide](DEVELOPMENT.md).
