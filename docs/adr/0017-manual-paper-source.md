# ADR 0017: Manual paper source in the existing observed-price account

Status: accepted for product 0.4 development.

## Decision

Freeze `execution_source` as `strategy` or `manual` when creating a paper session. Existing saved sessions default to strategy source. Both sources use the same `PaperJournal`, Nautilus-backed `PaperEngine`, sizing, costs, mark/funding and protection rules. Manual source disables strategy-generated orders, but keeps strategy evaluation, signals, notifications and stop/take/liquidation processing. Switching sources requires a new session; there is no mixed-ownership order manager.

Manual Buy opens a long and Manual Sell opens a perpetual short. Unborrowed spot cannot short. Close requests a full exit in either direction. The one-position rule rejects a second entry and rejects closing an empty account. Controls are unavailable while disconnected, stale, recovering, awaiting funding processing or awaiting paper-continuity revalidation. They cannot access real accounts or submit exchange orders.

## Request and crash semantics

Each UI action carries a random request ID. The service stores it with the session/action; a duplicate ID returns its existing status, while conflicting reuse fails. At most one request may await a quote. Execution uses a later actually observed provider quote, not the price shown at click time. A queued request expires after five seconds and is cancelled on pause/recovery/restart. Missing quotes are not synthesized from candle history.

When consumed, the request is atomically linked to a persisted paper input (`recorded`). The ordinary journal processes that input and marks the request `applied`. Restart reprocesses committed inputs through the existing verified reconstruction path without double charging or inventing another engine. Applied means the input was processed: risk/sizing/protection policy can still prevent a new fill. Inspect the resulting PAPER position and fill history rather than interpreting a queued acknowledgement as a fill guarantee.

Account display includes current/mark price, cash/equity, unrealized PnL, realized net PnL, fees/funding and entry/stop/take. These derive from the existing engine's account and recorded results. A separate additive terminal-summary table preserves display state on reopening without changing canonical old paper result JSON. Restart remains paused and requires continuity review; it does not automatically resume monitoring or paper execution.

## Validation and limits

Independent fixtures cover one-unit entry at 100 and exit at 110 with 0.1% fees: final equity 1009.79 and total fees 0.21. Tests cover request deduplication, expiration, future-quote requirement, source/position/spot guards and reconstruction. Existing independent perpetual accounting/funding/slippage/protection/replay tests remain applicable to the unchanged engine. Native public-market manual controls are checked separately in the development demonstration.

There are no limit orders, partial exits, DCA, averaging, exchange balances, private API keys or real trading. Paper results describe the configured observed-price simulation, not an exchange fill guarantee.
