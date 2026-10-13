# Trading Terminal

A local strategy research application with a retained Windows desktop route and a Linux/browser research candidate. Market supports chart-led observation; Lab supports reviewed strategy cards, reusable Bybit history and saved comparisons. Advanced editing and platform-supported monitoring/paper tools remain available. See the [current checkpoint](docs/CHECKPOINT.md) and [Research workflow](docs/RESEARCH.md).

**Current branch: `codex/terminal-mvp`, Trading Terminal 0.6-dev.** It starts
from the merged 0.6 implementation and retains NautilusTrader 1.231.0. Research
opens with seven reviewed templates, multi-timeframe comparisons and immutable
history reuse. Explicit coarse spot execution avoids requiring M1 data for every
closed-bar study. Strategy editor and More tools preserve detailed execution
and advanced research.
This remains a development build; owner acceptance of this extension is pending.
No real exchange orders or exchange trading credentials are supported.
See [verified status](docs/STATUS.md) and [execution assumptions](docs/adr/0025-research-resolution.md).

## Available workflow

- Shared visual graph: OHLCV, SMA, EMA, RSI, prior-bar Donchian channels, Bollinger Bands, MACD, ATR, comparisons, crossings and boolean logic; four entry/exit outputs and read-only position-state nodes.
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

## Linux adaptation preview

This branch adds a Linux x86_64 source-checkout path while retaining Windows.
See [Linux setup](docs/DEVELOPMENT.md#linux-source-checkout-research-preview) and
[exact validation status](docs/STATUS.md). The original native build and IPC
checks passed, but the actual native window was blocked by a missing system
WebKitGTK helper. After reconstruction, independent Linux/backend and
production-browser checks passed as recorded in the current status. This does not establish a working
native Linux window or current Windows regression acceptance.

Linux native Python execution, Windows/sound notifications and protected
Telegram storage are explicitly unavailable. No plaintext credential fallback,
installer or release is part of this bounded checkpoint.

## Local browser research mode

An owner-authorized loopback browser adapter uses the same local service and
managed workers without requiring the missing native WebKitGTK helper. Build the
frontend and run `scripts/browser.py` with the verified Python environment and
an explicit isolated data root. See [browser launch instructions](docs/DEVELOPMENT.md#local-browser-research-mode),
[security boundary](docs/adr/0030-local-browser-research.md) and
[current verification](docs/STATUS.md). Closing a tab leaves the local service
running; stop it explicitly in the UI or with Ctrl+C.

## Scope and documentation

Live trading, exchange credentials, optimization beyond bounded explicit grids, multiple simultaneous instruments, AI and background services remain deferred. Historical minute bars cannot reveal the true tick path; risk-tier history may be unavailable. Paper fills use observed prices and cannot guarantee exchange execution. Imported reports are viewable without their raw history but are not guaranteed rerunnable. Repeated holdout use weakens independence; the application does not recommend a profitable strategy.

- [PROJECT.md](PROJECT.md): authoritative product specification and deferred scope.
- [Architecture](docs/ARCHITECTURE.md) and [engine evaluation](docs/ENGINE_SELECTION.md).
- [Current checkpoint and UX continuation](docs/CHECKPOINT.md), [implementation status](docs/STATUS.md) and [development guidance](docs/DEVELOPMENT.md).
- [0.5 market/position demonstration](docs/DEMO_05.md), [retained 0.4 Live Terminal demonstration](docs/DEMO_04.md) and [0.3 live/paper demonstration](docs/DEMO_03.md).
- [0.2 demonstration and owner acceptance](docs/DEMO_V2.md), and [retained 0.1 demonstration](docs/DEMO.md).

## License

Trading Terminal is licensed under the [MIT License](LICENSE), copyright (c) 2026 Ilia Merkurev. Third-party components and market data retain their own licenses and provider terms; see [third-party notices](THIRD_PARTY_NOTICES.md). No distributable installer or binary release is provided.
