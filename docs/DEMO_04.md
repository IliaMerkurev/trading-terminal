# Product 0.4 Live Terminal demonstration

This is an early development build with public market data and virtual PAPER execution only. No real account, private Bybit credential or exchange order endpoint is available. Telegram delivery remains an open owner-acceptance issue, [ILI-37](https://linear.app/ilia-merkurev/issue/ILI-37/fix-telegram-notification-delivery-after-03-owner-acceptance).

## Launch an isolated workspace

From the project directory after the documented setup, with the executable closed before rebuilding:

```powershell
.\.venv\Scripts\python.exe scripts\desktop.py --build --data-root "$PWD\.local-data\04-demo"
```

Omit `--build` to reopen. This creates/uses a separate demonstration workspace; it never replaces the ordinary user database. To inspect deterministic retained signal examples instead of public history, use the separate [0.3 synthetic demonstration](DEMO_03.md). Synthetic records are not market evidence.

Save a visual strategy (the built-in SMA example is sufficient for interface checks), then select Live. Set the instrument, market and **strategy** timeframe/evaluation in Live settings before starting. Select spot or linear according to the intended supported account assumptions. Initial history recovery can take time; do not interpret RECOVERING or DEGRADED as CONNECTED.

## Market and strategy

1. Start a session. Confirm the market header updates and the state becomes CONNECTED. For perpetuals, inspect mark/funding separately from last price.
2. Observe the forming candle and subsequent finalized candles. Select a recorded indicator; its values come from the same IR evaluations used by signals. The chart uses UTC interval-end labels.
3. Change **Chart display** between supported intervals. The displayed strategy timeframe/evaluation and session identity must stay unchanged. Log → Market stream counters must not show a new subscription because of this change. The chart is a bounded context window, not an independent long-history download.
4. Inspect 15 levels per side in Order book, including size and relative depth. Both sides are scrollable within the panel. Recent trades show time, price, size and observed taker side; only a bounded tail is retained.
5. Switch bottom panels: Strategy shows four signal states and current IR values; Signals shows transition time/price/values; Paper Trades retains fills; Notifications and Log show readable outcomes. Core monitoring does not require scrolling through a long page.

## Manual PAPER account

Start with Paper trading enabled and execution source **Manual**. Source is frozen for that session. Strategy signals continue, but strategy-generated entries/exits are disabled. The existing account, fees, slippage, stop/take, mark/funding and liquidation assumptions still apply.

- Paper Buy opens one virtual long on a subsequent valid observed quote.
- Paper Sell opens one virtual perpetual short; it is disabled for unborrowed spot.
- Close Paper Position requests a full exit. There is no averaging, scaling, reversal or partial exit.
- A queued acknowledgement is not a fill. Check request status, the position, fill history and cash/equity. Risk/sizing rules may prevent a fill. Duplicate request IDs cannot create a second order.
- Inspect PAPER entry/stop/take markers/lines, quantity, unrealized/realized net PnL, fees and funding. Manual source does not bypass protections.

Queued actions expire after five seconds and are cancelled on pause/reconnect/restart. Strategy source continues to use the original automated virtual-paper behavior. Neither source can trade a real account.

## Recovery, persistence and replay

Pause before closing. Reopen the same demonstration root: saved history and account state remain, but monitoring does not auto-resume. Recover monitoring reconstructs confirmed missing minutes and resets market presentation state. Paper continuity remains paused until explicitly reviewed/revalidated; missing ticks are not reconstructed from candles. If a position exists, inspect it before acknowledging continuation.

During recovery, the book must wait for a fresh snapshot, ticker values must not appear fresh prematurely, and missing tape must not be presented as recovered. Reconnect uses bounded backoff. Recorded recovery signals are retained without sending old notifications. At a paused session, Signals → Verify recorded signals with replay must report MATCH for its recorded signal timeline.

## Notifications and acceptance boundaries

Windows and sound channels retain accepted 0.3 behavior and have independent Test controls. Native Windows tests and audible/visible owner checks are different evidence. Telegram Test must report a safe actionable result in Notifications/Log. Enter credentials only in its protected UI flow; never put them in terminal commands, screenshots, exports or issue comments. A successful mocked transport is not successful real delivery.

The required long-run development check uses this compiled application and real public data for at least 30 minutes. Record elapsed time, per-topic counters, process count, memory samples, UI responsiveness, strategy progression and errors. A deterministic reconnect is not a natural network outage. See [actual measured status](STATUS.md) for the executed run and remaining acceptance items.

## Known limitations

- One active instrument/strategy session; visual IR only in Live. Compatible native Python remains historical-only and is not sandboxed.
- Strategy forming-primary evaluation advances on confirmed M1 boundaries, while the displayed candle updates more frequently. Display intervals do not introduce multi-timeframe IR.
- Up to 2,880 recorded minutes and 600 projected bars are shown, so daily display has limited context. A truncated leading interval is omitted instead of fabricating its open/high/low. Older indicator samples absent from 0.3 journals are not invented.
- Recent tape is not persisted or backfilled. RPI liquidity is not included in the public order-book topic. PAPER is not an exchange execution guarantee.
- UI buffers and reconnects are bounded; persistent journals consume disk. Existing paper safety limits are 250,000 observations and 10,000 cached orders per session, after which review is required.
- Telegram owner delivery acceptance remains open. No installer, release binary, background service or stable/production claim is provided.
