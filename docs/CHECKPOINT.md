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

## Functional evidence baseline

The final tested code is `bc10a4cef57530fb843437678bd852c7e04aa7d1`, tree
`4bd2fae2aecd7c8e6a2bc95f7c5dde012a6db4ac`. The equivalent local recovery commit
and actual combined counts are recorded in [final bounded MVP verification](STATUS.md#final-bounded-mvp-verification--2026-10-10).
`66329507260e295d42d5aee47b6657cf40f3e5d0` subsequently recorded the final
acceptance evidence with documentation-only changes. This checkpoint also changes
only documentation; it does not claim a new build or another regression run.

The combined Linux/backend/frontend pass, complete offline restore and actual
production-browser partial-import/restart checks are already recorded. Do not
reopen those gates merely because older milestone entries say they were pending.
Reuse valid evidence for unchanged behavior; functional changes need focused new
evidence and a later combined candidate check under the budgeted validation rules.

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

1. Inspect both connected journeys in the built browser at ordinary and narrow
   widths, using existing synthetic work where possible. Identify a concrete
   usability gap before editing; do not restart a general redesign.
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
