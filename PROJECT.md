# Trading Terminal product specification

Product 0.5.1-dev was accepted through the owner-authorized conditional squash merge of PR #6. Product 0.6-dev is authorized for development, not accepted. Section 23 defines this extension; earlier behavior and immutable results remain supported.

Current accepted product: 0.5 development build (`0.5-dev`). Sections 1–20 retain the historical 0.1–0.4 contracts; section 21 defines the 0.5 extension and supersedes their scope exclusions only for explicitly listed features. Stored results retain their original versioned execution assumptions. Owner manual acceptance permits the 0.5 merge with remaining UI/UX issues deferred; it does not retroactively establish unperformed automated native measurements. Telegram delivery remains unverified and outside acceptance. This file is the sole current technical specification. ADRs explain implementations without silently removing requirements. Public artifacts are English; historical archives are not competing specifications.

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

OOS never participates in selection; verify causal warmup/fresh capital and future perturbation. Build Windows separately, reopen results, check import/navigation/active-batch cancellation and child cleanup. Distinguish component/automated/native checks from manual acceptance. Document exact commands, actual outcomes, bounded time/memory observations and limitations. Prepare an independent-data 0.2 demo; preserve 0.1 golden tests or explicitly version changed contracts. This was the 0.2 acceptance boundary; section 19 separately authorizes 0.3.

## 19. Product 0.3: live monitoring and paper trading

### Shared strategy semantics

Run a strategy already usable in historical backtesting against public live Bybit data without submitting exchange orders. Keep the selected stack/engine. Historical, live and recorded replay use the same Strategy IR indicators, initialization, crossings, Boolean logic, UTC timeframe boundaries, closed/forming-bar evaluation and transitions. Do not introduce a simplified live strategy. Document differences between observed live execution and historical synthetic paths. Forming primary-bar evaluation retains confirmed M1 updates inside the primary bar; live ticks may update price/protection without silently changing the IR evaluation cadence. Unsupported native behavior must fail visibly, never silently convert source into graph logic.

### Public data, recovery and persistence

Support one active strategy/instrument session. Use public spot and linear Bybit WebSocket market streams plus authorized REST history, without exchange credentials or order endpoints. Distinguish trade/last price, confirmed candles, mark and funding. Validate initial connection, disconnect/reconnect, duplicates, stale/out-of-order events, Windows sleep/wake, short network interruptions and missing minute ranges. Use backoff and prevent duplicated subscriptions/retry storms.

Before returning to CONNECTED after a gap, determine the missing range, reconstruct complete history, recalculate state, and verify synchronization. No notifications may escape unverified intermediate recovery state. A connected socket alone does not establish valid strategy state. Persist last valid data time, strategy/profile identity, session state and paper position. Restart discloses interrupted activity and requires recovery/revalidation when safe continuity cannot be established; never blindly resume paper trading over a long gap. Closing the application stops monitoring; no Windows service or always-on daemon.

### Signal events and notifications

FALSE→TRUE creates one event, TRUE→TRUE creates none, TRUE→FALSE resets. Store session, strategy identity/version, instrument, market, timeframe, evaluation mode, event type, observed timestamp, applicable observed/executable price and indicator snapshot. Define restart and durable notification-attempt semantics to avoid accidentally replaying old alerts. Distinguish warmup/recovered events from newly observed live events.

Provide independent Windows native, optional sound and direct local Telegram channels, with a Test control for each. Support Entry/Exit Long/Short; useful connection/recovery errors and paper protection events may also notify. Telegram configuration, test and clear use an owner UI flow and protected Windows credential storage. Never save token/chat ID in plaintext SQLite/JSON, logs, exports, screenshots/demo records, public diagnostics or task descriptions. Never reveal the full saved token. Delivery failure must not block strategy evaluation; bound dispatch queues and retries. Mock tests are not evidence of native Windows delivery. Owner-entered Telegram credentials are optional for manual acceptance, never requested through chat.

### Observed-price paper account

Use the retained engine/account model for one virtual position: initial capital, unborrowed spot, supported perpetual long/short, entry/full exit, simple stop/take, fees, explicit slippage, funding when adequately observed, PnL/equity and trade history. Execute from actual observed prices/events, not copied historical fills or leveraged spot PnL. Separate mark valuation from executable trade price. Disclose fill latency/liquidity, precision/tier/funding assumptions and missing observations. Paper execution is not a promise of real exchange fill equivalence. Recovery cannot invent missed executable ticks; uncertain paper continuity requires explicit revalidation.

