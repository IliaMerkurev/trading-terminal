# Backtest trade review: bounded acceptance

Status: implemented; focused verification passed. Production-browser acceptance
and final external-test archive verification remain pending.
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
