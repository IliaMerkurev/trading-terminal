# Implementation status

## Local manual-research observations — 2026-10-10

Market now has a Saved history subview and Data cards can open a local snapshot
without visiting Live. Bounded prepared-candle pages show provenance, synthetic
warnings and actual missing slots. Users enter a UTC observation range and short
hypothesis, optionally add a falsification condition, then save/reopen that exact
source. Note edits append revision-guarded history; source and dates remain fixed.

Test observation opens the existing Lab setup without executing. Its atomic
source/range/revision context survives async warmup and mismatched/restored
settings. Dates cannot change until explicit detachment. A successfully admitted
Library batch links transactionally to the exact note revision outside immutable
results, with return navigation in both directions. Later note edits cannot become
retroactive evidence. Admission storage failures roll back and prevent launch.
Existing saved comparison metadata/search/filters remain in place.

The initial backend focused pass had one incorrect mock target; the corrected
observations/evidence/storage pass passed 24 tests in 5.674s. After reader caps,
optional falsification and chronological paging, all 10 observation tests passed
in 0.214s. The initial UI pass had 35 passes and one duplicate-alert selector
failure; its corrected final Observations/UserJourneys pass passed 12 tests.
The unchanged LibraryResearch/HistoryWorkspace tests passed in the initial pass.
TypeScript and production Vite build passed with the existing large-chunk advisory.
Independent source review found two contract gaps (full source identity during
link admission, and restoration after mismatched Lab settings); both were fixed
and re-reviewed with no remaining blocking data/storage issue.

The new-only synthetic fixture script creates 900 independently invented hourly
candles plus a separate one-gap snapshot, one observation and no runs. It uses
invented instrument metadata and makes no market/profitability claim. Reader
limits, exact source checks, note/link write failure, revision preservation,
chronological pagination, warmup races and direct offline navigation are covered.
See [ADR 0033](adr/0033-local-history-observations.md).

Final focused validation passed all 11 observation/backend fixture tests in
0.862s and all 37 tests across Observations, LibraryResearch, HistoryWorkspace
and UserJourneys. Final TypeScript/production build passed. An actual synthetic
manager run completed one linked batch with three completed rows/runs. Editing
the note to revision 2 retained its batch link to revision 1; a service restart
preserved the link, all nine immutable JSON hashes and SQLite integrity. The
fixture's admitted-run count remained three after reopening.

Initial production-browser acceptance confirmed 500/400-candle paging, the
499-candle gap page, optional blank falsification, exact handoff dates and one
admitted batch despite a double Start click. Returning to the same observation
then exposed a reader-effect bug: clearing its page did not change any load
dependency. The bounded correction adds an explicit reopen/retry generation and
record identity, preserving stale-response cleanup and avoiding note-keystroke
rereads. The provenance line now uses the verified page classification. Seven
focused component tests passed, including same-record return followed by note
save and rejection of a late older page. Independent review found no blocker.

One combined cumulative Linux acceptance pass on the corrected code completed
297 Python tests in 114.521s: 289 passed and eight Windows-only native/lifecycle
checks were skipped, with no errors or failures. The prior thread-mock teardown
errors did not recur. All 150 frontend tests across 30 files passed in 11.53s.
Final TypeScript/production build passed with the existing large-chunk advisory.
No full suite was repeated for this documentation-only evidence update.

Subsequent actual browser checks verified that same-record return reloads its
252-candle local page. A post-test note edit saved revision 2; its linked batch
still returns historical revision 1. A separate first-day observation with an
empty optional falsification field kept its exact dates and blocked RSI Review
for insufficient preceding warmup, without adding a batch. The synthetic
workspace then retained six runs, two batches, three observations, five note
revisions and two links. The original nine immutable JSON hashes were unchanged
and SQLite integrity remained ok.

Ordinary wheel navigation then exposed a layout blocker at both 750px and
1180px widths: the Saved history wrapper did not bound its inner content scroller.
The minimal correction reuses the established workspace flex/min-height/hidden
host contract. All eight focused UserJourneys tests and TypeScript/production
build passed; no backend changes or repeated full-suite run were needed. The
structural component check alone does not establish actual browser scrolling.
After restarting the production browser host for the rebuilt static inventory,
actual wheel checks passed at both 1180px and 750px widths: scrolling outside the
chart reaches the note, controls, linked test and saved observations; scrolling
up returns to the chart while the header stays fixed. At 750px the fields and
buttons fit, lists stack, and no horizontal overflow was visible. Independent
source review found no blocking layout/state concern.

TT16 is a bounded manual-observation slice, not full research-journal acceptance.
Chart/report view tracking remains explicitly incomplete. The recorded browser
checks use the isolated synthetic local service, not native Windows or live
market data. Windows-native and live-source acceptance remain deferred; the
browser observations supplement, rather than replace, Linux and simulated-DOM
regression evidence.

## Forward-only research admission evidence — 2026-10-10

A new additive append-only registry records durable custom, Library and Experiment
run admissions, passive controls and actual frozen candidates. Admission commits
with the run before worker creation; freeze and its prior-overlap review commit
with the candidate. Failed persistence rolls back the database transaction and
uses the existing storage quarantine. Records retain owner/contract/dataset,
actual evaluation versus input/warmup ranges, and declared provenance/cohort.

Both freeze actions now open a bounded review dialog before confirmation. It
shows cross-route same-symbol calendar overlap, distinguishing spot/linear
cohorts, frozen candidates and passive controls. Explicit synthetic evidence is
isolated by declared source; unknown provenance remains visible and conservative.
The recorded prior review excludes its own freeze and does not change on later
admission or reopening. Old saved Library counters are labeled Library-only.

TT11 remains partial: chart/report views, replay/live activity, old/imported
attempts and external exposure are unrecorded. A durable coverage-start marker
makes the boundary explicit; no zero-result warning claims untouched history.
Snapshots, financial reports, accounting and product version are unchanged.
See [ADR 0032](adr/0032-research-admission-evidence.md).

Focused backend validation passed 15 tests across research evidence and storage
resilience (4.953s), plus the existing Library later-period parity test in the
initial pass. That initial command also named a nonexistent storage test module;
the corrected command above passed. Evidence covers real tiny synthetic workers,
cross-route freezes, no-worker admission failure, transactional freeze rollback,
append-only/restart preservation, migration lock release, repeated admissions,
unknown/real/synthetic classification, adjacent ranges and warmup exclusion.
The independent preservation assertions retain original snapshot/report bytes.

The first UI pass had 25 passes and one existing test missing the new confirmation
click. Its corrected focused pass and the final modal refinement each passed all
23 tests in LibraryResearch and EvidenceFreeze; the three unchanged Experiment
tests passed initially. Actual browser inspection then found ambiguous same-day
history choices. All Library history selectors now include declared source,
short dataset ID and precise UTC range; the overlap review also shows its exact
evaluation range. This refinement passed 24 focused UI tests and final
TypeScript/production build, retaining the existing large-chunk advisory. A separate tiny authentic synthetic fixture
completed custom, Library and Experiment runs and saved a never-started freeze.
Independent initial and final source review found no blocking lifecycle,
immutability or UI issue.

Actual local-browser acceptance on production code `0855f39` verified that the
source, short ID and full UTC labels distinguish three same-day datasets. Library
review for 2024-01-01 00:24–00:48 UTC showed three recorded events: one custom
admission, one Experiment admission and one Library freeze, with explicit partial
coverage. Cancel created no freeze. A separately declared synthetic source showed
zero overlap while retaining the warning that this does not establish unseen data.
Confirm created exactly one new frozen batch and no runs/admissions; its saved
prior review was three, while the original frozen candidate retained two.