### Dashboard and strategy status

Preserve the existing layout with Strategy / Backtest / Experiments / Live / Results. Select strategy, instrument, supported market, primary timeframe, closed/forming evaluation, paper mode and notification channels. Show connection state, current price/candle, recorded indicator values, all four condition states, recent signals, paper position, errors and recovery progress. Show meaningful CONNECTED / RECONNECTING / RECOVERING DATA / PAUSED / ERROR states. Provide readable events such as candle closed, condition became true, position opened, lost connection, recovering missing candles and failed delivery; raw protocol JSON is not the main UI. Simple Backtested/Live/Paper status identifies the monitored strategy without a new workflow engine.

### Node deletion

Delete/Del on the focused canvas removes selected ordinary nodes in one transaction and cleans all references/edges. Inputs, textareas and editable controls keep normal text editing. Fixed Entry/Exit outputs cannot be deleted. Undo restores nodes, layout and connections exactly; Redo repeats the same logical deletion, including multiselect. Node right-click opens a separate extensible menu containing only Delete node for 0.3. It must not open the canvas Add Node menu. Keyboard and context menu call the same underlying operation; the existing canvas search/add behavior remains.

### Recording, safety and acceptance

Persist enough causal live observations for reproducible replay with the same IR and compatible assumptions. Independently expected closed/forming, crossing, duplicate suppression, reconnect/recovered candle, restart/recovery and future-perturbation scenarios must match signal times/types (for example Entry Long at 14:31 in both). Explicitly separate signal equivalence from potentially different paper/historical fill results.

All migrations are additive and first tested on a consistent copy. Preserve existing strategies, runs, experiments, comparisons and archives with exact prior values; backup before ordinary-data migration. Live/demo/testing use separate data roots, never replace user data. Bound in-memory histories, UI logs, dispatch queues and retries; measure a sustained live demonstration and disclose resource limits.

Run all Python/frontend regressions plus deterministic stream/reconnect/gap/staleness/order/restoration/dedup/dispatch/Telegram failure, paper accounting/cost/protection/restart, recording equivalence/future perturbation, deletion/history and migration tests. Financial and temporal goldens use independently expected outcomes. Build and launch Windows from codex/03; verify Live, actual public data, safe reconnect, native notification/sound, paper lifecycle, minimize/restore/shutdown and editor menus/Delete. Test 100%/125%/150% scale where practical without changing unrelated applications. Unperformed native/Telegram/manual checks remain explicit acceptance items.

Keep Linear as the primary tracker with dependencies and actual evidence; Done requires tested behavior. Prepare a reviewed draft PR to main with secret/privacy/license checks. No autonomous main merge. Product 0.3 ends at owner acceptance preparation, not automatic 0.4.

### Exclusions

No real orders, exchange trading credentials, automatic live trading, DCA/averaging, partial exits, trailing/break-even/ATR position management, simultaneous instruments, visual multi-timeframe extension, AI, second engine/exchange, mobile app, background service or installer/release packaging (except a separately justified existing build blocker). No paid services, system security changes, project license assignment, release/tag/deployment or scope expansion.

## 20. Product 0.4: Live Terminal

### Workspace and shared state

Turn Live into a chart-led realtime market workspace retaining the existing visual style and research workflows. A compact market header, main candlestick chart, order book/tape side panels and switchable Position / Strategy / Signals / Paper Trades / Notifications / Log panels replace mandatory long vertical scrolling. Live settings are contextual/collapsible without changing Backtest or Experiments layouts.

Keep one centrally owned public Bybit V5 market pipeline for ticker, candles, order book and recent trades. Verify current official protocol documentation. Do not duplicate equivalent connections for widgets or change the existing Strategy IR/live/replay engine. Display instrument/market, last price, perpetual mark/funding, 24h change/high/low/volume or turnover where provided. Missing/stale data is explicit. CONNECTED, RECONNECTING, RECOVERING, DEGRADED, PAUSED and ERROR must not misrepresent freshness.

### Chart and strategy overlay

