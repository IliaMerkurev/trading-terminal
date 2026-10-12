# Trading Terminal product specification

## Saved backtest comparability extension — 2026-10-12

The owner approved a bounded read-only review of saved comparison conditions:
data/content/coverage, declared and recorded periods, capital, costs and execution
contracts. Missing historical evidence stays unknown. Preserve saved results and
existing metrics; do not rerun, reprice, rank or infer equivalence. See the
[comparability acceptance record](docs/BACKTEST_COMPARABILITY.md). Arbitrary new
saved-comparison workflows, merge and release remain later scope.

## Saved backtest trade review extension — 2026-10-12

The authorized development continuation improves the existing saved Results
workflow with one selected-trade inspector, actual entry/exit/lifecycle chart
navigation, saved costs and immutable strategy context. Preserve source clocks,
DCA/partial-fill accounting and explicit unavailable condition evidence. Do not
recompute historical signals or add an execution model. See the bounded
[trade-review acceptance record](docs/BACKTEST_TRADE_REVIEW.md). Product stays
0.6-dev; merge, release and later roadmap slices remain separate.

## Saved indicator rule to strategy extension — 2026-10-12

The owner authorized a bounded saved-rule conversion flow into the existing
strategy editor and backtest workflow. Preserve the exact frozen rule meaning
and provenance, expose execution defaults for review, and create an independent
editable strategy without starting execution. Unsupported contexts must fail
explicitly rather than approximate. The first-slice acceptance boundary is
[documented here](docs/RULE_STRATEGY_CONVERSION.md). Product remains 0.6-dev;
this authorization does not include a merge, release or later roadmap slices.

## Project license — 2026-10-10

The owner selected the [MIT License](LICENSE) for Trading Terminal. This explicit
authorization supersedes earlier project-license exclusions only for adopting MIT;
all other scope and publication limits remain in force. Third-party components
and market data retain their own licenses and provider terms. See
[third-party notices](THIRD_PARTY_NOTICES.md).

## Current authorized research-workspace extension

The owner authorized a simpler card-first Research workspace with a retained Pro
editor, reusable/updatable local history, explicit faster closed-bar backtests,
longer-horizon strategy candidates and timeframe comparison on 2026-09-30.
This extends section 23 without a product-version bump. Existing live features
remain available in Pro; current work prioritizes backtests. Preserve accounting,
native trust, immutable results and independent validation. See
[ADR 0025](docs/adr/0025-research-resolution.md). Git checkpoints are authorized;
merge, release and deployment remain separate owner decisions. Linear updates
are not required for this work. Finish the current safe milestone and stop adding
scope when account remaining usage falls below 10 percent.

Product 0.5.1-dev was accepted through the owner-authorized conditional squash merge of PR #6. Product 0.6-dev is authorized for development, not accepted. Section 23 defines this extension; earlier behavior and immutable results remain supported.

Historical accepted 0.5 baseline: `0.5-dev`; the accepted 0.5.1 maintenance checkpoint is recorded above. Current 0.6 development is not owner-accepted. Sections 1–20 retain the historical 0.1–0.4 contracts; section 21 defines the 0.5 extension and supersedes their scope exclusions only for explicitly listed features. Stored results retain their original versioned execution assumptions. Owner manual acceptance permits the 0.5 merge with remaining UI/UX issues deferred; it does not retroactively establish unperformed automated native measurements. Telegram delivery remains unverified and outside acceptance. This file is the sole current technical specification. ADRs explain implementations without silently removing requirements. Public artifacts are English; historical archives are not competing specifications.

## 1. Purpose and delivery target

Build a local desktop application for historical strategy research. The complete workflow is: create or import a strategy, prepare historical data, run a backtest, inspect trades and metrics, change parameters, and compare saved runs. The application does not promise profitable strategies. Example indicator strategies are test scenarios, not recommendations.

0.1 targets Windows 11 x64 with a 32 GB RAM reference configuration. Establish performance and memory budgets through measurements. Linux/macOS portability should remain feasible, but their releases and verification are outside 0.1. A documented development launch script with one-time setup is acceptable before a conventional installer. The project is licensed under the [MIT License](LICENSE).

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


### Owner-authorized usability refinement — 2026-09-30

