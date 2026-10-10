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

## Current UX-series evidence

The newest slice adds explicit saved-comparison card ordering in Lab. Name,
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
- Archive imports are sequential and non-atomic. Partial failure discloses known
  IDs/statuses; cancel does not undo records. No automatic retry/resume, rollback
  or durable receipt is promised for an unknown final response.
- Research admission/freeze/display evidence is bounded. It does not prove human
  reading or complete legacy/imported, live/replay or outside-app exposure.
- Funding gaps are conservatively refused; unsupported linear-to-spot benchmark
  substitutions remain N/A. Immutable reports and historical accounting stay
  unchanged. Technical integration is not profitability evidence.
- The native Linux window, current Windows candidate and owner usability are
  not accepted by the Linux/browser pass. No real exchange orders are supported.
