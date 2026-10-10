# Development guide

Read [PROJECT.md](../PROJECT.md), [architecture](ARCHITECTURE.md), [status](STATUS.md) and [AGENTS.md](../AGENTS.md). Preserve existing changes. Windows x64 remains the desktop target; historical native evidence does not establish acceptance of the current candidate. Linux/browser research has separate verified coverage. See the [current checkpoint](CHECKPOINT.md) for navigation, priorities and platform limits; a conventional installer remains deferred.

## Product versions and working branches

Current work is the Market/Lab UX continuation on `codex/terminal-mvp`, following the Research workspace extension originally developed on `codex/research-studio` from merged 0.6-dev main (`a5bb197`). No new product version is introduced. Owner-led unaided usability and current Windows/native acceptance remain pending. Product 0.1 was the first working milestone; 0.2 added research workflows; accepted 0.3 added live/paper monitoring. Version 1.0 is reserved for a mature stable release. Internal protocol/schema/profile versions and ADR numbers are independent of product versions.

`src-tauri/Cargo.toml` package version is the single product-version source (`0.6.0-dev` in SemVer for this branch). Tauri uses it when its configuration omits a version override; the existing UI badge reads Tauri app metadata. The private frontend package does not declare another product version. Update the root package entry in Cargo.lock alongside a version bump; do not change dependency versions. Window title and executable name stay `Trading Terminal` and `trading-terminal.exe`.

Build and launch the intended candidate checkout with its matching `.venv`, `node_modules` and platform toolchain. Keep the accepted source/runtime/build/data baseline independent; browser acceptance uses an explicit separate data root. Returning to `main` or integrating the candidate is a separate step, not implied by a successful checkpoint. Temporary worktrees are optional isolation tools, not required launch dependencies. Archive their private data separately before removing them. Never merge synthetic demo databases into the ordinary user database.

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

Inspect exact staged files and diffs, scan all outgoing commits with the pinned established secret scanner, and review privacy/license obligations before publication. Ordinary deletion never removes content from previous commits. The project uses the [MIT License](../LICENSE); changing it requires owner authorization. Do not distribute third-party binaries without the applicable license review.

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


## Product 0.5.1 maintenance

Historical maintenance candidate: `0.5.1-dev` on `codex/051`, from accepted 0.5-dev. Follow the current AGENTS.md budgeted-validation and owner-managed Linear rules. The 0.5 development branch instructions above are historical. Work is limited to ILI-135 through ILI-138; no 0.6 or Telegram work.

Run final regression/build once after focused checks. Use an isolated absolute data root and a separate Cargo target for native smoke; preserve the owner executable. Verify the additive `replay_jobs` table on a consistent database copy before ordinary data is opened. Replay jobs share the existing calculation slot and are cancelled on close; interrupted jobs remain inspectable after restart. See [maintenance acceptance](DEMO_051.md).


## Product 0.6 development

Keep the accepted source, Python runtime, executable and data independent from
the `codex/06` checkout. A copied executable alone is not a fallback: the backend
path is compiled in. Use the desktop launcher above from the intended checkout
and a separate Cargo target/data root for verification. See [0.6 acceptance](DEMO_06.md).
Use only the owner-created Library issues and budgeted validation; no optional
strategy expansion before the approved core and budget gates. No automatic
resume, main merge, release or next-version work is part of this candidate.

## Linux source-checkout research preview

The separate Linux adaptation retains the Windows setup, lockfile and Job Object
implementation. It does not establish Windows regression acceptance or a
packaged Linux release. Supported Linux runtime: x86_64, glibc 2.35 or newer,
CPython 3.12, and the same NautilusTrader 1.231.0 engine. The Linux wheel lock has
its own binary hashes and upstream's Linux-only uvloop dependency. Never install
the Windows wheel lock on Linux or silently upgrade the engine.

