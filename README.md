# Trading Terminal

A local Windows desktop application for strategy research, public market monitoring and virtual paper trading. Create a visual strategy or explicitly trust a compatible native Python strategy, prepare Bybit history, run a backtest, inspect trades, and compare saved results.

**Trading Terminal 0.5.1-dev is a maintenance candidate based on owner-accepted 0.5-dev.** It separates market viewing from strategy warmup and adds shared Position Management across historical, paper and experiment workflows. It retains NautilusTrader 1.231.0 and the accepted research/live features. It is not production-ready or stable. It does not submit real exchange orders or accept exchange trading credentials. Remaining UI/UX issues are accepted as non-blocking and deferred to a future version; Telegram delivery remains outside acceptance. See [verified status](docs/STATUS.md), [position assumptions](docs/adr/0019-shared-position-management.md), and the [0.5 demonstration guide](docs/DEMO_05.md). Owner manual acceptance is distinct from automated checks.

0.5.1 adds retryable chart paging, incremental access to older Results, and background recorded Replay with progress and cancellation. It is awaiting owner acceptance.

## Available workflow

- Shared visual graph: OHLCV, SMA, EMA, RSI, Bollinger Bands, MACD, ATR, comparisons, crossings and boolean logic; four entry/exit outputs and read-only position-state nodes.
- Unborrowed USDT spot and single-position cross-margin USDT perpetual long/short simulation, with editable sizing, fees, slippage, funding and mark-price liquidation assumptions.
- Closed primary-bar conditions or causal forming-bar evaluation on one-minute steps.
- Public Bybit downloads, coverage/gap reports, checked local datasets and offline runs.
- Cancellable workers, immutable run history, recorded indicators, charts, trade navigation, comparison and validated project archives.
- Source-only native Python preview with explicit execution consent. Workers are not a security sandbox.
- Right-click node search, reversible graph edits, duplication, Delete/context-menu deletion and navigable validation.
- Execution profile 1 discrete and profile 2 continuous-segment protection models introduced in product 0.2, with gap/cost/mark-price assumptions preserved.
- Sequential bounded parameter grids, immutable inputs, sortable in-sample results and separately frozen later-period validation.

- One public Bybit spot/linear live session with confirmed-minute Strategy IR evaluation, durable signal transitions, reconnect and history recovery.
- Verified Windows and sound notifications. Telegram integration uses Windows-protected local credentials, but Test notification delivery failed owner acceptance and remains a known issue.
- Observed-price paper execution through the retained engine, explicit fees/slippage/mark/funding assumptions, restart revalidation and recorded-signal replay.
- Chart-led Live Terminal with public ticker statistics, forming/final candles, depth-50 snapshot/delta state displayed as 15 levels per side, and a bounded recent-trades tape.
- Display-only chart intervals, recorded Strategy IR indicator values, signal/paper markers and paper entry/stop/take lines. Changing chart timeframe does not change the strategy or restart monitoring.
- Independent market viewing without a strategy, native chart history for 1m/5m/15m/1H/4H/1D, cached bounded pages, and separate market/strategy/paper readiness.
- Optional versioned Position Management: bounded scaling/DCA, partial take profit, trailing, cost-aware break-even and confirmed-primary ATR protection. Legacy profiles remain unchanged when this policy is absent.
- Compact Live settings and switchable Position, Strategy, Signals, Paper Trades, Notifications and Log panels. Manual PAPER Buy/Sell/Add/Reduce/Close share the same account engine; a manual account can run without a strategy, and unborrowed spot cannot short.
- One inspectable position lifecycle across entries/reductions/costs, recorded position context for replay, and validated position parameters in experiments and frozen later-period validation.

**Known issue — Telegram:** integration is implemented, but Test notification does not currently deliver in owner acceptance despite configured credentials. Automated transport tests do not prove delivery. Investigation is tracked in [ILI-37](https://linear.app/ilia-merkurev/issue/ILI-37/fix-telegram-notification-delivery-after-03-owner-acceptance); Windows and sound notifications are verified.

0.4 adds safe actionable Telegram diagnostics for rejected tokens/chats, access errors, rate limits and network/TLS failures. Credentials remain in Windows Credential Manager; no delivery success is claimed without a real owner check.

## Windows launch

With the documented toolchain and one-time project setup complete, run from the project directory:

```powershell
.\.venv\Scripts\python.exe scripts\desktop.py --build
```

The launcher builds this checkout's desktop assets and starts the application using the calling Python environment. Omit `--build` to reopen an existing build. To preserve an in-use older executable, add `--target-dir .local-tools/05-final-target`; both build and launch use that directory. For isolated acceptance, also supply an absolute `--data-root` as described in the demo guide. The launcher does not install tools or change PowerShell execution policies. For prerequisites, pinned setup and tests, read the [development guide](docs/DEVELOPMENT.md). An installer is deferred.

## Scope and documentation

Live trading, exchange credentials, optimization beyond bounded explicit grids, multiple simultaneous instruments, AI and background services remain deferred. Historical minute bars cannot reveal the true tick path; risk-tier history may be unavailable. Paper fills use observed prices and cannot guarantee exchange execution. Imported reports are viewable without their raw history but are not guaranteed rerunnable. Repeated holdout use weakens independence; the application does not recommend a profitable strategy.

- [PROJECT.md](PROJECT.md): authoritative product specification and deferred scope.
- [Architecture](docs/ARCHITECTURE.md) and [engine evaluation](docs/ENGINE_SELECTION.md).
- [Implementation status](docs/STATUS.md) and [development guidance](docs/DEVELOPMENT.md).
- [0.5 market/position demonstration](docs/DEMO_05.md), [retained 0.4 Live Terminal demonstration](docs/DEMO_04.md) and [0.3 live/paper demonstration](docs/DEMO_03.md).
- [0.2 demonstration and owner acceptance](docs/DEMO_V2.md), and [retained 0.1 demonstration](docs/DEMO.md).

## License

A project license has not been selected. Public availability does not grant an open-source license. See [third-party notices](THIRD_PARTY_NOTICES.md); no distributable installer or binary release is provided.
