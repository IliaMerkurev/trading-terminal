# Trading Terminal

A local Windows desktop application for historical strategy research. Create a visual strategy or explicitly trust a compatible native Python strategy, prepare Bybit history, run a backtest, inspect trades, and compare saved results.

**V1 development build is available for acceptance testing.** It uses NautilusTrader 1.231.0 with an explicit, independently tested simulation adapter. This is a historical research tool; it does not submit live orders. See [verified status](docs/STATUS.md), [model limitations](docs/adr/0002-simulation-profile.md), and the [demonstration guide](docs/DEMO.md).

## Available workflow

- Shared visual graph: OHLCV, SMA, EMA, RSI, Bollinger Bands, MACD, ATR, comparisons, crossings and boolean logic; four entry/exit outputs.
- Unborrowed USDT spot and single-position cross-margin USDT perpetual long/short simulation, with editable sizing, fees, slippage, funding and mark-price liquidation assumptions.
- Closed primary-bar conditions or causal forming-bar evaluation on one-minute steps.
- Public Bybit downloads, coverage/gap reports, checked local datasets and offline runs.
- Cancellable workers, immutable run history, recorded indicators, charts, trade navigation, comparison and validated project archives.
- Source-only native Python preview with explicit execution consent. Workers are not a security sandbox.

## Windows launch

With the documented toolchain and one-time project setup complete, run from the project directory:

```powershell
.\scripts\launch.ps1
```

The script builds the desktop assets and starts the application. It does not install system tools. For prerequisites, pinned setup and tests, read the [development guide](docs/DEVELOPMENT.md). An installer is deferred.

## Scope and documentation

V1 excludes live trading, exchange credentials, optimization, DCA, partial exits, multiple simultaneous instruments, AI and background services. Historical minute bars cannot reveal the true tick path; risk-tier history may be unavailable. Imported reports are viewable without their raw history but are not guaranteed rerunnable.

- [PROJECT.md](PROJECT.md): authoritative product specification and deferred scope.
- [Architecture](docs/ARCHITECTURE.md) and [engine evaluation](docs/ENGINE_SELECTION.md).
- [Implementation status](docs/STATUS.md) and [development guidance](docs/DEVELOPMENT.md).
- [Demonstration and owner acceptance](docs/DEMO.md).

## License

A project license has not been selected. Public availability does not grant an open-source license. See [third-party notices](THIRD_PARTY_NOTICES.md); no distributable installer or binary release is provided.
