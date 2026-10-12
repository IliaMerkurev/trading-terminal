# Saved rule to strategy: bounded acceptance plan

Status: backend and frontend implemented; focused automated verification and
production-browser synthetic acceptance passed. Independent review corrected
the recorded-source admission boundary. Product remains 0.6-dev on
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

## Using the first slice

1. In Market, open Local alerts and select a saved rule. Choose Create strategy
   from rule, enter a distinct strategy name and choose the entry direction.
2. Preview, inspect the complete frozen source and simulation defaults, then
   explicitly confirm creation. Cancel before creation does not save anything.
3. The saved strategy opens in the existing Pro editor. Select its frozen node
   to inspect original parameters/provenance. Add ordinary exit conditions and
   adjust stop/take, capital, allocation, fees and slippage as needed. Save edits.
4. Choose prepared native M1 history for the same market and instrument, with
   its start exactly equal to the displayed frozen origin. The selected dataset
   needs matching recorded Bybit REST provenance or explicit synthetic attribution.
   Current-chart data and imported source labels are not silently substituted.
5. Run the ordinary immutable backtest and inspect its results/trades. Conversion
   itself never starts a run. Existing simulations retain their original contract.

If creation loses its response, use Reconcile strategy creation. A read-only
receipt opens the already saved strategy. An absent receipt permits only an
explicit retry of the retained identity and exact content. Reload does not
automatically resubmit creation or navigate away from current work. A name
collision or stale/deleted rule requires another reviewed preview.

To change frozen indicator parameters, edit/rebind the original alert as usual
and create a new strategy. Saved strategies remain independent if that alert is
later edited, archived or deleted. Whole-strategy copies retain their own frozen
snapshot; ordinary nodes, output connections and simulation settings are editable.

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

The integrated follow-on pass ran 60 backend tests in 32.258 seconds, including
archive export/import preserving exact snapshot bytes and nullable diagnostics,
actual frozen-worker cancellation, experiments, storage resilience and signals.
There are now 109 distinct passing backend checks across the focused runs;
overlapping tests are counted once. The integrated frontend pass ran 81 tests
across seven files in 5.62 seconds, adding project-transfer regression coverage.
No commit status or PR-triggered workflow run was reported for the implementation
checkpoint; local test evidence is not a claim that remote CI ran.

Reproduction commands (existing pinned environment, after applying the external
regression-test archive described below):

```sh
PYTHONPATH=tests .venv/bin/python -m unittest tests.test_rule_strategy tests.test_graph tests.test_jobs tests.test_indicator_alerts tests.test_agreement_alert_history
PYTHONPATH=tests .venv/bin/python -m unittest tests.test_rule_strategy tests.test_archives tests.test_experiments tests.test_indicator_alert_store tests.test_storage_resilience tests.test_signals
node node_modules/vitest/vitest.mjs run frontend/src/RuleStrategyConversion.test.tsx frontend/src/FrozenRule.test.tsx frontend/src/editor.test.ts frontend/src/GraphEditor.test.tsx frontend/src/IndicatorAlerts.test.tsx frontend/src/App.test.tsx frontend/src/ProjectTransfer.test.tsx frontend/src/DisplayedEvidence.test.tsx
node node_modules/typescript/bin/tsc --noEmit
node scripts/frontend.mjs build
```

## Production browser acceptance — 2026-10-12

The actual own-cloud Chromium opened the production application with the real
BrowserServer, AppService and graph worker on an isolated local origin/database.
The prepared data were explicitly synthetic: 160 contiguous M1 candles with
SMA(2), ROC(1) and CMF(1). Providers, Arm, PAPER, native execution and external
notifications were guarded; none was attempted. No user computer was used.

Actual UI checks passed: cancelling preserves alert/editor drafts and creates
nothing; double confirmation creates one receipt/strategy and starts no run;
conversion from focused Market opens the normal Pro editor; exact source JSON
is read-only; risk/allocation/cost edits persist. Case-insensitive name collision
and unsupported OKX refuse visibly without overwriting existing data. An
agreement rule previews and converts with exact weights/contracts. The modal
fits 1736×813 and 791×713 viewports; Confirm and Cancel remain reachable.

Rebinding the original SMA rule from threshold 10 to 11 and revision 1 to 2 did
not alter the converted strategy's original threshold/hash. Reload retained
the frozen source and edited settings. An explicitly started ordinary backtest
completed through the real worker: all 160 recorded entry flags exactly matched
the original frozen replay, with 30 actionable hits and 30 completed trades.
The saved ordinary graph remained unchanged. This is functional synthetic
evidence, not a profitability claim. Agreement worker parity is automated
evidence; the browser-triggered worker run used the numeric SMA rule.

Browser review also prompted a readable UTC origin alongside exact Unix seconds.
It exposed a pre-existing Results bug: metrics and chart used identical sibling
React keys, duplicating metric groups on rerenders. A focused test reproduced
three groups instead of one; distinct keys correct it without changing result
data. Final focused UI verification passed 91 tests across eight files in
5.53 seconds, plus TypeScript and production build. The existing bundle-size
advisory remains. The corrected production build was rechecked in the actual
browser: UTC plus unchanged Unix origin are visible, and exactly one metrics
group remains after reload and three different trade selections. The original
immutable result and isolated synthetic database were preserved.

Async close/source-switch timing, stale/deleted rules, lost-response recovery,
archive round-trip and actual worker cancellation were covered by automated
checks rather than manually forced browser failures. No full historical suite,
Windows/native, live provider, old-owner-database or owner acceptance is claimed.

## Final regression archive and repository boundary

At the owner's request, the final additions to `frontend/src/App.test.tsx`,
`frontend/src/FrozenRule.test.tsx` and `tests/test_rule_strategy.py` are stored
in a private Drive archive rather than the final Git payload. Existing tracked
tests remain at their already-published implementation versions; no previously
published test is removed and no repository history is rewritten. The recorded
109/91 acceptance counts include this external patch. Repository CI does not
automatically include it, and those counts are not a claim about an unpatched
checkout. Application runtime code is identical to the tested runtime.

Archive: `TradingTerminal_rule_strategy_acceptance_2026-10-12_24097d2.zip`.
SHA-256: `be209960d0c82ece27ced6f3c54ea430fa448231c693d4d2fa3782f4802c319a`.
The archive contains the three full test files, their incremental patch, a
manifest with base/tested Git object IDs and SHA-256 fingerprints, runtime source
maps, exact commands, evidence/limits and reapplication instructions. It contains
no database, raw market data or credentials. Its base is the published
`57a94568c37af2bbf28a8c6b3e0c215afa485381` implementation.

In an isolated checkout, verify the runtime source map against the manifest,
back up local test edits, then run `git apply --check` followed by `git apply`
against the extracted `test-changes.patch`. Stop on a mismatch rather than force
the patch. Verify each restored file's SHA-256 before running the commands above.
Full workspace backups remain necessary; strategy archives are not substitutes
for the alert journal and research records.
