# Trading Terminal product specification

Version 0.5. Status: requirements specified; engine foundations under implementation. This file is the sole current technical specification. Architecture decisions explain implementations and tradeoffs; they do not silently remove requirements. Documentation and UI identifiers are English. Historical archives are not alternative specifications.

## 1. Purpose and delivery target

Build a local desktop application for historical strategy research. The complete workflow is: create or import a strategy, prepare historical data, run a backtest, inspect trades and metrics, change parameters, and compare saved runs. The application does not promise profitable strategies. Example indicator strategies are test scenarios, not recommendations.

V1 targets Windows 11 x64 with a 32 GB RAM reference configuration. Establish performance and memory budgets through measurements. Linux/macOS portability should remain feasible, but their releases and verification are outside V1. A documented development launch script with one-time setup is acceptable before a conventional installer. The project license remains undecided.

## 2. Markets and position semantics

The first historical data source is Bybit. Support ordinary, unleveraged USDT spot and linear USDT perpetual contracts. Perpetual positions support long and short. Spot Margin is excluded. Capital and results are denominated in USDT. Each run has one strategy and one instrument.

Cross and isolated margin are future targets; V1 may implement one verified mode with explicit limitations. Full Bybit Unified Trading Account simulation is not required. The first margin mode is an engineering decision, not yet selected.

At most one position may be open per run. Repeated same-direction entry signals do not add to the position. Close the entire position on an exit signal, simple stop-loss, or take-profit. Stop/take values are percentages of price movement from entry, not leveraged return on margin.

Position size is either a fixed amount of allocated margin or a percentage of available virtual capital. Leverage is separate. Distinguish allocated capital/margin from position notional. Spot must use unborrowed capital.

An opposite entry alone neither closes nor reverses an existing position. The same condition can explicitly feed an exit block. Simultaneous long and short entries while flat skip entry and create a diagnostic record. DCA, averaging, partial exits, trailing stops, break-even stops, ATR stops, and automatic reversal are outside V1.

## 3. Timeframes and causal evaluation

Offer standard timeframes actually supported by the implementation. A visual graph has one primary timeframe. Independent multiple visual timeframes are deferred.

Support both conditions evaluated on a closed primary bar and conditions recalculated inside a forming primary bar using finer data, initially one-minute bars. For an H1 strategy updated on M1 steps, use completed hourly bars plus the known partial current hour. Never use future minutes or future H1 high/low/close values. Updating a partial H1 indicator is not equivalent to running an M1 strategy.

Intrabar conditions must genuinely be recalculated; merely refining execution of a previously fixed signal or stop is insufficient. Minute data cannot reconstruct ticks or the unknown price path inside a minute. Record the assumed bar path, fills, gaps, precision, and missing history. If finer data is unavailable, disable intrabar mode with an explanation rather than silently substituting closed-bar mode. Execution granularity and multi-timeframe strategy logic are separate concepts.

## 4. Strategy authoring and Python import

### Visual graph

One graph shares indicators across four output blocks: Entry Long, Exit Long, Entry Short, Exit Short. This is a bounded declarative language for data, indicators, comparisons, boolean logic, and signals, not a general-purpose programming system.

Initial nodes: OHLCV/price/volume; SMA, EMA, RSI, Bollinger Bands, MACD, ATR; value comparisons; Cross Above and Cross Below; AND, OR, NOT. Indicator parameters are editable. Market, instrument, primary timeframe, capital, leverage, position sizing, and simple protection levels belong in a settings panel and need not be nodes.

### Native Python

V1 must import and execute compatible Python strategies in one selected native engine format. Availability of existing compatible strategies informs engine selection. Direct compatibility with several engines and a universal converter are not required. Keep future adapters possible without building a generic plugin framework prematurely.

Python need not convert back into a visual graph. An embedded source editor is optional. Imported strategies may use multiple timeframes within verified engine support; this does not imply visual multi-timeframe support.

