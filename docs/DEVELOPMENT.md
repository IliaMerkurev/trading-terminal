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


## Saved-equity inspector checks

Reuse an existing isolated saved comparison with at least two variants of one
strategy and passive references. No new backtest, download or observation is
required. Compare each row's equity at ordinary and narrow widths, check the
frozen timeframe/parameters/run ID, keyboard focus, Back to result, and filtered-
row fallback. Switching Lab or comparison dismisses the inspector. Only an
explicit new choice or retry reads equity; returning does not reopen it.

The focused suite exercises late responses, errors, retry, close/reopen, route
suspension and unmount, plus existing saved-review/navigation/display behavior:

```sh
node node_modules/vitest/vitest.mjs run frontend/src/EquityComparison.test.tsx frontend/src/LibraryResearch.test.tsx frontend/src/SavedReview.test.tsx frontend/src/DisplayedEvidence.test.tsx frontend/src/UserJourneys.test.tsx
node scripts/frontend.mjs build
```

Stop the host before building and restart afterward. Browser checks establish
rendered interaction separately from component-injected transport races. Do not
claim new exposure coverage, financial validation or native acceptance from this
frontend-only slice. See STATUS.md for the final combined frontend evidence.

## Modeled work and independent full-source admission (TT10 / A4)

The renewed original-plan continuation starts with A4. Keep this slice separate
from independent spot benchmark settings (A2), heavy-operation responsiveness
and recoverable import (TT13), and remaining research protocols. The earlier
bounded UX gate is historical evidence, not a claim that the original plan is
complete. Windows/native acceptance and new exchange/live work remain deferred.

Library workload version 2 counts each eligible strategy's entire source prefix
through the exclusive evaluation end, using that row's execution resolution.
Each eligible passive row counts only `[start,end)`. Incompatible rows count zero;
cache hits receive no discount. The cap remains 2,000,000 modeled source-candle
executions. `modeled_minutes` remains an additive compatibility alias; it does
not mean wall-clock minutes. New snapshots freeze `modeled_source_candles`,
`workload_version`, per-row `workload_breakdown`, and `source_load_policy`.
Old snapshots are read unchanged and labeled legacy; they are never recalculated.

`DatasetStore.load` still loads all trade, mark and funding tables, including
post-evaluation suffixes. A shared lower-level physical guard checks bounded
manifest metadata first, then each open Parquet descriptor's file hash, footer,
row count, schema, row groups and declared sizes before any table is eagerly
decoded. Chart inspection uses the same physical helper without importing the
observation/evidence layer into loading. Normalized-content checksums and existing
coverage/gap checks remain required. No indicator prefix or execution window is
truncated by the budget fix.

Source-load policy 1 bounds the manifest to 4 MiB; full source slots and each
physical table to 2,000,000 rows; each file to 256 MiB; each footer to 4 MiB;
each table to 8,192 row groups; each group's encoded uncompressed bytes to
128 MiB; and the aggregate decoded-size estimate across all three tables to
512 MiB. Parquet uncompressed page sizes are not fully decoded string sizes:
funding groups therefore use a deliberately pessimistic bound of group rows
multiplied by uncompressed rate-column bytes plus 12 bytes per row and 4 bytes
for Arrow offsets. This prevents dictionary repetition from bypassing admission.
It can refuse otherwise valid sources; prepare a smaller separate snapshot.

A separate materialization-policy estimate is capped at 1 GiB: 1,024 bytes per
trade/mark row, 512 bytes per funding row, plus three times the aggregate decoded
estimate. Per-table caps alone would permit multiplicative allocations, so the
aggregate checks are mandatory. These are finite admission estimates, not a
process peak-RAM guarantee; allocator, interpreter, dictionary/page decoding and
Python representations vary. The scheduler completes its source preflight before
launching a worker, and does not retain those tables across the return. Other
application state and output processing are outside this estimate. Refusing a
full source does not silently shorten it or raise the modeled-work cap.

Focused validation:

