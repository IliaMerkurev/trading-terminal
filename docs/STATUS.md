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

The existing Results comparison now reviews 28 saved conditions across Data,
Period, Capital and Costs & execution, separately from outcomes and raw metadata
changes. Each condition is matched, different or unknown with per-run evidence.
Missing currency, venue, execution resolution and actual readiness stay unknown.
No overall equivalence/ranking verdict, rerun, repricing or current-cache lookup
is introduced. Existing Lab batch overlays and comparison names/notes remain.

The recorded graph trace uses two indexed archived endpoints and does not prove
warmup completion or continuous evaluation. Dataset hashes cover full normalized
trade/mark/funding inputs, potentially beyond the evaluation window. Provider
claims are not authenticated. Malformed, unsupported or inconsistent evidence is
unknown. Raw detail is bounded; request cancellation, retry, selection/report
changes and obsolete replies are fenced. See [comparability acceptance](BACKTEST_COMPARABILITY.md).

### Latest verification

Focused checks passed **25 backend** (23 new plus two archive regressions) and
**30 frontend** (11 new plus 19 neighboring checks), TypeScript and production
build. Independent semantic review led to exact bounded decimal comparison and
stricter legacy coverage/type validation. The existing bundle-size advisory remains.

New tests are in an owner-only private Drive archive, with full files, additive
patch, commands/results and 205 runtime hashes tied to implementation `5414820`.
Downloaded bytes/CRC, source/test hashes, privacy and isolated `git apply --check`
passed. Existing Git tests are unchanged; the archive is required for this coverage.

Actual own-cloud production-browser synthetic checks passed matched/different/
unknown, incomplete legacy-shaped evidence, Cancel/retry, repeated-click blocking,
stale selection/report changes and reload. Saved reports persisted; transient
checkbox selection reset normally. Normal 1180px and 150%-zoom 787px layouts kept
controls reachable without body overflow. Ten saved JSON artifacts stayed unchanged;
no comparison started execution, acquisition, trading or notifications. Owned QA
service/tabs were closed, zoom restored, and one real screenshot was captured.

No Windows/native, live-provider, authentic old-owner database/archive, full-product
regression or owner acceptance is established. No CI statuses/workflow runs were
reported for the implementation commit. Final docs retain the tested runtime map.

## Preserved saved trade review

The selected-trade inspector retains exact saved gross PnL, fees, signed funding,
net PnL and managed lifecycle fills. Entry/exit/lifecycle chart targeting preserves
nanosecond source ownership. Original frozen conditions come from immutable
snapshots; context is not causal proof. Missing underlying leaf numerics/member
votes, candle-free imports and oversized legacy clock decoration stay explicit.

Its prior acceptance established 50 backend and 56 frontend checks (requiring its
separate private regression patch), TypeScript/build and production-browser
synthetic lifecycle/clock/cancellation/reload/keyboard checks. These are historical
trade-review evidence, not newly rerun totals. See [trade-review acceptance](BACKTEST_TRADE_REVIEW.md).

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
- Broader signal debugging, conversion contexts and broader comparison enhancements are
  separate work. Missing historical evidence is not a license to reconstruct it
  from current settings or substitute a nearby candle.
- Next: owner review of saved conditions alongside the existing saved-rule →
  editor → backtest → trade-review workflow within its stated limits. No later roadmap slice, merge or release is
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