Record engine identity, compatibility version, and dependency requirements. Preserve native Python signal and risk semantics. Unsupported behavior must fail visibly; do not silently reinterpret a strategy to fit graph settings. Arbitrary dynamic Python cannot be perfectly checked statically. Define the precedence of native strategy settings and simulation settings explicitly.

## 5. Data, simulation, and results

### Historical data

Select market, instrument, timeframe, and date range inside the application. Download, store locally, and reuse history. Once data is prepared, tests must run without a persistent network connection. Show actual coverage and gaps; missing data must never appear as complete coverage. Do not impose an arbitrary fixed limit of months or years. External CSV import is not mandatory for V1.

Trade OHLCV, Mark Price, and funding are separate datasets. API availability is not a guarantee of historical depth. Choose a native client, CCXT, or a small purpose-built client based on required endpoints; avoid redundant clients.

### Execution and accounting

Start with a documented simulation profile and simple market entries/exits. Profile parameters are manually editable. Complex limit orders, time-in-force rules, and an execution-profile designer are deferred.

Fees, slippage, perpetual funding, and intrabar assumptions must be represented and affect the calculation. No decorative or silently ignored controls. Missing cost history must be visible; neither zero nor another model can be substituted without disclosure.

Perpetual accounting must model available capital, initial/maintenance margin, and liquidation with independently verifiable outcomes. Multiplying spot PnL by leverage is not a futures model. A limited, documented margin profile is acceptable; a claim of compatibility with every Bybit mode is not. Define mark-price use, funding timing, risk tiers, quantity/price precision, minimum order size, and unavailable historical risk information.

Define signal/order/fill ordering, gaps, simultaneous stop/take/liquidation events, entry/exit conflicts, and open positions at test end. Definitions of realized/unrealized PnL, equity, drawdown, win rate, and costs must be explicit and comparable.

### Results and persistence

Provide candlesticks with the indicators actually used by the run, entry/exit markers, a trade table, PnL, drawdown, trade count, win rate, and included costs. Selecting a trade navigates to its chart region. Manual chart drawings, playback, and a detailed condition debugger are deferred.

Save every run independently with immutable strategy and parameter snapshots, simulation settings, dataset information, trades, and metrics. Editing a strategy must not overwrite earlier results. Include run history and a simple comparison table. Parameter search and optimization are deferred.

Record data provenance, range, schema, checksums, runtime/engine versions, parameters, strategy snapshot, and modeling assumptions. A dependency lockfile alone cannot reproduce changed market data. Preserve normalized results alongside engine artifacts. Comparisons must expose differing profiles, versions, and metric definitions.

## 6. Application behavior and export

Use an English single-window UI with Strategy, Backtest, and Results tabs, a strategy list on the left, and context settings on the right. Panels may collapse; arbitrary docking is optional. A dark theme is proposed, not mandatory. Russian localization is not required.

Run one backtest at a time. Keep the UI responsive with progress and logs. Support cancellation. Each worker receives an immutable snapshot, not live editor state. Minimizing does not stop a run. Closing during a run prompts to return or cancel and exit. Queues, parallel tests, and resuming after reboot are outside V1.

Export a project archive with strategy, settings, and selected results. Exclude secrets. Historical datasets are not copied by default; include their description. Optional data inclusion is deferred. A description cannot replace the data, and importing an archive without recoverable history cannot guarantee rerunning it. Distinguish viewing saved results from recalculation.

## 7. Trust and security

Require explicit trust before loading an imported Python module. Selection, preview, opening, and reopening must not execute imported code. Missing dependencies produce actionable errors; installing them requires permission. An embedded package manager is not required.

Worker processes improve lifecycle control and responsiveness but are not a security sandbox. Stronger isolation and network/filesystem restrictions require separate design before wider execution of untrusted strategies. A warning alone does not neutralize malicious Python.

The historical module does not accept exchange credentials. Use a bounded, versioned IPC command set. Validate archive paths and contents, reject traversal and unsafe destinations, and enforce size/resource limits. Do not expose eval/exec through graph nodes. Record strategy/dependency provenance and license obligations.

## 8. Proposed architecture

