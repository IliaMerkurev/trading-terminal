# ADR 0018: Independent market lifecycle and native chart history

Status: implemented and owner-accepted for product 0.5-dev. Measured evidence and automation limitations are recorded in [STATUS.md](../STATUS.md).

## Decision

Move public socket ownership into one `MarketHub`, independent from optional strategy monitoring. One connection owns ticker, book, trades and the six supported native candle intervals. These are distinct interval topics, not duplicated per-widget subscriptions. The confirmed M1 topic remains the only candle input to Strategy IR. A bounded consumer queue forwards observed events to the existing strategy/paper processing loop; queue overflow or a reconnect invalidates that consumer and requires recovery rather than dropping executable inputs silently.

Opening Live starts the market with no strategy. Strategy warmup runs independently and reports recovered/required M1 and page progress. Pausing strategy monitoring detaches its consumer but leaves the public market active while the view is open. Leaving Live releases the market only if no monitoring session is active. Closing the application stops both lifecycles. An active strategy prevents changing the market underneath its frozen snapshot. Market freshness does not imply strategy or paper readiness.

## Chart history

Use native Bybit public kline resolution for 1m, 5m, 15m, 1H, 4H and 1D. Add source-specific version-1 chart candle/page tables to the existing SQLite database. Store confirmed candles by market/symbol/interval/start; immutable confirmed overlap conflicts fail visibly. Recent REST pages exclude the incomplete candle; centralized native WebSocket observations supply that candle. Coarse candles never derive from strategy warmup M1 tails.

The chart API returns cached data immediately and schedules a bounded asynchronous REST page. Initial pages contain at most 300 candles; recent refresh fetches the missing suffix. Older pages are requested by an exclusive UTC cursor and cached. No full-history startup download. The UI renders a bounded 1,800-bar window and anchors logical coordinates on prepend. Latest market returns from a distant historical window; data outside the window remains in SQLite. Indicators/signals/paper markers come separately from recorded evaluation/execution values and never change candle ownership or IR semantics.

Only initial market/interval loading or an explicit Fit/Latest action changes the viewport fit. Strategy readiness and strategy selection must not reset it. Latest-bar updates use the chart series update API where the prefix is unchanged; history replacement preserves the visible range. Programmatic fits must not trigger automatic backward paging.

## Evidence and limitations

The isolated pre-change H1/closed measurement reproduced repeated intermediate warmup chart tails and delayed subscription: subscription began at 88.609s, first sampled ticker/book and strategy-ready at 90.7s. Seven REST pages took approximately 8.7s total; remaining elapsed time includes per-candle journal/evaluation and polling overhead. This is a bounded diagnostic reproduction, not a native UI timing benchmark or proof of one exclusive bottleneck. Warmup length is retained.

Protocol, cache, temporal, native startup and long-run acceptance must be recorded before marking the milestone complete. Market history and stream failures remain independent and visible; current public access does not guarantee complete exchange history. No new dependencies, credentials, database framework or engine are introduced.

Sources checked during 0.5 implementation: [Bybit native kline history](https://bybit-exchange.github.io/docs/v5/market/kline), [public kline intervals/confirmation](https://bybit-exchange.github.io/docs/v5/websocket/public/kline). Retained book/tape protocol and freshness rules are in [ADR 0016](0016-shared-market-terminal.md).
