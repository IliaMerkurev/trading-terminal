# Implementation status

## Product 0.3 development build — acceptance evidence

Product **0.3-dev** is accepted by the owner with Telegram delivery as an explicit exception. It is an early development build, not stable or production-ready. See the [0.3 demonstration](DEMO_03.md) and [scope](../PROJECT.md#19-product-03-live-monitoring-and-paper-trading).

**Verified:** Live Bybit monitoring, reconnect/recovery, Windows notifications, sound notifications, paper trading, Live/Replay consistency and node deletion. The owner completed manual acceptance of the non-Telegram functionality in addition to the automated evidence below.

**Known issue — Telegram:** notification integration is implemented, but owner acceptance is currently failing. Test notification did not deliver despite credentials configured through the UI. Windows notifications and sound are verified. Telegram delivery remains open for investigation in [ILI-37](https://linear.app/ilia-merkurev/issue/ILI-37/fix-telegram-notification-delivery-after-03-owner-acceptance); ILI-30 remains In Review. Automated transport tests do not establish successful delivery.

Pre-merge regression rerun: **121 Python tests passed in 54.336s**, **28 frontend tests passed in 24.32s**, TypeScript/Vite production build passed, and the locked offline Windows/Rust build passed in **19.91s**. Targeted runs passed **29 Python tests** covering shared signals/replay, deduplication, recovery, paper accounting and notification isolation, plus **14 frontend tests** covering deletion/Undo/Redo and Live. The opt-in native Windows toast-history test passed again. Sound audibility is verified by owner acceptance, separately from automated dispatch checks. The existing frontend bundle-size advisory remains non-failing.

- Shared historical/live/replay Strategy IR, confirmed-minute closed/forming evaluation, false-to-true event transitions, atomic recording and durable at-most-once notification claims are implemented. Independent goldens and future-perturbation checks pass.
- Public Bybit spot/linear ticker and M1 subscriptions, stale/duplicate/out-of-order checks, heartbeat, bounded reconnect backoff and complete REST gap reconstruction are implemented. A 10-minute actual linear session recovered two missing candles after an interruption injected only into its own socket. Exactly two successful subscription sets were opened (initial and reconnect).
- That session recorded **4,105 observed paper inputs** and **6 signal events**; fresh replay matched all six. Paper entry/exit and explicit post-gap revalidation ran. Sampled Python working set increased from **199.9 to 204.1 MiB**, with a 204.1 MiB maximum; this bounded observation is not an always-on memory guarantee. The worker stopped normally.
- Paper uses the retained Nautilus account/risk/protection and position policy with later observed executable quotes, explicit costs, mark and confirmed funding. Tests verify independent long/short balances, fees/slippage, gap stops/takes, mark liquidation, delayed funding, restart without double charging and write-failure safety. Missing ticks are never manufactured from historical candles.
- Live dashboard, frozen session settings, saved-session selection, signal/event history, paper account/fills, recovery controls and replay verification are implemented. Native Windows checks observed actual spot updates, signal state, a virtual position, minimize/restore, normal shutdown and paused state on reopening.
- Windows toast/sound and direct Telegram dispatch have separate controls and bounded error isolation. A real Windows Credential Manager synthetic write/read/clear passed. The opt-in Rust test confirmed a real toast was retained in **this application's** Windows notification history. Subsequent owner acceptance verified Windows and sound, but Telegram Test did not deliver.
- Delete/context Delete share one operation, preserve fixed outputs, clean edges and support Undo/Redo. Component tests cover multiple selection and typing guards. Native Delete, Undo/Redo buttons, both context menus and restored connections were checked. Controlled node measurements are preserved to prevent an initially blank canvas.
- **121 Python tests passed in 51.809s; 28 frontend tests passed.** TypeScript/Vite and the locked offline Windows Rust build passed (4.13s). Seven focused transport/manager tests passed after tightening stale-ticker/forming-order validation. Existing native Pandas deprecation and frontend bundle-size advisories remain non-failing.
- Additive migration on a consistent copy preserved every preexisting table row/hash, immutable result checksums and SQLite integrity. Ordinary user data was not used for experiments. New live/paper tables do not rewrite 0.1/0.2 records.
- The isolated offline demo checks three signal timelines (2/2/1 events), replay equality and independently expected paper equity **1009.79**. Synthetic labels and data roots remain distinct from public market recordings and user data.

### Owner acceptance and evidence limits

The owner accepted non-Telegram functionality; Telegram Test remains failed and requires a later delivery check. Earlier automation did not demonstrate localized physical keyboard chords, a controlled 100%/125%/150% scale matrix or physical sleep/wake. Owner acceptance does not retroactively turn those into measured automated checks. Stale/gap reconstruction is covered deterministically and by the isolated public-connection interruption. No system setting was changed to manufacture a pass.

Live accepts visual IR only; compatible native Python remains historical-only and fails visibly if selected for Live. Forming-primary semantics advance at confirmed M1 boundaries, not every live tick. Funding-history delays can pause account processing while observed quotes queue; missing funding continuity or exhausted retries require review. At-most-once notifications can be missed after an uncertain crash outcome. This is one active instrument/strategy session, without real orders, exchange trading credentials, cloud service, background daemon or installer.

## Historical accepted main baseline: 0.2 development build

Product milestones previously called V1 and V2 are now 0.1 and 0.2. These names never meant stable 1.0/2.0 releases. Protocol/schema/profile integers and ADR numbers are unchanged. The normal main checkout builds and launches `Trading Terminal`, with `0.2-dev` shown separately from the permanent window title. Product version comes from Cargo package metadata; no temporary parallel checkout is required.

The versioning/housekeeping verification passed **92 Python tests in 43.867s**, **20 frontend tests in 23.57s**, TypeScript/Vite and the offline locked Windows/Rust build (**30.29s**). The compiled main application opened with the ordinary data root and the expected title/version badge. A fresh backup and copied migration check preserved **17 runs and 8 strategies**; the ordinary additive migration also preserved all rows and result checksums. Synthetic demonstration data stayed separate. The frontend bundle-size advisory remains; no dependency upgrade, installer or release binary was introduced.

## Accepted 0.2 milestone history

0.2 passed owner acceptance and was squash-merged into main through [PR #2](https://github.com/IliaMerkurev/trading-terminal/pull/2), commit `1309b4a1f97e2cb889240f510abf707ee94e6740`, on 2026-09-11. 0.1 behavior and data remain supported. The [product specification](../PROJECT.md) remains authoritative. The [0.2 demonstration](DEMO_V2.md) and [retained 0.1 demonstration](DEMO.md) distinguish automated verification from native/manual acceptance.

The mandatory pre-merge checks were rerun on the exact accepted 0.2 head: **92 Python tests passed in 73.457s**, **20 frontend tests passed in 34.68s**, TypeScript/Vite passed, and a separate offline locked Windows/Rust build passed in **1m 35s**. Runtime verification and `pip check` passed. Gitleaks 8.30.1 found no secrets in either outgoing 0.2 commit. The existing frontend bundle-size advisory remains. No installed dependency, user database or running build was replaced.

The owner reported successful manual 0.2 verification and accepted the remaining review items. The observations below retain the original automated/native evidence and its limitations; owner acceptance does not retroactively turn unperformed automation scenarios into executed tests. No installer, release or 0.3 scope is included.

## 0.2 evidence — 2026-09-11

- Profile version 2 adds continuous intraminute protection crossings; version 1 retains discrete observations. Independent long/short 95/105 versus 80/120 goldens, gaps, fees/slippage, funding/mark liquidation and partial-H1 future perturbations pass. See [execution model](adr/0010-execution-v2.md).
- Sequential parameter grids, immutable editor/runtime/data snapshots, cancellation/errors/interruption and frozen later-period validation use the same worker service. Actual Windows tests compare a 2×2 grid with four independent runs, and OOS with a standalone window run. Altering only future OOS candles leaves IS metrics/ranking and frozen graph/parameters unchanged. Shared source candles are not duplicated per combination; archives retain research provenance. See [experiments](adr/0011-experiments.md).
- Context-menu search, keyboard selection, graph history/duplication/validation, compact fill groups, viewport preservation and comparison labels are implemented. Component tests use mocked React Flow transforms/IPC and do not establish native Windows scaling or picker behavior.
- The full Python suite passed **92 tests in 41.302s**. The final frontend suite passed **20 tests across 10 files in 16.96s**. TypeScript, production Vite build and offline locked Windows Cargo build passed using the existing tools. No dependency was added or updated. The approximately 651 KiB JavaScript bundle still produces a size advisory.
- Additive migration on a separate consistent 0.1 copy preserved **17 runs and 8 strategies**, all existing records/result checksums and SQLite integrity. Existing environments and the running older build were preserved; no destructive migration is required.
- The synthetic 16-combination demonstration plus one frozen OOS validation and matching standalone run completed in **28.194s**, with **140.0 MiB sampled combined service/worker working set**. This is a bounded 240-minute fixture, not a guarantee at the maximum grid/history size. The limits are validated before materializing a grid: 256 combinations and 2,000,000 minute-runs including warmup. No date range is silently truncated to satisfy a budget.

The final compiled 0.2 window opened with its separate synthetic workspace and a working service connection. Actual native checks verified full-name context search, Enter creating exactly one selected node at the original click, Undo/Redo, independent node duplication and visible disconnected-input validation. The saved 16/16 experiment reopened, its candidate report displayed candles, fill markers and equity, and its frozen candidate displayed separate IS/OOS metrics matching the recorded demo. Two automation drag attempts produced no visible movement; native dragging and one-drag Undo remain unverified. Native Windows picker import, visibly active cancel-and-exit, and actual 100%/125%/150% scaling also remain manual 0.2 acceptance checks. No other application or system scaling was changed for testing. The separate development build/demo is ready for those checks; no installer, binary release or 0.3 work is included.

## Retained 0.1 evidence

## Implemented and tested

| Area | Evidence |
| --- | --- |
| Engine and account model | [ADR 0001](adr/0001-engine.md), [ADR 0002](adr/0002-simulation-profile.md); independent spot/perpetual long/short, sizing, costs, funding, mark liquidation and protection fixtures |
| Causal strategy graphs | [ADR 0003](adr/0003-strategy-ir.md); all 0.1 indicators/operators, typed acyclic IR, partial H1 and future perturbation tests |
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

## Historical 0.1 acceptance notes

The native Windows file-picker import and a cancel-and-exit click before a desktop calculation finishes remain manual acceptance checks. The automation helper could not address the WebView-owned picker; bounded calculations completed before the exit click. Backend archive roundtrip, browser File transfer, close-dialog IPC ordering and actual worker cancellation pass independently. These observations do not establish that the unperformed native actions were tested.

Review the complete [demonstration](DEMO.md), including source trust, edited strategy wiring, indicator display and usability. Owner acceptance is distinct from implementation and automated checks. Deferred live trading, AI, optimization, DCA, multiple instruments and other post-0.1 features remain outside this build.