```sh
.venv/bin/python -W ignore -m unittest tests.test_workload_admission tests.test_source_limits tests.test_library_batches tests.test_accounting_guards tests.test_observations -q
node node_modules/vitest/vitest.mjs run frontend/src/WorkloadSummary.test.tsx frontend/src/LibraryResearch.test.tsx frontend/src/UserJourneys.test.tsx
node scripts/frontend.mjs build
.venv/bin/python scripts/measure_source_load.py
```

The calibration generates only 30,000 synthetic linear trade rows, 30,000 mark
rows and 63 funding rows. Generation and measurement are separate sibling
subprocesses; Linux `ru_maxrss` includes the measured interpreter/imports but not
fixture generation. It measures full-load duration and process high-water RSS,
not largest-supported execution, cancellation latency or Windows memory.
For GUI inspection, Review a small source, expand Workload breakdown and
source-loading limits, then inspect an existing old comparison: its saved count
must say legacy and remain unchanged. Start remains a separate reviewed action.
No new run is needed merely to inspect the labels.

## Independent spot passive controls (TT10 / A2)

Linear-origin Library comparisons can include Buy & Hold and scheduled DCA on
actual matching spot history. In **Passive comparisons**, select a same-source,
same-symbol, same-resolution spot snapshot, review its own precision/order limits,
and enter spot fee/slippage percentages and an assumption note. Inputs use
the same percentage convention as strategy settings; saved contracts use fractions. The explicit copy
button copies only the numerical strategy cost assumptions once and records
`explicit_shared`; subsequent strategy edits never update that spot assumption.
The metadata route uses the selected spot snapshot. It labels current metadata
as a historical modeling assumption, or synthetic metadata as invented. Missing
metadata does not silently substitute futures constraints. Choose reviewed manual
modeling explicitly, supply every constraint and a note, or leave baselines N/A.
Confirm the independent-assumptions checkbox, then Review test.

The optional `spot_benchmark` request field is admitted by
`library_batch_preview` and `library_batch_start` only when supplied:

- `version: 1`
- `profile`: explicit spot `market`, `symbol`, `capital`, `fee_rate`, `slippage`,
  `tick_size`, `quantity_step`, `min_quantity`, `max_quantity`, `min_notional`,
  `max_notional`; a full Profile snapshot is accepted.
- `assumptions`: exactly `version: 1`, `fee_source`, `fee_note`,
  `slippage_source`, `precision_source`, `precision_note`. Cost sources are
  `explicit_spot` or `explicit_shared`; precision sources are `dataset_metadata`
  or `reviewed_manual`. Both notes contain 1–1000 characters.

The profile must match strategy capital, symbol and execution resolution and
use spot/profile 1 without leverage, stops or Position Management. Passive
account conventions normalize to 100% scheduled deployment, no funding/margin,
closed bars and rejected gaps. Full trade coverage and evaluation range are
required. Path and all costs/precision/order limits remain independent. The
retained passive scheduler caps purchases by maximum quantity/notional and
rejects purchases below minimums; this work does not change that math.

Provenance is part of the validated additive benchmark document field
`execution_assumptions`, included in its immutable hash. Jobs, worker, resume
and archive validation reconstruct the same hash from document/profile/data/
runtime. The existing `research: {benchmark_contract: hash}` shape remains.
Different provenance with identical numbers yields different identity. Ordinary
spot callers omitting the new field retain the exact legacy document/contract
shape; no profile or document version bump or database migration is needed.

Incomplete optional settings or absent/mismatched history leave passive rows
unavailable while valid strategies can run. A disappeared optional source file
or empty optional evaluation discovered during asynchronous preparation affects
only its passive rows. Checksum/schema/resource-limit failures, main-source
failures, storage errors and cancellation retain global handling. Frozen later-
period verification binds new history/dates to the original spot costs,
precision and provenance, never refreshed metadata or current draft settings.
Saved review displays frozen values; old contracts explicitly lack separate
provenance. Spot and linear comparison cohorts remain separate, with the
non-equivalent-risk warning retained.

