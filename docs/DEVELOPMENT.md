# Development guide

Read [PROJECT.md](../PROJECT.md), [architecture](ARCHITECTURE.md), [status](STATUS.md) and [AGENTS.md](../AGENTS.md). Preserve existing changes. Windows x64 is the verified target; other platforms and a conventional installer are deferred.

## Prerequisites and setup

The verified environment uses CPython 3.12.14 x64, Node 24.19.0, pnpm 11.19.0, Rust/Cargo 1.98.1 with the x86_64-pc-windows-msvc toolchain, MSVC 2019 16.11.40, Windows SDK 10.0.19041 and an installed WebView2 Runtime. The build succeeds with these existing Microsoft tools; system updates are not part of setup. `node`, `pnpm` and `cargo` must be available in the setup shell.

From the project directory:

```powershell
.\scripts\setup.ps1
.\scripts\launch.ps1
```

If necessary, pass an installed CPython 3.12 x64 executable to `setup.ps1 -Python`. Setup creates `.venv` only when absent and installs hash-pinned binary wheels from official PyPI using `requirements/runtime-windows-py312.lock`. An existing environment is checked and preserved; mismatches fail visibly. Frontend packages use the frozen pnpm lock and disabled install scripts. Cargo fetches its locked Windows dependencies from crates.io. Project caches remain local. No system tool is installed or updated.

The launcher uses the configured tools recorded during setup if Node/Cargo are absent from the current shell. It builds frontend assets and the embedded Windows executable with locked offline Cargo dependencies, then opens it. Moving the checkout requires rebuilding. Close the application before rebuilding its executable. No execution-policy or security-policy bypass is part of these commands. Run from a shell permitted to execute local project scripts.

## V2 launcher and separate demonstration

After project setup, the calling pinned Python can launch without PowerShell script execution:

```powershell
.\.venv\Scripts\python.exe scripts\desktop.py --build
```

Omit `--build` when reopening. `--no-launch` verifies/builds only. `--data-root` accepts an absolute isolated data directory; `--cargo-home` can reuse an existing locked project cache. An isolated checkout can be invoked with another verified environment's Python executable. No dependency or system setting is changed. The existing setup scripts remain available in shells permitted to execute them.

See [V2 demonstration](DEMO_V2.md) for the separate synthetic data root. To check additive migrations, pass a consistent backup and a **new** destination to `scripts/verify_migration.py`; it refuses to overwrite a destination. Never run migration experiments on the active user database.

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
