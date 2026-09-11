# Trading Terminal product specification

Product version: 0.2 development build. Status: 0.1 baseline retained; agreed 0.2 accepted and merged into main. Sections 1–11 retain the 0.1 contract; sections 12–18 define the 0.2 extension. This file is the sole current technical specification. Architecture decisions explain implementations and tradeoffs; they do not silently remove requirements. Documentation and UI identifiers are English. Historical archives are not alternative specifications.

## 1. Purpose and delivery target

Build a local desktop application for historical strategy research. The complete workflow is: create or import a strategy, prepare historical data, run a backtest, inspect trades and metrics, change parameters, and compare saved runs. The application does not promise profitable strategies. Example indicator strategies are test scenarios, not recommendations.

0.1 targets Windows 11 x64 with a 32 GB RAM reference configuration. Establish performance and memory budgets through measurements. Linux/macOS portability should remain feasible, but their releases and verification are outside 0.1. A documented development launch script with one-time setup is acceptable before a conventional installer. The project license remains undecided.

## 2. Markets and position semantics

The first historical data source is Bybit. Support ordinary, unleveraged USDT spot and linear USDT perpetual contracts. Perpetual positions support long and short. Spot Margin is excluded. Capital and results are denominated in USDT. Each run has one strategy and one instrument.

Cross and isolated margin are future targets; 0.1 may implement one verified mode with explicit limitations. Full Bybit Unified Trading Account simulation is not required. The first verified mode is single-position cross margin; see ADR 0002 for its limitations.

At most one position may be open per run. Repeated same-direction entry signals do not add to the position. Close the entire position on an exit signal, simple stop-loss, or take-profit. Stop/take values are percentages of price movement from entry, not leveraged return on margin.

Position size is either a fixed amount of allocated margin or a percentage of available virtual capital. Leverage is separate. Distinguish allocated capital/margin from position notional. Spot must use unborrowed capital.

An opposite entry alone neither closes nor reverses an existing position. The same condition can explicitly feed an exit block. Simultaneous long and short entries while flat skip entry and create a diagnostic record. DCA, averaging, partial exits, trailing stops, break-even stops, ATR stops, and automatic reversal are outside 0.1.

## 3. Timeframes and causal evaluation

Offer standard timeframes actually supported by the implementation. A visual graph has one primary timeframe. Independent multiple visual timeframes are deferred.

Support both conditions evaluated on a closed primary bar and conditions recalculated inside a forming primary bar using finer data, initially one-minute bars. For an H1 strategy updated on M1 steps, use completed hourly bars plus the known partial current hour. Never use future minutes or future H1 high/low/close values. Updating a partial H1 indicator is not equivalent to running an M1 strategy.

Intrabar conditions must genuinely be recalculated; merely refining execution of a previously fixed signal or stop is insufficient. Minute data cannot reconstruct ticks or the unknown price path inside a minute. Record the assumed bar path, fills, gaps, precision, and missing history. If finer data is unavailable, disable intrabar mode with an explanation rather than silently substituting closed-bar mode. Execution granularity and multi-timeframe strategy logic are separate concepts.

## 4. Strategy authoring and Python import

### Visual graph

One graph shares indicators across four output blocks: Entry Long, Exit Long, Entry Short, Exit Short. This is a bounded declarative language for data, indicators, comparisons, boolean logic, and signals, not a general-purpose programming system.

Initial nodes: OHLCV/price/volume; SMA, EMA, RSI, Bollinger Bands, MACD, ATR; value comparisons; Cross Above and Cross Below; AND, OR, NOT. Indicator parameters are editable. Market, instrument, primary timeframe, capital, leverage, position sizing, and simple protection levels belong in a settings panel and need not be nodes.

### Native Python

0.1 must import and execute compatible Python strategies in one selected native engine format. Availability of existing compatible strategies informs engine selection. Direct compatibility with several engines and a universal converter are not required. Keep future adapters possible without building a generic plugin framework prematurely.

Python need not convert back into a visual graph. An embedded source editor is optional. Imported strategies may use multiple timeframes within verified engine support; this does not imply visual multi-timeframe support.

Record engine identity, compatibility version, and dependency requirements. Preserve native Python signal and risk semantics. Unsupported behavior must fail visibly; do not silently reinterpret a strategy to fit graph settings. Arbitrary dynamic Python cannot be perfectly checked statically. Define the precedence of native strategy settings and simulation settings explicitly.

## 5. Data, simulation, and results

### Historical data

