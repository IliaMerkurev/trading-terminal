# Trading Terminal

A local Windows desktop application for historical strategy research. Create a visual strategy or explicitly trust a compatible native Python strategy, prepare Bybit history, run a backtest, inspect trades, and compare saved results.

**V2 is accepted and available on main, preserving the V1 workflow.** It uses NautilusTrader 1.231.0 with explicit, independently tested versioned execution. This is a historical research tool; it does not submit live orders. See [verified status](docs/STATUS.md), [model limitations](docs/adr/0010-execution-v2.md), and the [V2 demonstration guide](docs/DEMO_V2.md). Owner acceptance remains distinct from automated verification.

## Available workflow

- Shared visual graph: OHLCV, SMA, EMA, RSI, Bollinger Bands, MACD, ATR, comparisons, crossings and boolean logic; four entry/exit outputs.
- Unborrowed USDT spot and single-position cross-margin USDT perpetual long/short simulation, with editable sizing, fees, slippage, funding and mark-price liquidation assumptions.
- Closed primary-bar conditions or causal forming-bar evaluation on one-minute steps.
- Public Bybit downloads, coverage/gap reports, checked local datasets and offline runs.
- Cancellable workers, immutable run history, recorded indicators, charts, trade navigation, comparison and validated project archives.
- Source-only native Python preview with explicit execution consent. Workers are not a security sandbox.
- Right-click node search, reversible graph edits, selected-node duplication and navigable validation.
- Explicit V1 discrete and V2 continuous-segment protection models, with gap/cost/mark-price assumptions preserved.
- Sequential bounded parameter grids, immutable inputs, sortable in-sample results and separately frozen later-period validation.

## Windows launch

With the documented toolchain and one-time project setup complete, run from the project directory:

```powershell
.\.venv\Scripts\python.exe scripts\desktop.py --build
```

The launcher builds this checkout's desktop assets and starts the application using the calling Python environment. Omit `--build` to reopen an existing build. It does not install tools or change PowerShell execution policies. Keep a running older build in a separate checkout; do not rebuild its executable. For prerequisites, pinned setup and tests, read the [development guide](docs/DEVELOPMENT.md). An installer is deferred.

## Scope and documentation

Live trading, exchange credentials, optimization beyond the bounded V2 grid, DCA, partial exits, multiple simultaneous instruments, AI and background services remain deferred. Historical minute bars cannot reveal the true tick path; risk-tier history may be unavailable. Imported reports are viewable without their raw history but are not guaranteed rerunnable. Repeated holdout use weakens independence; the application does not recommend a profitable strategy.

- [PROJECT.md](PROJECT.md): authoritative product specification and deferred scope.
- [Architecture](docs/ARCHITECTURE.md) and [engine evaluation](docs/ENGINE_SELECTION.md).
- [Implementation status](docs/STATUS.md) and [development guidance](docs/DEVELOPMENT.md).
- [V2 demonstration and owner acceptance](docs/DEMO_V2.md), and [retained V1 demonstration](docs/DEMO.md).

## License

A project license has not been selected. Public availability does not grant an open-source license. See [third-party notices](THIRD_PARTY_NOTICES.md); no distributable installer or binary release is provided.