The baseline is Tauri 2; React, TypeScript, and Vite; React Flow; Lightweight Charts; Python; Pydantic; JSON Strategy IR; SQLite metadata; Parquet data; uv with pinned dependencies. The backtesting engine is undecided. Exact package versions, Python ABI, Node/Rust toolchains, SQLite access, validation, and test tools require compatibility checks. A simpler reliable replacement is possible with evidence in an ADR; product behavior must remain intact.

UI communicates through bounded Tauri IPC with a Python application layer and a managed backtest worker. A separate REST/FastAPI server is not mandatory. Externally accessible servers require a concrete reason and security design. Do not mix protocol messages with arbitrary imported Python stdout. Use explicit messages for errors and cancellation; bound table payloads. Windows cancellation must not leave uncontrolled child processes.

Strategy IR must describe trading semantics independently of React Flow coordinates: schema version, stable node IDs, typed ports, graph validation, crossing semantics, and partial-bar semantics. Visual IR and native Python are separate inputs. Convert graphs through an adapter or generated engine code; choose the mechanism through experiments. Candidate adapter operations include capabilities, validation, preparation, execution, cancellation, and normalized result retrieval.

Charts must use run indicator values. Any independent UI indicator computation with different initialization or partial-bar behavior must be clearly separate. Do not add a second calculation engine, Docker requirement, server database, Kubernetes, cloud backend, AI SDK, or extra plugins without a justified decision within scope.

See [architecture notes](docs/ARCHITECTURE.md) and [engine evaluation](docs/ENGINE_SELECTION.md).

## 9. Required validation

Use tiny synthetic fixtures with independently derived expected results and future-perturbation tests. A successful upstream example is not proof of product correctness.

| Area | Required evidence |
| --- | --- |
| Windows | Pinned environment installation, launch, and managed shutdown on Windows |
| Markets | Spot trade and perpetual long/short; spot never borrows |
| Capital | Sizing, rounding, fees, slippage, funding change fills/balances correctly |
| Margin | Independently expected initial/maintenance margin and liquidation in both directions |
| Mark price | Mark changes can cause liquidation with unchanged last price |
| Intrabar | A signal appears within an H1 bar and disappears by its close; modes differ as expected |
| Causality | Perturbing future data cannot change earlier outputs |
| Indicators | Repeated partial H1 updates do not append fictitious closed bars or become M1 indicators |
| Execution | Documented causal ordering and stop/take/liquidation/gap assumptions |
| Python | Licensed native example runs without semantic rewrites and only after trust |
| Reproducibility | Identical inputs and versions yield identical outputs within stated precision |
| Cancellation | A cancelled run is not successful and incomplete output is not final |
| UI/export | Responsive research workflow, comparison differences, validated archives and reproducible Windows instructions |

Distinguish native engine behavior from adapter behavior, synthetic demos from integrated tests, Linux checks from Windows checks, and automated verification from user acceptance. Unknown tiers require explicit assumptions. Never remove a requirement to make a test pass.

## 10. Open engineering decisions

Record the selected engine/version, Python/dependencies, first margin mode, bar/indicator availability times, timezone and boundaries, warm-up and gaps, signal/order/fill ordering, protection conflicts, end-of-run positions, capital/precision/minimum-size rules, mark/funding behavior, indicator initialization, partial-bar crossings, native risk-setting precedence, IR/export versions, metric definitions, archive limits, and measured performance budgets in ADRs and executable tests. Unresolved details do not prevent small bounded experiments, but must not be presented as validated financial modeling.

## 11. Deferred scope

After V1: market signals, Telegram, Windows/audio notifications, dry-run and live execution, multiple pairs, DCA/partial exits, visual multi-timeframe graphs, batch experiments and optimization, other engines, stronger isolation, installers, and other OS releases. Telegram remains a required future notification channel. Background-service deployment and playback are outside V1.

AI is an optional final-stage extension, using user-supplied API access or a paid option that covers its costs; a local model is optional. Core research functionality must work without AI. No provider-funded token usage for free users is assumed. These roadmap items do not authorize their implementation in V1.