The card-first extension uses task navigation: Strategy library, Market data,
Saved tests and Strategy editor. This supersedes the Research/Pro switch and
earlier tab names while retaining their capabilities under explicit tasks or
More tools. Direct card testing needs no editable copy; Customize strategy
creates an independent draft. Selection and active work survive navigation.
History preparation returns to the preserved test setup. Review shows the
actual period, capital, costs, variants and passive comparisons before start.
Saved comparisons and individual reports remain reopenable without execution.
Later-period verification has its own date/data controls and uses the original
candidate's frozen settings. See [ADR 0027](docs/adr/0027-task-oriented-testing-workspace.md).


### Owner-authorized catalog batch comparison — 2026-09-30

Provide a Test all strategies action that forms the full catalog by a shared,
explicitly selected timeframe set. Default to 4h and 1d. Search/family filters
must not silently reduce the catalog batch. Each strategy retains its current
indicator parameters across timeframes; all rows share history, evaluation
dates, initial capital, sizing, costs and execution settings. Preserve model
versions and native trust; unsupported rows remain visible with reasons.
Persist immutable inputs, row states and results in the existing local database.
Saved comparisons support filters and bidirectional metric sorting within
compatible execution cohorts. This finite matrix is not a parameter optimizer.
At most 96 strategy/timeframe rows plus two passive alternatives are admitted,
with the existing 2,000,000-source-candle workload cap. No product-version bump,
database migration, parallel execution or automatic resume is required.
See [ADR 0028](docs/adr/0028-catalog-batch-comparison.md).


### Original-plan workload admission correction — 2026-10-10

TT10/A4 retains the 2,000,000 modeled source-candle execution cap while counting
actual modeled row windows: full preceding source prefix plus evaluation for
strategies, evaluation only for passive references, zero for unavailable rows,
and no cache discount. Resolve source units per row. Preserve all indicator
history and numerical execution semantics. Thus 600,000 preceding candles plus
100,000 evaluation candles with two passive references counts 900,000 for one
strategy, 1,600,000 for two, and rejects 2,300,000 for three.