Focused checks (see STATUS.md for the actual initial/corrective chronology):

```sh
.venv/bin/python -W ignore -m unittest tests.test_independent_spot tests.test_benchmarks tests.test_benchmark_jobs tests.test_library_batches tests.test_library_validation tests.test_accounting_guards tests.test_workload_admission tests.test_source_limits tests.test_archives.ArchiveTests.test_passive_benchmark_archive_preserves_contract_and_result -q
node node_modules/vitest/vitest.mjs run frontend/src/SpotBenchmarkSettings.test.tsx frontend/src/LibraryResearch.test.tsx frontend/src/WorkloadSummary.test.tsx
node scripts/frontend.mjs build
```

For a new isolated offline GUI fixture, with no application owning that root:

```sh
PYTHONPATH=. .venv/bin/python scripts/seed_independent_spot.py --data-root /absolute/path/to/new-empty-a2-fixture
.venv/bin/python scripts/browser.py --data-root /absolute/path/to/new-empty-a2-fixture --port 8773
```

The seeder refuses a nonempty root. It creates one completed three-row synthetic
comparison and a separate frozen, unexecuted later-period review. In Saved tests,
open **A2 independent spot controls**: strategy fees/slippage are 2%; passive
fees/slippage are 1%, quantity step 0.1, tick 0.5, maximum quantity 20 and maximum
notional 2000. Flat-price passive final equity is 960.8 USDT from 1000 initial
capital, including both fills' costs. The strategy has no signals. Inspect
**A2 frozen later-period review** without pressing Run to verify inherited
settings. This is an accounting/UX fixture, not evidence of market performance.
Do not merge its database or generated datasets into ordinary research data.

The seeder also returns `complete_linear_dataset_id`: a separate synthetic
linear source with complete trade/mark data and declared zero funding. Use that
source for fresh Lab preview with the default historical mark/funding policies.
The original linear source intentionally lacks mark/funding for the saved
proxy/assumed-zero comparison; selecting it with historical policies must fail
visibly beside Review. Choose the complete source to retry without weakening
coverage checks. No source or prior result is overwritten by this addition.


## Recoverable background import (TT13 import slice)

Use the production Project archive UI: upload, background start, inspect progress,
and cancel the current attempt when needed. Cancellation retains published reports;
wait for terminal acknowledgement before treating the worker as stopped. Recent
imports is read-only. Continue this import is an explicit checksum/content-verified
attempt using the same destination IDs. If retained source bytes are missing,
provide the exact original ZIP through the separate replacement input, then
continue explicitly. Neither inspection nor continuation executes imported Python
or grants trust. See [ADR 0035](adr/0035-asynchronous-recoverable-import.md).

Focused checks are `tests.test_archive_async`, existing archive/receipt/transport/
backup tests and storage/lifecycle tests. `scripts/prepare_archive_load_fixture.py`
creates four independently invented, streamed semantic fixtures in a new external
directory: near compressed, expanded, single-entry and individual-row limits.
`scripts/measure_archive_import.py FIXTURES NEW_DESTINATION` makes one bounded
Linux/HTTP pass with exact hashes/counts, durable progress, foreground writes,
cancellation/resume, transaction timing, process-tree RSS and integrity checks.
The scripts refuse existing output roots. Their results are engineering evidence,
not market history, financial research or a Windows performance promise. Preserve
existing supported limits if measurements fail; report the measured blocker.
Export/download, chart reads and local result-finalization work remain unfinished.


## Background project export and bounded download

Project archive exports use a managed background process. Inspect or cancel the
exact operation from Project archive; cancellation is a request until the worker
has stopped. Recent exports is launch-local. An uncertain start can be inspected
or retried with its original frozen request identity without creating duplicates.
Restart never resumes unfinished exports and revokes browser download grants,
while completed local ZIPs remain in the exports folder.

