# ADR 0028: Catalog-wide batch comparison

Status: implemented; acceptance evidence in STATUS.md.

## Decision

The owner requested one action to compare every strategy under common settings
across timeframes and preserve sortable results. Extend the existing library
controller and sequential batch manager. Test all strategies selects every
catalog card regardless of display filters and opens the existing setup dialog.
The shared timeframe set defaults to 4h and 1d. Indicator parameters are specific
to each strategy and remain fixed across its variants; capital, history, dates,
sizing and costs are shared. Review and explicit Start freeze the same immutable
contract used by individual card tests. No additional dependency is introduced.

Seven strategies at two timeframes create 14 variants plus two passive rows.
On spot H4 history, twelve strategy variants are runnable and two native variants
remain incompatible. Preview and Start distinguish runnable and unavailable
counts. Expected optional native preparation failures become unavailable rows,
without executing source or blocking compatible graph rows. Hash-bound trust,
runtime identity and worker isolation requirements are unchanged.

## Bounds and storage

Raise the selection bound from 12 to 96 in preview/warmup and archive provenance;
the Python definition is shared by the manager and archive validator. Frontend
admission uses the matching bound. Keep the existing 2,000,000-source-candle
budget, one calculation slot, cancellation and explicit unchanged-input resume.
All eleven current timeframes across seven strategies fit the row count but can
exceed the workload cap, particularly when daily warmup requires minute history.
Do not raise that resource budget or alter indicator warmup to make a batch fit.

Reuse library_batches, library_rows and ordinary immutable run records. There
is no migration, recalculation on reopen, new server or parallel worker pool.
Archive tests cover the last new ordinal, the first invalid ordinal and legacy
ordinal 11. Saving a comparison does not include downloaded candles in Git.

## Comparison

Add ascending/descending order and a frozen shared-settings summary to Saved
tests. Rank only within matching dataset/profile cohorts, ignoring the strategy
timeframe but retaining execution-model versions. Show comparison group numbers.
Missing metrics remain last within each cohort in both directions. Do not mutate
stored metrics, rank holdouts or hide losing and incompatible rows. Differences
in strategy logic and model versions remain material limitations to comparisons;
this matrix does not establish out-of-sample profitability.

Existing per-card testing and later-period validation remain available. A new
optimizer, portfolio simulation and universal ranking across distinct execution
models were rejected as unnecessary for this request.
