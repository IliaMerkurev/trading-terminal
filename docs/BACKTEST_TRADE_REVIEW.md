# Backtest trade review: bounded acceptance

Status: acceptance plan; implementation and verification are pending.
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
