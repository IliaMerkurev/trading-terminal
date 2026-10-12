# Current implementation status

Updated 2026-10-12. This is a concise current-state summary, not a chronological
work log. [PROJECT.md](../PROJECT.md) remains the product specification. Detailed
contracts, reproducible checks and qualifications live in the linked documents.

## Product and release boundary

- Product remains **0.6-dev** on `codex/terminal-mvp`; it is a development build,
  not an owner-accepted release. No merge, version bump or deployment is included.
- Historical accepted baselines remain in Git. The current extension preserves
  existing versioned simulation contracts and immutable saved results.
- The application is a local strategy-research workspace. Example rules and
  synthetic results are test cases, not recommendations or profitability claims.
- The project uses MIT; component licenses, formula-file exceptions and market
  data terms remain separate. See [third-party notices](../THIRD_PARTY_NOTICES.md).

## Available workflow

The application retains the card-first strategy Lab and Pro graph editor,
prepared local history, managed cancellable backtests, saved reports and trade
navigation, comparison tools and bounded project archives. Market has display
indicators, compatible panes, named presets, local alerts, current agreement and
cache-only historical rule research. These capabilities have different evidence
boundaries; availability is not a claim of Windows, provider or owner acceptance.

The recovered pane/alert/agreement/history scope is recorded in
[RECOVERY.md](RECOVERY.md) and the [88-row acceptance ledger](RECOVERY_ACCEPTANCE.md).
Recovery reconstructed documented behavior; it does not establish byte identity
with unavailable former source or compatibility with unavailable old databases.

## Latest bounded slice: saved rule to strategy

A saved indicator rule now offers an explicit preview/review/create action.
Confirmation saves an independent graph strategy and opens the normal editor.
Conversion itself does not start a run, acquire market data, arm an alert or
perform a PAPER/order/notification action.

One immutable frozen-rule node retains the original definition, normalized
parameters, formula and agreement-weight contracts, native source context,
calculation origin, rule identity/revisions and definition hash. Backtests reuse
the existing frozen replay engine's actionable close hits. Unknown truth, state
edges, pulses, ALL/ANY and confirmed divergence timing are not approximated by
ordinary graph indicators. Editing, archiving or deleting the original alert
does not rewrite a previously saved strategy or immutable result.

Direction must be selected explicitly. Review shows initial allocation, capital,
fees, slippage and execution settings; no exit, stop or take-profit is invented.
Ordinary exit nodes, output connections and simulation settings remain editable.
To change frozen parameters, edit/rebind the source rule and convert it again.
Durable request identities support read-only reconciliation and explicit safe
retry; repeat clicks, stale previews and name collisions do not overwrite data.

### Execution limits

- Matching Bybit source, market and instrument; native M1, closed primary bars,
  M1 execution, contiguous full-origin data and reject-on-gap policy.
- At most 10,000 bars and the existing estimated 256 MiB replay-memory budget.
  This is a modeled admission bound, not a measured total-process peak guarantee.
- Data must retain matching recorded Bybit REST request/hash/close-clock evidence,
  or explicit synthetic attribution. Recorded provenance is not independent
  authentication of a provider response; synthetic evidence stays synthetic.
- Other source/timeframe/origin/profile combinations, uncertain provenance,
  reseeding, parameter experiments, research windows and live/PAPER execution
  refuse visibly. No aggregation, truncation or provider fallback is substituted.

See [the complete conversion acceptance record](RULE_STRATEGY_CONVERSION.md) for
usage, recovery behavior, exact test commands and semantic boundaries.

## Latest verification

For this conversion slice, the tested application plus the separately archived
final regression changes establish **109 distinct backend checks** (overlap
counted once) and a final **91 frontend tests across eight files**. At the owner's
request, the three final test-file changes are retained in a version-bound
private Drive archive rather than this Git checkpoint. Previously published
tests remain unchanged; the archive patch is required to reproduce these exact
counts. See the conversion acceptance record for its checksum and instructions.
TypeScript and the production build passed; the existing bundle-size advisory
remains. Backend evidence includes actual worker completion/cancellation, archive
round-trip, immutable snapshots, repeat/concurrent requests, resource admission,
recorded-source refusal and replay parity. Independent semantic review found a
provenance-context weakness; it was corrected and independently rechecked.

