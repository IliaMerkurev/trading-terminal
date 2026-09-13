# Development guide

Read [PROJECT.md](../PROJECT.md), [architecture](ARCHITECTURE.md), [status](STATUS.md) and [AGENTS.md](../AGENTS.md). Preserve existing changes. Windows x64 is the verified target; other platforms and a conventional installer are deferred.

## Product versions and working branches

The accepted product is **0.5 development build**, displayed as `0.5-dev`. Product 0.1 was the first working milestone; 0.2 added research workflows; accepted 0.3 added live/paper monitoring. Product 0.6 and later milestones remain future work and are not authorized by the 0.5 merge. Version 1.0 is reserved for a mature stable release. Internal protocol/schema/profile versions and ADR numbers are independent of product versions.

`src-tauri/Cargo.toml` package version is the single product-version source (`0.5.0-dev` in SemVer). Tauri uses it when its configuration omits a version override; the existing UI badge reads Tauri app metadata. The private frontend package does not declare another product version. Update the root package entry in Cargo.lock alongside a version bump; do not change dependency versions. Window title and executable name stay `Trading Terminal` and `trading-terminal.exe`.

Use the main project checkout for the current build, with its existing `.venv`, `node_modules`, local Cargo cache and ordinary `.local-data`. After feature acceptance, return it to current `main`; temporary worktrees are optional isolation tools, not required launch dependencies. Archive their private data separately before removing them. Never merge synthetic demo databases into the ordinary user database.

The historical branches `codex/v1` and `codex/v2` remain unchanged: their product milestones are now called 0.1 and 0.2. Future branches use `codex/03` for product 0.3, `codex/04` for 0.4, and so on. Naming a future branch does not authorize starting it. Existing `DEMO_V2.md` and `terminal.demo_v2` names remain compatibility entry points for the 0.2 demonstration; execution `v2` module/test names mean internal profile 2. Existing saved labels and historical Git/PR text are not rewritten.

## Verified toolchain

The verified environment uses CPython 3.12.14 x64, Node 24.19.0, pnpm 11.19.0, Rust/Cargo 1.98.1 with the x86_64-pc-windows-msvc toolchain, MSVC 2019 16.11.40, Windows SDK 10.0.19041 and an installed WebView2 Runtime. The build succeeds with these existing Microsoft tools; system updates are not part of setup. `node`, `pnpm` and `cargo` must be available in the setup shell.

From the project directory:

```powershell
.\scripts\setup.ps1
.\scripts\launch.ps1
```

If necessary, pass an installed CPython 3.12 x64 executable to `setup.ps1 -Python`. Setup creates `.venv` only when absent and installs hash-pinned binary wheels from official PyPI using `requirements/runtime-windows-py312.lock`. An existing environment is checked and preserved; mismatches fail visibly. Frontend packages use the frozen pnpm lock and disabled install scripts. Cargo fetches its locked Windows dependencies from crates.io. Project caches remain local. No system tool is installed or updated.

The launcher uses the configured tools recorded during setup if Node/Cargo are absent from the current shell. It builds frontend assets and the embedded Windows executable with locked offline Cargo dependencies, then opens it. Moving the checkout requires rebuilding. Close the application before rebuilding its executable. No execution-policy or security-policy bypass is part of these commands. Run from a shell permitted to execute local project scripts.

## Launcher and separate demonstrations

After project setup, the calling pinned Python can launch without PowerShell script execution:

```powershell
.\.venv\Scripts\python.exe scripts\desktop.py --build
```

Omit `--build` when reopening. `--no-launch` verifies/builds only. `--data-root` accepts an absolute isolated data directory; `--cargo-home` can reuse an existing locked project cache. An isolated checkout can be invoked with another verified environment's Python executable. No dependency or system setting is changed. The existing setup scripts remain available in shells permitted to execute them.

See [0.2 demonstration](DEMO_V2.md) for the separate synthetic data root. To check additive migrations, pass a consistent backup and a **new** destination to `scripts/verify_migration.py`; it refuses to overwrite a destination. Never run migration experiments on the active user database.

## Validation commands

```powershell
.venv/Scripts/python.exe scripts/verify_runtime.py
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m unittest discover -s tests -v
node node_modules/vitest/vitest.mjs run
.\scripts\launch.ps1 -NoLaunch
```