The Experiment freeze review for 00:36–00:48 UTC then showed three events: one
custom admission and two Library freezes. Cancel changed nothing. After Stop
local service and restarting the same launcher, all three batches persisted; the
original candidate retained its prior count of two, frozen status, 0/3 completed
rows and explicit Run action. SQLite integrity was ok. The five completed runs
and admission counts stayed unchanged (three strategy, two passive); there were
two strategy freezes. All 15 original immutable run JSON files retained their
hashes. The final overlap dialog was visually checked at 1180px width.

This is synthetic local-browser/restart acceptance supplementing focused Linux
and simulated-DOM checks. Narrow-screen acceptance for this slice, full-suite,
Windows-native and live-source checks remain uncompleted. View tracking remains
partial, and synthetic fixtures provide no profitability evidence.

## Saved research details and numeric thresholds — 2026-10-10

Actual browser checks on the functional checkpoint verified reopening a legacy
matrix, saving a name and Unicode notes, finding it with uppercase Cyrillic
search, and locking comparison selection while details are unsaved. Thresholds
of 0% drawdown and 1,000 positions retained passive references and N/A context;
a negative minimum-position value displayed the validation warning.

Final local-browser acceptance on production code `b859f5a` verified persistence
after Stop local service and restarting the same launcher: the named legacy
comparison and exact Unicode note reopened, and uppercase Cyrillic search found
it. Edit details reopened the saved text; an unsaved change disabled comparison
switching and Hide details; explicit discard restored the saved name. A subsequent
rename and Save details collapsed the editor and updated the selector. Opening
the RSI report and returning with Back retained search, selection and numeric
filters on the feature checkpoints. The legacy matrix remained at 14 completed
and two unavailable rows, with two total saved comparisons and no rerun. SQLite
integrity_check returned ok; all 42 original report/snapshot files retained their
hashes. These are synthetic local-browser workflow and preservation checks.
Narrow-screen visual acceptance of this latest refinement remains pending.

That walkthrough also identified excessive explanatory text above the results.
The bounded presentation refinement moves detailed filter/cohort guidance into
a disclosure while retaining a visible scope/baseline/context summary. Saved
details initially show the name, a short note preview and Edit details; a
successful save collapses the editor. Drafts, pending saves and errors cannot be
hidden through that control. This presentation-only change passed all 23 tests
in the two affected UI files, plus production TypeScript/build with the existing
large-chunk advisory. Independent source review found no blocking issue.

Saved Library comparisons now support editable names and research notes in a
separate additive metadata table. Revision-checked transactional writes preserve
immutable batch snapshots, run summaries and report files. Legacy comparisons
remain readable with empty details. Failed writes retain editor text; polling
cannot replace drafts, and switching comparisons requires save or discard.

Literal, Unicode-case-insensitive search covers names, notes, IDs and creation
dates across the full saved catalog before the existing bounded keyset paging.
Search does not include strategy names or metrics. Selected reports remain
available outside the current search page; reset requests invalidate pending
older-page responses. Numeric drawdown, completed-position and period-return
thresholds apply only to the selected comparison. Cohort sorting and holdout
order are unchanged. Passive references bypass thresholds; N/A and unfinished
rows are labeled context, never passing measurements. See
[ADR 0031](adr/0031-saved-comparison-details.md).

Focused backend verification passed 10 tests across `test_library_history`,
`test_library_batches` and `test_library_validation`. After the final unknown-ID
read guard and a new API/file-preservation fixture, four history tests passed;
the new test initially expected the wrong IPC envelope key. Its corrected
assertion passed in a one-test rerun. These are overlapping focused passes,
not a combined full-suite count. Evidence includes 125-record pagination,
old-record literal/Unicode search, restart, revision conflicts, rollback after
an injected write failure and unchanged independently supplied report bytes.

The focused UI rerun passed 29 tests in `LibraryResearch`,
`SavedComparisonDetails` and `StrategyLibrary`; the first pass found a JSX
syntax typo and passed the two independent metadata-editor tests before the
correction. Production TypeScript/build passed with the existing large-chunk
advisory. Independent source review caught and resolved a concurrent paging
reset race and floating-point percentage-boundary comparison before this final
pass. No dependency, accounting, network or security change was made. The
browser/restart results above supplement these focused passes, not a new full
regression suite. Windows-native and live-public-data gates remain uncompleted.
Synthetic fixtures are not profitability evidence.

## Saved-result presentation refinement — 2026-10-10

Saved comparisons now distinguish their immutable settings from the current
editable draft without requiring a rerun to view reports. The strategy/cohort
column and its Open report action stay pinned while scrolling across metrics;
a keyboard-focusable region and visible horizontal-scroll guidance retain access
to every metric and action. Losses, N/A values and cohort rules are unchanged.
Opening an individual report collapses the loaded run history and puts the
selected report, metrics and chart ahead of comparison/export tools. History,
paging and run selection remain available; Back retains the saved comparison
and its filters.

Focused presentation verification passed 36 existing/updated frontend tests in
three files, plus one new 17-run report/history/back-navigation regression. The
new fixture initially assumed input ordering for equal timestamps; unique dates
corrected the fixture, and its focused rerun passed. Production TypeScript/build
passed with the existing large-JavaScript-chunk advisory. Backend calculations,
accounting, data, schemas and dependencies are unchanged. Actual browser checks
at 1180px and 750px verified pinned row identity, horizontal scrolling, collapsed
history and report-first layout. Those checks found that the run-status response
may omit its creation date. The heading now falls back to a valid timestamp from
the matching history row, or explicitly says the date is unavailable. Two focused
regressions and production TypeScript/build passed for this correction. Its
actual browser recheck passed as recorded below.

At the preceding functional checkpoint, actual local-browser checks verified
that a double Start produced one three-row batch with all rows completed, copy
cancellation created no strategy, both copy-setting choices retained their
selected capital, and a saved report reopened after restart. All 42 immutable
original report files retained identical hashes, and SQLite integrity was ok.
This is synthetic browser acceptance, separate from Windows-native acceptance.

## Final local-browser acceptance — 2026-10-10

Actual browser checks on the final source checkpoint passed at 1180×757 and
750×757: the selected report remains primary, the 17-row run history starts
collapsed and remains accessible, and narrow-screen metrics use two columns.
The strategy identity and Open report action remain visible when the comparison
table is scrolled fully right. Saved-versus-draft wording does not require a
rerun to view results. Opening a report from its saved batch displays the real
10 October creation timestamp through the history fallback, never Invalid Date.

The earlier actual functional checks remain applicable: preparing Data returned
to the preserved test setup; a double Start created exactly one batch with three
completed rows; copy cancellation and both explicit settings choices behaved as
selected; and saved results reopened after restart. Final integrity checks found
two saved batches, unchanged hashes for all 42 original immutable report files,
and SQLite integrity ok. This documentation-only checkpoint changes no source,
data or dependencies and requires no repeated test/build pass.

These are synthetic local-browser workflow and preservation checks, not evidence
of real-market profitability. Windows-native acceptance, native display scaling,
and live public-feed acceptance remain separate, uncompleted gates.

## Storage finalization and safe shutdown — 2026-10-10

Failed final storage writes now release calculation/scheduler ownership and set
one shared, non-durable diagnostic. Further run, replay, grid, Library and frozen
validation starts are blocked in that application session. Saved statuses and
completed metrics remain distinct from the diagnostic. A global notice reads
memory-only scheduler state, including actual worker/reservation ownership;
it is visible across connected transports even when SQLite cannot be opened.
Native close and replay controls no longer confuse an unfinished saved status
with a still-running worker. Independent active downloads retain their close
confirmation and cancellation flow. Restart retains existing interruption
recovery; it neither retries calculations nor proves that storage is repaired.

