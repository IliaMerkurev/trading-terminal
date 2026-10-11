# Current engineering checkpoint

Updated 2026-10-11. Working branch: `codex/terminal-mvp`; product remains
`0.6.0-dev`, licensed MIT. The original bounded Linux/browser engineering and
research continuation is complete, along with the later daily candidates, nine
chart display tools and chart context/navigation improvements. This is a development source checkpoint, not a packaged
release, main merge or final owner acceptance. [PROJECT.md](../PROJECT.md) remains
the specification; [STATUS.md](STATUS.md) records exact-source evidence.

## Current chart focus checkpoint

The latest frontend-only candidate adds reversible Focus chart / Exit chart
focus to the actual App / Live market layout (ADR 0046). It retains the mounted
chart and editors, exposes a sticky source/freshness/Exit bar, hides surrounding
chrome/book/tape and uses one outer scroll owner. Escape yields to drawing/editor
work; drafts, selection/undo and pending Return survive layout changes. Source
namespaces retain their existing reset rules; leaving Live market clears focus.
Saved history/run charts are outside this feature. Focused scope: 84 distinct
passing frontend tests plus TypeScript/production build. Independent source
review and full-App browser acceptance passed on frozen `51b75fb` at 1180×757,
995×688 and 625×432 CSS pixels (compact sizes through browser zoom). Compact
views had no document-width overflow; expanded editors/chart remained reachable
through the outer scroller with sticky Exit/source/status available. Wide checks
retained chart/drawing history and drafts, layered Escape, source namespace reset
and visible synthetic degraded/error recovery. See STATUS.md for exact evidence.
Staged/outgoing Gitleaks 8.30.1 scans passed. This documentation-only acceptance
record does not rerun tests/build or establish live-provider, native/Windows or
owner-led unaided acceptance. No broad/backend rerun, new dependency,
provider/trading behavior or product-version change.

## Delivered chart context and navigation

Pre-focus checkpoint `84d1d60` includes the later ADR 0044 context controls,
ADR 0045 latest navigation and older-page viewport eviction correction, in
addition to the earlier ADR 0043 tools described below. Drawing properties and
indicator legends sit outside the plot, retain collapsed drafts and show failed
save recovery. Non-scrolling drawing focus prevents capture-time anchor jumps.
Return to latest preserves zoom and scale/editor state; Following latest is
separate from feed freshness. A fully evicted older-page view moves only to the
nearest retained boundary at the same zoom, preserving partial overlap/gaps.

ADR 0044 has focused 40-test and pre-focus-correction 528-test aggregate evidence,
then 16 post-correction drawing tests/build and bounded offline-wrapper browser
acceptance. ADR 0045 has 61 focused tests/build/review and offline-wrapper
navigation acceptance; the eviction correction adds 44 focused tests/build/review
and same-zoom/partial-overlap/automatic-paging browser checks. Exact original
source hashes, measurements and retained limits are in STATUS.md. These earlier
wrapper checks do not substitute for the new full-App focus acceptance or prove
live-provider, current Windows/native or owner unaided acceptance.

## Current indicator and drawing additions

ADR 0043 adds ATR (explicit Wilder/SMA seed), Stochastic and OBV display tools,
plus custom Fib ratios/reset and optional names in the saved-object selector.
Graph/recorded IR, six previous display formulas and immutable runs are unchanged.
Legacy drawing documents retain their fields on read. All three additions stay
unavailable before the saved origin; OBV retains native source units. Focused
coverage: 25 distinct Python / 34 frontend tests, TypeScript/build. Frozen clean
source `227c025`: backend 491 total (483 passed / eight expected platform skips)
in 194.067s; frontend 520/520 across 57 files in 18.00s; TypeScript/Vite passed.
Source SHA/worktree remained unchanged throughout. Parent-led fixed-H4 offline
browser acceptance passed on `227c025`: independent indicator readouts and edited
parameters, normal auxiliary panes under log price, custom Fib levels/name,
validation, reset/undo, lock and reload. See STATUS for exact evidence and the
remaining live-provider/native/Windows and unperformed navigation limits.
No dependency, provider fetch, version bump or main integration.

## Current chart-workspace candidate