Use existing Lightweight Charts. Seed historical context and deterministically merge ordered confirmed/forming candles, recovered data and duplicate messages. Chart interval is independent from strategy timeframe/evaluation: changing display interval must not modify IR, restart the session or change execution. Only expose actually supported intervals. Show real strategy timeframe, evaluation mode and latest evaluation time at all times.

Chart indicator values must be recorded/evaluated Strategy IR values, never frontend RSI/EMA/etc. recomputation. Display signal transitions, paper entries/exits, entry/stop/take/current/mark lines where applicable. Preserve indicator values, four Entry/Exit Long/Short conditions and timestamp/price/value details in readable panels. Retain false-to-true deduplication. UI rendering frequency cannot influence strategy semantics.

### Order book and tape

Initialize book from a snapshot, apply insert/update/zero-size removal deltas, replace on a new valid snapshot/service reset and reject stale/out-of-order input. Reconnect invalidates all old book state; no delta may repair an unknown book without a snapshot. Display about 10–15 levels per side with price/size/relative depth, not complete exchange depth. Prevent duplicate subscriptions.

Recent trades display time, price, size and reliably supplied taker side. Keep a bounded deduplicated buffer; tape persistence is outside scope. After reconnect, explicitly restart tape without claiming missed trades were recovered. Restore candles/strategy history first; retain paper continuity/revalidation rules.

### Paper terminal and manual actions

Clearly label PAPER and show side, instrument, quantity, entry/current/mark price, unrealized and session/realized PnL, stop/take, fees/funding and cash/equity. Add Paper Buy, Paper Sell and Close Paper Position through the existing paper account/execution system. Never create a second account engine, private order endpoint or exchange credential field.

Use a simple frozen session execution source, Strategy or Manual, with documented conflict semantics. Enforce one position, full exits, no scaling/reversal and normal protection/fee/funding rules. Manual commands must execute on a later valid observed quote, not an old displayed price, and must not survive an uncertain reconnect as an automatic order. Validate and record actions/restart behavior without duplicate fills.

### Telegram investigation and resource safety

Investigate ILI-37 within a bounded scope using current official Bot API documentation and reviewed prior diagnostics. Preserve Windows Credential Manager storage; never expose token/chat ID, provider URLs or credential-bearing exception details. Report safe actionable error categories for request/configuration/network/response failures. Do not claim mocked success proves delivery. ILI-37 remains open if real delivery needs owner acceptance and is not a 0.4 completion blocker.

Bound tape, event logs, UI arrays, chart history, queues and retries. Batch/throttle rendering independently from strategy processing; clean up timers/subscriptions. Preserve historical research, native Python, editor/context-menu/Delete/Undo/Redo, experiments/results, notifications and live/replay regressions.

### Acceptance and preservation

All migrations are additive and tested on a copy before ordinary data use. Preserve all strategies, runs, experiments, result files, live sessions, signals and paper history; use separate test/demo roots. Deterministic tests cover book snapshot/delta/reset/zero removal/staleness, ticker/tape bounds, recovery/deduplication, chart/strategy interval isolation, overlay/layout/panels/settings, manual paper lifecycle/conflicts/restart, credential-safe diagnostics and absence of private order APIs.

Run the actual public compiled Live Terminal for at least 30 minutes (prefer 30–60). Record UTC start/end, memory/process counts, reconnects, ticker/candle/book/trade counters, evaluation/error state and subscription evidence. Confirm responsive UI and ongoing forming candles/book/tape/evaluation without notification storms. Distinguish natural reconnect from injected deterministic tests. Full Python/frontend suites, TypeScript/Vite and Windows/Rust build must pass. Document exact evidence, limitations and remaining manual checks; update Linear and open a reviewed Draft PR from codex/04 to main. Do not merge or start 0.5.

Real exchange trading and its credentials remain prohibited. Other exclusions remain: DCA, averaging, partial exits, trailing stop, break-even stop, ATR position management, multiple active instruments, multi-timeframe visual IR, AI, another engine or exchange, installers, releases and background services. Manual PAPER controls do not enable real trading.

## 21. Product 0.5: independent market terminal and Position Management

### Independent market and chart lifecycle

Opening Live provides chart, ticker/header, order book and bounded tape without any selected strategy. Pausing/stopping monitoring, changing selected strategy, disabling signals or paper, and strategy warmup must not stop or unnecessarily reset the market view. Keep central public-stream ownership and separate Market Ready, Strategy Ready and Paper Ready states. Strategy readiness requires complete causal history; strategy-driven signals/notifications/orders cannot escape warmup or recovery. Manual paper may depend on validated market/account readiness without requiring strategy readiness.

