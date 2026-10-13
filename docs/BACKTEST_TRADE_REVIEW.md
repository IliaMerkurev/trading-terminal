# Backtest trade review: bounded acceptance

Status: implemented. Focused automated checks, production-browser synthetic
acceptance and private test-archive readback passed.
Product remains 0.6-dev on the authorized codex/terminal-mvp development branch.

## Outcome and existing foundation

Extend the existing saved Results workflow so selecting a trade shows its saved
outcome and costs beside chart navigation to its actual entry, exit and available
lifecycle fills. Existing entry-row navigation, verified paged chart reads,
recorded indicators, immutable run manifests and managed-position lifecycle
records are reused. This is a usability increment, not another results engine.

## Required behavior

- Keep one visible selected trade, with keyboard selection and previous/next
  review on the loaded page. Selection must never silently follow an obsolete
  run/page response. Clearly distinguish first entry, final exit and full-position
  statistics for multiple entries and partial reductions.
- Present saved gross PnL, fees, signed funding and net PnL without recalculating
  accounting or subtracting slippage twice. Preserve individual fill quantities,
  prices, times, fees and reasons. Lifecycle events are not all execution fills.
- Entry, exit and eligible lifecycle-fill controls navigate the existing bounded
  chart. Fill time remains distinct from source-candle close/marker time and
  recorded signal availability. Missing history and targets remain explicit.
- Show only original immutable strategy/condition context or recorded values.
  Do not claim a fill-to-condition causal link that was not archived. Explain
  absent per-fill signal evidence and native/imported/legacy limitations rather
  than replaying current settings or inventing an explanation.
- Preserve existing run data, execution semantics, cost basis, DCA and partial
  trade grouping, chart-read cancellation and latest-request ownership.

## Exclusions

No new execution model, strategy timeframe, provider acquisition, live/PAPER
operation, trading, external notification, dataset/schema migration, merge,
release or product-version change. Do not add a detailed condition debugger.
Existing source timeframe and saved availability clocks remain authoritative.

## Acceptance and preservation

Inspect current implementation and immutable schemas first. Obtain independent
semantic review, then run focused new and nearest-regression checks, TypeScript
and production build. Exercise actual own-cloud production UI using isolated,
clearly synthetic data, including repeated selection, switching, cancellation,
reload, missing/imported history and fill navigation. Capture a readable final
screenshot. Browser evidence does not establish Windows/native, live providers,
authentic old databases, full-product regression or owner acceptance.

New/changed tests are retained in a version-bound private Drive archive, outside
Git at the owner's request. The archive must contain the base patch, complete test
files, hashes, exact commands/results and reapplication instructions. Preserve
existing published tests unchanged. Verify tested runtime hashes against the
final source and independently read back both the Drive archive and Git tree.
An ordinary checkout or CI does not include external test changes automatically.

Each coherent milestone is committed, published without force against the exact
remote parent, and remotely read back. Any save/publication failure stops further
implementation and validation until saving is repaired. Completion requires
accepted bounded behavior, verified publication and verified external-test archive,
or a clearly reported blocker. Later roadmap work remains separate.

## Implementation contract

`result_page` accepts optional Boolean `review` only for trade pages. Omission
retains the ordinary saved-row representation. The additive transport view gives
exact nanoseconds as strings, UTC with nine fractional digits, source OPEN/CLOSE,
source interval and the last whole second available by each event. Python integer
arithmetic assigns a close-minus-one-nanosecond fill to the preceding candle; an
exact opening fill belongs to the new candle. No saved artifact is rewritten.

The existing 512 KiB row/page budget includes metadata. A lifecycle whose metadata
alone exceeds the single-row limit remains readable as its complete original row
with an explicit clock-unavailable notice. No events are omitted; unsupported
exact targets are disabled. Pages use actual returned next cursors, retaining the
visited starts for Previous navigation across tab changes. Late report/page/read
responses cannot replace the currently selected owner.

The inspector shows saved decimal strings and synchronizes the existing managed
position lifecycle with table selection. First entry and final exit remain
individual fills, including their individual quantities; they are not weighted
whole-position prices. Entry, scale, reduction and exit can navigate; funding,
stop changes and rejected actions are not relabeled as fills. Repeated explicit
Show actions reveal the selected candle even after manual panning. Settled failed
or cancelled same-target reads can be requested again; unresolved cancellation
continues to require inspection.

Original definitions and simulation settings come only from `run_manifest`. The
chart can display the last recorded evaluation within the loaded page whose
recorded availability is no later than the exact fill. This is conservatively
limited context, never a causal join or a reconstructed explanation. In particular,
a close-minus-one-nanosecond fill does not receive the next second's evaluation.
Unknown/null, false and unavailable remain distinct. Frozen backtests archive
actionable hit/condition/state outputs, but not underlying leaf numerics or
agreement member votes. Native signal outputs can be absent. Legacy/imported
records and missing candles retain explicit unsupported/missing states.

No new dependency, schema migration, financial calculation, simulation rule or
provider/market/notification operation is introduced.

## Focused implementation verification

The first integrated pass establishes 50 distinct backend checks: 26 independent
external trade-review checks and 24 nearest existing position-management, worker,
archive and nanosecond-chart regressions. The eight-file frontend pass passed 54
tests, including 21 new external review/chart checks. TypeScript and production
build passed; the pre-existing bundle-size advisory remains. These are focused
checks, not a full-product or native Windows acceptance claim.

