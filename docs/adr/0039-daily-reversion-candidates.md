# ADR 0039: bounded daily close-reversion candidates

Date: 2026-10-11. Product stays 0.6.0-dev, MIT. This later authorized catalog
addition follows completion of the original bounded TT17/TT18 program; it does
not alter or rerun its frozen cohorts. No chart-display indicators, Supertrend,
new dependency, exchange acquisition or live execution is included.

## Decision and primary-rule review

Add two independently authored historical daily spot long/flat graph templates:

- **C12 / double-seven-reversion v1:** [Cesar Alvarez, 2016-02-10](https://alvarezquanttrading.com/blog/double-7s-strategy/).
  Close must exceed SMA200 and equal the minimum of seven closes including today.
  Exit on a seven-close maximum including today. Ties qualify. This describes
  original closing rules; the article's later next-open experiment is distinct.
- **C13 / improved-r2-reversion v1:** [Larry Connors, 2007-02-21](https://tradingmarkets.com/recent/the_improved_r2_strategy_84_correct_with_just_6_rules_-674361).
  On entry day t, close exceeds SMA200, RSI2[t-2]<65, RSI2[t-1]<RSI2[t-2], and
  RSI2[t]<RSI2[t-1]. Exit requires RSI2[t]>75. Comparisons are strict; there is
  no extra RSI<5 condition in this source. Entry-day trend placement is explicit.

Primary articles independently reviewed on 2026-10-11. The database candidate
IDs identify the source list, not empirical approval. The original source list
was not modified. Neither original ETF/SPX results nor source-platform numerical
parity transfer to spot crypto.

The existing Nautilus Wilder RSI convention is retained: zero first difference,
recursive gain/loss smoothing, 0–100 scale, loss-zero value 100 (including flat
input). Existing SMA readiness remains unchanged. These are disclosed local
implementation choices, not a claimed recreation of the source's software.

Source default periods/thresholds are distinguished from local editable bounds.
C12 admits max(trend_period,window) complete preceding days; C13 requires
trend_period >= rsi_period+3 and admits max(trend_period,rsi_period+3). Default
prefix is 200 days for both. Historical admission rejects insufficient or
noncontiguous immediate prefix, even if older complete bars could satisfy a
count-only test. No missing bar is synthesized.

## Generic graph nodes

Add numeric source/value nodes rolling_min and rolling_max (integer period
1–1000) and lag (integer bars 1–1000). No executable expression or new IR version.

Extrema include the current candidate observation. Full windows are required;
a null source occupies its slot and makes that window unavailable. Lag reads
before appending: it returns the source from N completed primary bars earlier,
including null slots. A null current input does not hide an available lagged
value. Forming evaluations clone committed queues; only completed primary bars
advance them. Existing duplicate-commit and monotonic-time guards apply.

Editor catalog, labels, numeric-port constraints, parameter validation,
serialization and experiment warmup/parameter fields recognize the nodes.
Existing nodes, defaults, archives and prior seven-entry fixtures remain intact.
The full-catalog batch retains its 4h/1d default: unsupported daily-candidate
4h selections remain explicit unavailable rows, while individual new cards offer
only daily. Unsupported rows never execute or alter warmup; invalid nonstandard
intervals still fail validation.
The original fixture explicitly names its original seven strategies rather than
silently enlarging historical validation when the catalog grows.

## Execution and provenance boundary

Templates use terminal profile 2 observed-close execution, configured fees,
slippage, rounding, sizing, optional simple stop/take and costed terminal flatten.
The local default profile uses fixed 100 USDT allocation, 0.1% fees, zero slippage,
no stop/take and no position-management overlay. They are local conveniences,
not published portfolio rules. Spot-only, closed evaluation, gap rejection and absence of a
position-management overlay are enforced at catalog copy/research boundaries.
The generic editable graph remains an ordinary graph; subsequent user changes
are custom research, not continued equivalence to the catalog rule contract.
No pyramiding or shorts occur under these templates. Engine same-step exit
ordering prevents immediate reentry, but a later daily signal may reenter.

Each catalog entry and contract identify the exact SHA256 of its project-authored
UTF-8 rule-summary string in terminal/daily_rules.py, including final newline.
The source_hash_basis explicitly states this scope. It is not the upstream
webpage content hash. source_commit is null; webpage publication and review dates
are separate. Article rights are retained; no prose, Pine, external Python,
private market data or upstream source implementation is copied. The new code
uses the project's MIT license and existing dependency notices.

UI labels these entries **Synthetic implementation verified** and **Empirical
validation: not performed**, with source, author, dates, exact rule hash/basis
and implementation-evidence locations. Existing catalog evidence remains
unchanged. Implementation verification does not establish profitability.

## Independent acceptance fixtures

The independently reviewed arithmetic predates execution assertions:

- period3 closes [12,11,10,10,11,12,13] give minima
  [null,null,10,10,10,10,11] and maxima [null,null,12,11,11,12,13].
- lag2 of [null,10,11,12] gives [null,null,null,10]. Repeated forming
  replacement, committed history, null propagation, bounds and future perturbation
  are tested separately.
- C12 prefix [100]*194+[120,119,118,117,116,115], then [114,113,120,121]
  enters at 114 and exits at 120, without scaling at 113. An alternate first
  evaluation of 115 qualifies by tie; trend equality fails.
- C13 prefix [100]*200 then [120,118,116,114,112,130,131] yields RSI values
  [100,250/3,125/2,125/3,25,3725/41] on the first six new closes. Entry is
  112, exit is 130. A separate rational recurrence, not a production helper,
  verifies all RSI outputs. Injected sequences additionally isolate exact
  65/75 and descent-equality boundaries.
- With allocation100, fee0.001, slippage0.01, tick0.5 and quantity step0.1,
  both quantities are 0.8. C12 fills115.5/118.5, fees0.1872, net2.2128;
  C13 fills113.5/128.5, fees0.1936, net11.8064. Independent costed final-close
  fixtures instead produce negative PnL and preserve fees.
- Prefix exclusion, first evaluation timestamp, no same-step reentry,
  future invariance, one-bar-short/full/gapped admission, actual managed worker
  execution, graph save/reopen and archive preservation all have explicit gates.

See tests/test_daily_reversion.py and frontend editor/catalog tests. Actual
aggregate outcomes and limitations belong in STATUS.md. The reproducible manual
fixture in scripts/prepare_daily_reversion_fixture.py creates only a new isolated
synthetic root, two saved editable strategies and labeled observations, with zero
automatic runs or batches. No browser/native acceptance is inferred from tests.

## Deferred work

No empirical C12/C13 study was designed or run. No optional Supertrend or chart
indicator controls are delivered here. Original M1 history, untouched holdout,
Windows/native and owner-interpretation limitations stay open. No candidate is
promoted for production or live orders.
