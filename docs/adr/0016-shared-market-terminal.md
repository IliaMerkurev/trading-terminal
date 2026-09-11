# ADR 0016: Shared public market state and display-only charts

Status: accepted for product 0.4 development.

## Decision

Extend the existing `LiveManager` and `PublicStream`, rather than creating a WebSocket in each widget. One active session owns one connection and one subscription set: public ticker, M1 kline, depth-50 order book and public trades. The existing confirmed-M1 Strategy IR and REST recovery path remain authoritative. No private exchange endpoint or credential is introduced.

The synchronized in-memory `MarketState` owns presentation data and counters. Ticker snapshot/delta fields are merged by the transport. Book snapshots replace both sides; deltas insert/update levels and remove zero-size levels. Update IDs and cross-sequence values are monotonic checks, not a claim of contiguous IDs. A service-reset snapshot (`u=1`) replaces state. A delta without valid state fails into recovery. Invalid/crossed books fail visibly. Reconnect clears the book, ticker freshness and tape before accepting a new snapshot; it cannot reuse the old book.

The depth-50 subscription is retained centrally; the UI returns at most 15 levels per side. The recent-trades buffer holds 100 events with 2,048 recent deduplication IDs; the UI shows 50. Trade timestamp/order and identity checks are independent of WebSocket batch boundaries. Missing tape is explicitly not reconstructed. Public ticker/book ages over 15 seconds produce a degraded terminal even if the strategy stream remains synchronized. Price/confirmed-minute staleness invokes the existing bounded reconnect/recovery loop.

## Chart projection

The existing Lightweight Charts dependency displays a bounded window of 2,880 recorded M1 candles, plus the current forming candle. Initial REST context is at least 1,440 minutes, or the larger required strategy warmup. Display intervals are 1m, 5m, 15m, 1H, 4H and 1D, with at most 600 projected bars. Coarse intervals therefore have limited context; there is no independent long-history chart downloader.

REST and WebSocket confirmed candles share the journal's unique minute keys and validation. Forming candles never replace an already finalized minute. UTC display buckets use interval-end labels. Changing a display interval changes only this projection: it does not save a profile, restart a subscription or change frozen Strategy IR inputs.

Each new evaluation stores its actual IR values atomically with the confirmed candle and signal events. The chart selects the last recorded numeric value within a display bucket; it never recalculates an indicator. Selecting 1H display does not turn an M1 strategy's SMA into an H1 SMA. Older sessions without recorded evaluation rows have no fabricated historical indicator overlay. Signals and paper fills retain their observed timestamps and are placed in their display buckets. Paper entry/protection and fresh last/mark lines are presentation only.

## Alternatives and limits

Per-widget streams would duplicate subscriptions and create conflicting recovery lifecycles. A second chart framework or frontend indicator implementation would add dependencies and risk divergent semantics. Neither is needed. UI polling is bounded and sequential (status 500 ms, chart 3 s); evaluation does not depend on UI renders. Disk journals retain reproducibility; tape is memory-only. Long-running disk retention/archival remains explicit future work, not silently lossy cleanup.

## Protocol sources and verification

Checked against official Bybit V5 documentation during implementation:

- [Order book](https://bybit-exchange.github.io/docs/v5/websocket/public/orderbook): snapshot/delta, zero removal, service reset, cross-sequence and excluded RPI liquidity.
- [Public trades](https://bybit-exchange.github.io/docs/v5/websocket/public/trade): trade IDs, taker side and multi-trade batches.
- [Ticker](https://bybit-exchange.github.io/docs/v5/websocket/public/ticker) and [kline](https://bybit-exchange.github.io/docs/v5/websocket/public/kline).
- [REST kline](https://bybit-exchange.github.io/docs/v5/market/kline).

Deterministic tests cover book mutations/reset/staleness, tape ordering/bounds, allowed public topics, candle projection and stored-value projection. Actual public-session and native Windows evidence is recorded separately in [status](../STATUS.md); mocks alone do not establish live delivery or long-run stability. No dependency or project license change is required.
