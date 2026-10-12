# Saved rule to strategy: bounded acceptance plan

Status: backend and frontend implemented; focused automated verification passed.
Independent review corrected the recorded-source admission boundary. Actual
production-browser acceptance remains pending. Product remains 0.6-dev on
codex/terminal-mvp.

## Complete outcome

Create strategy from a saved indicator rule opens a review. After explicit
confirmation it saves an independent visual strategy and opens the existing
editor/backtest workflow. Cancel is read-only. Creation never arms an alert,
starts a backtest, acquires provider data, sends a notification or trades.

The graph contains one declarative frozen-rule node. It retains the saved
definition, normalized parameters, formula/weight contracts, source/native
interval, seed origin and rule identity/revisions/hash. The node is immutable;
ordinary graph exits and simulation settings remain editable. An edited source
rule never rewrites an existing strategy or result. Conversion does not lower
display formulas into superficially similar strategy indicators.

The user explicitly selects entry direction. Review discloses that no exit,
stop or take-profit is invented, and shows the initial allocation, capital,
fees, slippage and execution settings before saving. Existing settings remain
editable and visible in the normal strategy editor.

## First execution boundary

One frozen node consumes exact per-close hit values from the existing frozen
replay engine. Nullable condition truth remains separate from an actionable
hit. State edges, pulse timing, ALL/ANY, agreement weights and confirmed
divergence timing retain their existing contract; no extra edge detector or
alternative formula engine is introduced.

The first slice admits only matching Bybit M1 context, closed primary bars,
M1 execution and contiguous full-origin data within the existing 10,000-bar
and estimated 256 MiB replay limits. Data provenance must be checked and shown;
synthetic tests remain explicitly synthetic. Unsupported source, interval,
origin, coverage, profile or contract fails visibly before execution. Parameter
experiments, live/PAPER and research-window reseeding are excluded. There is no
silent aggregation, truncation, rebinding, approximation or provider fallback.

## Acceptance evidence required

- Preview/create revision and definition-hash fences; deleted/archived rules
  and stale previews cannot create a misleading draft.
- Atomic idempotent creation and durable read-only request reconciliation;
  repeated clicks, lost responses, reloads and name collisions preserve data.
- Source edits after conversion do not mutate frozen provenance or results.
- Exact replay-hit parity, unknown/first-known/state/pulse/ALL/ANY semantics,
  equality crossing, confirmed divergence and agreement evidence; perturbing
  future input cannot alter earlier signals.
- Missing origin, gaps, wrong context, wrong profile, missing schedule,
  duplicate/skipped clocks and unsupported execution routes fail closed.
- Existing graph editing, save/load, immutable backtest and trade/report flows
  remain usable; no alert Arm, provider, PAPER or notification commands run.
- Focused backend/frontend tests, TypeScript/build, independent semantic review
  and actual production-browser synthetic acceptance. Windows/native, live
  providers and owner acceptance remain separate, unclaimed checks.

Every small finished milestone must have a local commit and verified remote
publication. A commit/publication failure pauses implementation until restored.
Only reviewed, secret-scanned source, synthetic tests and technical documents
are published; private workspaces, databases and market datasets are excluded.

## Implemented checkpoint evidence — 2026-10-12

The backend stores one canonical, immutable `frozen_rule` node and an atomic
creation receipt. The existing replay engine prepares its single-use full-origin
hit schedule; ordinary graph exits and simulation costs remain editable. A saved
source node cannot be replaced or removed by saving over that strategy. The UI
provides explicit direction/preview/review/create and retains exact pending
request identities for read-only reconciliation across reloads.

Recorded Bybit admission requires matching kline category/symbol/M1 interval,
requested origin/end, a response hash, and retrieval/provider clocks after the
last close. This validates recorded matching REST provenance, not independent
authentication of the historical response. Explicit test fixtures require
synthetic metadata and source attribution and remain labeled synthetic.

Focused backend evidence: the first 16-test pass had two test-harness errors
(the Service response key and the store trash-method name). Correcting those
selectors, the combined new-feature/graph/jobs/core/agreement run passed 65 tests
in 10.054 seconds. A later focused 20-test run passed in 1.911 seconds after the
independent provenance finding was corrected and four boundary cases added.
Together these establish 69 distinct passing checks, not 85 independent checks.
They include actual worker backtest/trades, linear short simulation, confirmed
divergence timing, exact agreement hits, future independence, physical memory
admission, atomic rollback, concurrent repeated creation and immutable snapshots.

Frontend evidence: 77 tests across conversion, frozen source, editor, GraphEditor,
IndicatorAlerts and App passed. TypeScript and production build passed; the
existing large-bundle advisory remains. Component mocks are not browser evidence.
No provider/PAPER/order/external-notification operation was used for acceptance.
Windows/native, live providers, owner acceptance and full-product regression
are not established by this focused checkpoint.