ADR 0042 implements independent default volume overlays and optional separate
panes, convenient native/time/price controls, and seven bounded, persisted MIT
drawing tools plus a transient ruler. Source+market+instrument annotations share
absolute UTC interval-end time/price anchors across native timeframes. No
financial or six-indicator formula changes and no new dependency. Focused final
checks: 17 Python / 27 frontend tests plus TypeScript/build passed. Clean frozen
backend `adf1bb9`: 483 tests, 475 passed and eight Windows-only skips (205.132s).
Final frontend-only no-op and new-tool selection-context corrections: full
515/515 across 57 files (17.16s), TypeScript/build passed; backend runtime unchanged.
Private offline saved-H4 browser acceptance at final source `41e9dc7` verified
all seven tools, body/endpoints, lock/hide, history, transient ruler/pan, volume
placement, log/auxiliary scales, reload, corrected selection behavior and 703px
layout. GUI cross-timeframe/older-page continuity was not exercised; tests cover
those contracts separately. Windows/native and live connectivity remain
unverified. This later candidate supersedes the older six-tool-only boundary,
not its recorded evidence. No optional indicator expansion, release or version bump.


## Public-source chart addition

The current Market UI adds an explicit persisted Bybit / OKX source selector.
OKX is public-data, display-only; strategy/paper monitoring remains Bybit-only.
Native confirmations, caches, indicator settings and replay origins are strictly
source-separated, and rapid switches discard obsolete responses. Legacy Bybit
IPC and data retain their meanings. See the newest STATUS entry and ADR 0041 for
verification, units, protocol sources and remaining live/Windows acceptance gates.
Final frozen source `3a2c0ce`: backend 479 tests, 471 passed and eight platform
skips; frontend 503 passed. TypeScript/build, independent review and source-switch
synthetic browser checks passed. Real OKX activation encountered network
unreachable (errno 101) for both WebSocket and REST, with no exchange data or HTTP
response. Live connectivity and current Windows acceptance remain unverified.
Earlier failed/non-frozen aggregates and their limitations are retained in STATUS.
No new credentials, strategy, research run, execution support or product version.

## Current closeout

- TT10 modeled-work/full-source admission and independent spot benchmark
  contracts are implemented. TT13 background operations, explicit same-operation
  import continuation, finalization and verified reads passed supported-load
  Linux acceptance with the documented latency/memory limits.
- The 291 fixed TT17/TT18 observations completed and reopened independently.
  None of the six adaptation variants qualified for promotion; negative and
  inconclusive outcomes remain final rather than restarting a search.
- C12 Double 7's and C13 Improved R2 have both independent synthetic evidence
  and a finite cached-public-data integration on `f8ffe1c2`. The latter was an
  explicitly recovered gate: four verified completed outputs plus one retained
  cancelled technical attempt. The original Library batch remains
  `completed_with_errors`; see STATUS for the harness failures and recovery.
  C12 had one completed position; C13 had no trades. Neither is a profitability
  or robustness claim.
- SMA, EMA, Bollinger Bands, RSI, MACD and source-native volume are separate
  cache-only display tools with persisted settings, independent instances,
  confirmed-input provenance and bounded stable-origin replay. Synthetic browser
  checks cover arithmetic, forming inputs, over-budget refusal, normal/narrow
  layout and retained settings without exchange or trading activity.
- Published application checkpoint `c3772d4` was followed by a production-
  unchanged test synchronization fix at `f8ffe1c2`: final frontend aggregate
  **496/496 across 55 files**. Backend aggregate, focused corrections, build and
  browser evidence retain their individual recorded identities; no new full
  backend run is implied by this documentation-only closeout.

The dated sections below preserve earlier slice boundaries. Their statements
about then-pending TT10/TT13/research or excluded later features are historical;
this closeout and the matching later STATUS evidence supersede them, without
rewriting old financial results or broadening platform acceptance.

## Current daily reversion checkpoint

The latest narrow frontend correction keeps the shared Lab profile compatible
when transferring a saved observation into daily/H4 research. Parent-led browser
runs on the preceding source completed both synthetic candidate lifecycles and
passive controls with exact costs; they used Lab percentage sizing and an explicit
resolution-toggle workaround. Read-only reconciliation preserved all six reports
and 195 normalized rows. Straight observation transfer and editor-copy reopen on
the corrected build passed parent browser checks. Full-catalog 4h/1d choices were
retained; mixed-resolution review was correctly blocked by the daily-only fixture.
Candidate-specific unavailable rows have automated coverage. See newest STATUS.