Independent review identified byte-shortened Previous paging, metadata-only
single-row overflow, and repeated same-candle navigation after manual panning.
Corrections retain actual cursor history across tab changes, preserve complete
undecorated oversized lifecycle rows with an explicit notice, and treat each
explicit focus request as viewport navigation. Delayed report selection, including
stale failures, is fenced independently from the selected trade-page owner.

## Final focused and production-browser acceptance — 2026-10-12

A further external regression established that an obsolete failed report request
cannot replace the newer report or raise a misleading global error. The focused
file passed 12 tests. Real-browser review then found that keyboard selection
scrolled the inspector into view while leaving focus in the table. A small
frontend correction transfers Enter/Space selection into the inspector and Close
back to its originating row, fencing obsolete focus callbacks. Its independent
regression passed in the final 13-test file run (3.49 seconds). Across overlapping
passes, the final evidence is **50 distinct backend and 56 frontend checks**.
TypeScript, including the final external tests, and production build passed.

Actual own-cloud Chromium used the production application, real AppService and
existing worker, with a fresh isolated synthetic workspace and guarded providers,
Arm, PAPER, native execution and notifications. A frozen-rule run completed with
640 source bars and 120 trades, exercising the 1–100 and 101–120 pages. Original
frozen parameters rendered exactly as saved. Review/close, repeated selection,
source clocks and conservative recorded context passed; the next close's
evaluation is correctly excluded from a close-minus-one-nanosecond fill.

A real managed-position run had two entry fills, a partial reduction and final
exit. Independently expected totals matched exactly: gross 50, fees 0.85, funding
−6.6 and net 42.55 USDT. Entry/scale/reduction/final-exit controls targeted their
actual source candles; funding remained labeled as a non-fill. The existing
archive export/import produced a candle-free copy: saved costs/fills remained
readable, missing raw history was explicit, and no nearby candle was substituted.

A briefly held owned reader, with automatic resume protection, exercised actual
Cancel/Retry and switching reports before an obsolete read completed. No old data
leaked into the new owner. Normal 1737×814 and narrow effective 868×407 layouts
kept controls reachable without horizontal card overflow; 200% browser zoom was
restored afterwards. Reload/reopen preserved the report. The final production
build recheck confirmed Enter/Space → inspector, Tab → review action and Close →
exact originating row, plus the explicit within-loaded-page navigation note.
All three report hashes stayed unchanged. Task-owned host/tab cleanup was verified
separately. No new provider, trading, notification or native execution was used.

Browser evidence is distinct from component mocks. This does not establish
Windows/native, live-provider, full-product, authentic old-database or independent
owner acceptance. Initial fixture funding metadata was corrected after visible
admission refusal; no application admission rule or financial expectation changed.

## External regression archive and reproduction

New files `frontend/src/TradeReview.test.tsx`,
`frontend/src/TradeReviewChart.test.tsx` and `tests/test_trade_review.py` are retained
only in the owner's private Drive archive. Existing published test files are
unchanged. No repository history is rewritten. The stated acceptance counts
require this external patch; checkout/CI does not include it automatically.

Archive: `TradingTerminal_trade_review_tests_2026-10-12_e49e487.zip`.
SHA-256: `11f9d85657543555f93711878481469e139493779139f372d74141fbb52e84b3`.
Size: 47,890 bytes. The six entries contain three complete tests, an additive
patch, manifest and reapplication instructions; no database, raw market data,
credentials or browser state is included. The archive binds source commit
`e49e487caf8fe6f9e01280757e5d67cf3164c500` and tree
`49ddf00e70b6d2c612dacdb226690d2e176143dc`, with 201 runtime file fingerprints.
Downloaded Drive bytes and CRC are independently checked; final documentation-only
publication retains the exact tested runtime map.

In an isolated checkout at that source version, verify the manifest's runtime/test
SHA-256 values. Back up local edits, run `git apply --check` and then `git apply`
against `test-changes.patch`; stop rather than force a mismatch. Verify restored
file hashes before running these commands with the existing pinned environment:

```sh
PYTHONPATH=tests .venv/bin/python -m unittest -v tests.test_trade_review
PYTHONPATH=tests .venv/bin/python -m unittest -v tests.test_position_management tests.test_jobs tests.test_archives.ArchiveTests.test_roundtrip_preserves_metrics_but_never_bundles_history_or_overwrites_runs tests.test_chart_reads.ChartReadTests.test_run_chart_preserves_nanoseconds_availability_equity_and_unavailable_history
node node_modules/vitest/vitest.mjs run frontend/src/TradeReview.test.tsx frontend/src/TradeReviewChart.test.tsx frontend/src/App.test.tsx frontend/src/SavedReview.test.tsx frontend/src/RunChartRequests.test.tsx frontend/src/RunChart.test.ts frontend/src/PositionLifecycle.test.tsx frontend/src/DisplayedEvidence.test.tsx
node node_modules/typescript/bin/tsc --noEmit
node scripts/frontend.mjs build
```

The new backend file was measured outside the checkout under module
`test_trade_review`; after applying the patch its equivalent module path is
`tests.test_trade_review`. Final frontend evidence combines the initial 54-test
pass with two added regressions verified in the final 13-test file; unchanged
overlap is counted once. The manifest records exact commands, durations, results
and reuse limits. Workspace/database backup remains a separate responsibility.