Shutdown now attempts all owned resource cleanup despite failed live-journal or
cancellation writes, preserves the original failure evidence, and retains the
workspace lock while workers, scheduler threads, live warmup, market/chart,
notification or download threads remain active. Cancellation still terminates
the owned process when its status write fails. No completed result is fabricated.
The existing native host's ten-second forced-backend fallback is unchanged;
slow cleanup may still reach that fallback. Graceful Windows disk-failure
shutdown is not established by Linux fault injection.

Migration verification traverses bounded keyset history pages (at most 100 rows)
and checks every completed report against an independent SQL count. The report
includes the verified count; corruption in the oldest of 101 reports is rejected.

Focused integrated Linux evidence: 13 backend fault tests and 11 selected UI
close/notice tests passed. Separately, four existing calculation regressions and
two nearest live/blocked-warmup regressions passed. Tests use injected SQLite/
filesystem failures, isolated workspaces and independently specified outcomes;
they do not fill or remount the host disk.

The combined candidate pass ran 277 Python tests in 102.417s: 260 passed, eight
Windows-only checks were skipped, and nine legacy manual-paper fixtures failed
only during teardown because their mocked live thread stayed alive after join.
Two fixture lifecycle mocks were corrected without changing production code or
financial assertions. All nine affected tests plus four shutdown ownership guards
then passed in a focused 13-test rerun (3.062s); the full suite was not repeated.
The same candidate passed all 132 frontend tests in 27 files and production
TypeScript/build. The existing large-JavaScript-chunk warning remains. Actual
final-candidate browser acceptance and Windows acceptance remain separate.

## Card-to-saved-test journey — 2026-10-10

Lab setup now retains its origin when preparing data. Custom-backtest history
returns to its editor route, while later-period preparation returns to the
selected frozen candidate. Global Data navigation does not invent a later-period
candidate. Wrong instruments, resolutions, dates, warmup and incomplete metadata
have specific remedies; backend preflight remains authoritative.

Graph customization explicitly chooses Lab or editor settings, exposes differing
costs and assumptions, and discloses the graph's model-2 contract. Invalid
transfers are rejected before any strategy is saved. Native copies retain their
reviewed template settings and never grant trust or load Python. Missing metadata
raises an actionable data error; explicitly synthetic metadata cannot claim
current exchange precision.

Review and saved settings show exact declared cost fractions, separate from
rounded performance metrics. Synthetic instrument assumptions remain visible in
saved comparison and individual report views. Saved-card empty states distinguish
no selected comparison from absent rows in that comparison. Losses, zero-trade
rows and unavailable metrics remain visible; passive rows survive candidate
filters. Existing compatible-cohort sorting and passive calculation semantics
are unchanged. Later-period guidance explicitly notes incomplete exposure records.

Saved comparisons have fixed 50-row keyset pages with a bounded response budget,
including continuation when the byte limit shortens a page. Reopening older work
is read-only. The copy API extension and history endpoint do not change schemas,
engine versions, dependencies, financial formulas or existing report bytes.

Fresh focused verification passed 49 frontend tests in seven files and 32 backend
tests covering atomic copy, native trust, metadata, fixture preparation, coarse
execution and history pagination. Independent review found a small-cost display
rounding issue; its correction passed 20 targeted tests across two files. These
counts overlap and are not a full-suite total. Production TypeScript/build passed;
the existing large-bundle advisory remains (about 757 kB JavaScript).

A separate independently generated 4,032-hour BTCUSDT spot fixture executed the
existing seven-template H4/D1 matrix: 12 graph variants and two passive alternatives
completed; two native/spot variants remained explicitly unavailable. Model-2 graph
and model-1 passive reports retained measurable deltas and losing outcomes.
All 14 completed reports reopened after service restart, 42 immutable JSON files
kept identical hashes, and SQLite integrity was ok. This is synthetic integration
evidence, not market-performance or Windows-native acceptance. Actual browser
acceptance of this journey and final combined regression remain pending.


## Conservative historical accounting gates — freshly verified 2026-10-10

Historical linear runs with historical funding require complete trade coverage,
including leading and trailing coverage in the dataset's declared range.
Dataset preflight refuses incomplete history; the direct simulator also refuses
internal gaps or supplied funding events without matching trade candles before
constructing the engine. The remedy is complete history or a verified continuous
range. No synthetic prices or automatic zero-funding substitution are introduced.
Old profile snapshots and saved reports remain readable.

Linear-origin Library comparisons retain Buy & Hold and Scheduled DCA as
explicitly unavailable until an independent spot execution profile and explicit
spot fee assumption are available. Linear constraints are not copied into new
purported spot alternatives. Spot-origin comparisons retain their declared manual
contract and full cache identity. Unavailable baseline rows have no run or metrics
and do not block a valid strategy's frozen later-period test; strategy preflight
errors still block it. Completed batches with unavailable rows retain the existing
`completed_with_errors` status.