Reproduce and measure the H1/closed startup defect before changing it. Record recovery start/pages/minute counts, first usable chart/ticker/book/trade, strategy-ready and paper-ready times on cold and warm cache. Do not shorten required causal history for a faster score. Intermediate warmup tails must never become the visible market chart. Show meaningful preparation progress, such as recovered/required M1, independently from current market freshness.

Chart history is a market feature, independent of strategy journals. Use native public Bybit intervals 1m/5m/15m/1H/4H/1D where supported. Load a recent bounded page, then preceding pages when the user pans left. Deduplicate overlaps, order deterministically, preserve viewport on prepend and keep the realtime candle attached to the newest range. Never download all history at startup or keep all exchange history in React. Cache by source/market/symbol/interval/schema/range using existing SQLite storage; render cached history promptly and fetch missing/recent ranges. Clearly disclose actual available exchange coverage. Changing display interval never changes IR, strategy timeframe, paper position, signal history or warmup. Chart indicators remain actual recorded IR values, never independently calculated frontend indicators.

### Shared Position Management contract

Add one explicit versioned, bounded Position Management model between signals and Backtest/Paper execution. Retain the selected engine, Decimal precision and risk/accounting assumptions. Future execution adapters may consume normalized decisions; no real execution is authorized. Legacy strategies without these fields retain no-scaling, full-exit and prior stop/take behavior. Old snapshots/results keep their original assumptions and are never silently recalculated.

Support optional Ignore/Scale repeated same-direction entry transitions and configurable bounded DCA steps with adverse price distance and allocation. Enforce maximum notional, capital allocation percentage, entry count and existing leverage constraints. Rejected additions produce explicit diagnostics. Scaling updates total quantity, weighted entry, margin, exposure, fees/funding, cash/equity and realized/unrealized PnL. Partial TP reduces a declared portion while retaining one position identity, correctly allocating costs and releasing margin; final close closes only the remainder.

Add activation/distance trailing, fee/cost-aware break-even, ATR stop and ATR trailing with mirrored long/short semantics. Define causal priority for liquidation, stops/trailing/BE, partial TP, strategy exit, manual reduction and DCA. No mode may invent its own ordering or use future extrema/ATR. Keep configuration understandable in a dedicated Position Management section rather than forcing risk management into graph nodes.

Add read-only typed IR nodes for Position Side, Position Size, Average Entry Price, Unrealized PnL %, and Bars Since Entry. Their observation boundary must be deterministic in historical and paper execution; never expose arbitrary mutable account state. Shared IR still defines indicators, crossings, Boolean logic and timeframe boundaries.

### Integration and results

Backtest and Paper share position decisions/accounting semantics and normalized lifecycle records: initial entry, additions, average-entry changes, reductions, stop changes, TP, funding/fees and final close/PnL. A scale is not an unrelated trade. Results show lifecycle direction/open/close, entry/reduction counts, average entry, final PnL, costs and maximum exposure with inspectable events. Paper consumes observed quotes rather than historical path fills, preserves one-position/source/recovery rules and adds manual Add, Reduce 25%, Reduce 50% and Close through the same model.

Live PAPER presentation shows side/quantity/average/current/mark, margin/exposure, realized/unrealized PnL, fees/funding, active stop/trailing/BE/TP and entry count. Chart displays entries, reductions, average-entry and protection levels without excessive clutter. Experiments may vary validated DCA, allocation, trailing and ATR parameters while enforcing all constraints; candidates execute the exact standalone Backtest path and preserve frozen later-period validation.

### Verification, compatibility and limits

Before downstream accounting integration, independent synthetic long/short goldens must reconcile weighted entries, scale/full/partial/final exits, fees/funding across entries, trailing, cost-aware BE, ATR and allocation rejection. Verify realized/unrealized and cash/equity reconciliation, maintenance/liquidation after scaling/reduction, rounding/minimum size, end close and deterministic repeats. Failure to reconcile is a blocker, not grounds to weaken expected results.