Select market, instrument, timeframe, and date range inside the application. Download, store locally, and reuse history. Once data is prepared, tests must run without a persistent network connection. Show actual coverage and gaps; missing data must never appear as complete coverage. Do not impose an arbitrary fixed limit of months or years. External CSV import is not mandatory for 0.1.

Trade OHLCV, Mark Price, and funding are separate datasets. API availability is not a guarantee of historical depth. Choose a native client, CCXT, or a small purpose-built client based on required endpoints; avoid redundant clients.

### Execution and accounting

Start with a documented simulation profile and simple market entries/exits. Profile parameters are manually editable. Complex limit orders, time-in-force rules, and an execution-profile designer are deferred.

Fees, slippage, perpetual funding, and intrabar assumptions must be represented and affect the calculation. No decorative or silently ignored controls. Missing cost history must be visible; neither zero nor another model can be substituted without disclosure.

Perpetual accounting must model available capital, initial/maintenance margin, and liquidation with independently verifiable outcomes. Multiplying spot PnL by leverage is not a futures model. A limited, documented margin profile is acceptable; a claim of compatibility with every Bybit mode is not. Define mark-price use, funding timing, risk tiers, quantity/price precision, minimum order size, and unavailable historical risk information.

Define signal/order/fill ordering, gaps, simultaneous stop/take/liquidation events, entry/exit conflicts, and open positions at test end. Definitions of realized/unrealized PnL, equity, drawdown, win rate, and costs must be explicit and comparable.

### Results and persistence

Provide candlesticks with the indicators actually used by the run, entry/exit markers, a trade table, PnL, drawdown, trade count, win rate, and included costs. Selecting a trade navigates to its chart region. Manual chart drawings, playback, and a detailed condition debugger are deferred.

Save every run independently with immutable strategy and parameter snapshots, simulation settings, dataset information, trades, and metrics. Editing a strategy must not overwrite earlier results. Include run history and a simple comparison table. Parameter search was deferred in 0.1; 0.2 permits only the bounded visual-strategy experiments in section 16.

Record data provenance, range, schema, checksums, runtime/engine versions, parameters, strategy snapshot, and modeling assumptions. A dependency lockfile alone cannot reproduce changed market data. Preserve normalized results alongside engine artifacts. Comparisons must expose differing profiles, versions, and metric definitions.

## 6. Application behavior and export

Use an English single-window UI with Strategy, Backtest, and Results tabs, a strategy list on the left, and context settings on the right. Panels may collapse; arbitrary docking is optional. A dark theme is proposed, not mandatory. Russian localization is not required.

Run one backtest at a time. Keep the UI responsive with progress and logs. Support cancellation. Each worker receives an immutable snapshot, not live editor state. Minimizing does not stop a run. Closing during a run prompts to return or cancel and exit. Queues, parallel tests, and resuming after reboot are outside 0.1.

Export a project archive with strategy, settings, and selected results. Exclude secrets. Historical datasets are not copied by default; include their description. Optional data inclusion is deferred. A description cannot replace the data, and importing an archive without recoverable history cannot guarantee rerunning it. Distinguish viewing saved results from recalculation.

## 7. Trust and security

Require explicit trust before loading an imported Python module. Selection, preview, opening, and reopening must not execute imported code. Missing dependencies produce actionable errors; installing them requires permission. An embedded package manager is not required.

Worker processes improve lifecycle control and responsiveness but are not a security sandbox. Stronger isolation and network/filesystem restrictions require separate design before wider execution of untrusted strategies. A warning alone does not neutralize malicious Python.

The historical module does not accept exchange credentials. Use a bounded, versioned IPC command set. Validate archive paths and contents, reject traversal and unsafe destinations, and enforce size/resource limits. Do not expose eval/exec through graph nodes. Record strategy/dependency provenance and license obligations.

## 8. Proposed architecture

The baseline is Tauri 2; React, TypeScript, and Vite; React Flow; Lightweight Charts; Python; Pydantic; JSON Strategy IR; SQLite metadata; Parquet data; uv with pinned dependencies. NautilusTrader 1.231.0 is the selected first engine; see ADR 0001. Exact package versions, Python ABI, Node/Rust toolchains, SQLite access, validation, and test tools require compatibility checks. A simpler reliable replacement is possible with evidence in an ADR; product behavior must remain intact.

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