C12 Double 7's and C13 Improved R2 are available as daily spot long/flat
clean-room graph candidates with editable rolling extrema/closed-bar lag nodes.
Source and authored-rule hash disclosures explicitly distinguish synthetic
implementation verification from empirical validation, which is not performed.
Existing defaults/archive contracts remain intact, including the 4h/1d full-
catalog selection with unsupported daily-candidate rows shown unavailable.
See [ADR 0039](adr/0039-daily-reversion-candidates.md) and STATUS for exact rules,
independent arithmetic, costed execution, prefix/gap and persistence evidence.

Final Linux aggregate: 454 backend tests (8 expected platform skips), 481
frontend tests (485 after the narrow observation-transfer correction), TypeScript/production build and runtime/dependency verification
passed. Independent financial/source/UI-state review approved the final source.
The new-only synthetic/local fixture and manual workflow are in DEVELOPMENT.md.
Parent-led bounded browser acceptance is recorded above; Windows/native, owner acceptance and
empirical C12/C13 work are not implied. No extra strategy, chart-indicator, live,
exchange-acquisition, merge or release scope is included. Product stays 0.6.0-dev.

## Bounded original research completion

All 291 predeclared TT17/TT18 observations completed and passed independent saved-result
reopening: 228 neighbor/reference/control observations and 63 own-adaptation/control
observations. No failed/cancelled rows, financial retries, changed windows or post-result
selection. Six slow-ROC/deadband variants passed implementation checks; none qualified
for promotion. Sparse, sensitive and loss-making conclusions are retained.

Execution used `1b532796707aa3cf39af681f64148bfabf4b1c86`; subsequent alignment to
`9239d53de8ab973d171f6b8e4a2a6d76e9def997` retained identical tested tree
`fe6d86fc5709aa70f4b201b7ba5c7bdc0f930ccf`. Saved identities remain unchanged.
See STATUS for aggregate evidence and limits. Required native-minute prefix is
unavailable, no untouched holdout exists, and Windows/native and unaided-owner
acceptance remain deferred. The later C12/C13 additions are a separate engineering
slice, not new variants of this completed frozen campaign.

## Current TT13 verified-read checkpoint

Both saved chart routes and observation-save verification use the independent
managed read lane in [ADR 0038](adr/0038-verified-background-chart-reads.md).
Full same-descriptor integrity, full-stream value/order/gap checks, bounded pages,
stale generation guards and separate durable note-save outcomes are retained.

The exact-source Linux/browser gate passed on `9a9c3e9`: all six admitted rows
at 2,000,000 modeled source candles executed once, with 3,672,046 exact normalized
rows verified. Both charts and note verification remained usable during actual
calculation/finalization. Maximum ordinary request was 1.998035 seconds (little
margin); maximum cancellation-to-terminal was 0.571451 seconds. Report READY
peaked at 1.667432 seconds and observation READY at 2.164473 seconds; READY is
separate from the ordinary-request target. Sampled summed process RSS peaked at
4.35 GB, excluding browser and postmeasurement full verification. See STATUS for
full scope, timing, memory caveats and aggregate tests.

Parent-led corrected-control browser checks passed Cancel/Retry, actual READY,
neutral note cancellation and report reopening. Lab review close/reopen is
verified automatically; its GUI preview was blocked by fixture metadata. The
bounded TT13 Linux/browser chart-read and combined campaign gate is complete.
Windows/native, live and the separate remaining research plan stay pending; this
is not whole-plan acceptance or a release. Current checkpoint changes are docs-only
and preserve measured runtime/build bytes.

## Current TT13 local finalization checkpoint

Local calculation output now enters an observable managed `finalizing` phase;
JSON/artifact/normalized work is outside scheduler ownership locks. Local-only
generation authority, bounded ordinary batches, compatible isolated oversized
rows, independent full-content verification and a short mutation-epoch-guarded
commit preserve exact financial output and provenance. The same monitor retains
batch/worker ownership through cleanup. Cancellation remains requested until
reaping; completion-winning races, persistence quarantine and restart without
automatic promotion are explicit. See [ADR 0037](adr/0037-managed-local-result-finalization.md).

