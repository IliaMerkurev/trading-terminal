# Current implementation status

Updated 2026-10-13. This is a concise current-state summary, not a chronological
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

## Current bounded slice: compatible custom-backtest history

Custom history choices now share Lab's market/instrument/execution-resolution
checks, with disabled mismatches and visible reasons. Counts are stored bars,
with native timeframe, source and actual UTC coverage; missing metadata remains
unknown. Profile/list changes revalidate selection, stale refreshes cannot erase
newer choices, and unavailable observation sources block Lab review/start.
Data estimates are labeled total requested candles before local reuse.

Focused frontend and backend regression, TypeScript and production build were
checked. Existing published tests stay unchanged; private asynchronous timing
corrections and added regression tests are in the version-linked archive.
Actual GUI/native acceptance remains unestablished. See the [history selection
contract and verification limits](BACKTEST_HISTORY.md).

## Preserved safe strategy draft replacement

The editor now uses a shared Save/Discard/Cancel guard for saved Open, New, Copy,
Lab customization, experiment copies, imports and converted-rule opening. Draft
fields and Undo/Redo survive cancellation and failed loading/saving. Synchronous
revision, replacement-generation and intent checks prevent late work from
replacing newer edits. Pending/uncertain saves conservatively invalidate the old
saved baseline. Created conversion receipts remain reopenable.

Focused verification passed 80 frontend checks across 8 files, TypeScript and
production build. Existing published tests are unchanged; added tests belong to
the private version-linked archive. Actual own-cloud GUI/screenshot acceptance
is blocked by a current loopback connection refusal. No full suite, Windows or
owner acceptance is claimed. See [workflow and limits](STRATEGY_DRAFTS.md).

## Preserved latest daily BTC sentiment

Market now includes a small collapsible Fear & Greed semicircle with a latest
BTC/daily label, exact UTC source date and adjacent Alternative.me attribution.
A separate bounded fetch worker/cache never changes chart prices, strategies,
backtests, alerts or agreement. Invalid/future data is rejected; offline/invalid/
outdated states preserve only dated last-good data. See [display contract and
acceptance](FEAR_GREED.md) for schedules, cancellation and cache boundaries.

Focused verification passed 22 backend and 50 frontend checks initially, followed
by 18 backend and 12 frontend checks for review corrections (overlapping totals),
TypeScript and production build. The application worker also obtained the actual
provider value 69 / Greed, source date 2026-10-12. Runtime availability is not an
uptime guarantee. The existing bundle-size advisory remains.

Actual production-browser visual/keyboard/layout acceptance is blocked by the
current own-cloud control route. No screenshot, Windows/native, full-product or
owner acceptance is claimed. New/modified tests remain outside Git; its private version-linked archive and
remote checkpoint were independently verified.

## Preserved saved comparison conditions

Results retains a 28-condition read-only review of saved Data, Period, Capital
and Costs & execution, with matched/different/unknown per-run evidence. It does
not rerun, reprice or rank results; missing historical evidence remains unknown.
The prior comparability acceptance passed 25 backend and 30 frontend checks,
TypeScript/build and actual own-cloud synthetic production-browser checks. These
are historical counts, not newly rerun totals. Its separate owner-only regression
archive is required to reproduce that coverage; tracked tests remain unchanged.
See [comparability acceptance](BACKTEST_COMPARABILITY.md) for all source-evidence,
clock, provider-authentication, archive and platform limitations.

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
