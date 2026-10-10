# Current engineering checkpoint

Updated 2026-10-10. Working branch: `codex/terminal-mvp`; product remains
`0.6.0-dev`. This is a browser-verified development candidate, not a packaged
release or owner-accepted final UX. [PROJECT.md](../PROJECT.md) remains the
product specification; [STATUS.md](STATUS.md) owns detailed test evidence.

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

1. Continue from the verified UX series rather than rebuilding its controls.
   Inspect both connected journeys in the built browser at ordinary and narrow
   widths, using existing synthetic work where possible. Identify a concrete
   remaining usability gap before editing; do not restart a general redesign.
2. Address one evidenced friction point per small slice: clear next action,
   retained source/selection/return context, result readability, scrolling,
   keyboard focus and dialog dismissal. Verify the changed surface and nearest
   regression risk. Record actual outcomes and limits in STATUS before the next
   milestone checkpoint on `codex/terminal-mvp`.
3. Finish owner-led unaided usability acceptance of both journeys and the
   supporting later-period Data/review/cancel route. Earlier layout direction
   approval and automated/browser checks do not establish this acceptance.
4. Keep Windows/native acceptance separate: installed source/build identity,
   startup diagnostics, file pickers, lifecycle/Job Objects and 100/125/150%
   scaling. Current live-feed/reconnect and actual native notification behavior
   also require their own evidence; offline history cannot establish them.

No new strategies before the two journeys are UX-ready. Broader strategy
research, new venues, universal exposure tracking, richer journals, benchmark
warmup efficiency, packaging and release work are outside this UX continuation.
No new product/schema/dependency version is implied by an internal milestone.

## Capability limits to preserve

- Linux research supports graph tests and saved reports; native Python execution,
  Windows notifications/sound and protected Telegram storage are unavailable.
- Archive-wide imports remain sequential and non-atomic, with durable status-only
  receipts and atomic per-run publication. Cancel does not undo records. No
  automatic retry/resume, rollback or in-flight responsiveness is promised.
  Inspection/ordinary report opening does not verify artifact files.
- Research admission/freeze/display evidence is bounded. It does not prove human
  reading or complete legacy/imported, live/replay or outside-app exposure.
- Funding gaps are conservatively refused; unsupported linear-to-spot benchmark
  substitutions remain N/A. Immutable reports and historical accounting stay
  unchanged. Technical integration is not profitability evidence.
- The native Linux window, current Windows candidate and owner usability are
  not accepted by the Linux/browser pass. No real exchange orders are supported.
