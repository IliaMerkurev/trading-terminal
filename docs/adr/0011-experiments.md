# ADR 0011: Sequential grids and frozen later-period validation

Status: implemented; verification recorded in [status](../STATUS.md).

## Contract

Experiments use saved visual strategies and the same managed worker/accounting path as ordinary runs. Each combination gets a fresh worker, capital and graph state. One application-wide reservation excludes concurrent ordinary runs, grids and validation. The scheduler never launches cloud work.

Preparation validates 1–6 stable node/profile parameter fields, 1–100 explicit values per field and deduplicates typed values before computing the Cartesian count. Maximums are 256 unique combinations and 2,000,000 processed minute-runs including preceding warmup. Costs, dataset, execution model and primary timeframe are fixed rather than optimization dimensions. Node numeric/enum fields and allocation, leverage, stop/take fields remain constrained by the actual graph/profile validator. Invalid grids fail before workers start.

The experiment snapshot freezes graph, layout, parameters, profile, runtime identity, dataset identity and both UTC ranges before queuing. SQLite adds experiments, combination rows and validation attempts without rewriting existing strategies/results. Every combination keeps status, parameters, error and run identity. Cancel stops the active worker and prevents subsequent starts. Pending rows remain visibly unstarted; successful completed results survive. Application restart marks unfinished work interrupted and never auto-resumes. A batch with failed combinations is `completed_with_errors`, not a successful calculation.

Only completed in-sample results enter sorting/filtering. Undefined no-trade win rate sorts last and remains undefined. Failed/cancelled/interrupted rows stay in the status list. The UI gives no profitability recommendation. A selected result opens the ordinary report; copying it creates an independent saved strategy without changing the source or previous runs.

## Holdout boundary

In-sample and later, nonoverlapping out-of-sample ranges must be declared before starting. The grid and ranking never calculate OOS metrics. Selecting a completed candidate creates an immutable validation attempt containing exact graph, parameters, profile, runtime/data identity and candidate checksum. Validation runs once per attempt; changing candidates or repeating the holdout creates a new explicit record with a reuse warning. OOS metrics are displayed separately from IS, without a combined PnL or equity curve.

The same window-run path performs standalone and experiment validation. Preceding dataset bars warm the graph and primary-timeframe state, while the account remains flat. They generate no trades, fees, funding or measured equity points. Only bars starting within the declared trading range may generate orders. All preceding complete primary bars are available; preparation conservatively checks sufficient warmup for every grid candidate. Unavailable warmup fails OOS preparation visibly. IS beginning before full warmup is disclosed in preview.

## Storage and portability

Large source candles remain in one immutable dataset shared by combinations. Experiment result files/SQLite series omit repeated candles; charts read a bounded time window from the referenced, checksum-verified dataset. Missing source history is disclosed without changing stored metrics. Derived series, fills and immutable snapshots remain per run. Export omits market history and includes experiment/phase/parameter/window/selection provenance in the run snapshots. Import never resumes an experiment, fetches missing history, grants trust or treats imported results as locally verified.

## Verification

Independent accounting fixtures are complemented by actual Windows worker tests: a 2×2 grid equals four standalone runs; frozen OOS equals a standalone window run; editor changes do not alter queued inputs; cancellation/error/interruption preserve accurate statuses; changing only future holdout candles leaves IS metrics/ranking and chosen graph/parameters unchanged. The changed dataset checksum intentionally changes provenance identity, even when IS behavior remains identical.