Actual production-browser acceptance used an isolated, explicitly synthetic
workspace and the real application, Service and worker. It verified canceling
the creation review, repeat confirmation, collision and unsupported-source
refusals, preserved drafts,
source-edit isolation, reload, read-only frozen provenance and editable risk/cost
settings. Normal and narrow review dialogs kept Confirm/Cancel reachable.

An explicitly started numeric-rule backtest recorded 160 indicator rows; every
entry flag matched the original frozen replay, with 30 hits and 30 trades.
Agreement conversion was checked in the browser; agreement worker parity is
separate automated evidence. No provider, Arm, PAPER, native execution or external
notification was attempted. Task-owned acceptance services and browser resources
were stopped/closed afterwards; test data were not mixed with existing user data.

The browser pass also prompted readable UTC plus exact Unix origin, and exposed
a pre-existing Results duplicate-key defect. Distinct metrics/chart keys passed
a reproducing regression and real-browser recheck: one metrics group remained
after reload and three trade selections. The saved result remained unchanged.

Historical recovery evidence records 804 backend passes with eight Windows-only
skips (812 discovered), 1,008 frontend passes and a production build. Those are
prior recovery results, **not a fresh full-product run of this conversion slice**.
The recovery ledger retains their exact scope. No commit status or PR workflow
run was reported for the published conversion implementation; local checks do
not imply remote CI ran.

## Remaining acceptance and next step

- Windows/native execution and packaging, live-provider acceptance, old-owner
  database compatibility, full-product regression and independent owner review
  are not established by this focused synthetic acceptance.
- Reconstructed functionality does not recover missing historical application
  data. Preserve the complete workspace database; strategy archives do not
  include alert journal/research records. Synthetic fixtures are separate.
- Broader conversion contexts, experiment support and subsequent trade-chart or
  comparison enhancements are outside this completed first slice.
- Next: owner review of the existing saved-rule review → editor → backtest flow
  within its stated eligibility limits. Any broader scope, merge or release is
  a separate decision. Do not present development evidence as owner acceptance.

## Durable checkpoints and documentation

- [Working conversion implementation](https://github.com/IliaMerkurev/trading-terminal/commit/57a94568c37af2bbf28a8c6b3e0c215afa485381)
- [Conversion acceptance and reproduction](RULE_STRATEGY_CONVERSION.md)
- [Recovery evidence and limitations](RECOVERY_ACCEPTANCE.md)
- [Development and isolated acceptance guide](DEVELOPMENT.md)
- [Alert UI](ALERT_UI.md), [runtime API](ALERT_RUNTIME_API.md),
  [historical research UI](ALERT_RESEARCH_UI.md)
- [Architecture decisions](adr/) and [research contracts](RESEARCH.md)
- [Branch commit history](https://github.com/IliaMerkurev/trading-terminal/commits/codex/terminal-mvp/)

Older status entries remain recoverable from Git history. They are intentionally
not copied into another growing status archive. Future updates should replace
current facts here and link detailed evidence rather than append another log.

## Older anchored references

<a id="combined-ux-series-verification--2026-10-10"></a>
<a id="durable-archive-import-inspection--2026-10-10"></a>
<a id="explicit-chart-to-observation-period-capture--2026-10-10"></a>
<a id="explicit-saved-equity-inspection--2026-10-10"></a>
<a id="final-bounded-ux-candidate-verification--2026-10-10"></a>
<a id="historical-bounded-mvp-verification--2026-10-10"></a>
<a id="independent-saved-history-date-navigation--2026-10-10"></a>
<a id="named-indicator-preset-candidate--2026-10-11"></a>
<a id="natural-lab-catalog-scrolling--2026-10-10"></a>
<a id="saved-comparison-card-ordering--2026-10-10"></a>
<a id="saved-history-display-intervals--2026-10-10"></a>
<a id="saved-history-ohlcv-inspection--2026-10-10"></a>
<a id="saved-test-filter-outcome-clarity--2026-10-10"></a>

Links from earlier checkpoint documents land here so they remain usable. Their
original evidence is retained in the [previously published status snapshot](https://github.com/IliaMerkurev/trading-terminal/blob/57a94568c37af2bbf28a8c6b3e0c215afa485381/docs/STATUS.md).
Use its section headings for the historical verification; the current acceptance
limits and latest checks are stated above.
