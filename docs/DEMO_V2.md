# V2 demonstration and acceptance

V2 is a Windows development build. Keep V1 data/builds separate during acceptance. Use the already configured, pinned Python environment; no system policy change is needed.

## Prepare and open the separate synthetic workspace

From the V2 checkout, with its configured environment:

```powershell
.\.venv\Scripts\python.exe -m terminal.demo_v2
.\.venv\Scripts\python.exe scripts\desktop.py --build --data-root (Join-Path (Get-Location) '.local-data/v2-demo')
```

An isolated worktree can use a verified Python environment from another checkout by invoking that executable directly. The launcher passes that interpreter to the service. Pass `--cargo-home` with an existing project cache for an offline build if it is stored elsewhere. Omit `--build` to open an already built executable without replacing it. Never rebuild an executable currently in use.

The bounded demo creates one synthetic visual strategy, 16 fixed combinations, one predeclared candidate validation and an equivalent standalone window run. It stores actual identities, metrics and measurements under the selected local data root. Repeating the unchanged demo reuses its record. It never reads or modifies a different data root. All candles are synthetic; results are not evidence of market profitability.

## Editor

1. Open the synthetic visual strategy. Right-click empty canvas, search `EMA` or `Exponential Moving Average`, then press Enter. Confirm exactly one selected node appears at the original click location with settings visible.
2. Repeat after pan/zoom, window resizing and toggling side panels. Try corners and an empty search. Escape/outside click must create nothing. Check arrows and Enter; typing in search/settings must not invoke graph shortcuts.
3. Connect the new indicator, edit its period, drag it, delete it, and use Undo/Redo. One drag must undo as one action. Duplicate selected connected nodes and verify independent parameters/remapped internal edges. Copy the strategy and save; the original and reports must remain unchanged.
4. Leave an input disconnected. Save the draft, reopen it and navigate its validation message. A run must fail visibly until the graph is valid. Check zero/negative/noninteger periods, incompatible ports and attempted cycles.

## Experiments and validation

1. Open Experiments and choose the completed synthetic experiment. Inspect all 16 completed rows, costs, sorting and drawdown/trade-count filters. Open a result using the ordinary report and create an independent strategy from a candidate.
2. Inspect the frozen candidate and separate IS/OOS metrics. The fixture selected ordinal zero before OOS calculation. It did not select the highest holdout return. Open the OOS report: warmup candles do not contribute trades or statistics, and the account starts flat with fresh capital.
3. Prepare a new grid from a saved visual strategy. Select the fixed dataset/profile and both UTC ranges, enter explicit comma-separated values, and Preview. Stop/take values are fractions: `0.05` means 5%. Duplicate equivalent values count once. Invalid values, overlapping periods and oversized grids must fail before work starts.
4. Start the grid, then change editor settings. Saved queued snapshots must stay fixed. While it is active, ordinary runs must be rejected. Cancel during an active combination: already completed reports survive and later combinations never start. Close during an active grid: Return must keep work running; Cancel and exit must stop it. Reopening after interruption must not resume it automatically.
5. Freeze an explicitly chosen successful candidate. Confirm its identity before running OOS once. A repeated selection creates a separate attempt with a holdout-reuse warning; it never overwrites the old result.

## Charts, transfer and native acceptance

Dense executions use compact grouped markers with complete fill details and trade rows. Pan/zoom a saved chart, change its recorded indicator, then toggle panels: the viewport should remain stable. Indicator values must match the saved report, and no primary timeframe changes through chart controls. Comparison labels show units while retaining raw input/version identifiers.

Export a completed candidate report and import it through the Windows picker into a separate acceptance workspace. Imported reports retain experiment/selection provenance, omit raw candles and never run or grant native source trust. Reopen/export a copied V1 report and compare its recorded result checksum.

Native Windows picker interaction, cancel-and-exit while visibly calculating, and Windows 100%/125%/150% scaling are manual acceptance items unless an actual observation is recorded in status. Component mocks and worker tests do not establish these UI observations. Do not change other applications or system scaling solely for automated verification.

## Expected evidence

Independent protection goldens are in `tests/test_execution_v2.py`: V2 OLHC/OHLC exits at 95/105, V1 retains 80/120, gaps use available prices, and costs/mark liquidation remain explicit. `tests/test_experiments.py` verifies actual worker grid equivalence, warmup/window behavior, freeze, future-holdout perturbation, errors, cancellation and interruption. See [status](STATUS.md) for actual timings/results and the [execution ADR](adr/0010-execution-v2.md) for model limits.