The frozen-source focused backend gate passed 80 tests, with additional narrow
HTTP/composed-restore/cancellation measurements; 55 frontend tests and the
TypeScript/production build passed. Actual admitted 440k-source M1 execution
published 720,274 normalized rows with exact worker/result hashes and independent
full-row comparison. Ordinary HTTP writes stayed below 36 ms in that case;
the preserved 67-MB single-row exception stayed below 331 ms. Combined sampled
M1 memory peaked at about 4.12 GB, distinct from the 1-GiB source-estimate guard.
The six-row 2M workload was previewed, not all executed by this slice. See STATUS
for exact commands, chronology, latency/memory scope and synthetic-only limits.

Initial parent-led production-browser checks passed pending/cancel/reload/save
and success-after-cleanup paths, then identified small status/history UX issues.
The frontend-only correction passed 37 focused tests and the build; corrected
browser spot checking passed active-history navigation, separated progress,
cancellation copy and existing completed-report selection. A final text-only
pre-poll loading fallback passed all 9 progress tests, TypeScript and build;
that last branch was not browser-rerun. Backend load evidence is unchanged. Verified chart-read
and combined Linux/browser acceptance are recorded above;
Windows/native, live exchange work and later research are separate gates. No
whole-plan completion is claimed.

## Current TT13 export checkpoint

Managed background export and bounded authenticated download are implemented in
[ADR 0036](adr/0036-background-project-export.md). Explicit request identities,
frozen inputs, cancel/publication ordering, launch-local grants, 256-KiB verified
chunks and browser final checksum retain the archive privacy/integrity limits.
The near-64-MiB compressed and distinct near-128-MiB expanded synthetic cases
passed the declared 2-second request and 5-second cancellation targets, including
ordinary SQLite writes and a deliberately stalled receiver. See STATUS for exact
commands, source scope, metrics and memory exclusions.

Parent-led production-browser export acceptance passed on source `3f287f7`:
two-report cancellation/restart/repeat-download checks and an actual eight-report
**65,439,135-byte** verified browser download. Closed-workspace reconciliation
preserved exact results/snapshots, normalized rows and import receipts. Browser
RSS/heap/Blob peak remains unmeasured because Chrome process roots were not
observable through the available process-resource interfaces; no zero-memory
claim is made. Windows/native and live exchange work remain deferred. Import GUI
acceptance below remains valid. The newer local-finalization checkpoint above
supersedes that pending path; verified chart-read combined
Linux/browser acceptance is recorded above. No new financial
calculation or source trust was introduced.

## Current TT13 import checkpoint

The latest source implements the managed asynchronous import and explicit
checksum-bound same-operation continuation in [ADR 0035](adr/0035-asynchronous-recoverable-import.md).
Production UI uses background start/status/cancel, retains published IDs and
separates cancellation request from reaped terminal state. Additive attempt
history, exact missing-source replacement, startup reconciliation and hidden
staging preserve old receipt/archive contracts and completed content. No source
trust, financial execution or automatic retries were added.

See the newest STATUS entry for 71-test combined focused acceptance plus narrow
correction checks, component/build evidence and four supported-limit dimensions.
The largest normalized row remained admitted and measured below the declared
local request targets; peak combined sampled memory was about 1.46 GB. This is
Linux engineering evidence, not Windows/native or owner acceptance. Parent-led
production-browser import acceptance passed on corrected build `54152e8`, including
immediate continuation notice/history updates, same-ID completion and normal
shutdown. Query-only post-close reconciliation preserved exact source/reservation
identity, artifacts, normalized values and both attempt outcomes with zero trust.
This import checkpoint was published before the export slice; see STATUS.md for the bounded GUI evidence.

TT13 chart-read combined Linux/browser acceptance is recorded above;
the separate remaining bounded research requirements remain unfinished. Keep the
accepted independent baseline and do not reopen TT10 accounting/contracts merely
because this import slice changes storage/lifecycle code. Product stays
`0.6.0-dev`; no whole-plan completion is claimed.

## Renewed original-plan continuation: TT10 / A4 and A2