The Python suite tests real Windows worker processes and independent accounting/causality expectations. Component tests use a simulated DOM and mocked IPC; they do not prove native file-dialog behavior. The production frontend is type-checked before building. See [status](STATUS.md) for actual outcomes and [demo](DEMO.md) for acceptance steps.

For an offline synthetic demonstration, close the application and run:

```powershell
.venv/Scripts/python.exe -m terminal.demo
.\scripts\launch.ps1
```

The demo creates four labeled synthetic cases with independently checked expected results. Existing strategies, results and market data are preserved. Repeating with the same implementation reuses the demonstration record. This is not a benchmark of strategy profitability.

## Local data and publication

Application databases, downloaded data, WebView state, exports and worker artifacts are under ignored `.local-data/`. Environments and build caches are also ignored. Native source consent is local and is not exported. Back up local data with the application closed; never commit raw datasets, private instructions or credentials.

Inspect exact staged files and diffs, scan all outgoing commits with the pinned established secret scanner, and review privacy/license obligations before publication. Ordinary deletion never removes content from previous commits. Do not assign a project license or distribute third-party binaries without the applicable license review.

## Live development and acceptance

See [the 0.4 demonstration](DEMO_04.md) and retained [0.3 demonstration](DEMO_03.md). Use an absolute isolated `--data-root` for public-stream probes, synthetic paper fixtures and notification tests. Never merge these journals into user research data. Public subscriptions require network access but no exchange credentials. Confirmed M1 candles drive shared historical/live/replay IR; forming primary bars still advance on minute closes, not every tick.

`websockets==15.0.1` is pinned by wheel hash in the runtime lock (BSD-3-Clause). It has no runtime dependencies. Windows notification bindings use the already locked `windows` Rust crate; credentials use the Windows API through Python ctypes. Do not add a cloud backend. Telegram secrets must enter only the application password-field flow and never command lines, fixtures or test logs.

Reconnect and account goldens run offline in the Python suite. A successful toast API/mock call does not prove a visible toast; sound audibility and owner-configured Telegram delivery are separate acceptance checks. Native notification settings are respected, never changed by the application. Ordinary shutdown stops monitoring; this is not a background service.

For 0.4, one `PublicStream` owns all four public topics; widgets must not open independent connections. Display timeframe state stays in `LiveChart` and never enters `live_start_terminal`. Recorded IR samples are the only indicator source. Manual PAPER requests use unique IDs, a next-observed-quote rule and the existing account engine; see [ADR 0016](adr/0016-shared-market-terminal.md) and [ADR 0017](adr/0017-manual-paper-source.md).

The required long-run check uses the compiled Windows application, an isolated public session and at least 30 minutes of wall time. Record start/end, per-topic counters, process/memory samples, UI interactions, reconnects and errors. Do not substitute a headless probe, claim a natural disconnect from a simulated one or infer Telegram delivery from a mocked transport. Bounded UI arrays do not imply unlimited disk retention; paper input/order safety budgets remain explicit.


## Product 0.5 development

Work in `codex/05` from the accepted main baseline. Public market ownership is independent from selected strategy; no widget owns another socket. Native display intervals and chart page cache remain independent from strategy M1 warmup. Use isolated data for cold/warm H1 measurements and test migrations on consistent copies. Preserve the in-use executable; `CARGO_TARGET_DIR` may select a separate ignored build directory. No historical branch deletion, main merge, Telegram investigation or 0.6 is authorized by this milestone.

`scripts/desktop.py --target-dir .local-tools/05-final-target` uses the same directory for build and launch. It also honors an existing `CARGO_TARGET_DIR` when no argument is provided. Without either, the ordinary `src-tauri/target` remains the default. A separate `--data-root` must be absolute; omission uses ordinary user data. Never copy a demo database over that data.

The [0.5 demo](DEMO_05.md) prepares two small synthetic parameter candidates and one frozen later-period run in a new directory. Position Management is opt-in and schema-versioned independently from product version. Add its fields through `PositionConfig`, keep decisions in `PositionManager`, and reconcile actual Nautilus fills through `PositionLedger`. Do not add frontend financial calculations or a second paper engine. Runtime snapshots hash Python modules: do not edit them during a reproducibility test or measured live run.
