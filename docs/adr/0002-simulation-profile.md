# ADR 0002: Explicit single-position historical simulation profile

Status: implemented and checked with synthetic Windows fixtures. Historical
coverage, graph UI and native import integration are later milestones. Scope:
[PROJECT sections 2, 3, 5 and 9](../../PROJECT.md). Profile/metric schema version 1.

## Market and capital

Use unborrowed USDT spot and a **single-position cross-margin** model for linear
USDT perpetuals. This is not a full Bybit Unified Trading Account simulator.
All virtual capital backs the one perpetual position. Leverage changes allowed
notional and required initial margin, not the realized-PnL formula.

For quantity q, entry e, current mark m and signed direction s (+1 long, -1 short):

- Initial margin = q × e / leverage, held until full close.
- Cash = starting capital + realized price PnL − commissions + funding cashflows.
- Perpetual equity = cash + s × q × (m − e).
- Available capital = equity − initial margin; no second position may consume it.
- Maintenance = q × m × the explicitly selected constant maintenance rate.
- Liquidate when equity ≤ maintenance + estimated close commission at mark.
- Spot equity = remaining USDT cash + base quantity × observed trade price.
- Negative perpetual equity is retained as a modeled deficit, not silently
  floored or credited from an insurance fund. No ADL or insurance model is claimed.

NautilusTrader processes all fills, commissions, positions and cash changes.
The application supplies the risk gateway, funding cashflows and liquidation
trigger. The default numeric settings are editable modeling assumptions, not
verified historical exchange/account fee or risk settings.

Fixed allocation means margin capital. Percentage allocation uses available
flat capital. Desired notional is allocation × leverage. Reserve the entry fee
if allocation consumes all capital, then round quantity down to quantity step.
Reject allocations above available capital, below minimum quantity/notional or
above the declared risk tier; do not silently increase leverage or tier. Quotes
round bid down and ask up to tick size. Profile input supports up to eight decimal
places. The risk gateway independently checks collateral and the entry fee.

Use one explicitly declared constant tier with a maximum notional. If marked
notional exceeds it, fail the run instead of pretending another tier is modeled.
Current instrument/risk metadata is not proof of historical values. Preserve its
retrieval date and the declared historical assumption in later dataset manifests.

## Data and event order

Input consists of sorted, unique UTC one-minute trade candles. Mark candles and
funding events are separate. Perpetual runs require mark coverage and a supplied
funding history, unless the user explicitly selects a disclosed last-price proxy
or assumed-zero funding profile. The data layer must verify historical coverage;
an empty short-period funding series can be valid, but is not proof of coverage.

The price path is explicit: O-L-H-C or O-H-L-C. Each minute produces four modeled
quote observations at interval start, +20s, +40s and close (end minus 1ns). Mark
OHLC follows the same declared phase order; their real relative tick timing is
unknown. These synthetic observations do not reconstruct actual ticks. Strategy
minute bars are delivered only after the close observation. Forming primary-bar
indicators update only at minute closes, never at synthetic extrema.

At each quote observation: update executable quote, apply funding due at that
exact boundary to an already held position, test mark liquidation, then test
stop/take. At a minute close, evaluate the graph only after those checks. Market
orders execute immediately against the current quote; no queue or assumed latency.
This is a market-on-observed-close model, not a claim of realizable zero-latency
historical trading. A funding-boundary entry at the preceding minute's closing
observation is held at the next interval open and receives that funding event.

Percentage slippage produces adverse executable bid/ask around the observed
trade price. Stop/take trigger on unadjusted price movement from actual entry;
the exit receives slippage and commission. A trigger executes at the **first
modeled observation** beyond its threshold, not at an invented threshold fill.
This can be much worse/better than a threshold price; four-point OHLC execution
is deliberately coarse and must remain visible in results. If both protective
levels are touched in a minute, path order decides which is observed first.
Liquidation wins when it conflicts with protection at one observation.

Default gap policy rejects missing minutes. Explicit closed-mode skip preserves
and reports gaps; a protection crossing a gap fills at the next observed open.
Intrabar mode rejects gaps rather than substituting complete-bar logic. Primary
bars missing constituent minutes are not treated as complete. No future minute
or final primary-bar extreme enters an earlier indicator calculation.

## Signals and end of run

One position only. Repeated entries do not add; an opposite entry does not close
or reverse. Exit blocks close the full corresponding position. Simultaneous flat
long/short entries skip and log. A same-step explicit exit has priority and does
not reenter. Spot short signals log an unsupported-market diagnostic. After a
protective close, no graph reentry occurs in that minute.

Open positions close fully at the final executable quote, with ordinary costs
and `end_of_run` reason. The observer collects engine events even during strategy
shutdown; relying only on `on_order_filled` misses shutdown fills in this engine.
Incomplete fill pairs or remaining open positions invalidate the result.

## Metrics and validation

Net PnL = final equity − starting capital, including fees and funding. Trade net
PnL = signed price PnL − both-side fees + funding while that trade was held.
Winning means strictly positive trade net PnL; no trades yields undefined win
rate. Drawdown uses peak-to-current marked equity at every modeled observation,
including the final close and costs. It is expressed as a fraction of peak.
Results expose cash, equity, initial/maintenance margin and available capital.
Order identifiers are omitted from normalized numerical outputs, making identical
snapshots deterministic; later manifests must include datasets and runtime locks.

Windows regression cases in `tests/test_simulation.py` check both directions,
fees, percentage slippage, funding and funding-caused liquidation, mark-only
liquidation, sizing and precision, entry conflicts, path/protection/gap behavior,
end closure, capital/metrics reconciliation and repeatability. They supplement
the earlier engine probes; they do not validate unknown historical exchange tiers.

Primary API field references for the subsequent data implementation:
[instrument precision](https://bybit-exchange.github.io/docs/v5/market/instrument),
[risk limits](https://bybit-exchange.github.io/docs/v5/market/risk-limit),
[mark history](https://bybit-exchange.github.io/docs/v5/market/mark-kline), and
[funding history](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate).