Full trade/mark/funding source loading is a separate bounded admission policy,
including suffix history outside the modeled window. Check manifest and physical
Parquet metadata/schema/integrity before eager decoding, retaining normalized
content verification. State materialization estimates honestly; they are not a
peak-memory guarantee. Freeze additive workload version/breakdown and source-load
policy for new contracts; retain the old alias and unchanged historical reports.
See [development guidance](docs/DEVELOPMENT.md#modeled-work-and-independent-full-source-admission-tt10--a4).
Historical A4 slice boundary: independent linear-origin spot contracts, TT13
and bounded research were separate then; subsequent completed evidence is in
[the current checkpoint](docs/CHECKPOINT.md).

### Original-plan independent passive contract — 2026-10-10

TT10/A2 admits an explicit independent spot execution profile and versioned
cost/precision provenance for linear-origin Library comparisons. Use actual
same-source/symbol/resolution spot history, matching initial capital and dates,
and unleveraged passive policies. No futures fees, precision or order limits may
be copied implicitly. Explicit numerical cost sharing is separately reviewed and
frozen. Missing/incomplete optional settings leave passive references N/A without
blocking valid strategies. Provenance participates in the additive benchmark
execution document/hash used by jobs, workers, archives and frozen resume.
Ordinary spot legacy documents remain unchanged when the field is absent.
Later-period verification retains original costs/precision against new history;
current metadata never retroactively changes a frozen result. Manual historical
modeling requires explicit review and a note. Preserve separate risk cohorts and
all TT10/A4 modeled-work/source-loading guards. TT13 and bounded research were
outside this historical A2 slice and are now recorded as completed in the current
checkpoint; Windows/native/live acceptance stays separate.


### Original-plan TT13: recoverable background import slice

The production archive importer uses a managed background process and durable
start/status/attempt-targeted cancellation. Explicit checksum-bound continuation
retains original reserved IDs, verifies completed artifacts and normalized rows,
and inserts only missing verified content. Staged rows remain unavailable as
successful results until per-run atomic visibility. Startup never promotes,
retries or grants source trust. Legacy synchronous finish remains compatibility
only; archive and receipt schema 1 remain readable through additive controls.
See [ADR 0035](docs/adr/0035-asynchronous-recoverable-import.md).

The historical import slice alone did not close TT13. Subsequent export/download,
local finalization and verified-read work is complete under ADRs 0036–0038 and
current STATUS evidence, along with the bounded research program. TT10 modeled/
source budgets and independent spot contracts are unchanged. Windows/native,
new exchange/live and the explicitly conditional data/owner gates remain separate.

### Later authorized bounded catalog additions — 2026-10-11

After the original bounded TT17/TT18 program completed, add C12 Double 7's and
C13 Improved R2 as independently authored daily spot long/flat graph candidates.
Use generic current-inclusive numeric rolling minimum/maximum and completed-bar
lag nodes with editor support. Preserve all existing templates/defaults and
archives. Both candidates initially support historical closed daily execution,
strict gaps, configured profile-2 costs/sizing and no position-management overlay.
Separate synthetic implementation verification from empirical validation, which
has not been established for these additions. Their separately recorded finite
cached-public-data gate is now complete with explicit technical recovery, four
verified outputs and one retained cancelled attempt; it establishes integration
only, not profitable or robust behavior. Source rules, adaptations, authored
rule-summary hashes and limitations are explicit in ADR 0039 and catalog cards.
Test all strategies retains its 4h/1d default and unavailable rows; individual new
cards offer daily only. No optional Supertrend, chart-display indicator controls,
new source acquisition, live orders, main merge or release belongs to this slice.

### Later authorized baseline chart indicators — 2026-10-11

Following the daily catalog addition, add explicitly separate cache-only chart
SMA/EMA/Bollinger Bands/RSI/MACD/native-volume presentation tools, with atomic
parameters/colors/visibility, multiple instances and workspace-local persistence.
This later authorization extends the older recorded-IR-only display restriction;
recorded IR itself and every strategy/financial computation remain unchanged.
Require explicit confirmed provenance, deterministic persisted calculation origins,
gap/warmup disclosure, bounded cancellable off-dispatch replay and independently
verified engine seed conventions. See [ADR 0040](docs/adr/0040-cache-only-chart-indicators.md).
No new data acquisition, real orders, release, version change or Windows claim.

### Later authorized chart workspace convenience — 2026-10-11

Deliver a bounded research-chart workspace using the existing open-source
Lightweight Charts 5.2.1, while retaining MIT application source and Apache-2.0
attribution. This is not TradingView product parity or a Pine runtime. Native
volume defaults to a bottom-of-price overlay on an independent zero-based scale;
explicit per-instance separate-pane placement remains available and persistent.
Legacy volume entries lacking placement migrate additively to overlay. Existing
hidden or removed instances stay hidden or removed. Large volume cannot enter
price autoscaling. Retain the six existing display formulas and source-specific
origins without modifying strategies, execution, signals or immutable results.

Provide quick native timeframes, OHLC/volume hover readout, fit, automatic/manual
and logarithmic price scale controls, and searchable indicator selection with a
bounded settings panel. Provide independently authored horizontal/vertical line,
trend/ray, rectangle, Fibonacci retracement and text tools, plus a transient ruler.
Support selection, body/endpoint movement, color/width/style, candle-OHLC snapping,
hide/lock, deletion and bounded undo/redo. Gestures commit atomically; Escape or
pointer cancellation discards an unfinished gesture. Shortcuts belong only to
the drawing workspace and must not capture typing in inputs.

Persist at most 100 drawings in existing workspace SQLite by source, market and
instrument, shared across native timeframes. Store UTC interval-end time and
price anchors, never screen pixels or mutable bar indexes. Require strict
finite/range/schema/text bounds, optimistic revisions, atomic writes, visible
save errors and stale-response rejection. Drawings remain visual annotations;
there is no execution/trading meaning or new data acquisition. Optional new
indicator formulas are deferred in this first slice. See ADR 0042 for rendering,
acceptance boundaries and implementation limits. No release, main merge,
version bump, subscription, proprietary chart product or dependency installation.

### Later authorized chart indicator and drawing extension — 2026-10-11

Add native-timeframe cache-only display ATR (Wilder with explicit SMA seed),
Stochastic (rolling high/low, SMA K/D) and zero-origin OBV. Preserve the previous
six formulas, source confirmations/origins, bounded replay and native volume
units. Disclose that display ATR initialization differs from graph/recorded IR;
no Pine equality or new strategy/execution support is implied. Add optional
validated custom Fibonacci ratios with labels/reset and optional drawing names
in the existing selector. Legacy version-1 drawings remain readable without
read-time rewrites. See [ADR 0043](docs/adr/0043-chart-indicator-drawing-additions.md)
for formulas, warmup, limits and acceptance boundaries. No new dependency,
provider acquisition, release, main merge or version bump.

### Later authorized chart context ergonomics — 2026-10-11

Move drawing properties into a collapsible in-flow context before all chart
panes, with saved-object access and visible failed-save recovery even when
collapsed. Keep context geometry stable throughout pointer capture and retain
keyboard text-input protections. Add an outside-plot indicator instance legend
with ordered parameter labels, explicit visibility saves and focused settings
access. Preserve unsaved parameter drafts when collapsing; quick actions cannot
overwrite them or bypass loading/save state. Keep numeric axis values readable
without verbose display-series titles, with source-unit and ATR seed caveats
nearby and full provenance still available. See ADR 0044 for exact interaction
and layout limits. This slice is frontend-only; all formulas, backend/schema,
persistence, strategy/trading, dependencies and product version stay unchanged.

### Later authorized explicit latest-chart navigation — 2026-10-11

Provide Return to latest with explicit Following latest / Browsing history states,
independent of feed freshness. Preserve logical zoom, log/manual price options,
indicator settings/origins/drafts and drawings/revisions/undo. Following keeps the
latest candle visible across forming updates, append and the bounded rollover;
manual navigation away stops following. A historical buffer's right edge never
implicitly becomes current. Return navigates a recent buffer directly, or keeps
history visible until a successful bounded recent response replaces it. Loading,
empty/error retry and obsolete-response cancellation must not destroy the visible
graph. Remove obsolete auxiliary timestamps and hover on replacement; ordinary
polls retain accepted indicator data. Keep existing paging/cap/retry contracts,
initial/explicit Fit behavior and all financial/provider boundaries. See
[ADR 0045](docs/adr/0045-chart-latest-navigation.md); no new dependency or product
version is introduced.

### Later authorized Market chart focus — 2026-10-11

Provide reversible Focus chart / Exit chart focus in the actual App / Live market
layout. Temporarily remove surrounding application/quote/paper/book chrome while
retaining the same mounted chart, zoom/following state, price options, indicator
drafts and drawing selection/history. Keep a labelled sticky Exit, essential
source/symbol/market/freshness, reachable timeframe/chart controls and truthful
errors. Use one outer scroll owner with wrapping narrow/short layouts. Escape
must yield to drawing/editor interactions and never discard their drafts merely
to exit focus. Restore normal layout/scroll without persisting a preference;
leaving Live market clears focus. Source namespaces retain their existing reset
rules. Saved history and run charts are not part of this workspace feature.
See [ADR 0046](docs/adr/0046-market-chart-focus.md). No dependency, backend,
provider/network, key, strategy/trading, Windows or product-version change.

### Later authorized chart catalog, styles and formula expansion — 2026-10-11

Deliver a compact reference-inspired Market toolbar and searchable categorized
catalog with type-only UI favorites and a single selected-instance settings
editor. Preserve atomic whole-draft saves/revisions, hidden-instance cap of eight,
source namespaces, focus/Return, source-unit and seed disclosures. Collapse keeps
drafts; Cancel discards. Catalog/controls must remain reachable in flow without
covering axes, handles or Exit. No inert service or chart-style controls.

Continue in gated slices with candles/Heikin Ashi/line and a finite 30-type free-
compatible display catalog. HA must use a stable cache-derived origin, explicit
synthetic-price labeling and independent seed/gap/paging tests; raw prices,
indicator inputs and all trading/recorded IR stay unchanged. Formula additions
need bounded contracts, independent fixtures, causality, persistence and series
integration before catalog exposure. The current integrated candidate exposes all 30 implemented types with bounded
catalog pagination and Candles/Heikin Ashi/raw-close Line. Advanced integration
adds explicit UTC VWAP coverage, local SAR dots and causal Ichimoku primitive
projections; see ADRs 0049 and 0050. The bounded 30-type implementation and
actual-App browser milestone passed through corrected source `e4d35a0`; this is
not whole-product, platform-parity, live-provider, Windows/native or owner-led
unaided acceptance. Earlier bounded synthetic actual-App acceptance for
price styles and the 21-type catalog passed on corrected source `7086f36`. Price style
is transient and resets to Candles on reload; indicator/drawing persistence
remains unchanged. See the
[expansion plan](docs/CHART_EXPANSION_PLAN.md) and [ADR 0047](docs/adr/0047-market-indicator-catalog.md).
No Pine runtime, paid chart package, additional dependency, provider acquisition,
strategy/trading change, product-version bump, release or main merge is implied.

The chart styles and first twelve formula additions follow [ADR 0048](docs/adr/0048-chart-price-styles-and-formula-batch.md).

### Later authorized removal of fixed indicator-instance limits — 2026-10-11

There is no fixed count limit for visible or hidden chart indicator instances.
Hidden instances are not calculated. Large result/settings transport must be
paged and coherent; applying settings remains atomic and revision-checked.
Explicit byte/work safety guards remain and must never truncate settings or
claim unlimited hardware. ADR 0051 supersedes earlier eight-instance references;
unchanged historical bar/origin, strategy/trading and provider boundaries apply.
See [ADR 0051](docs/adr/0051-uncapped-indicator-instances.md).

### Later authorized VuManChu display extension — 2026-10-11

The chart catalog now contains 33 implemented types, adding Cipher B Core +
confirmed divergences, Cipher A and Swing Free. Preserve raw-price inputs,
confirmed native-timeframe causality, two-bar divergence confirmation delay,
atomic numeric/event snapshots, source namespaces and saved origins. Use accurate
Fast WT and candle-body-proxy flow labels; omit Sommi/MTF/Schaff features and do
not claim Pine or proprietary-product parity. ADR 0051's no-fixed-instance-limit
contract and existing 10,000 input / 1,800 viewport, 64 MiB serialized / estimated
256 MiB working-resource guards remain unchanged. See [ADR 0052](docs/adr/0052-vumanchu-display-events.md)
and [third-party notices](THIRD_PARTY_NOTICES.md) for the file-level MPL-2.0
exception, source availability and exact scope. No strategy/trading, dependency,
provider, product-version, release or main-merge change is authorized here.

### Later authorized named indicator presets — 2026-10-11

Provide a local workspace preset library with Save current, staged selection,
explicit Apply, Duplicate/Save as, Rename and recoverable Trash/Restore. The
library is reusable across chart namespaces, but Apply affects only the current
source/market/symbol. Save current captures the applied revision, not unapplied
edits; never silently overwrite existing preset content or discard dirty work.
Preserve all typed parameters, hidden instances, colors and placement. Empty
presets are valid. Keep atomic revision guards, resource-bounded paged transport
and no fixed preset/indicator count quota. Never transplant calculation origins,
history, alerts or execution state. Retain a versioned extension seam for later
pane layouts without implementing panes or alerts in this slice. See
[ADR 0053](docs/adr/0053-named-indicator-presets.md). Current Windows/native,
live-provider and owner-led acceptance are deferred; development does not imply
publication, release or acceptance.

### Reconstructed compatible chart pane layout — 2026-10-12

Provide persistent pane order, relative weights and compatible indicator groups
as part of the same atomic indicator Apply/Cancel revision. RSI/Stochastic share
0–100; MACD/Momentum share price differences; ATR/standard deviation share the
separate price-distance unit. VMC B remains an exclusive signed group, with all
seven ports together. Price stays first and Recorded IR separate and last.
Hidden panes release space but retain order/weight. Extra panes are linear;
price scale options and the independent volume overlay scale are preserved.
Preset snapshots include supported layout, while old presets retain legacy
kind grouping and unsupported extensions cannot be staged. There is no fixed
pane-count quota. Layout-only edits preserve formulas, values and origins.
See [ADR 0054](docs/adr/0054-compatible-chart-pane-layout.md). This reconstructed
implementation does not establish byte identity with unavailable historical
source or compatibility with unavailable old databases. Platform, actual-browser
and owner acceptance are recorded separately from focused automated checks.

### Later authorized frozen local indicator alerts — local restoration

Restore local indicator rules with exact source/market/symbol/native interval,
frozen normalized formula parameters and saved seed origins. Supported bounded
expressions are level states, causal crossings and confirmed VMC B divergences,
with 1–16 conditions in one same-close ALL/ANY group. Preserve unknown states;
state-only rules emit on consecutive known false → true, never initial or
unknown → true. Saved rules have no fixed count quota; serialized definition,
active-set and computation resource budgets remain explicit.

Frozen calculations survive hiding/deleting graph originals. Changed surviving
parameters require explicit reviewed paused rebind. Rules are saved paused and
startup never restores monitoring. Local immutable event evidence and cursor
advance must be atomic and deduplicated, with exact raw-open/confirmed-close/
pivot clocks and separate observation time. Read state and recoverable rule
Trash/Restore are durable. No strategy conversion, new formulas, providers,
orders, PAPER or external notification is part of this restoration.

The current checkpoint implements the pure core/storage and a passive observed
runtime with strict Service routes, explicit asynchronous Arm, UI session/context
registration, periodic source/input fences and durable uncertain-reply recovery.
The reconstructed local UI adds paged rule CRUD/archive/restore, catalog-driven
condition capture, separate reviewed preview and Arm, explicit paused rebind,
uncertain-write reconciliation, journal/read state and at-most-once banner
attempts. A stable App-level session controller fences context changes even
when the panel is collapsed. Historical scans remain a separate milestone.
See [the interface contract](docs/ALERT_UI.md). [ADR 0055](docs/adr/0055-frozen-local-indicator-alert-core.md)
records core semantics; [ADR 0056](docs/adr/0056-passive-local-alert-runtime.md)
records the bounded runtime and [Service contract](docs/ALERT_RUNTIME_API.md). Original old-alert schema
compatibility is unverified because authentic fixtures are unavailable. Product
remains 0.6-dev; implementation does not establish release or owner acceptance.

### Later authorized cached alert-history and evidence backend restoration

Provide asynchronous durable scans of a reviewed frozen alert revision over an
inclusive UTC confirmed-close range. Snapshot the complete contiguous confirmed
raw cache from the frozen origin through End, replay all pre-range warmup through
the existing formulas, and persist per-close values/evidence. No provider fetch,
reseed, gap fill, truncation or alternate formula engine is allowed. Preserve
immutable completed rule/raw/value snapshots across edits and restart; expose
unknown values separately from false. Limit full-origin work to 10,000 raw rows
and an estimated 256 MiB, eight unfinished jobs, and existing definition/response
byte guards. Cancellation/interruption never claims complete coverage or resumes
automatically. Durable request identities permit read-only lost-reply recovery.

Keep saved runs/matches paged at 20 and chart windows at most 200 plus bytes;
markers include all matches in the displayed window. Exact close/raw-open lookup
must never substitute a nearby candle, and byte-shortened navigation discloses
an omitted target with an exact fallback. Original event evidence remains
immutable and authoritative, with separately labeled current-cache price context
and explicit missing/unconfirmed target states. Reads and scans do not alter
Market, Arm, cursor, live journal, unread state or banner claims. See
[ADR 0058](docs/adr/0058-cache-only-alert-history-evidence.md) and the
[Service API](docs/ALERT_HISTORY_API.md). Frontend and agreement-condition/history
integration remain separately scoped; no old-schema, Windows or live-provider
acceptance is implied by this reconstructed backend.

### Reconstructed current indicator-agreement panel — 2026-10-12

Provide a compact below-chart summary of applied visible display indicators at
the common latest confirmed raw close in the recent buffer. Reuse the shared
versioned agreement manifest/evaluator and existing verified display response;
introduce no formula engine, data acquisition, provider call or monitoring.
Exclude hidden, unavailable, context-only and unsupported members explicitly.
Show up/down/neutral, exact UTC, group distributions/conflict, fully covered
supported visible types and available/total parameter variants. Overall requires
at least two available groups and at least 50% fully covered supported visible
types. Neutral remains in the denominator. Explain member parameters, rule and
reason in initially collapsed details; keep the heuristic warning visible.

Require matching source/market/symbol/native interval, applied settings revision,
raw snapshot, response identity, origin/generation, window and exact close.
Suppress paused/stale, inactive, loading, saving, error and separate historical
buffer states. Ordinary recent-buffer panning, hover, forming candles, synthetic
price style and unsaved parameter drafts must not change the reference or votes.
Never substitute older output for a missing latest value. See
[ADR 0059](docs/adr/0059-current-indicator-agreement-panel.md). Agreement alert
conditions and historical agreement timelines remain separate milestones.

### Later authorized detached historical research interface restoration

The frozen-rule history/evidence backend now has a separately mounted research
interface: explicit UTC inclusive confirmed-close setup, frozen revision/context/
parameter review, durable exact Start recovery, asynchronous cancellation/status,
saved scans, paged matches and immutable snapshot charts. Original events open a
separate view with authoritative saved evidence and explicitly current-cache price
context. Exact close/open navigation never substitutes nearest candles. These
views do not register live alert contexts, change Market drafts/layout/focus,
Arm/Pause, alter journal/read state or claim banners. See
[the workflow and limits](docs/ALERT_RESEARCH_UI.md) and
[ADR 0060](docs/adr/0060-detached-frozen-rule-research-ui.md).

Agreement predicates/full-group timeline, strategy conversion and trading remain
separate scope. Component evidence does not imply actual-browser, old-database,
Windows/native, live-provider, owner or release acceptance.

### Reconstructed frozen agreement alert/history backend — 2026-10-12

Freeze the applied visible supported indicator composition for a directional
agreement state condition, inclusive exact overall threshold and optional strict
majorities in each required group. Reuse the versioned shared agreement manifest,
weighting, coverage, duplicates and existing formulas. Preserve original member
IDs, normalized parameters, context, origin and formula versions independently
of later hidden/deleted/added/layout graph changes. Surviving parameter changes,
including change/revert while paused, durably require explicit reviewed rebind;
rebind stays paused. Applied revision/composition changes invalidate an old
preview. Arm never captures a replacement composition.

State-only known false-to-true transitions fire; initial/unknown-to-true and
sustained true do not. Preserve mixed ALL/ANY pulse semantics. Historical research
persists every close with full overall/group/type/variant/member evidence,
coverage, true/false/unknown and opposing group-majority conflict, including
nonhits and sustained true. Live evidence retains the same frozen result and
actual observation clock. Scans remain immutable and isolated from live state.
Keep full-origin 10,000-input/256 MiB, definition/active 256 KiB and response
600 KiB budgets, with complete member-copy accounting and no count quota or
silent truncation. See [ADR 0061](docs/adr/0061-frozen-agreement-alert-history-backend.md).
The new strict v2 definition is additive; ordinary v1 bytes/hashes/replay and the
legacy catalog predicate list remain compatible. Agreement-specific editor and
timeline presentation, authentic old-database compatibility, Windows/native and
live-provider acceptance remain separate. Product version stays 0.6-dev.

### Reconstructed agreement editor and immutable timeline — 2026-10-12

The agreement-specific frontend extends ADR 0061 through an exact versioned
capability gate, explicit fraction threshold and required-group editor, actual
server preview, normalized frozen membership/contracts review and paused save.
Applied revision/composition drift requires explicit refresh and review. Numeric
and divergence controls and uncertain-write recovery remain supported.

Historical research shows immutable overall/trend/momentum/volume distributions
for every returned candle, including unknown, neutral, false, sustained true and
nonhit conflict. Distinguish condition state, new rule match and opposing-group
conflict. Multiple agreement conditions are selectable without losing generic
condition evidence. Exact row/previous/next selection and actual byte-aware
cursors preserve all returned candles. See [ADR 0062](docs/adr/0062-frozen-agreement-editor-timeline.md).
No current-panel recalculation, formula engine, backend/dependency/provider,
strategy/trading or product-version change is introduced. Actual-browser,
Windows/native, live-provider and owner acceptance remain separate evidence.