The original remaining engineering/research plan is reopened after the bounded
UX candidate. This checkpoint implements modeled-work versus full-source
loading admission and additive independent spot passive contracts. New library workload version 2 counts full strategy prefix
plus evaluation and evaluation-only passive rows; no cache discount. New reviews
freeze per-row counts and source-load policy 1. Old saved counts remain legacy
and unchanged. Full trade/mark/funding sources receive separate bounded metadata,
physical and materialization-estimate checks before eager decoding; no execution
or indicator history is shortened. See the new A4 evidence in STATUS.md and
[development guidance](DEVELOPMENT.md#modeled-work-and-independent-full-source-admission-tt10--a4).
A2 now freezes independent spot costs, precision/order limits and explicit
provenance across preview/start, cache, resume, later-period verification and
archives. Metadata and deliberately reviewed manual assumptions are available;
missing optional settings/history retain N/A passive rows. Legacy spot contract
shapes are preserved. See [A2 guidance](DEVELOPMENT.md#independent-spot-passive-controls-tt10--a2).
TT13 and remaining bounded research are not implemented by this slice. Windows/native and new exchange/live work remain
deferred. Parent-led production-browser inspection and publication follow the
local engineering checkpoint; neither is implied by component tests/build.
The subsequent A2 production-browser check passed visible failure/retry,
one-ready-plus-two-N/A and three-ready review paths, percentage-to-fraction
serialization, explicit cost provenance and stale-preview invalidation. Saved
and frozen independent-cost values remained unchanged; no runs or freezes were
created. See STATUS.md for exact evidence. This does not close TT13, remaining
research, Windows/native/live or owner acceptance.

## Start here

- [Development guide](DEVELOPMENT.md): matching platform setup, browser and
  retained Windows launch commands, isolated data roots and lifecycle rules.
- [Research workflow](RESEARCH.md): the two main journeys and existing controls.
- [Architecture](ARCHITECTURE.md): retained service/engine responsibilities.
- [Archive contract](adr/0008-archives-comparison.md),
  [browser boundary](adr/0030-local-browser-research.md),
  [saved details](adr/0031-saved-comparison-details.md),
  [admission evidence](adr/0032-research-admission-evidence.md),
  [observations](adr/0033-local-history-observations.md) and
  [display evidence](adr/0034-displayed-period-evidence.md): invariants and limits.

From the intended checkout, use the [browser launch instructions](DEVELOPMENT.md#local-browser-research-mode)
with its matching Python environment, built frontend and an explicit absolute
separate data root. Open only the numeric loopback address printed by the host.
Keep the host running; closing a tab does not stop it. Stop cleanly before
rebuilding assets, then restart. The [Windows launcher](DEVELOPMENT.md#launcher-and-separate-demonstrations)
is retained but needs current native acceptance. These are source-checkout
routes, not a portable executable bundle: moving a desktop checkout requires a
rebuild. Back up the complete data root after shutdown; never substitute a
synthetic fixture database for ordinary research data.

## Final bounded candidate gate

Corrected source is `cfe60f62ff9ba6f866219c80cc2fafbccea0b426`, tree
`3c5e8fda136e0e9a2f2f6217f5fde4d53724519a`; subsequent changes are documentation
only. Composed production-browser journeys passed through exact observation/Lab
return, saved comparison/equity, later-period data preparation and review/cancel,
without new runs or freezes. Corrected Cancel and physical Escape both restored
the exact originating Freeze button with no open dialogs.

Pre-focus-correction source `ace120c3b14e6a77bec2fb5f738fcc191d8e67c1`, tree
`ce8aea0dfcd0d2c9a0b4bbac308cb111c5f364bc`, passed one combined closure run:
**413 frontend tests across 45 files**, followed by TypeScript/production build.
This includes the frozen-equity-default correction and saved-filter summary.
Composed browser inspection then found lost origin focus after asynchronous
freeze review. The narrow explicit-origin correction has **48 distinct focused
tests** plus a final TypeScript/build pass; the 413-test aggregate is retained as
pre-correction evidence; corrected browser confirmation passed.
Backend bytes are unchanged; retain **327 passed / eight Windows-only skips**
without a redundant backend rerun.
See [final bounded UX candidate verification](STATUS.md#final-bounded-ux-candidate-verification--2026-10-10).
No further feature slice is implied; current Windows/native, live-feed and
owner-led unaided acceptance remain separate.


## Current saved-filter clarity slice

The Saved tests table distinguishes numeric strategy matches, retained context-only
rows and passive references using its actual filtered rows. Zero matches are
explicit; blank/invalid thresholds neutrally count rows shown. Existing filters,
sort/holdout order, evidence recording and run actions are unchanged. The focused
pass passed **57 tests across five files**; final TypeScript/production build
passed after a test-only type annotation correction. Production-browser checks
passed at 750px for zero matches, retained context/baselines, combined category
filters, invalid input and Clear; independent review found no blocker. See [saved-test filter outcome clarity](STATUS.md#saved-test-filter-outcome-clarity--2026-10-10)
for exact evidence and retained platform/acceptance limits.


## Current saved-equity slice

Compare equity opens a reachable, focused inspector with frozen row identity,
timeframe, original context and expandable saved parameters/IDs. Its independent
read/loading/error/retry state preserves the surrounding comparison and Lab
draft. Back to result restores the action or a visible table fallback; late
responses cannot revive inspection after close, navigation or a batch change.
No new calculations or display-evidence category is added. The final combined
frontend pass before the frozen-default display correction passed **399 tests
across 44 files**; the correction and added regressions then passed **10 focused
equity tests**. Final TypeScript/production build passed. Production-browser inspection passed at ordinary and 750px widths for
focus/return, distinct variants, route dismissal, repeat activation and frozen
resolved defaults. Transport races/failures remain component evidence. See
[saved-equity inspection](STATUS.md#explicit-saved-equity-inspection--2026-10-10)
for verification scope and platform limits.

## Current chart-to-observation slice

The newest bounded frontend slice adds explicit start/end capture from a pinned
Saved history candle into an unsaved observation. Open/exclusive-close UTC
boundaries, complete aggregate coverage, immutable saved dates and separate
Save/Test actions remain explicit. Live page/source/display and action guards
reject stale selections; activation rechecks visibility before deferred clearing.
The focused pass passed **113 tests across six files**, and TypeScript/production
build passed. Production-browser checks passed at 1180×757 and 750×757 for
price/volume click pinning, exact start/exclusive end, keyboard use, gap/reset
behavior, invalid periods, draft return and an explicitly saved revision-bound
Lab attachment. No calculation was started; current Windows/live and owner-led
unaided acceptance remain separate. See
[chart-to-observation period capture](STATUS.md#explicit-chart-to-observation-period-capture--2026-10-10).

## Current storage/recovery slice

The newest bounded slice adds durable status-only archive-import receipts, all-ID
reservation before artifact writes, transactional per-run publication and
insert-only strategy/terminal completion. Recent imports restores inspection after
reload/restart; it never resumes or retries. Partial receipts distinguish completed
reports from reserved/incomplete items. Import refresh/open errors and late
navigation callbacks cannot rewrite a completed outcome or replace a newer draft.

The final complete backend pass passed 327 tests plus eight Windows-only skips
(335 total). The final complete frontend pass passed 377 tests across 42 files;
TypeScript/production build passed. Full closed-copy validation preserved
26 existing tables and 41 non-database files across two
lifetimes. See [durable import inspection](STATUS.md#durable-archive-import-inspection--2026-10-10)
for exact fault/crash/HTTP evidence, correction chronology and platform limits.
Production-browser read-only receipt/restart inspection passed at 1180px and
750px widths, with unchanged mapping/counts and receipt-bound artifact hashes
confirmed after shutdown. A fresh actual browser upload also recovered its exact
completed IDs after a deliberately discarded reply, without reupload; ordinary
restart and explicit report/strategy opening retained those same IDs. Post-close
read-only reconciliation confirmed no duplicate import or execution. Finalization
is synchronous; artifact verification by the UI is not checked, and Windows/native
recovery is unverified.

## Current UX-series evidence

The newest slice adds independent exact-UTC Saved history navigation, anchored
First/Latest pages and explicit failed-page Retry. Note dates/revisions/text,
Lab inputs and compatible display choice remain separate. Focused evidence is
**155 distinct tests across seven files**; final TypeScript/production build
passed. Production-browser checks passed at 1180×757 and 750×757: exact 500/400/
last-slot pages, invalid dates, missing openings, wrapping/keyboard use and
saved/dirty/historical note context all behaved as specified. Retry/races and
persisted exposure counts remain component evidence. The preceding combined
285-test frontend pass remains evidence for its unchanged surfaces, not a new
full regression claim. See [independent saved-history date navigation](STATUS.md#independent-saved-history-date-navigation--2026-10-10).

The preceding slice gives desktop Lab one natural outer scroll surface instead of
a fixed inner card well. Lab and Saved tests retain independent session-local
offsets without remounting cards or moving focus. Corrected production-browser
checks passed at 1180×757 and 750×757: expanded parameters and actions remain
reachable, exact route-return positions survive, dialog focus returns correctly,
and filtered Test all retains all seven strategies. One combined final frontend
pass passed **285 tests across 38 files**, including the preceding chart/display
and ordering slices; TypeScript/production build also passed. See
[natural Lab scrolling](STATUS.md#natural-lab-catalog-scrolling--2026-10-10)
for the exact geometry, validation and remaining acceptance limits.

The preceding slice adds bounded Source/1h/4h/1d display projections to Saved
history. Only complete UTC buckets render; missing and outside-page coverage
stay distinct, with exact contributing-source display evidence. The original
500-source-slot page budget, source-aligned observations and Lab inputs stay
unchanged. Same-source display choice survives navigation; exact-source changes
reset it. Focused coverage is **106 tests across five files**, and TypeScript/
production build pass. Corrected production-browser checks passed at 1180px
and 750px widths, including visible gap bands, exact aggregate values, incomplete
daily page edges, navigation and same-source retention. The check also corrected
a pre-existing fractional-coordinate band defect and its inaccurate test mock.
Persisted exposure counts remain component evidence. See
[saved-history display intervals](STATUS.md#saved-history-display-intervals--2026-10-10)
for exact evidence and explicit daily-from-minute/cross-page limits.

The preceding slice adds explicit saved-comparison card ordering in Lab. Name,
return, drawdown and completed-position ordering preserve card drafts and
catalog-order Test all payloads. Numeric ranking requires the saved timeframe
and compatible cohort; ambiguous parameter variants remain N/A. Actual finite
card metrics reuse displayed-period evidence with stable presentation recorders.
Focused coverage is **70 distinct tests across six files**; TypeScript and the
production build pass. Bounded production-browser checks passed at 1180×757 and
750×757, including the compact context disclosure, keyboard use, draft retention
and filtered Test all. Holdout reset and display-write counts remain automated
evidence only. See [saved-comparison card ordering](STATUS.md#saved-comparison-card-ordering--2026-10-10)
for the exact focused passes and separate platform/owner acceptance limits.

The preceding slice adds synchronized source-volume inspection, exact UTC OHLCV,
keyboard candle navigation and explicit gap whitespace/bands to Saved history.
Its focused scope has 64 passing tests across six files, including regressions
for a browser-discovered synthetic crosshair callback issue; TypeScript and the
production build pass. Corrected production-browser inspection passed at
1180×757 and 750×757, including gap selection, keyboard reveal, page reset and
exact-revision Lab return. Browser checks did not recount display-evidence
database writes; component tests cover that boundary. See
[saved-history OHLCV inspection](STATUS.md#saved-history-ohlcv-inspection--2026-10-10)
for exact automated evidence, retained bounds and platform limits.

The preceding UX-series code is `fba0e5c4c3e0f316c55209738c255976c11e5501`, tree
`06f96249c960b000a60c439e6858e7da25058ce7`. One complete frontend pass on that
code passed **197 tests across 34 files**. Its final read-recovery slice also
passed TypeScript and the production build. See [combined UX-series verification](STATUS.md#combined-ux-series-verification--2026-10-10)
for that checkpoint's evidence and browser-versus-component limits.

This series delivered compact Saved tests review, a visible attached-observation
cue in Lab, compact pre-review test selection, exact observation-date guidance,
and explicit read-only recovery of the saved-observation list. Source/range,
saved revision, test selection, warnings and explicit Review/Start boundaries
remain intact. The slice entries record bounded production-browser checks at
ordinary and narrow widths; owner-led unaided usability is still pending.

## Historical functional baseline

The preceding bounded MVP baseline was `bc10a4cef57530fb843437678bd852c7e04aa7d1`,
tree `4bd2fae2aecd7c8e6a2bc95f7c5dde012a6db4ac`; it is not the current UI code.
Its equivalent local recovery commit and historical combined counts are recorded
in [historical bounded MVP verification](STATUS.md#historical-bounded-mvp-verification--2026-10-10).
`66329507260e295d42d5aee47b6657cf40f3e5d0` subsequently recorded those acceptance
results with documentation-only changes.

Reuse its unchanged backend evidence: **304 passed, eight Windows-only skips**,
complete offline restore and actual production-browser partial-import/restart
checks. This UI-only series did not change backend, accounting, schemas,
dependencies or product version, and did not rerun those backend checks.
Do not reopen established gates merely because older entries say they were
pending; verify changed behavior under the budgeted-validation rules.

## Two primary journeys

1. **Manual: Market → observation → explicit test.** Saved history reads local
   candles without starting a strategy. Observations retain exact source/range
   and immutable note revisions. Lab handoff preserves that context; Review and
   Start remain separate. Linked reports return to the original revision.
2. **Mass testing: Lab → filter → compare.** Single-card and catalog tests share
   explicit setup and saved comparisons. Numeric thresholds apply to the selected
   comparison; sorting respects compatible cohorts. Names/notes/search, report
   reopening and Back retain research context. Losses, N/A, no-trade and
   unavailable rows remain visible and distinct from execution failures.

Data preparation and later-period freeze/review are supporting routes for these
journeys. Market, Lab and editor profiles remain separate; profile transfer is
explicit. Existing peer navigation, observations, metadata/search/paging and
filters are implemented, not a backlog to rebuild.

Implementation entry points: `frontend/src/App.tsx` owns navigation;
`Observations.tsx` / `ObservationChart.tsx` own local manual research;
`LibraryResearch.tsx` / `SavedComparisonDetails.tsx` own test/comparison context;
`HistoryWorkspace.tsx` owns data preparation/return. Backend contracts remain in
`terminal/observations.py`, `library_batches.py`, `research_evidence.py`,
`displayed_evidence.py` and `archives.py`. Inspect the relevant tests and ADR
before changing a surface; do not move financial calculations into the UI.

## Prioritized continuation

1. Preserve the separate candidate branch and its documentation; do not repeat
   the completed financial programs or add an arbitrary new strategy family.
2. Owner-led unaided Market→observation→test, Lab→compare→reopen, and later-period
   Data/review/cancel journeys remain distinct acceptance. Correct interpretation
   of market, dates, costs and execution model matters as much as navigation.
3. Current Windows/native startup, lifecycle/Job Objects, pickers, transport and
   scaling remain deferred, as do actual live-feed/reconnect checks. Existing
   Linux/browser evidence must not be relabelled as native acceptance.
4. The conditional M1 detail probe is blocked by its incomplete required prefix.
   No untouched/future holdout is established and no candidate was promoted.
   Do not shorten history, fabricate inputs, bypass denied acquisition or launch
   a future study solely to mark this conditional row complete.
5. Further feature development follows owner priorities or an evidenced defect.
   Main integration, release, packaging and deployment remain separate decisions.

## Capability limits to preserve

- Linux research supports graph tests and saved reports; native Python execution,
  Windows notifications/sound and protected Telegram storage are unavailable.
- Archive-wide imports remain sequential and non-atomic, with durable receipts,
  explicit checksum-bound same-operation continuation and atomic per-run
  publication. Background status/cancel and bounded responsiveness have measured
  evidence. Cancel does not undo records; automatic retry/resume and rollback
  are not promised.
  Inspection/ordinary report opening does not verify artifact files.
- Research admission/freeze/display evidence is bounded. It does not prove human
  reading or complete legacy/imported, live/replay or outside-app exposure.
- Funding gaps are conservatively refused; unsupported linear-to-spot benchmark
  substitutions remain N/A. Immutable reports and historical accounting stay
  unchanged. Technical integration is not profitability evidence.
- The native Linux window, current Windows candidate and owner usability are
  not accepted by the Linux/browser pass. No real exchange orders are supported.