Preserve all 0.1–0.4 strategies/runs/results/experiments/live sessions/signals/paper journals and caches. Additive migrations run on consistent copies first; goldens/demo/public probes use separate data roots. Verify no-strategy market, paused tracking, H1 warmup, strategy/display switches, lazy history/viewport and cached restart. Test native chart pages/cache/dedup/current candle on 5m/1H/4H/1D. Run full Python/frontend regressions, TypeScript/Vite and Windows build, plus compiled public Live Terminal for at least 30 minutes with historical paging, active strategy/account, bounded memory/buffers, subscription/reconnect/retry and notification observations. Distinguish native evidence, deterministic mocks and unperformed manual checks.

Telegram ILI-37 remains open and intentionally deferred; preserve protected storage and known-issue status, running regression only where shared code changes. No Telegram investigation, real orders/private exchange credentials/accounts/positions, multiple live instruments/strategies, second engine/exchange, AI, visual multi-timeframe IR, installer/release or background service. Linear is the primary tracker. Work in codex/05; publish reviewed small commits and a draft PR to main, with secret/privacy/provenance checks. No main merge, release/tag, history rewrite or 0.6. Completion requires all listed behavior, reconciled goldens, preserved data, measured 30+ minute Windows evidence, current docs/Linear and draft PR; disclose all remaining manual limitations.


## 22. Product 0.5.1 maintenance

The authorized maintenance target is `0.5.1-dev` on `codex/051`, based on accepted 0.5-dev. Scope is limited to retryable chart-history paging, bounded access to older Results, asynchronous recorded Replay, and one budgeted final validation. No 0.6 work or Telegram investigation is included.

Only a successful chart page may confirm end-of-history. Results use deterministic newest-first cursor pages without changing immutable records. Replay uses the existing managed worker lifecycle with start/status/progress/completion/error/cancellation; ordinary IPC stays responsive. Cancelled/interrupted Replay never reports successful completion. Existing signal/accounting contracts remain unchanged. See [maintenance design](docs/adr/0020-maintenance-paging-replay.md) and [status](docs/STATUS.md) for actual evidence and remaining acceptance limits.

## 23. Product 0.6 Strategy Library

The authorized core contains five distinct reviewed strategies across at least three approach families, including a compatible native Python path. First deliver two strategies end to end, then expand. Baselines and parameter variants do not count. Source selection records immutable provenance, license, review, adaptations, typed defaults, warmup and compatibility. Distinguish author-recommended, source-default and locally tested timeframes. Browsing never loads Python; explicit hash-bound native consent remains mandatory.

Use the existing engine/jobs for sequential independent multi-strategy research, bounded workload preview, asynchronous shared data preparation, persisted row states, cancellation retaining completed rows and explicit unchanged-input pending-row resume. Freeze source, parameters, runtime/profile/data identity and capital. No automatic resume, second engine, parallel portfolio or exhaustive Cartesian search.

Buy & Hold and scheduled DCA use the same initial capital available at evaluation start, actual spot data and retained cost/precision/fill primitives. DCA divides that capital over predeclared daily/weekly/monthly UTC dates inside [start,end); unused cash remains in equity, and purchases do not occur at final liquidation. Warmup creates no trades/performance. Common default end treatment closes fully with costs. Cache baselines by the full immutable contract; perpetual comparisons are explicitly different spot capital alternatives, or N/A when spot data is unavailable.

Backend saved metrics include net PnL, period return, final equity, drawdown, completed position lifecycles, nullable win rate, costs and baseline deltas. Annualized geometric return uses (final_equity/initial_capital)^(365/elapsed_days)-1, defaults to N/A below 365 days or for invalid equity/cashflows, and is never labeled advertised APR. Changing capital requires a real rerun.

Cards and sortable table expose provenance, compatibility, original/default versus chosen timeframe, actual saved-report links, comparison equity and Create my copy. Bundled templates remain immutable. Input changes label old results stale; untested/failed values are N/A. Rank comparable cohorts only. Freeze selected candidates before separate later-period validation with fresh capital/baselines; retain attempted variants, source dates and repeated-holdout warnings.

Count a strategy only after independent nontrivial synthetic evidence and a finite cached public-data integration run; losses remain valid observations. Preserve accepted features, native trust and user data using copied additive migration checks. Six–ten strategies are optional only after the core and owner budget gate. No Telegram, real trading, new license, 0.7, release or 0.6 merge is authorized. Actual verified progress is recorded in STATUS.md; partial safe checkpoints are not completed core acceptance.
