# Product 0.3 live/paper demonstration

This is an early development build, not real trading. No exchange credentials or order interface are provided. The accepted 0.1/0.2 historical workflows remain available. Native Python is still supported for compatible historical runs; Live requires a saved visual Strategy IR and never converts or executes native source.

## Reproducible offline fixtures

Choose a **new absolute test directory** under ignored local data, distinct from the ordinary user data root. Substitute that directory for `<absolute-demo-directory>` in both commands, from this checkout:

```powershell
.\.venv\Scripts\python.exe -m terminal.demo_live --data-root '<absolute-demo-directory>'
.\.venv\Scripts\python.exe scripts\desktop.py --build --data-root '<absolute-demo-directory>'
```

The generator refuses the ordinary root and reuses its completed demonstration marker. It preserves other records and never opens a network connection. All three strategies/sessions are explicitly labeled Synthetic. The repeated price shapes are authored fixtures, not exchange candles or a strategy-profitability claim.

Open Live and select each saved session. Verify recorded signals with replay while paused:

| Fixture | Independent expected signal boundaries (UTC epoch seconds) | Expected replay |
| --- | --- | --- |
| Observed paper golden | 180 Entry Long; 300 Exit Long | MATCH, 2 events |
| Forming H1 | 3660 Entry Long; 5460 Exit Long | MATCH, 2 events |
| Closed H1 | 7200 Exit Long | MATCH, 1 event |

The paper fixture buys one unit at observed 100 and sells at observed 110. With 0.1% fees, capital 1000 becomes **1009.79**. Displayed signal price is the confirmed candle close; the later observed paper quote is a separate input. Historical simulation may produce different fills because it uses a specified synthetic intraminute path. Signal semantics must match, executable observations need not.

## Public market session

1. Select a saved visual strategy. Choose spot or linear, a valid Bybit USDT instrument, primary timeframe and closed/forming evaluation in the existing settings. For a quick observation choose 1m. Review capital, sizing, costs, precision, mark/funding and protection assumptions before enabling paper.
2. Open Live, optionally enable Paper trading and individual notification channels, then Start new live session. The session freezes strategy/profile settings. Editing the saved strategy later does not change this running session. Only one session can run at a time.
3. Wait for REST warmup/recovery and fresh subscribed data. CONNECTED requires current coverage; RECONNECTING/RECOVERING DATA are not success states. Inspect observed last/mark price, exchange candle, shared indicator values, four condition states, event history and virtual account/fills.
4. Strategy evaluation advances on **confirmed M1 closes**, including partial higher-timeframe evaluation. Forming H1 is not every-tick H1 evaluation. A true condition generates an alert only on false-to-true transition. Persistent events include strategy identity/hash, market/timeframe, logical and observed timestamps and values.
5. Pause, then verify recorded signals with replay. Reopen a saved session after restart: monitoring stays paused, last valid minute and any virtual position remain visible. Recover monitoring reconstructs missing confirmed minutes; paper continuity needs explicit revalidation because missed executable ticks cannot be recreated from candles.

Use only a disposable test session for network interruption experiments. Do not alter system networking or security settings. The deterministic test suite injects connection loss into its own fake socket and checks recovered candles, suppressed notifications and replay equality. The actual bounded acceptance probe also interrupted only its own connection.

## Notifications

**Owner acceptance:** Windows notifications and sound are verified. Telegram notification integration is implemented, but owner acceptance is currently failing: Test notification did not deliver despite configured credentials. Telegram delivery remains a known issue for investigation in [ILI-37](https://linear.app/ilia-merkurev/issue/ILI-37/fix-telegram-notification-delivery-after-03-owner-acceptance). Passing automated transport tests do not replace real delivery acceptance.

Windows, sound and Telegram have separate Test controls. The event log distinguishes queued, dispatched and failed delivery. A failure never stops strategy evaluation. Windows honors existing notification settings; the application does not enable disabled permissions. The native opt-in integration test checks that Windows retained this application's toast, not that a banner was visible or a sound was heard.

Configure Telegram only through the password fields in Live. Save writes token and chat ID to Windows Credential Manager; saved values are not returned to the UI. Test Telegram attempts delivery directly from this computer to the official Bot API. Clear stored credentials removes only this data root's credential. Never put credentials in commands, screenshots, exports or issue comments. Successful delivery must be demonstrated after the known issue is resolved.

Delivery claims are durable and at-most-once: an uncertain attempt after a crash is not automatically retried. This prevents duplicate alerts at the cost of possibly missing an external notification. The saved signal event remains available. Recovered historical events are labeled and do not send old notifications.

## Editor and Windows checks

Select an ordinary node and press Delete while canvas has focus; connected edges disappear and validation updates. Undo restores the node and connections; Redo repeats the same operation. Test multiple selection, typing in a parameter input (no deletion), fixed outputs (never deleted), node right-click Delete and canvas right-click Add Node. Undo/Redo buttons remain available in addition to Ctrl+Z/Ctrl+Y.

Verify minimize/restore, normal shutdown and restart, toast visibility, sound audibility, owner-configured Telegram delivery and practical 100%/125%/150% display scales. [Status](STATUS.md) separates completed checks from remaining owner acceptance; do not infer native behavior from component tests.

## Resource and execution limits

UI events/signals and displayed fills are bounded; persistent journals stay local. Paper sessions cap retained orders at 10,000 and observations at 250,000, then stop for review. Reconnect uses bounded exponential backoff; repeated failure becomes ERROR. Funding-history publication is asynchronous: account processing waits while real prices are journaled in order, without substituting an estimate. Missing funding continuity or failed journal writes require review/recovery.

Paper assumes sufficient liquidity and immediate observed-quote fills with configured adverse slippage/fees. Perpetual accounting uses separate mark, maintenance and confirmed funding assumptions through the retained engine; it is not an exact exchange execution model. Monitoring ends when the application closes; there is no background service, installer or released binary.