After 0.1: market signals, Telegram, Windows/audio notifications, dry-run and live execution, multiple pairs, DCA/partial exits, visual multi-timeframe graphs, general optimization beyond the bounded 0.2 experiments, other engines, stronger isolation, installers, and other OS releases. Telegram remains a required future notification channel. Background-service deployment and playback are outside 0.1.

AI is an optional final-stage extension, using user-supplied API access or a paid option that covers its costs; a local model is optional. Core research functionality must work without AI. No provider-funded token usage for free users is assumed. These roadmap items do not authorize their implementation in 0.1.


## 12. 0.2 scope and preservation

Extend the existing engine and Windows stack. Preserve 0.1 markets, position semantics, causal graph evaluation, native Python import/trust and immutable reports. 0.2 adds graph authoring improvements, readable results, a versioned protection model, sequential visual-strategy parameter experiments and explicit later-period validation. An experiment owns a finite sequential queue; there is no general background job server.

Use a consistent SQLite snapshot and preserve referenced immutable artifacts before migration. Verify migration on a copy, including unchanged 0.1 strategy/result values and readable archives. Tests, bulk experiments and demonstrations use separate data roots. Historical source branches and data backups preserve the 0.1 baseline; the normal main checkout runs the current 0.2 build after verified additive migration. A temporary build/worktree must not silently open another workspace's database. Existing 0.1 reports remain viewable without executing code or recalculating them. Opening/copying an old strategy creates new results only after an explicit run.

Still excluded: live orders/current-market signals, paper trading, Telegram/system notifications, AI, DCA/partial exits, new margin modes, visual multiple timeframes, multiple instruments per run, a second engine, arbitrary Python optimization, distributed/parallel calculation, walk-forward optimization, installers and other OS releases. These remain future scope rather than being removed from the roadmap.

## 13. 0.2 graph authoring

Right-click on empty canvas opens a searchable node catalog near the cursor and suppresses the browser menu only there. Focus search immediately; match existing short/full names case-insensitively, group the catalog when empty and show no-match feedback. Arrow keys select, Enter creates, Escape/outside click close. Search/text inputs retain normal editing shortcuts. The four fixed outputs are not catalog entries.

Create exactly one node with a fresh ID/default parameters at the original invocation point converted through the installed React Flow screen-to-graph transform. Pan, zoom, canvas offset, collapsed panels and DPI must not shift that position. Clamp the menu independently to the viewport; do not clip it in parent panels. Select the new node and open settings; do not alter existing nodes or auto-connect it. Node menus may duplicate/delete ordinary nodes while respecting fixed outputs.

Bounded Undo/Redo covers creation, deletion, duplication, parameter edits, connections and positions. One drag is one history action. History is isolated per strategy and shortcuts do not intercept text editing. Selection duplication gives fresh IDs, remaps internal references and deep-copies mutable objects. Create strategy copy produces an independent saved strategy; previous reports and new Python execution consent are not inherited.

Validation identifies the faulty node/port/field and supports navigation. Incomplete drafts remain editable, while invalid runs fail clearly. Preserve typed connections, cycle rejection and all four output semantics.

## 14. 0.2 interface and chart behavior

Dense fills must remain countable/readable with compact markers and hover/selection detail or explicit grouping. Never remove trades or conceal multiple fills in one candle. Preserve meaningful viewport across unrelated renders and verify zoom, trade navigation, pane height and indicator switching. Chart window changes do not change strategy timeframe, and displayed indicators remain saved run values.

Comparison uses human-readable field labels and units while retaining complete data/profile/runtime differences in details. Keep the current tabs/layout and add the targeted Experiments workspace rather than redesigning the application. Check ordinary window sizes and available Windows scaling 100/125/150%; report any unperformed visual checks honestly.

Revisit native file-picker import and cancellation before work finishes using a bounded controlled-duration test. A completed-before-click run is not evidence of cancellation. Native checks unavailable in the current environment remain explicit manual acceptance items.

## 15. 0.2 versioned execution

Retain execution profile 1's discrete O/L/H/C contract under its original version. A new profile distinguishes protective-level crossing inside an assumed continuous segment from a gap or first available observation already beyond the level. Support both O-L-H-C and O-H-L-C. Record assumed path and conditional crossing time; neither is recovered tick data.

Define signal observation, order creation/activation and fill ordering. No order may fill on a segment before it exists. A stop/take-triggered market exit must not silently become a limit order. Within a continuous modeled segment, trigger at the crossed level; across a gap use the first available executable trade price with adverse slippage, not a guaranteed stop price. Document both directions, fee/tick/quantity precision and funding/liquidation/protection conflicts. Mark-price triggers are separate from executable trade prices; no full exchange liquidation-mechanism equivalence is claimed. Preserve primary-timeframe causality and minute-close partial-H1 evaluation.

