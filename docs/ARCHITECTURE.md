# Architecture

Product 0.3 extends the accepted research baseline. [ADR 0013](adr/0013-live-recovery-and-replay.md) defines the shared confirmed-minute signal path and additive live journal. Historical simulation and live/replay must use this one IR path; the UI never recomputes indicators. Public stream, notification and observed-price paper adapters extend the existing local Python/Tauri service, with no cloud backend or exchange order interface. Implementation and native acceptance status are tracked separately in [status](STATUS.md).

Status: implemented Windows development build; owner acceptance remains pending. [PROJECT.md](../PROJECT.md) is the authoritative specification; [ADR 0001](adr/0001-engine.md) selects the first runtime and records measured limitations.

| Component | Baseline | Responsibility |
| --- | --- | --- |
| Desktop host | Tauri 2 | Window lifecycle and bounded IPC |
| Interface | React, TypeScript, Vite | Strategy / Backtest / Experiments / Live / Results |
| Graph editor | React Flow | Layout and visual editing, independent of trading IR |
| Charts | Lightweight Charts | Display values from completed/active run data |
| Application layer | Python dataclasses and explicit validators | Validation, projects, data, worker orchestration |
| Storage | SQLite and Parquet | Metadata and reproducible historical datasets |
| Strategy representation | Versioned JSON IR plus native Python | Two distinct strategy inputs |
| Runtime | NautilusTrader 1.231.0 with simulation adapter | Calculation in a cancellable worker |
| Environment | Hash-pinned Python wheels, pnpm and Cargo locks | Reproducible Python setup |

The UI never independently computes financial results. The worker receives an immutable run snapshot and returns normalized results with engine artifacts and assumptions. Protocol output is isolated from native strategy stdout. Messages, errors, cancellation, and schema versions are explicit. Large table payloads are bounded.

A separate REST server is not required. Runtime selection must precede a large interface implementation. Changes to the baseline require an ADR with evidence and preserved product behavior. Exact versions, verified installation commands and limitations are recorded in the development guide.

See [engine evaluation](ENGINE_SELECTION.md) and [development guide](DEVELOPMENT.md).

0.2 retains this stack. [Execution versioning](adr/0010-execution-v2.md) adds causal protection crossings through the same engine. [Experiments](adr/0011-experiments.md) reserve the global calculation slot and reuse ordinary workers with frozen windows and shared source datasets. [Editor/runtime isolation](adr/0012-editor-and-isolation.md) documents reversible authoring and separate data/build roots. Migrations add tables without rewriting 0.1 snapshots.

[ADR 0009](adr/0009-development-delivery.md) records the validated installation path, explicit-validation choice and acceptance boundaries.

## Live/paper service

One `LiveManager` owns one public subscription pair (ticker and confirmed M1 candles), a durable `LiveSession` journal and bounded notification dispatch. `SignalStream` and `GraphEvaluator` are shared with historical execution and recorded replay. REST recovery replays missing confirmed minutes before CONNECTED; paper remains paused across missing ticks until explicit continuity revalidation. Windows sleep appears as a stale stream/gap, never a trustworthy continuation.

`PaperJournal` persists observed quotes before forwarding them to the retained Nautilus account, shared position rules and protection adapter. It reconstructs committed account results and verifies them on restart. Confirmed funding lookup is asynchronous; unpublished settlement rates delay account processing while retaining ordered prices. See [observed execution](adr/0015-observed-paper-execution.md).

The Tauri host emits native Windows toasts through a short-lived mode of the same executable. Sound uses the Windows system notification alias. Direct Telegram delivery uses only an exact per-data-root Windows Credential Manager target; the database and exports contain no Telegram secrets. See [notification/storage boundary](adr/0014-notifications-and-protected-storage.md). No exchange execution client, account API credential field, cloud backend or background service is created.