The recovered focused tests cover profile versions 1/2, long/short and both
funding signs (quantity 1, mark 100, rate ±0.01), internal/leading/trailing gaps,
Position Management, continuous controls, explicit assumed-zero/spot controls,
managed-worker refusal without successful output, byte-identical saved-result
reopening, baseline N/A counts, spot contract invalidation and later-period
strategy rejection/acceptance. Fresh integrated Linux verification passed all
**48 tests in 20.804 seconds** across `test_accounting_guards`, `test_simulation`,
`test_position_execution`, `test_library_batches`, `test_benchmarks`,
`test_benchmark_jobs` and `test_library_validation`. The command was
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests .venv/bin/python -m unittest test_accounting_guards test_simulation test_position_execution test_library_batches test_benchmarks test_benchmark_jobs test_library_validation -v`.
Pinned Python 3.12.14 / NautilusTrader 1.231.0 runtime verification and `pip check`
also passed. Upstream Pandas Timestamp.utcnow deprecation warnings remain.
No full-suite or Windows-native acceptance is claimed.

The conservative 2,000,000-source-candle workload cap and existing warmup
accounting remain unchanged. Benchmark warmup overcount is deferred: reducing
modeled counts must first preserve a separate source-load memory bound. This
patch does not repair the funding timeline, introduce independently configured
cross-market benchmarks, revise schemas/versions, or rewrite historical results.
Direct callers without a declared dataset range cannot establish missing edge
coverage from absent information; dataset preflight remains authoritative for
that range, while every supplied unmatched funding event is refused directly.

## Recovered Market / Lab workspace — 2026-10-10

The accepted Market/Lab source was reconstructed against the recovered browser
frontend. This is a new verified source reconstruction, not recovery of the lost
Git commit or reuse of its historical test results.

- Market and Lab are peer tasks. Market has an independent draft profile and no
  editor chrome. Its chart stays mounted across navigation, retaining display
  interval, candles and fitted viewport; hidden market status/chart polling stops.
  Leaving Market releases viewing without pausing an explicitly active strategy.
- Advanced strategy/paper controls and diagnostics start collapsed. Replay and
  paper lifecycle panels mount only when visible and selected. Frozen active
  session instruments label the screen correctly, including non-BTC instruments.
- Lab retains its controller state while closed setup fields are unmounted.
  Current context stays visible; card actions precede optional metadata. History
  preparation returns to the preserved setup. Hidden completed batches stop
  polling; active batches continue until completion.
- The restored CSS stacks a full-width 420px chart above depth/tape at widths
  at or below 900px and places the no-data explanation above chart canvases.

Fresh focused validation on Linux used nine affected frontend test files. The
first pass had 60 passes and three outdated-test failures (63 total). One
corrective pass updated explicit modal interaction and a duplicate-label query,
added two batch lifecycle cases, and passed all 20 tests in the three affected
files. Together with the unchanged six files from the first pass, all 65 distinct
focused tests pass. TypeScript and the production Vite build pass; the existing
747.64 kB JavaScript size advisory remains. Final test edits also pass TypeScript.

These checks use simulated DOM and mocked IPC. Fresh real-browser geometry,
public candles and Windows native/scaling/keyboard acceptance are not established
by this patch. Browser service shutdown logic, backend accounting, schema and
Windows integration files are unchanged. Integrated release validation remains
separate.

## Recovered local browser mode — 2026-10-10

The browser transport has been reintegrated on the independently verified Linux
checkpoint. The six frontend production files match their original Git blob
hashes; the host and tests were reconstructed from retained source. One fresh
review fix keeps the service reference available if cleanup raises, allowing a
later close attempt to finish. Historical graphical acceptance below remains
separate from current evidence.

Fresh focused verification on this recovered source:

- **6 browser-host tests passed in 2.907 seconds**. Coverage includes exact
  Host/Origin/fetch metadata, authenticated bootstrap and bounded commands,
  static traversal/symlinks, archive export/download/import, exclusive workspace
  ownership, real worker cancellation and active shutdown with SQLite integrity.
  Same-port POSIX restart now sends an old token over HTTP and verifies rejection,
  then verifies a new bootstrap token works. A failed cleanup retains its service
  reference and a later close releases the workspace.
- **36 frontend tests across 7 files passed in 4.41 seconds**, covering desktop
  transport preservation, browser bootstrap/capabilities, run/download recovery,
  leave warnings, confirmed shutdown, archive transfer and whole-response
  timeout/unknown-outcome behavior without automatic POST retries.
- TypeScript and production build passed. The existing bundle-size advisory
  remains (approximately 744 KiB JavaScript).
- The real `scripts/browser.py` launcher passed runtime verification, readiness,
  serving built HTML, SIGTERM exit code 0, workspace reopening and SQLite
  integrity. The smoke harness was corrected to skip the expected runtime-check
  banner before looking for readiness; this was a harness parsing correction.

Fresh graphical browser acceptance is still pending. These focused checks are
not another full Python regression, Windows native pass, merge, or release.
Windows/Tauri launch and IPC, engine version, calculations and storage schemas
remain unchanged. Linux native execution and protected secret integrations
retain their fail-closed restrictions. See
[ADR 0030](adr/0030-local-browser-research.md) and
[browser launch instructions](DEVELOPMENT.md#local-browser-research-mode).

## Historical browser adapter acceptance — before source recovery

All results in this section were observed before the validation VM was lost.
They are preserved as historical evidence, not fresh verification of the
recovered source or environment. Fresh recovery checks are recorded separately.

The owner-authorized browser transport uses the existing AppService and managed
workers behind a numeric loopback-only HTTP host. Windows/Tauri launch and
IPC remain available. There is no storage migration, product/engine version
change, financial formula change, new dependency or public deployment.
See [ADR 0030](adr/0030-local-browser-research.md).

- Five focused backend tests passed, covering strict Host/Origin/fetch metadata,
  bootstrap/session authentication, missing and duplicate security headers,
  unsupported CORS, bounded JSON, unknown commands and static traversal/symlink
  rejection. An independent nine-case hostile-boundary probe also passed.
- Authenticated archive export/download/import, repeat session bootstrap, saved
  strategy recovery and changed-export rejection passed against real AppService.
- Real managed-worker cancellation and shutdown with active work passed;
  subsequent reopening recovered cancelled statuses, exclusive ownership was
  released and SQLite integrity was `ok`. Desktop/browser concurrent workspace
  ownership is rejected by the existing shared lock.
- Closing/reloading browser tabs deliberately keeps the host and workers alive.
  Service shutdown is explicit; interrupted writes are never automatically
  retried. Linux native execution and protected secret integrations retain their
  fail-closed limitations.

Frontend focused verification passed **34 tests across 7 files**. A subsequent
whole-response timeout correction passed **13 targeted tests across 2 files**,
including stalled/truncated response bodies and the no-retry contract; these
counts overlap and must not be added. TypeScript and the production build passed
in both the isolated frontend worktree and integrated checkout. The existing
bundle advisory remains (about 744 KiB JavaScript). Independent safety review
reported no remaining blocking issue after the correction. The actual launcher
passed runtime verification, readiness, SIGTERM exit and workspace reopening.

Actual Chromium acceptance on the separate Linux validation workspace passed
launch, catalog loading, four saved reports, reopening the losing forming-H1
report (entry 130, exit 90, quantity 0.769, net PnL -30.76), visible charts/fills,
and reload/reconnection. A new run was started using the visible route
**Synthetic: spot fees golden case → More tools → Custom backtest → Prepared
dataset (three-minute spot fixture) → Run immutable snapshot**. Worker preparation
was displayed, then a new completed report persisted with one trade, entry 100,
exit 110, quantity 1, fees 0.2100 and net PnL 9.79. Existing reports remained
unchanged. The first graphical shutdown succeeded, but immediate restart
revealed a same-port TIME_WAIT bind failure. The host now enables POSIX address
reuse without port sharing; Windows retains its non-reuse setting. The added
same-port restart test verifies a fresh token, workspace reopening, active
listener rejection and no creation of a conflicting workspace. The corrected
five-test host pass succeeded. Independent review additionally verified an old
session token is rejected after restart and the new token works. The corrected
Chromium cycle then passed UI stop, same-port launcher restart after 12 seconds,
reconnection, all five saved reports and reopening the new 9.79 / 0.21-fee report
with the same chart and trade. The host and browser were left open after this
verification.

The legacy tiny synthetic fixtures have no exchange instrument metadata.
Market data's **Use this history** routes to the Library research selection,
not the independent custom editor dataset. Library's existing automatic
metadata request exposes an `instrument` error for these fixtures; this is a
retained fixture/UX limitation, not evidence of a successful Library workflow.
The custom backtest path above remains valid. Origin-aware selection and clearer
metadata errors belong to the subsequent workspace UX slice.

These focused adapter checks reuse the prior verified backend/Windows dispatch
implementation; they are not a new full regression or Windows native pass.


## Recovered Linux adaptation — 2026-10-10

The initial Linux checkpoint was lost with its validation VM. The original
upstream baseline was restored and the bounded adaptation reconstructed. The
backend patch and original Rust host patch match their pre-loss SHA-256 hashes
exactly. Integration files were recreated from recorded edits; documentation now
separates fresh verification from historical observations. This is a new source
checkpoint, not a claim that the lost commit or environment still exists.

Fresh checks on the recovered checkout:

- Official hash-pinned Linux Python wheels installed; `pip check` and platform
  runtime verification passed with Python 3.12.14/NautilusTrader 1.231.0.
- Frozen pnpm 11.19.0 installation passed with install scripts disabled.
- All 88 frontend tests in 21 files passed; TypeScript and production build
  passed. The existing approximately 739 KiB JavaScript advisory remains.
- Four standalone Rust 1.98.1 portability tests passed (platform Python path,
  safe exports arguments, relative-path rejection, unavailable Windows toast).
- Full Python regression: **243 tests in 98.175 seconds**, with **235 passed,
  8 explicit Windows-only skips, no failures or errors**. The skips retain seven
  native-execution acceptance cases and the Windows Job Object lifecycle test.
  Pinned upstream Pandas Timestamp.utcnow deprecation warnings remain.

Native Tauri compilation and the real Rust-to-Python host test passed in the
original environment, but were **not rerun after recovery**. They are historical
evidence only. The original supported-desktop launch failed before a native
window appeared: `/usr/lib/x86_64-linux-gnu/webkit2gtk-4.1/WebKitNetworkProcess`
was absent. A normal system WebKitGTK runtime installation remains necessary;
project-local shared libraries alone do not supply its absolute helper paths.
No sandbox-disabling flags, binary patching or system-security changes are used.

Windows setup scripts, wheel hashes, Cargo.lock and Job Object implementation
remain unchanged. Windows native regression has not been run on this adaptation.
Native Python execution and Windows/sound/Telegram protected-storage integration
are explicitly unavailable on Linux. The Linux supervisor handles service/host
death while the supervisor stays alive; killing the supervisor or escaping its
process group is outside the guarantee. This is not a security sandbox.

Financial formulas, storage schemas and engine version remain unchanged.
See [ADR 0029](adr/0029-linux-research-preview.md) and [Linux setup](DEVELOPMENT.md#linux-source-checkout-research-preview).

## Catalog-wide batch comparison — verified, owner review pending

**Test all strategies** opens every catalog strategy at a common selected set of
timeframes, default 4h and 1d, regardless of search/family filters. All variants
share history, evaluation dates, initial capital, sizing and costs. Each
strategy's current indicator parameters stay fixed across timeframes. Preview
counts ready and unavailable rows separately. Results and frozen inputs use the
existing SQLite batch/run storage; no migration or new dependency is required.
Saved tests adds a shared-settings summary, comparison groups and ascending or
descending metric order. Losses and incompatible rows remain visible.

Windows verification on 2026-09-30:

- `node node_modules/vitest/vitest.mjs run frontend/src/StrategyLibrary.test.tsx frontend/src/LibraryResearch.test.tsx frontend/src/UserJourneys.test.tsx frontend/src/App.test.tsx`:
  **29 passed in 4.60s**, including all seven cards despite filters, shared
  timeframe changes, retained parameters, both sort directions and prior flows.
- `.venv/Scripts/python.exe -W ignore -m unittest tests.test_library_batches tests.test_library_validation tests.test_archives -q`:
  **14 passed in 23.516s**. Covers durable all-catalog matrix contracts,
  cancellation/resume, unavailable native preparation, archive ordinals 11/95
  and rejected 96, saved metrics and later-period validation.
- TypeScript/Vite passed. Review found the batch button inherited a hidden
  stats container at narrow widths; corrected that CSS and rebuilt successfully.
  Final locked offline Windows build passed in 3.57s, with verified pinned
  Python/Nautilus runtime. Existing 738.82 kB bundle advisory remains.
- Native batch selected seven strategies at 4h/daily, reused BTCUSDT spot H4
  history, reserved a common 2024-02-26—2026-09-01 evaluation period, and reviewed
  1,000 USDT / 0.10% fee / 0.05% slippage. Preview showed 16 rows, 14 ready and
  2 unavailable. All twelve graph variants and both passive alternatives
  completed. The two native rows remained incompatible with spot, with reasons;
  final status was `completed_with_errors`, not sixteen successful tests.
- Native Lowest first reordered losses correctly within execution-model groups.
  The application was rebuilt/restarted and the same saved comparison reopened
  with its metrics and original settings, without another test or download.

Selection/archived strategy ordinal bounds are now 96; the 2,000,000 modeled
source-candle budget is unchanged. All eleven timeframes at once may exceed that
budget. Native trust, execution accounting, old results and holdout exclusion
remain unchanged. Full regression and display-scaling sweeps were not repeated;
native evidence used the ordinary wide window, not the narrow CSS breakpoint.
See [ADR 0028](adr/0028-catalog-batch-comparison.md).

## Visible strategy test action — verified, owner review pending

Every **Test this strategy** click opens an explicit backtest setup dialog,
including repeated clicks on the same card. Settings survive dismissal and
history navigation; Start closes setup and opens Saved tests. Changing a
timeframe alone does not run a backtest. Incompatible source intervals now show
an explanation and a compatible resolution before review. Active-work exit
confirmation temporarily suspends setup and restores it on Return.

Windows evidence on 2026-09-30:

- Focused command: `node node_modules/vitest/vitest.mjs run frontend/src/StrategyLibrary.test.tsx frontend/src/LibraryResearch.test.tsx frontend/src/UserJourneys.test.tsx frontend/src/App.test.tsx`.
  Initial 26 checks passed in 4.60s; review identified the native-dialog/exit
  prompt interaction. After its correction and regression test, **27 checks
  passed in 4.61s**. Coverage includes repeated open/close, input retention,
  incompatible timeframes, history return, exactly one explicit batch start,
  navigation and active-work exit handling. IPC is mocked in these tests.
- `node scripts/frontend.mjs build` passed TypeScript/Vite. Locked offline
  Windows Rust build passed in 3.64s; Python 3.12.14 / NautilusTrader 1.231.0
  runtime verification passed. Existing bundle advisory remains (736.28 kB JS).
- Native Windows walkthrough confirmed visible setup, Escape dismissal with
  focus returned to the card, repeated opening, cached H4 history selection
  returning to setup, warmup reservation, Review and Start. A daily Donchian
  batch reached **3/3 completed** and displayed results in Saved tests and on
  its card. Donchian executed; passive rows reused verified cached results.
  No market-history download was needed. The active-work exit/suspend case was
  checked automatically, not repeated as a native cancellation run.

No new dependency, backend computation, schema, version or trust change.
Unchanged broader regression evidence below is retained; no full backend suite
or display-scaling sweep was repeated. Owner usability acceptance remains open.

## Task-oriented usability refinement — verified, owner review pending

Research/Pro navigation is replaced by Strategy library, Market data, Saved tests
and Strategy editor. Cards offer direct testing and explicit comparison;
prepared history returns to preserved selections. Review shows dates, capital
and costs before start. Saved comparisons remain mounted during navigation for
progress/cancellation. Later-period verification has independent data/date
controls; incomplete downloaded coverage cannot enable Continue. Keyboard focus,
plain task labels and bounded catalog/setup panes improve navigation.

Windows evidence on 2026-09-30:

- Focused UI and neighboring checks passed 28 entries in 3.84s after correcting
  an old Results-label assertion. The first pass had 24 passes and that one
  failure. Review corrections added later-period and incomplete-history checks.
- `node node_modules/vitest/vitest.mjs run` passed all 83 entries across 21 files
  in 6.43s. Inspection then removed one accidentally duplicated coverage case;
  the remaining three HistoryWorkspace checks passed in 1.27s. Evidence covers
  **82 distinct frontend tests**, including complete first-test, timeframe,
  saved-result, independent-copy and navigation/cancellation journeys.
- `node scripts/frontend.mjs build` passed TypeScript/Vite after rendering the
  capital summary through its string representation. Locked offline Windows
  Rust builds passed; final shell rebuild took 3.58s. The existing chunk advisory
  remains (734.47 kB JavaScript). No application dependency changed.
- Native inspection exposed a setup pane extending below the viewport; cards
  and setup now scroll independently within the available desktop space. The
  corrected compiled window displayed the full Review and Start actions.
- Native flow selected daily Donchian, reused the existing complete BTCUSDT H4
  snapshot, preserved selection, reserved warmup to 2024-02-26, reviewed 1,000
  USDT / 0.10% fee / 0.05% slippage, and started three real tests. All three
  completed through 2026-09-01. The saved table showed Donchian, Buy & Hold and
  DCA including the negative DCA result. Donchian's report reopened with eight
  trades, its recorded candles and equity; returning preserved the comparison.

Backend calculations and schemas are unchanged from the 222-test checkpoint
below. New UI tests mock IPC and do not establish native cancellation timing or
new-download transport behavior. No additional full backend/live acceptance or
Windows scaling sweep was repeated. Owner usability acceptance remains open.
Reviewed text-only authoring skills and their pins/licenses are recorded in
[ADR 0027](adr/0027-task-oriented-testing-workspace.md).

## Research workspace extension — implementation verified, owner review pending

Branch `codex/research-studio` starts from merged main `a5bb197` (0.6 PR #7).
Product version remains 0.6-dev. Historical acceptance wording below is retained
as checkpoint evidence; this extension is a separate owner review.

Strategy library opens with cards, explicit timeframe comparisons and compact
capital/cost controls. Market data and Saved tests are separate tasks. Strategy
editor retains its independent draft/profile and native trust. Parameter
experiments and live/replay remain under More tools. New
EMA trend and prior-bar Donchian breakout graphs bring the catalog to seven
templates across four families. Source review and test evidence are separate
from profitability; see [Research guide](RESEARCH.md),
[ADR 0025](adr/0025-research-resolution.md),
[ADR 0026](adr/0026-research-workspace-and-trend-candidates.md) and
[all cohort results](library/VERIFICATION.md).

Explicit native 5m/15m/1h/4h/daily spot history drives closed-bar graph backtests
and passive alternatives through retained Nautilus accounting. Dataset coverage,
bar paths, source resolution, fees/slippage and precision are recorded. Exact
complete history reuse is offline; updates reuse checked immutable overlaps and
download missing spans into new snapshots. Contradictory overlaps fail. Charts
page by source candles and preserve recorded indicator/fill times. Native Python,
perpetuals, intrabar evaluation, Position Management, live/paper and parameter
experiments retain M1 where their coarse semantics have not been validated.

Windows validation on 2026-09-30:

- Focused new strategy/graph/coarse checks: 23 passed in 4.473s. The original
  backend checkpoint's seven new tests and financial/data/native neighbors also
  passed after preserving the legacy M1 download mock call shape.
- Combined Python regression: **222 passed in 146.279s** using
  `.venv/Scripts/python.exe -W ignore -m unittest discover -s tests -q`.
- Frontend acceptance covers **77 tests across 20 files**. The combined run passed
  76 and exposed a new test's incorrect history-sort assumption; selecting fixture
  rows by ID corrected it, and all nine App tests passed in 3.75s. Earlier focused
  checks exposed the intentional Donchian catalog count and unsupported test-only
  `exact` query typing, both corrected. No assertions were weakened.
- After a native-observed sticky-panel overlap correction and the saved-comparison
  shortcut, all 11 affected Library/StrategyLibrary tests passed in 3.15s.
- TypeScript/Vite and locked offline Windows/Rust builds passed. The latest Rust
  build took 3.76s. The non-failing frontend chunk-size warning remains (729 kB).
- Public BTCUSDT spot H4 history preparation: 5,844 candles in 3.59s; exact verified
  offline reopening in 0.047s. Six graph strategies at 4h/daily plus two baselines
  all completed over the common 918-day period in **87.72s**. Losing rows are
  retained. Baseline reuse, saved checksums, chart intervals and equity comparison
  passed. This is not an M1-equivalent fill model or a claimed M1 speedup ratio.
- Compiled Windows inspection confirmed Research-first layout, seven cards,
  History coverage, H4 selection and automatic prior warmup. The saved 14-row
  comparison reopened, the Donchian report displayed candles, fills, equity and
  recorded channels, and the independent graph editor opened. Component tests
  use mocked IPC and do not substitute for owner acceptance.

No dependency, product version, database schema or ordinary owner dataset was
changed by this extension. No merge, binary release, Telegram investigation or
new long-running live acceptance is included. Coarse execution changes path
fidelity; it does not establish superior investment returns. Source commit dates
postdate the measured market period; the cohort is retrospective integration.

## Product 0.6-dev — five-strategy candidate awaiting owner acceptance

The authorized Library core contains five independently verified implementations
across trend, mean reversion and momentum: Native EMA trend v2, and explicit graph
adaptations RSI threshold reversion, Bollinger RSI reversion, MACD normalized
momentum and Historical return direction. Thirteen primary-source candidates
were reviewed. Native EMA remains historical/linear-only with explicit source-
bound consent and a disclosed warmup adapter; the four graphs support spot and
linear closed-bar research. No author-recommended interval is invented. See the
[source matrix](library/SOURCES.md) and [strategy evidence](library/VERIFICATION.md).

Library controls freeze source/parameter/timeframe/profile/runtime/data contracts,
preflight asynchronously, and use the existing sequential managed-job slot.
Cancellation retains completed rows; explicit resume runs pending rows only.
Independent accounts use common initial capital and dates. Actual spot Buy & Hold
and scheduled DCA execute through retained Nautilus accounting, with full close,
fees/precision and cash included. Annualization is N/A below 365 days; losses and
no-trade results are retained. Baselines reuse only exact immutable contracts.
See [ADR 0021](adr/0021-passive-benchmarks.md), [ADR 0022](adr/0022-library-batches.md)
and [ADR 0023](adr/0023-native-library-window.md).

Cards/table expose saved metrics, prior-run state, cohort-aware sorting/filtering,
ordinary reports, copy actions and a sampled three-curve equity comparison.
Later-period verification freezes a completed selection before an explicit start,
restarts accounts/baselines on non-overlapping dates, and stays outside selection
ranking/card results. It records attempted variants, holdout reuse and pinned
source dates; it cannot prove external authors had not seen that history.
See [ADR 0024](adr/0024-library-later-period-validation.md).

Final combined verification on the five-strategy/later-period implementation:
**210 Python tests passed in 151.599s; 67 frontend tests across 19 files passed
in 6.81s.** TypeScript/Vite passed; locked offline Windows/Rust build passed in
4.81s with verified Python 3.12.14/NautilusTrader 1.231.0. Final review completed
missing card metrics and filter/delta-sort controls; the affected 7 frontend
checks passed in 3.13s. The affected TypeScript/Vite and Windows build passed (Rust 4.08s) after adding
the filter helper return type required by strict test compilation. Unchanged
Python tests were not repeated for that frontend-only change.

Copied-data compatibility preserved all 20 existing tables and 1,428,407 rows
with matching logical hashes and SQLite integrity. Library tables are additive;
later-period metadata uses existing snapshots. Normal owner data, immutable
artifacts and the experimental runtime lock were not modified. Accepted 0.5.1
source/runtime/executable remain independently runnable.

The bounded common cached BTCUSDT spot cohort (2026-09-01 12:00–24:00 UTC) completed
all four graph strategies at 1m/5m and both alternatives. Native EMA's verified
linear runs on the same dates retain actual separate spot alternatives. Existing
independent benchmark/accounting, native trust, batch parity and cancellation/
resume checks are included in the regression suite. No tuning, new endurance
session or optional sixth strategy was attempted. Compiled Windows smoke displayed all five cards, opened the predeclared frozen
later-period contract, completed its strategy and two baselines, and retained
separate verification labels and disabled selection ranking. The corrected
compiled UI reopened the completed 10-row cohort, displayed full prior-run card
metrics, and filtered momentum rows without hiding their losses/no-trade states.
Earlier compiled copy/stale/equity/report smoke and focused backend chart evidence
are retained for unchanged paths. Remaining non-failing advisories are the
frontend bundle size and native Pandas deprecation; this is not a release or
investment-performance claim.

Maintenance PR #6 was conditionally squash-merged as
`1d6918c939ffa9db7480ee179b12cca6a9ca3368`, with a tree identical to approved head
`69741c7cb990cf94861eef27512b4227d1a4f3e4`. Fresh isolated accepted startup passed.
The following maintenance sections retain the evidence recorded before that merge.

## Product 0.5.1-dev — maintenance candidate awaiting owner acceptance

The authorized ILI-134 maintenance scope is implemented on `codex/051`; owner acceptance and merge remain pending. See [acceptance steps](DEMO_051.md) and [ADR 0020](adr/0020-maintenance-paging-replay.md). No new dependencies, financial execution rules or stored result formats were introduced.

- **ILI-135:** chart paging distinguishes loading, retryable failure, ready and confirmed exhaustion. Failure retains current candles and permits a successful viewport-preserving retry. Focused verification: 6 Python tests passed (11.250s), 8 frontend tests passed (4.49s after one fixture correction).
- **ILI-136:** Results exposes bounded keyset pagination in deterministic newest-first order, with loading/error/empty/end states. A 125-record fixture covers timestamp ties and concurrent newer insertion without duplicates. Focused verification: 2 Python tests passed (1.061s), 7 frontend tests passed (2.93s after one fixture correction). Experiments and saved Live session paging remain outside this maintenance scope.
- **ILI-137:** Replay uses the existing managed worker slot with start/status/progress/completion/error/cancellation and persisted lifecycle. A deliberately slow worker exceeds the old 30-second request duration while ordinary service commands remain responsive. Cancellation never publishes a successful result. Initial focused verification: 10 Python tests passed (39.000s), 24 frontend tests passed (3.13s).
- **ILI-138 combined Windows verification:** `python -m unittest discover -s tests -v` passed **187 tests in 134.687s**; `node node_modules/vitest/vitest.mjs run` passed **60 tests across 17 files in 6.17s**. The pinned CPython 3.12.14 / NautilusTrader 1.231.0 runtime verified. TypeScript/Vite passed (1.41s); a fresh isolated locked/offline Windows/Rust build passed (1m 28s). Existing bundle-size and native Pandas advisories remain non-failing.
- Compiled Windows launch displayed `0.5.1-dev`. Native synthetic smoke verified chart failure followed by successful retry with anchored viewport/current market retained, and Results loading older pages to the end of a 125-record fixture. Background Replay progress and panel navigation remained responsive; the close confirmation exposed return/cancel-and-exit controls.
- The final native cancellation smoke exposed a Windows SQLite WAL lifetime failure. One corrective change keeps a service connection alive through worker termination and terminal-state publication. The affected Python regression rerun passed **10 tests in 38.903s**, including cancellation inside an actual read transaction and SQLite integrity. The corrected diagnostic IPC check ended cancelled without a result or stderr error, and corrected compiled Windows UI smoke displayed `Replay: cancelled`. The full suites and native build above preceded this Python-only correction; only its affected surface was rerun.
- Copied migration verification preserved **19 preexisting tables, 21 runs, 8 strategies and 105 immutable run artifacts**, with SQLite integrity intact. `replay_jobs` is additive. Subsequent read-only comparison confirmed the ordinary data's 19 tables and 105 artifacts unchanged; the experimental Windows lockfile remained unchanged. Destructive checks used isolated synthetic data only.

The corrected native short Replay also completed with **MATCH and 3 independently expected recorded signal events**. The isolated application then closed normally. Publication checks use pinned Gitleaks 8.30.1 on staged changes, the tracked tree and all outgoing commits; no secret findings were detected.

These are automated regression and synthetic Windows lifecycle observations, not owner acceptance, natural-network endurance or production readiness. Valid 0.5 financial and public-market evidence below is retained. No additional 30-minute public-market test or real Telegram delivery test was performed; ILI-37 remains untouched. No authorized issue required deferral to Backlog, no new Linear tasks were created, and product 0.6 was not started.

## Product 0.5-dev — owner-accepted development build

The owner manually accepted the current 0.5-dev build at `c7aae69005df81a5cee09f6ed1c6373c29ddee98` and authorized squash merge through [PR #5](https://github.com/IliaMerkurev/trading-terminal/pull/5). Remaining UI/UX issues are accepted as non-blocking and intentionally deferred; no redesign is part of this merge. Telegram delivery remains outside acceptance. This is an early development build, not stable or production-ready. See [demonstration](DEMO_05.md), [0.5 requirements](../PROJECT.md#21-product-05-independent-market-terminal-and-position-management), [market lifecycle](adr/0018-independent-market-lifecycle.md) and [position policy](adr/0019-shared-position-management.md).

- Market socket ownership is independent from optional strategy history and PAPER. Native 1m/5m/15m/1H/4H/1D chart pages have a confirmed-history cache, bounded recent history, incremental updates and viewport-preserving prepend. The chart never derives coarse history from a partially warmed M1 strategy.
- Optional policy schema 1 shares bounded scaling/DCA, partial TP, trailing, cost-aware break-even, confirmed-primary ATR protections and risk constraints across retained-engine Backtest/Paper. Legacy profiles without the policy retain their old snapshots and behavior.
- Explicit read-only position nodes use pre-decision account context; live records that context for replay. Manual PAPER may start without a strategy, and Add/Reduce25/Reduce50/Close share the same account/journal. Settings, backend protection lines and paged position lifecycle views are integrated.
- Experiments expose validated position axes with fixed risk caps and the same ordinary worker execution. Actual grid candidates equal standalone runs across metrics/fills/trades/indicators/equity; frozen later-period validation retains the policy.
- Merge regression rerun: **182 Python tests passed in 101.558s; 54 frontend tests across 16 files passed in 4.48s.** TypeScript/Vite passed; fresh isolated locked Windows/Rust build passed in **1m 24s**. Existing frontend bundle-size and native Pandas advisories remain non-failing. No dependency or license was changed.
- ATR readiness has a dedicated regression: an initialized value from partial historical warmup cannot enable protected manual actions; current history must finish first. Independent financial/temporal goldens verify weighted long/short entries, scaling after reduction, partial/full exits, fees/funding, cash/equity/margin/liquidation, rounding/rejections, trailing/ATR/cost-aware break-even, historical crossings, observed gaps and future perturbation. Full regressions retain native historical, editor, live/replay/recovery and notification behavior. Mocked notification tests do not establish native delivery.
- Fresh copied additive migration preserved all preexisting table records, result checksums and SQLite integrity. Ordinary user data was not used for tests. The separate synthetic demo completes two managed candidates and one frozen later-period validation.

### Startup evidence and native acceptance boundary

An isolated H1 service reproduction measured the old subscription delay at 88.609s. The first market milestone measured cold chart 1.625s, ticker/book 2.25s and trades 2.578s while causal warmup continued; warm cached chart appeared at 0.047s. These are bounded service timings with PAPER disabled, not UI latency guarantees. Earlier native Windows checks observed no-strategy chart/book/tape, H1 progress with current market retained, historical page prepend and independent market after monitoring pause.

The final automated Windows UI inspection could not complete because the automation helper returned `foreground window did not report a process id`. This is an automation limitation, not evidence of a product failure. Subsequent owner manual acceptance supersedes that blocker for this merge. It does not turn process launch or the service endurance check into automated native control/viewport/responsiveness evidence. No completed automated integrated native 30-minute session is claimed.

### Final public-data service evidence — 2026-09-13

A **31m 0.8s service-only run**, 07:27:53–07:58:54 UTC, observed one public connection, 2,833 ticker updates, 956 forming-M1 updates, 31 finalized M1 candles, 26,360 book updates and 4,818 trades. No natural reconnect or connection error occurred. Deterministic reconnect/reset/gap tests are separate evidence. The recent-trades buffer stayed at 100 rows; the log reached 35 rows. After warmup, interpreter working set stayed at **206.74–207.28 MiB**; one service interpreter with no direct child was sampled, with 26 OS threads (7 Python threads after warmup). This does not measure React/WebView memory or native UI responsiveness. Notifications were disabled in this probe; it does not establish native delivery or notification-storm behavior.

Cold service timing with non-ATR managed PAPER: chart 1.594s, ticker/book/PAPER ready 2.125s, trades 4.328s, H1 strategy ready 93.235s. Required causal history was retained. The recorded virtual lifecycle executed Buy 0.012, Add 0.012, Reduce25 0.006, Reduce50 0.009 and Close 0.009. A smaller preliminary fixture visibly rejected a below-minimum reduction; request processing is labeled separately from fills/rejections in the UI.

A bounded restart restored the same closed PAPER balance, initially required revalidation, and passed explicit revalidation. Cached chart appeared at 0.015s, market at 1.953s and strategy at 2.812s. Market updates continued after strategy pause. Recorded replay matched with **zero new H1 signal events** because the interval contained no new primary-hour close. Nonzero transition/context/future-perturbation proof comes from deterministic tests, not this zero-event comparison.

Actual REST paging also passed on all six supported intervals: 300 recent + 300 older candles each, ordered/contiguous/unique, 12 requests total. Reopening older pages reused the cache without new requests. Owner manual acceptance permits publication of the implementation through PR #5; the measured service evidence remains distinct from unperformed automated native measurements.

Telegram ILI-37 remains intentionally deferred/open. Windows/sound acceptance from 0.4 is retained; Telegram delivery is not claimed. The owner authorized only the 0.5 squash merge and verification, without a release or product 0.6 development.

## Product 0.4 development build — accepted and merged

The owner accepted product **0.4-dev** with real Telegram delivery explicitly unverified. [PR #4](https://github.com/IliaMerkurev/trading-terminal/pull/4) was squash-merged into `main` on 2026-09-12 as `f26cec685d9ef0bf6bd5ac53962ae4935e2604bd`, from the exact accepted head `348fce7324eaf89c14ee8da82aa53f3e19242a65`.

The pre-merge rerun passed **142 Python tests in 74.862s**, **40 frontend tests in 29.26s**, targeted **46 Python tests in 16.043s** and **20 frontend tests in 2.18s**. TypeScript/Vite and the locked offline Windows/Rust build passed (Rust **24.13s**). Gitleaks 8.30.1 found no leaks in the complete tracked tree or all four outgoing commits. The targets cover Live Terminal/chart/editor behavior, live/replay, reconnect/book recovery, manual paper accounting and notification diagnostics. Telegram mocked transport results do not establish delivery.

After merge, the normal main checkout rebuilt successfully (Windows/Rust **6.39s**) and launched as Trading Terminal **0.4-dev** on the ordinary user data root. A fresh backup, copied migration check and post-launch comparison preserved all preexisting table rows, **8 strategies, 21 saved runs and 105 result files**, with SQLite integrity and result checksums intact. Separate demo/live journals were not imported or replaced. No dependency on a temporary acceptance root is required.

Product **0.4-dev** adds the chart-led Live Terminal over the accepted 0.3 engine and shared Strategy IR. It is an early development build, not stable or production-ready. See the [0.4 demonstration](DEMO_04.md), [scope](../PROJECT.md#20-product-04-live-terminal), [shared market state](adr/0016-shared-market-terminal.md) and [manual PAPER semantics](adr/0017-manual-paper-source.md).

Implemented: one centrally owned public ticker/M1/order-book/trade pipeline; fresh/stale market header; forming/final candlestick chart and recorded IR overlays; independent display intervals; snapshot/delta book with 15 displayed levels per side; bounded recent-trades tape; compact settings and switchable terminal panels; manual virtual Buy/Sell/full Close through the retained paper account. Reconnect invalidates the old book/tape and retains confirmed-minute recovery and paper revalidation.

Final regression evidence: **142 Python tests passed in 72.663s**, **40 frontend tests across 13 files passed in 4.14s**. TypeScript/Vite production build and locked offline Windows/Rust build passed (final Rust build 4.17s). The opt-in native toast-history test passed. No dependency version or license was changed. Existing Pandas deprecation and frontend bundle-size advisories remain non-failing.

Deterministic checks include book snapshot/delta/zero removal/order/reset, one subscription set per connection, bounded tape, display interval/IR independence, stored-value and future-perturbation checks, manual spot/perpetual accounting, protection prices, no strategy orders in Manual mode, request deduplication/expiry/restart, restored paper accounting and existing live/replay/recovery regressions. Independent manual spot equity is 1009.79 after 0.21 fees; the perpetual short golden ends at 1019.62 after 0.38 fees. Native checks observed virtual long/short entry/full close, a 5m chart with unchanged 1m/closed strategy and connection, recorded SMA values, panel/settings navigation, minimize/restore and normal paused reopening.

### Real public-market measurement

The compiled Windows terminal monitored public linear BTCUSDT for a **32-minute measurement on 2026-09-11**, starting at 20:36:36 UTC. Its 127 resource samples span 20:36:36–21:08:32 UTC (31.923 minutes between first/last sample); monitoring continued until the final UI capture at 21:09:27 UTC, then paused normally. Final cumulative subscription counters were **34 finalized candles, 1,400 forming updates, 13,248 ticker updates, 63,377 book updates and 27,304 trades**. The subscription began shortly before measurement, so these are cumulative totals rather than exact measurement-window deltas. Strategy evaluation reached 21:09 UTC, chart/book/tape continued updating and the interface remained responsive.

- There was exactly **one successful subscription set** and **no natural disconnect** in this run. A separate deterministic reconnect recovered two missing candles, invalidated old book/tape state and opened exactly two subscription sets. An actual normal restart before measurement recovered one missing candle and required paper continuity revalidation. Missing tape/ticks were not invented.
- Application plus descendant process count stayed **11**. Combined working set was **702.37 → 768.85 MiB**, maximum **776.86 MiB**; combined private memory was **979.61 → 1033.02 MiB**. Python working set was **213.36 → 219.08 MiB**, maximum **219.09 MiB**, and stabilized during the run. Most additional working memory was in WebView. This finite measurement does not prove indefinite memory stability; longer sessions remain an acceptance boundary.
- Chart history, book, trade IDs/tape, event/signal displays, notification queue and manual request history have explicit bounds. No duplicate subscription, retry loop or service error was observed. Automatic notification channels were disabled during the measured session; one explicit native sound Test dispatched successfully. Anti-spam semantics are covered by durable transition/claim tests, not a claim of sustained real notification delivery.
- Paused replay reported **MATCH for all 22 recorded signal events**. A separate consistent journal copy reconstructed **12,387 committed paper observations exactly** and matched its then-current 15 signals. Real manual actions ended flat; recording and replay did not alter ordinary user data. A separate 12.02-second real spot probe also observed ticker, forming candle, book and trade updates; it is not the long-run evidence.
- The prolonged run used integration commit `6313c09`. Follow-up `277d822` changes only chart projection/formatting and strengthens tests: omit a truncated leading coarse candle, constrain indicator samples to visible history, preserve the evaluation timestamp and format funding precisely. The final executable was rebuilt afterward and reopened the saved paused session. Native checks observed its 5m chart, recorded SMA and fresh funding display after recovery; the backend/transport/account used in the prolonged run is unchanged.

The owner accepted the non-Telegram 0.4 functionality. This does not turn unperformed automated checks into measurements: no controlled 100%/125%/150% DPI matrix, physical sleep/wake measurement or multi-hour resource guarantee is claimed. Native Windows toast history was checked; Telegram real delivery was not. Product 0.4 is now in `main` and remains an early development build, not stable or production-ready.

Additive migration on a consistent copy preserved all preexisting records, result checksums and SQLite integrity (8 strategies, 21 saved runs). All public-market/demo work uses isolated data, not the ordinary user database.

**Telegram remains a known acceptance issue (ILI-37).** The request matches the official Bot API; no real delivery root cause was established. Safe actionable HTTP/API/network/TLS diagnostics were added and malicious-response tests pass. Credentials remain in Windows Credential Manager. No real Telegram delivery success is claimed; a new owner Test notification is required. Windows and sound behavior retain their separate accepted baseline.

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