Independent no-cost example: long entry100, stop95/take105, next minute O100/L80/H120/C100 exits at95 on OLHC and105 on OHLC. A next open below95 must not guarantee95. Add short, gap, activation, costs and conflict examples with independent expectations; compare execution profiles 1/2 on identical inputs. Explain baseline changes by contract rather than changing expectations to match output.

Version profile semantics in snapshots, comparisons and calculation/cache identity. Preserve old reports/metrics. A new run is a new record with explicit profile choice. Only claim old-profile replay when its semantics remain supported; otherwise explain unavailable old runtime without blocking report viewing.

## 16. 0.2 parameter experiments

Experiments select a saved visual strategy, instrument/dataset, range and execution profile, then finite lists of node parameters and allowed risk controls such as stop/take. Address stable node IDs and fields through typed schemas, never executable expressions. Costs, data and execution model are fixed across the batch; do not optimize fees/funding/execution quality or introspect arbitrary Python.

Validate integers, percentages, enums and bounds; deduplicate equivalent values before counting. Check product size before materializing it. Preview count, inputs and warnings before start. Document and measure a finite combination/resource limit, independent of historical range limits. RSI periods[14,21,28], thresholds[25,30,35], stops[1%,2%,3%] form27 unique combinations.

Freeze grid, graph, dataset/ranges, versions, fixed profile and varied fields before execution. Each combination uses the ordinary calculation path, independent flat state/capital and its own immutable snapshot. Later editor changes cannot affect queued combinations. One worker globally within the application: a standalone run cannot overlap a batch. Sequential progress reports completed/total, current parameters, errors and cancellation. Cancel stops current and future work while retaining completed reports. Close prompts return or cancel batch/exit. Interrupted rows never become success or automatically resume after restart.

Results show parameters, Net PnL(USDT), Max drawdown, Trades, Win rate, Costs and status; support sorting and drawdown/min-trades filters. Failed/cancelled rows are excluded from successful rankings and no-trade win rate remains undefined. Do not label any result a profitable strategy or recommendation. Open normal reports and create independent strategy copies from chosen results. Persist experiment/grid/run IDs/selected values using existing storage; avoid duplicating raw candle arrays per combination. Selected-result archives retain essential experiment provenance, not the whole dataset or arbitrary code/trust.

## 17. 0.2 out-of-sample validation

Predeclare in-sample selection range and a strictly later disjoint out-of-sample range in UTC. Enumerate/rank only in-sample results; selection tables do not receive OOS metrics. After explicit candidate choice and validation action, freeze parameters/profile/candidate identity and run that attempt once through the same calculation path. No automatic reselection based on OOS performance.

Permitted preceding-data warmup must not create trades, costs/funding for absent positions or OOS statistics. Start OOS with fresh flat state and explicit capital, not IS positions/wealth. Explain boundaries, coverage and insufficient warmup. Report IS/OOS separately without concatenating equity or PnL. Parameter changes create new versions/attempts and retain old ones. Warn that repeatedly inspecting the same period does not create a fresh untouched holdout.

An automated demo uses a predeclared synthetic candidate rather than selecting the observed OOS maximum. Perturbing OOS data must not change the IS grid, ranking or frozen selected snapshot. The OOS run equals a standalone run with the same range/warmup/execution contract.

## 18. 0.2 required validation

Verify node creation coordinates and single insertion after pan/zoom/resize/panel changes; cancel leaves graph intact. Undo/Redo restores nodes/parameters/edges/layout, copies are independent and invalid fields are navigable. Dense-fill displays retain all executions.

Independent protective execution tests cover both versions, directions, paths, crossing/gaps, activation, costs and conflicts. Migration preserves exact 0.1 strategy/result values and archive readability. A2x2 batch produces four unique results identical to corresponding single runs including trades/costs. Test editor mutation, invalid parameters, worker failures, cancellation and interruption without losing completed runs or starting extra work.

OOS never participates in selection; verify causal warmup/fresh capital and future perturbation. Build Windows separately, reopen results, check import/navigation/active-batch cancellation and child cleanup. Distinguish component/automated/native checks from manual acceptance. Document exact commands, actual outcomes, bounded time/memory observations and limitations. Prepare an independent-data 0.2 demo; preserve 0.1 golden tests or explicitly version changed contracts. Do not expand into 0.3.
