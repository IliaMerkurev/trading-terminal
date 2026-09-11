# 0.1 demonstration and acceptance

Use the [Windows setup and launch instructions](DEVELOPMENT.md). The prepared development build is for owner acceptance, not a release or a claim of financial-model equivalence with every exchange account mode.

## Offline golden cases

With the application closed, run `.venv/Scripts/python.exe -m terminal.demo`, then `.\scripts\launch.ps1`. The command performs real managed-worker calculations and checks independent expectations before reporting success.

| Saved synthetic strategy | Expected net PnL (USDT) | Completed trades |
| --- | ---: | ---: |
| Synthetic: forming H1 condition | -30.760 | 1 |
| Synthetic: closed H1 condition | 0 | 0 |
| Synthetic: spot fees golden case | 9.790 | 1 |
| Synthetic: perpetual short golden case | 9.810 | 1 |

The H1 pair uses 60 minutes at 100, 30 at 130, then 30 at 90. A two-hour SMA crosses the 110 condition within the second hour and falls below it before that hour closes. Intrabar and closed-bar outcomes therefore differ. The spot case buys one unit at 100 and sells at 110 with 0.1% fees: 10 - 0.10 - 0.11 = 9.79. The short case sells one unit at 100 and buys at 90: 10 - 0.10 - 0.09 = 9.81. The latter explicitly uses last-price mark proxy and assumed zero funding; it does not validate historical funding or liquidation by itself.

1. Open a saved synthetic strategy, change a node parameter, and save. Observe all four shared outputs and collapsible panels. Saved simulation settings reopen with the strategy.
2. In Backtest, choose the matching labeled synthetic dataset and run. In Results, open the record, inspect costs, select a recorded indicator and select a trade to navigate to its chart region.
3. Compare the two H1 cases. The contract difference should identify `profile.evaluation`; saved results must not change when the editor changes.
4. Select results for export, expand Project archive, and export. The archive stays in the local exports folder.
5. Import that archive using the file picker. Confirm the new strategy/results have new identifiers, show imported-report labels and explain that raw candle history is omitted. Import must not launch a run or grant native execution consent.

## Public data and native Python

In Backtest, set spot or linear BTCUSDT and a complete past UTC day, then download public Bybit history. Inspect actual coverage and gaps. Applying dataset instrument constraints explicitly adopts current precision/risk-tier information as a historical assumption; review costs separately. Perpetual trade, mark and funding coverage are separate. Prepared data can run offline. Incomplete funding or mark history must fail or require an explicit disclosed alternative, never an invisible zero substitution.

For native Python, start Native Python, inspect the installed official NautilusTrader EMA example's configuration, provenance and exact dependencies, then review and explicitly consent before running. Selection, inspection, save and reopening must not execute the module. Native config controls its signals, sizing, timeframes and exits; unsupported feeds, order behavior or missing dependencies fail visibly. Do not trust arbitrary downloaded source merely to complete this demonstration.

## Lifecycle and manual acceptance

During a sufficiently long calculation, switch tabs and inspect progress/logs. Minimize and restore; the worker should continue. Close during active work: Return keeps it running, while Cancel run and exit must stop it and preserve a cancelled, unsuccessful history record. A calculation that finishes before the click is correctly completed rather than retrospectively cancelled.

Automated tests cover the close-dialog IPC ordering and real Windows worker-tree cancellation separately. The compiled desktop was checked for active minimize/restore, close prompt, return, completed-run exit, chart navigation, comparison and export. Native Windows file-picker import and cancellation clicked before a desktop run finishes remain explicit owner acceptance checks: the automation helper could not address the WebView-owned picker, and the bounded calculation completed before the exit click. Backend archive roundtrip, exact browser File chunk transfer and nonexecuting native import were verified automatically. These distinctions must remain in acceptance reporting.

## Limits to inspect

Minute OHLC path is assumed, not recovered ticks. Fills/protections occur at observed modeled points. One verified single-position cross-margin profile is implemented; full Bybit UTA and historical risk-tier changes are not modeled. Imported reports carry integrity checks, not proof of authenticity, and require matching data/runtime/trust for recalculation. Arbitrary native Python is not sandboxed. No installer, live trading, optimizer or other deferred feature is part of this demo.
