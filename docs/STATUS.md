# Current implementation status

Updated 2026-10-12. This is a concise current-state summary, not a chronological
work log. [PROJECT.md](../PROJECT.md) remains the product specification. Detailed
contracts, reproducible checks and qualifications live in the linked documents.

## Product and release boundary

- Product remains **0.6-dev** on `codex/terminal-mvp`; it is a development build,
  not an owner-accepted release. No merge, version bump or deployment is included.
- Historical accepted baselines remain in Git. Current work preserves versioned
  simulation contracts, existing tests and immutable saved results.
- The application is a local strategy-research workspace. Example rules and
  synthetic results are test cases, not recommendations or profitability claims.
- The project uses MIT; component licenses, formula-file exceptions and market
  data terms remain separate. See [third-party notices](../THIRD_PARTY_NOTICES.md).

## Available workflow

The card-first Lab and Pro editor retain local history, cancellable backtests,
saved reports/trade review, comparisons and project archives. Market retains
display indicators/panes/presets, local alerts, current agreement and cache-only
rule research. Capability availability does not establish platform acceptance.

Recovered pane/alert/agreement/history scope is recorded in
[RECOVERY.md](RECOVERY.md) and the [88-row acceptance ledger](RECOVERY_ACCEPTANCE.md).
Recovery reconstructed documented behavior; it does not establish byte identity
with unavailable former source or compatibility with unavailable old databases.

## Current bounded slice: saved comparison conditions

The Results comparison now has condition-specific matched/different/unknown
evidence, separate from outcomes and raw metadata differences. Missing currency,
venue, execution resolution and actual readiness remain unknown. Saved content
fingerprints and coverage do not authenticate providers or current cache.
Cancellation, retry, selection/report changes and obsolete replies are fenced.

Focused checks establish 25 backend and 30 frontend passes, TypeScript and build.
The new 23-backend/11-frontend tests are external to Git; final private archive and
actual-browser acceptance remain pending. See [comparability acceptance](BACKTEST_COMPARABILITY.md).

## Preserved bounded slice: saved trade review

Selecting a saved trade opens one inspector beside the existing recorded chart.
It shows exact saved gross PnL, fees, signed funding and net PnL; first-entry and
final-exit prices, quantities, reasons and exact UTC execution times remain
individual fills. Managed positions retain original entries, DCA/scales, partial
reductions, funding and other lifecycle events. Selection synchronizes the
lifecycle instead of displaying another position independently.

Entry, exit and lifecycle fills navigate the existing chart. Server-derived
integer clocks preserve close-minus-one-nanosecond candle ownership before JSON
transport. Fill, candle-close and evaluation clocks remain distinct. Repeated Show
reveals the target after panning; settled failed/cancelled reads can be retried.
Keyboard focus, within-page trade navigation and actual byte-shortened cursors
are supported. Visited page starts survive tab changes; stale responses are fenced.

Original conditions and execution settings come only from the immutable run
manifest. Optional chart context shows the last archived evaluation within the
loaded window available no later than the selected fill. This is context, not
proof of causation. No signals, indicator values or accounting are recalculated.
Frozen backtests do not archive underlying leaf numerics or agreement member
votes; missing per-fill evidence is disclosed. Unknown/null, false and absent
values remain distinct. Native signal outputs and legacy lifecycles can be absent.

Imported/candle-free reports retain saved fills and costs with an explicit missing
history state. A lifecycle too large for additive clock metadata remains readable
as the complete original row; its unsupported exact targets are disabled, without
truncating events. No execution engine, provider, timeframe, dependency or schema
change is introduced. See [trade-review acceptance](BACKTEST_TRADE_REVIEW.md).

## Latest verification

Trade review establishes **50 distinct backend checks** (26 new independent plus
24 nearest regressions) and **56 distinct frontend checks** (overlap counted once).
They cover exact M1/H1/D1 clocks, independently expected long/short average-cost
lifecycles, partial-fill fee/funding attribution, unchanged SQLite/artifact bytes,
metadata-inclusive byte budgets, actual worker/archive regressions, stale owners,
keyboard navigation, cancellation, retry and conservative recorded-value context.
TypeScript and production build passed; the existing bundle-size advisory remains.

