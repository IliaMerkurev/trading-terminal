# ADR 0019: Shared versioned Position Management

Status: implemented and owner-accepted for product 0.5-dev; automated evidence and its limits remain tracked separately in [STATUS.md](../STATUS.md).

## Authority and compatibility

Nautilus remains the sole execution/account engine. `PositionManager` makes bounded decisions and `PositionLedger` projects **actual fills and actual funding cashflows** into one average-cost lifecycle. Neither creates synthetic account debits or a second portfolio engine. The engine risk gateway independently enforces entry limits against current equity/mark. Final historical lifecycle PnL must reconcile with engine equity before completion.

Position Management is an optional `position_management` object with policy schema version 1. Product 0.5 is not policy schema 5. Legacy profiles omit the object entirely and retain their previous snapshot shape and behavior. Historical managed execution requires existing execution profile 2 and a visual graph; native Python retains its explicit historical contract. Existing saved results are not recalculated.

## Decisions

- One net position. Same-direction entries scale only on a new FALSE-to-TRUE transition when enabled. No implicit reversal. DCA distances are adverse moves from the **first actual entry price**, attempted once per configured step. Rejected steps remain rejected, with a diagnostic, rather than retrying on every tick.
- Add sizes are percentages of initial session capital, converted to notional by the declared leverage and rounded down by quantity step. Maximum entries (1–32), allocated initial capital percentage, aggregate current notional, and leverage are explicit. Limits reject; they do not silently resize.
- Reductions retain the lifecycle ID and remaining average cost. Entry fees and funding are attributed pro rata when reducing; fees/funding are still expensed as they occur in cash/equity. Reduction net PnL and whole-lifecycle net PnL remain distinct. Adding after a reduction weights only the remaining cost basis.
- Partial take levels are favorable distances from current weighted entry, each attempted once. Fractions use quantity at the first take trigger as their fixed basis; a cumulative fraction of 1 closes all remaining quantity, including any later adds. Manual reductions use a fraction of current remaining quantity. Minimum-size or residual-dust violations are rejected without silently enlarging the reduction.
- Protections ratchet toward the position and never loosen after an add/reduction. Trailing uses only observed favorable prices. Fixed ATR stop freezes the latest **confirmed primary-bar ATR at entry**; ATR trailing uses the latest confirmed primary ATR. The shared existing native ATR implementation is used; the frontend does not calculate ATR. ATR-dependent entry is rejected until initialized.
- Break-even covers remaining attributed entry fees/funding and configured adverse exit fee/slippage. It rounds the required executable exit price first, then the observed trigger price, so a second adverse price rounding cannot put the nominal break-even stop below its cost target. This is an assumption-based threshold, not an exchange fill guarantee.

## Causal ordering

At each observation: funding and mark liquidation, existing stop, ratcheted protection, full take/partial takes, strategy exit/entry, manual reduction/entry, then DCA. A reduction/exit blocks new entries on that same observation. Multiple reached partial levels can reduce in ascending schedule order; no action sees a later observation. Strategy/manual source exclusivity is enforced by the session adapter.

Historical profile 2 walks its declared continuous OHLC path, inserting the earliest active stop/take/DCA/liquidation crossing and reevaluating after each actual fill. A bounded crossing budget fails visibly if exhausted. Minute-open gaps execute at the observed open. Paper evaluates actual observations only and never interpolates an unavailable price across a live gap. The position policy is shared; the observation paths are explicitly different.

## Persistence and bounds

Historical lifecycle records include entries, scales, reductions, stop changes, rejections and funding. Paper emits incremental lifecycle events for its durable observation journal; its in-memory event tail is bounded to 256 events and 50 completed summaries. A cursor API pages the complete committed journal (maximum 100 events per response; UI uses 50). Reconstruction must match recorded inputs/results. Copied additive migration checks preserve old rows and result checksums.

## Position IR and readiness

Read-only nodes expose side (-1/0/1), quantity, weighted remaining entry, unleveraged last-price PnL percentage and elapsed primary intervals since first entry. Flat side/size/PnL/bars are zero; average entry is unavailable. They receive explicit context before the current decision. Historical context comes from the retained engine; live context is the last committed paper observation at or before the candle evaluation cutoff. A later fill cannot alter an earlier signal. Additive `live_position_contexts` records are reused by replay; missing required context fails visibly. Market-only evaluation supplies a flat position.

Manual PAPER may start without a strategy. It uses the same frozen profile, journal, funding handling and one-position policy. Initial strategy history runs independently; manual actions require fresh market data, a synchronized account and current protection ATR when configured, but not strategy signals. An ATR number produced partway through old history is insufficient: ATR-dependent actions and paper revalidation wait until that shared history initialization finishes. Strategy actions remain suppressed until recovery finishes. Reconnect/restart still require explicit paper continuity revalidation. No strategy order may bypass Manual source selection.

Experiments vary explicit validated `pm.*` axes on the same immutable profile and worker path. Allocation/notional/leverage caps remain fixed constraints, not optimization targets. Frozen later-period validation retains the selected policy. Enabling this policy is explicit; opening a native strategy clears the unsupported policy instead of silently translating native behavior.

## Evidence

Independently specified examples cover weighted long/short entry, scaling after reduction, partial/full exits, cash, margin, maintenance, fees/funding, entry limits, rounding, trailing, ATR, cost-aware break-even and future perturbation. They are reconciled against actual Nautilus fills in spot/perpetual fixtures. Historical integration checks multiple crossings in one segment, post-scale funding/liquidation and end-of-run closure. Observed paper checks lifecycle costs, gap execution and deterministic reconstruction. Passing these tests does not establish owner acceptance or real exchange execution accuracy.

No new dependency, order endpoint, credential type, license or engine is introduced.