Install the [official Tauri Linux prerequisites](https://v2.tauri.app/start/prerequisites/)
for your distribution first. On an authorized Debian machine with an administrator:

```sh
sudo apt-get update
sudo apt-get install build-essential pkg-config libwebkit2gtk-4.1-dev libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev xdg-utils
```

Debian production WebKit uses absolute helper-process paths. Extracting libraries
into a project folder alone does not provide a working renderer. Do not disable
the sandbox or patch system paths to make a window appear. Node 24.19.0, pnpm
11.19.0 and Rust/Cargo 1.98.1 must be available on PATH. Then:

```sh
python3.12 scripts/setup_linux.py
.venv/bin/python scripts/desktop.py --build --data-root /absolute/path/to/separate-research-data
```

Setup manages project dependencies, never system packages/security/credentials.
An existing mismatched environment is preserved and rejected. The launch command
requires a desktop session and uses native Tauri IPC with the Python service.
It does not provide a browser transport. Omit `--build` to reopen;
`--no-launch` validates/builds without launching. Output is
`src-tauri/target/debug/trading-terminal`, or the requested `--target-dir`.
Moving the checkout requires rebuilding its embedded backend path.

Use isolated data for validation. Native Python execution (including native
library candidates), Windows notifications, sound and protected Telegram storage
are explicitly unavailable on Linux. Static previews and saved reports remain
available. No plaintext/in-memory credential fallback or real orders are added.

Linux uses a pipe-controlled supervisor for application-owned graph/replay
workers and inherited workspace locks. It handles service/host death while the
supervisor remains alive; killing that supervisor can orphan workers. Process
groups do not contain arbitrary escaped descendants and are not a security
sandbox. Windows retains its original Job Object implementation.

Linux snapshots record their own platform/runtime; do not represent them as
Windows repeats. See [status](STATUS.md) for fresh versus historical evidence,
GUI blockers and Windows acceptance still required before integration.

## Local browser research mode

After the matching platform setup and production frontend build, use the same
verified Python environment to run the browser adapter:

```sh
node scripts/frontend.mjs build
.venv/bin/python scripts/browser.py --data-root /absolute/path/to/browser-research-data --port 8765
```

On Windows use `.venv/Scripts/python.exe` instead. Open the exact numeric
loopback URL printed by the launcher (normally `http://127.0.0.1:8765`). This
uses the built frontend, not the Vite layout preview. Stop and restart the host
after rebuilding frontend assets; its allowed static-file inventory is fixed at
startup. No system WebKit runtime
is required for browser mode; a current local browser is required. The original
Windows/Tauri launch commands remain available without conversion or migration.
The workspace lock prevents concurrent desktop/browser ownership of one data
root. Use separate synthetic roots for verification and never copy them into
ordinary user data.

The host stays running after tabs close or reload. Use the UI's confirmed Stop
local service action or Ctrl+C in its terminal to stop managed work and release
the workspace. Browser exports download through the authenticated local session;
desktop exports retain their folder-opening action. Do not expose this server
through a proxy, forwarding rule, public port or remote bind. Session tokens are
per-launch memory-only material and must never be copied into URLs or logs.
See [ADR 0030](adr/0030-local-browser-research.md) for the boundary and limitations.


## Local observation fixture

Create a new, isolated synthetic root (the command refuses any existing path):

```sh
.venv/bin/python scripts/prepare_observation_fixture.py /absolute/new/observation-fixture
node scripts/frontend.mjs build
.venv/bin/python scripts/browser.py --data-root /absolute/new/observation-fixture --port 8770
```

Use the corresponding `.venv/Scripts/python.exe` on Windows. Start in Data and
choose Observe this history for the synthetic hourly-cycle snapshot. Expected:
900 invented candles, pages of 500 and 400; the separate gap snapshot has 499
candles in its first page and a missing 2024-01-02 00:00 UTC slot. Reopen the saved
observation for 2024-01-26 00:00–2024-01-27 00:00 UTC; its first/last closes are
100.5/123.5. No runs exist after fixture creation or observation opening.

Test observation must open Lab with that exact period and no execution. Select
RSI threshold, 1h and period 2 for a small compatible explicit test. A new
observation starting at the source's first hour must retain its dates and show
insufficient preceding warmup. Review and Start are separate actions. After a
successful linked test, edit the note, reopen the test and return to its original
revision; restart and check persistence. Keep fixture and user data separate.

## Displayed-period evidence fixture

Create a new isolated root with `scripts/prepare_display_fixture.py` using the
verified Python runtime. It reuses the independent observation candles, then
completes one three-row synthetic comparison. It writes
`synthetic-display-fixture.json` containing exact dataset/run/batch IDs, a
never-run later interval, the separate gap source, initial counts and immutable
JSON hashes. It refuses any existing root. Build and start the browser adapter
with this root; never merge it into ordinary research data.

Open the never-run interval in Saved history without testing it. A later-period
overlap review must show manual displayed ranges and zero admissions in that
interval. Panning records only actual visible candle labels; gaps remain absent.
Selected comparison numeric cells and individual report metrics expose their
full evaluation interval; individual charts record only the visible candle pane.
Hidden/prefetched surfaces, dataset lists and saving notes create no view event.
Repeated callbacks in one presentation deduplicate. Reopen/restart must preserve
old events, source isolation, note revisions, frozen prior reviews and immutable
JSON hashes. An injected display-write failure must leave reading available and
show incomplete tracking, including in subsequent freeze reviews.

This is partial in-app display evidence, not proof of human reading. Imported or
legacy reports without original local admissions, replay/live, other surfaces
and outside-app exposure remain incomplete. View coverage starts separately
from original admission coverage. Backend-issued chart references retain up to
32 verified pages in memory; expired references warn instead of guessing. The
frontend allows 256 outstanding records and 4,096 distinct callbacks per
presentation, warning explicitly if that bound is reached. Read-only use does
not start a strategy, and no financial artifact is rewritten.


## Saved-history display projection checks

Reuse an existing isolated observation fixture for this UI-only slice; no new
history, note or test run is necessary. Source starts with the native resolution.
On the hourly cycle, the first complete 4h bar is O100/H105/L99/C103.5 with volume
40; a full day is O100/H125/L99/C123.5 with volume 240. The gap source suppresses
the January 2 00:00 four-hour bucket and daily bucket. Source still exposes the
other recorded hours. The first 500-hour page's final day has 20/24 slots; the
next page starts with the same day's remaining 4/24. Neither partial day renders
an aggregate, and outside-page slots are not labeled missing history.

Check keyboard reveal, pointer selection after display changes, Fit page and
page switching at ordinary and narrow widths. Reopen an exact saved revision,
switch display, visit Lab and return without saving or starting a test. Existing
source-aligned dates, locked notes and test choices must stay intact. Browser
layout/navigation inspection alone does not establish persisted exposure counts;
separate deterministic mapping tests cover that boundary when no read-only
database diagnostic is used.

```sh
node node_modules/vitest/vitest.mjs run frontend/src/observationChartData.test.ts frontend/src/ObservationChart.test.tsx frontend/src/Observations.test.tsx frontend/src/DisplayedEvidence.test.tsx frontend/src/UserJourneys.test.tsx
node scripts/frontend.mjs build
```

Stop the local host before rebuilding, then restart to refresh its static-file
inventory. This adds no backend/schema, dependency, product-version or native
acceptance gate. Actual evidence and remaining limits are in STATUS.md.


## Saved-history date navigation checks

Reuse an isolated existing 900-hour observation fixture; no new market data,
observation save or strategy run is needed. First reads 500 source slots and
Latest the final 400. An arbitrary native UTC target must remain exact, including
a short page at the last opening; the exclusive end and misaligned dates are
rejected. The independent browse draft, dirty note and compatible display choice
survive ordinary Market/Lab returns. Explicit Return to observation start uses
the note's original date. Test the known missing opening and display-misaligned
page edges without fabricating bars or extending the 500-source-slot budget.

The focused frontend pass covers strict UTC/source arithmetic, immutable failed-
page retry, stale response/declaration guards, note and Lab preservation and
actual-chart visibility cleanup. Existing chart projection/recorder behavior is
unchanged; do not report component fault injection as a production-browser test.

```sh
node node_modules/vitest/vitest.mjs run frontend/src/observationNavigation.test.ts frontend/src/ObservationsNavigation.test.tsx frontend/src/Observations.test.tsx frontend/src/ObservationsHistory.test.tsx frontend/src/UserJourneys.test.tsx frontend/src/DisplayedEvidence.test.tsx frontend/src/ObservationChart.test.tsx
node scripts/frontend.mjs build
```

Stop the host before building, then restart with the same isolated root and the
printed numeric loopback URL. Check wrapping, keyboard Go and reachable actions
at ordinary and narrow widths. Windows/native and owner-led unaided acceptance
remain separate; no new backend or full-regression gate is implied.


## Durable import receipt checks

Use a new disposable synthetic root for storage faults; never inject a fault into
ordinary research data. The fixture archive contains two independently authored,
different results and no market downloads or imported source execution. The
subprocess probe terminates at explicit barriers rather than timing sleeps.

```sh
.venv/bin/python -W ignore -m unittest tests.test_archive_receipts tests.test_archive_receipt_backup tests.test_archive_receipt_transport tests.test_archives tests.test_storage_resilience -q
node node_modules/vitest/vitest.mjs run frontend/src/ProjectTransfer.test.tsx frontend/src/ImportRecovery.test.tsx frontend/src/AppImportRecovery.test.tsx frontend/src/api.test.ts frontend/src/AppStorageSafety.test.tsx frontend/src/UserJourneys.test.tsx
node scripts/frontend.mjs build
```

On Windows use the matching `.venv/Scripts/python.exe`; do not infer native
acceptance from these commands running elsewhere. The complete backend pass and
subsequent focused corrections are distinguished in STATUS.md.

For browser inspection, use Saved tests → Individual run reports → Project
archive → Recent imports. Inspect completed, partial and interrupted receipts;
open only a published member, return, reload and restart the same isolated service.
The exact operation and destination IDs must persist. A completed report can still
be read from SQLite when an artifact is missing: this UI always says artifact
verification is not checked. Never deliberately damage ordinary artifacts.

A lost-response acceptance harness, if used, must remain outside production code
and act only on a new synthetic workspace after ordinary authenticated request
handling has really committed completion. Do not add a product fault switch,
proxy, authentication bypass or automatic POST retry. Keep actual browser upload,
automated HTTP lost-reply recovery, Windows/native acceptance and maximum-load
timing as separate evidence.

`tests.test_archive_receipt_backup.copy_closed` is a bounded synthetic helper,
not a live-workspace copier. Its caller closes the source, backs up SQLite and
copies every other directory into a new destination. Existing
`scripts/verify_migration.py` still copies only SQLite/runs; its success alone is
not a complete receipt/workspace restore check.
