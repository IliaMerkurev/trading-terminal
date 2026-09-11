# Implementation status

V2 passed owner acceptance and was squash-merged into main through [PR #2](https://github.com/IliaMerkurev/trading-terminal/pull/2), commit `1309b4a1f97e2cb889240f510abf707ee94e6740`, on 2026-09-11. V1 behavior and data remain supported. The [product specification](../PROJECT.md) remains authoritative. The [V2 demonstration](DEMO_V2.md) and [retained V1 demonstration](DEMO.md) distinguish automated verification from native/manual acceptance.

The mandatory pre-merge checks were rerun on the exact accepted V2 head: **92 Python tests passed in 73.457s**, **20 frontend tests passed in 34.68s**, TypeScript/Vite passed, and a separate offline locked Windows/Rust build passed in **1m 35s**. Runtime verification and `pip check` passed. Gitleaks 8.30.1 found no secrets in either outgoing V2 commit. The existing frontend bundle-size advisory remains. No installed dependency, user database or running build was replaced.

The owner reported successful manual V2 verification and accepted the remaining review items. The observations below retain the original automated/native evidence and its limitations; owner acceptance does not retroactively turn unperformed automation scenarios into executed tests. No installer, release or V3 scope is included.

## V2 evidence — 2026-09-11

- Profile version 2 adds continuous intraminute protection crossings; version 1 retains discrete observations. Independent long/short 95/105 versus 80/120 goldens, gaps, fees/slippage, funding/mark liquidation and partial-H1 future perturbations pass. See [execution model](adr/0010-execution-v2.md).
- Sequential parameter grids, immutable editor/runtime/data snapshots, cancellation/errors/interruption and frozen later-period validation use the same worker service. Actual Windows tests compare a 2×2 grid with four independent runs, and OOS with a standalone window run. Altering only future OOS candles leaves IS metrics/ranking and frozen graph/parameters unchanged. Shared source candles are not duplicated per combination; archives retain research provenance. See [experiments](adr/0011-experiments.md).
- Context-menu search, keyboard selection, graph history/duplication/validation, compact fill groups, viewport preservation and comparison labels are implemented. Component tests use mocked React Flow transforms/IPC and do not establish native Windows scaling or picker behavior.
- The full Python suite passed **92 tests in 41.302s**. The final frontend suite passed **20 tests across 10 files in 16.96s**. TypeScript, production Vite build and offline locked Windows Cargo build passed using the existing tools. No dependency was added or updated. The approximately 651 KiB JavaScript bundle still produces a size advisory.
- Additive migration on a separate consistent V1 copy preserved **17 runs and 8 strategies**, all existing records/result checksums and SQLite integrity. Existing environments and the running older build were preserved; no destructive migration is required.
- The synthetic 16-combination demonstration plus one frozen OOS validation and matching standalone run completed in **28.194s**, with **140.0 MiB sampled combined service/worker working set**. This is a bounded 240-minute fixture, not a guarantee at the maximum grid/history size. The limits are validated before materializing a grid: 256 combinations and 2,000,000 minute-runs including warmup. No date range is silently truncated to satisfy a budget.

The final compiled V2 window opened with its separate synthetic workspace and a working service connection. Actual native checks verified full-name context search, Enter creating exactly one selected node at the original click, Undo/Redo, independent node duplication and visible disconnected-input validation. The saved 16/16 experiment reopened, its candidate report displayed candles, fill markers and equity, and its frozen candidate displayed separate IS/OOS metrics matching the recorded demo. Two automation drag attempts produced no visible movement; native dragging and one-drag Undo remain unverified. Native Windows picker import, visibly active cancel-and-exit, and actual 100%/125%/150% scaling also remain manual V2 acceptance checks. No other application or system scaling was changed for testing. The separate development build/demo is ready for those checks; no installer, binary release or V3 work is included.

## Retained V1 evidence

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

## Historical V1 acceptance notes

The native Windows file-picker import and a cancel-and-exit click before a desktop calculation finishes remain manual acceptance checks. The automation helper could not address the WebView-owned picker; bounded calculations completed before the exit click. Backend archive roundtrip, browser File transfer, close-dialog IPC ordering and actual worker cancellation pass independently. These observations do not establish that the unperformed native actions were tested.

Review the complete [demonstration](DEMO.md), including source trust, edited strategy wiring, indicator display and usability. Owner acceptance is distinct from implementation and automated checks. Deferred live trading, AI, optimization, DCA, multiple instruments and other post-V1 features remain outside this build.