The three new tests are in a private version-bound Drive archive; existing Git
tests are unchanged. These counts require its patch and are not a claim about
unpatched checkout/CI. The archive binds source/test hashes, base patch, commands,
outcomes and reapplication instructions. Final runtime and downloaded archive
bytes are checked separately from Git publication.

Actual production-browser checks used isolated synthetic data and the real
Service/worker: a 640-bar frozen-rule run produced 120 trades; a managed position
matched independently expected gross 50, fees 0.85, funding −6.6 and net 42.55 USDT.
Entry/scale/reduction/exit navigation, candle-free imported review, cancellation,
late-reader/run isolation, reload and normal/narrow layout passed. Enter/Space now
focuses the inspector; Close restores the original row. Original snapshots and
all three saved report hashes remained unchanged. Owned QA services/tabs were closed; existing resources were preserved.

These are focused synthetic checks. Prior conversion evidence reports 109 backend
and 91 frontend checks (requiring its separate external patch), build and actual
browser/worker acceptance: 160 recorded rows matched original replay, with 30 hits
and trades. See [conversion acceptance](RULE_STRATEGY_CONVERSION.md).

Historical recovery recorded 804 backend passes, eight Windows-only skips and
1,008 frontend passes. Neither earlier count is a fresh trade-review/full-product
run. No status or workflow run was reported for the implementation checkpoint;
local checks do not imply remote CI ran.

## Preserved saved-rule conversion

An explicitly reviewed saved rule becomes an independent editable graph strategy.
Its frozen node retains original definition, formula/weight contracts, parameters,
context, origin, identity/revisions and hash. Ordinary outputs, exits and risk/cost
settings remain editable. Conversion starts no run or external operation.

First-slice execution requires matching Bybit source/market/instrument, native M1,
closed primary bars, M1 execution, contiguous full-origin reject-on-gap data and
matching recorded provenance or explicit synthetic attribution. The 10,000-bar
and estimated 256 MiB bounds are admission limits, not measured process peaks.
Other contexts, uncertain provenance, reseeding, experiments and live/PAPER refuse
visibly. Durable identities support read-only lost-response recovery. The linked
conversion acceptance record retains complete usage, limits and evidence.

## Remaining acceptance and preservation

- Windows/native execution and packaging, live providers, authentic old-owner
  database compatibility, full-product regression and independent owner review
  remain unestablished by this bounded synthetic acceptance.
- Reconstructed functionality does not recover missing application data. Preserve
  the complete workspace database: strategy archives omit alert journal and
  research records, and regression archives contain no application data.
- Broader signal debugging, conversion contexts and comparison enhancements are
  separate work. Missing historical evidence is not a license to reconstruct it
  from current settings or substitute a nearby candle.
- Next: owner review of the existing saved-rule → editor → backtest → trade-review
  workflow within its stated limits. No later roadmap slice, merge or release is
  implied by these development checkpoints.

## Durable checkpoints and documentation

- [Trade-review implementation](https://github.com/IliaMerkurev/trading-terminal/commit/9c64e945de5c33e7eb92f6a2b640be719d332509)
- [Trade-review acceptance and reproduction](BACKTEST_TRADE_REVIEW.md)
- [Saved-rule conversion and reproduction](RULE_STRATEGY_CONVERSION.md)
- [Recovery evidence and limitations](RECOVERY_ACCEPTANCE.md)
- [Development and isolated acceptance guide](DEVELOPMENT.md)
- [Alert UI](ALERT_UI.md), [runtime API](ALERT_RUNTIME_API.md),
  [historical research UI](ALERT_RESEARCH_UI.md)
- [Architecture decisions](adr/) and [research contracts](RESEARCH.md)
- [Branch commit history](https://github.com/IliaMerkurev/trading-terminal/commits/codex/terminal-mvp/)

Older status entries remain recoverable from Git history. Do not create another
growing status archive. Replace current facts here and link detailed evidence.

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
