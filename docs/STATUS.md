# Implementation status

V1 is implemented as a Windows development build and prepared for owner acceptance. The [product specification](../PROJECT.md) remains authoritative. The [demonstration guide](DEMO.md) distinguishes automated verification, actual desktop observations and pending manual acceptance.

## Implemented and tested

| Area | Evidence |
| --- | --- |
| Engine and account model | [ADR 0001](adr/0001-engine.md), [ADR 0002](adr/0002-simulation-profile.md); independent spot/perpetual long/short, sizing, costs, funding, mark liquidation and protection fixtures |
| Causal strategy graphs | [ADR 0003](adr/0003-strategy-ir.md); all V1 indicators/operators, typed acyclic IR, partial H1 and future perturbation tests |
| Public history and replay | [ADR 0004](adr/0004-data-manifests.md); separate trade/mark/funding, hashes, coverage/gaps and repeated offline results |
| Managed calculations | [ADR 0005](adr/0005-workers-storage.md); snapshots, SQLite history, bounded IPC, actual Windows worker-tree cancellation |
| Native Python | [ADR 0006](adr/0006-native-import.md); AST-only preview, source-bound consent, installed licensed EMA example, declared multiple native bar timeframes and visible unsupported behavior |
| Desktop research UI | [ADR 0007](adr/0007-desktop.md); editor/settings, downloads, real workers, saved charts/indicators, trade navigation and window lifecycle |
| Comparison and archives | [ADR 0008](adr/0008-archives-comparison.md); input/version differences, JSON-only bounded archive, fresh imported IDs, nonexecuting import and omitted history |

## Executed Windows checks

On 2026-09-11, `.venv/Scripts/python.exe -m unittest discover -s tests -v` passed **79 tests in 14.818s**. A separate newly created Windows Python environment installed all **17 hash-pinned packages** from verified wheels, passed `pip check`, and passed the same 79-test suite in 14.937s. The existing environment was preserved.

`node node_modules/vitest/vitest.mjs run` passed **8 tests across 6 files**. These cover typed graph wiring, save/native consent behavior, stored-value chart projection, comparison, exact archive File chunk transfer, sequential polling, and cancellation-before-desktop-exit ordering. Component tests mock IPC and are not native desktop automation.

`./scripts/setup.ps1` completed with the configured toolchain. `./scripts/launch.ps1 -NoLaunch` passed TypeScript, the production frontend build and locked offline Windows Rust build using existing MSVC/SDK. The frontend emits a 500 KiB chunk-size advisory (approximately 630 KiB JavaScript before compression); it is not a build failure.

Actual compiled desktop checks verified graph save into SQLite, a real cached BTCUSDT spot run, restart/reopening, visible candles/fill markers/equity, trade-to-chart navigation, comparison and export. A fresh public BTCUSDT spot day downloaded through the UI with **1,440 candles and complete requested coverage**. Active minimize/restore continued the worker to completion. Closing while active displayed the return/cancel dialog; returning preserved work. Completed-run exit closed the application.

One real BTCUSDT day for each market was previously downloaded and replayed twice offline with identical normalized results. The integrated spot example produced five completed trades, final equity 999.31274578 and fees 0.99993082 USDT; this is verification evidence, not a recommendation. The four offline demo cases separately pass hard-coded independent PnL/trade expectations.

## Performance and limits

A seven-day, 10,080-minute synthetic intrabar fixture measured **1.464s**, **260.5 MiB peak working set**, and **9.13 MiB normalized JSON** on Windows. A 30-day synthetic dataset also completed in the compiled desktop lifecycle checks. These are bounded measurements, not a guarantee for arbitrary native strategies or long histories. Run one calculation at a time; chart windows and IPC pages are bounded. Larger-scale memory budgets need further measurement before expanding supported workloads.

The model implements one single-position cross-margin profile, not full Bybit UTA or isolated margin. Minute paths and historical precision/risk-tier assumptions are explicit. Historical tier changes remain unknown. Native workers are not security sandboxes. Unsupported orders/feeds or unavailable dependencies fail visibly. Archives omit raw history and logs; checksums do not authenticate imported performance claims. No installer or binary release is provided; the project license remains undecided.

## Owner acceptance still pending

The native Windows file-picker import and a cancel-and-exit click before a desktop calculation finishes remain manual acceptance checks. The automation helper could not address the WebView-owned picker; bounded calculations completed before the exit click. Backend archive roundtrip, browser File transfer, close-dialog IPC ordering and actual worker cancellation pass independently. These observations do not establish that the unperformed native actions were tested.

Review the complete [demonstration](DEMO.md), including source trust, edited strategy wiring, indicator display and usability. Owner acceptance is distinct from implementation and automated checks. Deferred live trading, AI, optimization, DCA, multiple instruments and other post-V1 features remain outside this build.