The browser fetches ordered 256-KiB chunks, verifies each hash and the final
SHA-256/count before presenting a download. Stop archive download aborts the
transfer and retains the completed export. A slow receiver may fail the bounded
response and require an explicit download retry. Closing a tab does not cancel
export; Stop local service cancels active work and retains saved results.

Synthetic load tooling extends the existing archive fixture generator with
`--mode export`; `scripts/measure_archive_export.py` measures actual authenticated
HTTP status, cancellation, SQLite foreground writes and chunk transfer on a new
isolated workspace. Its `--workspace` input must be a closed synthetic workspace
and is copied before use. See [ADR 0036](adr/0036-background-project-export.md)
and [STATUS](STATUS.md); direct HTTP RSS excludes browser/WebCrypto/Blob copies.


## Managed local result finalization (TT13)

A completed computation enters `finalizing` while a separate managed process
verifies and publishes the immutable result. Status reports actual phase, staged
rows/bytes and `worker_active`; a completed durable record can precede worker
cleanup. Wait for cleanup before assuming the calculation slot is free. Batch
waiters do this automatically. Cancellation is requested first; completion may
win the guarded cutoff. Interrupted local finalization never resumes on restart.

Normal normalized writes use preencoded 128-row/256-KiB batches; a previously
valid oversized row remains a measured single-row exception. No result schema
limit or financial output changed. Storage failures quarantine new calculations
until restart and uncertain cleanup retains workspace ownership. Keep the whole
closed data root when backing up, including incomplete artifacts and additive
local control/receipt tables. See [ADR 0037](adr/0037-managed-local-result-finalization.md).

`scripts/measure_result_finalization.py NEW_DESTINATION SYNTHETIC_INPUT` measures
the serialized HTTP service and exact output on a new isolated workspace. With
`--engine`, the input is the prepared synthetic M1 source/preview directory and
one normal graph calculation is executed; otherwise the input contains an
independently authored snapshot/result pair and proves persistence only. The
script refuses an existing destination and records measured scope explicitly.

## Synthetic daily reversion acceptance

Create a new isolated fixture root (refuses any existing destination):

```sh
.venv/bin/python scripts/prepare_daily_reversion_fixture.py /absolute/new/daily-reversion-fixture
node scripts/frontend.mjs build
.venv/bin/python scripts/browser.py --data-root /absolute/new/daily-reversion-fixture --port 8771
```

Use the printed numeric loopback URL. No network acquisition, exchange session or
live orders are needed. Both history labels explicitly say Synthetic/local;
all prices/cost constraints are invented. The fixture contains two saved graph
copies and observations but no runs or batches.

In Lab find Double 7's and Improved R2, inspect their rule sources/hash basis and
synthetic-versus-empirical verification status. Only daily timeframe is offered.
Customize/save/reopen in Pro; inspect Rolling Minimum/Maximum and Closed-bar Lag
nodes and parameter validation. Keep the unchanged fixture graphs for arithmetic
checks. In Data open each matching Synthetic/local observation and test only its
matching candidate with daily execution, capital 1000 and Lab allocation 10%,
fee0.1%, slippage1%, tick0.5 and quantity step0.1. Lab exposes percentage sizing;
the automated fixture uses fixed allocation 100. Both produce the same 100 USDT
first entry in these one-entry cases, but their sizing contracts remain distinct. Review first, then explicitly
Start. Expected single strategy lifecycle: C12 fills115.5/118.5, fees0.1872,
net2.2128; C13 fills113.5/128.5, fees0.1936, net11.8064. Passive comparison rows
are separate calculations and not these strategy expectations.

Check saved report reopening and recorded indicator outputs. An attempted
one-day-earlier evaluation must disclose insufficient 200-day prefix. Export and
reimport preserves graph and saved result bytes; imports do not grant native
trust. Stop the host before rebuilding, and retain fixture versus ordinary
research data separation. Browser, Windows and owner acceptance are separately
reported; synthetic values are never presented as market profitability.
