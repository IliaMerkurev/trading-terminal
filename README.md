# Trading Terminal

Trading Terminal is a planned Windows desktop application for historical strategy research: create a visual strategy or import a compatible Python strategy, run a reproducible backtest, inspect trades, and compare saved results.

## Development status

**Engine foundations under development.** NautilusTrader 1.231.0 is the first implementation engine. Sixteen Windows tests cover synthetic accounting, a risk adapter, causal partial-hour evaluation, a native strategy example and worker cancellation. There is no runnable desktop application or complete research workflow yet. See the [engine decision and limitations](docs/adr/0001-engine.md).

## Planned V1 capabilities

- Visual strategy graphs and one supported native Python strategy format.
- Bybit USDT spot and linear perpetual historical tests, including long/short perpetual positions.
- Closed-bar and causal intrabar condition evaluation.
- Explicit fees, slippage, funding, margin, liquidation, and execution assumptions.
- Local historical data, reproducible run snapshots, charts, trade tables, comparisons, and export.
- A responsive English interface with cancellable backtests.

V1 does not include live trading, exchange credentials, optimization, DCA, partial exits, multiple simultaneous instruments, or AI features.

## Documentation

- [Product specification](PROJECT.md): authoritative scope and acceptance requirements.
- [Architecture](docs/ARCHITECTURE.md): proposed components and boundaries.
- [Engine evaluation](docs/ENGINE_SELECTION.md): selection criteria and required experiments.
- [Development guide](docs/DEVELOPMENT.md): contribution workflow and validation.
- [Implementation status](docs/STATUS.md): verified capabilities and current limitations.

## Running the project

No application launch command is available yet. In the documented Windows Python environment, run the foundation tests with `.venv/Scripts/python.exe -m unittest discover -s tests -v`. Setup requirements and limitations are recorded in the [development guide](docs/DEVELOPMENT.md).

## License

A project license has not been selected. Public availability does not grant an open-source license. Third-party code requires a license review before inclusion.
