# Trading Terminal 0.5 development demonstration

This is an owner-accepted early development build, not a stable release or real trading system. Remaining UI/UX issues are accepted as non-blocking and deferred. [STATUS.md](STATUS.md) distinguishes owner manual acceptance from actually executed automated checks. Telegram ILI-37 remains outside acceptance and intentionally deferred; do not enter credentials for this demonstration.

## Build and isolated examples

Run from this checkout with the documented project environment. Choose a **new absolute directory** for synthetic examples; the preparation command refuses existing directories and the ordinary user data root.

```powershell
$demoRoot = Join-Path (Get-Location) '.local-data\05-owner-demo'
.\.venv\Scripts\python.exe -m terminal.demo_05 --data-root $demoRoot
.\.venv\Scripts\python.exe scripts\desktop.py --build --target-dir .local-tools/05-final-target --data-root $demoRoot
```

Preparation creates two explicitly synthetic parameter candidates, freezes ordinal zero before reading the later-period result, and completes one separate validation. It also saves an H1 public-monitoring example with optional Position Management. No market connection or notification is opened during preparation. Reopening the same prepared data requires only the launcher, not another preparation command. Omit `--build` if this checkout's current build already exists.

Without `--data-root`, the application uses its ordinary data root. Do not copy these examples into user data. The target-directory argument preserves an in-use older executable; it creates no manual executable copy or installer.

## Market first

1. Open Live before selecting a strategy. Confirm current ticker, book, trades and chart appear independently.
2. Select the saved H1 example and start monitoring with PAPER disabled. Confirm the chart/book remain current while strategy history reports progress. Market readiness and Strategy readiness must remain separate.
3. Change display interval among 1m, 5m, 15m, 1H, 4H and 1D. Strategy timeframe remains 60m/closed and the session identifier does not change.
4. Load older chart history. Confirm earlier candles prepend without jumping the current viewport; Fit latest is an explicit action. Restart and revisit the same page to check cached history.
5. Pause monitoring. The market view should remain connected while the strategy is paused.

The owner manually accepted the current build for merge. The scenarios below remain useful for repeatable review; service/component tests do not establish native controls, viewport stability or a measured 30-minute compiled-UI run.

## Optional managed PAPER

In Live settings, enable Position Management and review limits before starting a new frozen session. Existing legacy strategies have this policy disabled unless explicitly enabled. A manual paper account can start with no strategy. Strategy and Manual execution sources are exclusive; protections remain active in both.

- Use a virtual allocation large enough for several quantity steps. Very small BTC positions may reject a 25% reduction because it rounds below the instrument minimum. This rejection must appear in the event/lifecycle history, not silently enlarge the order.
- Start manual PAPER, then Buy (or Sell for linear perpetuals), Add, Reduce 25%, Reduce 50%, and Close. Check remaining quantity, weighted entry, margin/notional, costs and one lifecycle identity. Each request waits for a fresh observed quote.
- Inspect Paper Trades and its lifecycle pages. Verify entry, scale, reduction and exit rows; chart entry/stop/TP/DCA lines are backend values.
- Configure separate bounded DCA, partial TP, trailing, break-even or ATR scenarios. ATR-dependent entries wait for confirmed-primary warmup. Stops never loosen. Fees/slippage remain visible; gaps can produce losses beyond a threshold.
- Reopen a saved active session. Confirm it is paused, displays its persisted account, recovers history and requires explicit paper continuity revalidation before continuing. Missing live ticks are not fabricated.

No button submits an exchange order. All capital and positions are virtual.

## Historical lifecycle and experiments

Open the saved synthetic experiment and inspect either candidate in Results. Position Management appears in the frozen settings. The Position lifecycle panel groups entries/reductions/costs under one position, with bounded event pages. Synthetic prices intentionally repeat; they are not exchange history.

Open Experiments with Position Management enabled to expose validated `pm.*` parameters. Risk caps remain fixed. The included example varies add allocation over two values. Compare the predeclared candidate with its frozen later-period validation; do not repeatedly choose candidates using holdout outcomes.

The editor includes read-only Position Side, Position Size, Average Entry Price, Unrealized PnL % and Bars Since Entry. PnL here is unleveraged last-price change, not account return. Live records position context at each evaluation boundary for reproducible replay. Historical continuous OHLC-path fills and actual observed PAPER fills can differ even when the decision policy is shared.

## Evidence and remaining acceptance

Automated evidence includes independent financial goldens, actual retained-engine fills, live/replay context restoration, standalone/grid/later-period equivalence, editor/settings/lifecycle components and copied-data preservation. See [ADR 0019](adr/0019-shared-position-management.md) for exact assumptions.

Record native start/end times, topic counters, process/memory observations, chart paging, responsive controls and strategy/account continuity during at least 30 minutes of real public data. Keep native evidence separate from service-only endurance tests. Do not claim a natural reconnect unless one occurred; deterministic reconnect tests remain separate evidence. Existing Windows/sound behavior is retained, while Telegram delivery remains a known issue.
