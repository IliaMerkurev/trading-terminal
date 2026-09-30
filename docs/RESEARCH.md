# Strategy testing workspace

Use **Strategy library** to test supplied strategies, **Market data** to prepare
or update history, and **Saved tests** to reopen comparisons. **Strategy editor**
is for creating or customizing strategies. Custom backtests, parameter
experiments and live/replay tools remain under **More tools**.

1. On a card, choose its timeframe and any **Compare also** timeframes. Click
   **Test this strategy** to open its backtest setup dialog. Changing a timeframe
   alone does not start execution. **Add to comparison** includes other cards
   in the side setup. Testing does not require copying or editing a strategy.
2. In **Your test**, review the selected names, timeframes and initial capital.
   Choose saved history. If none matches, **Prepare market data** opens history
   preparation while preserving your selection. Using history returns to the
   dialog. Escape or **Back to strategies** closes it and keeps your settings.
3. Prepare history once, then **Continue with this history** or **Use this
   history**. For longer-horizon spot tests, 4h history supports 4h and daily
   strategies; 1h history supports comparing 1h, 4h and daily together. Complete
   snapshots reopen offline. **Update to latest** downloads missing spans into a
   new immutable snapshot; earlier runs retain their data.
4. Review costs and the suggested period, which reserves preceding warmup.
   Choose **Review test**, inspect dates, capital, costs and compatibility, then
   **Start N tests**. Up to 12 strategy/timeframe tests run sequentially alongside
   Buy & Hold and DCA. The app opens **Saved tests** for progress and results.
5. Compare returns, drawdown, positions, costs and passive alternatives. Open a
   row's report or compare equity. **Cancel remaining tests** retains completed
   work; resuming pending rows is explicit. **Individual run reports** includes
   custom and imported runs. Saved results retain their original settings when
   you change a new test's inputs.

**Customize strategy** creates an independent editable copy and opens the
editor. Returning to the library keeps the card selection. Native Python still
requires explicit source review and trust before execution.

For a completed candidate, open **Verify on a later period**, then **Set up
later-period test**. Choose compatible later history and dates, and **Freeze
later-period candidate** on its row. Review that separate contract before
starting it. Original parameters, capital and costs remain fixed; ordinary
new-test settings do not alter the candidate. Repeated holdout use is recorded.

Simulation detail and strategy timeframe are different settings. Coarse spot
execution models four price points per source candle; it cannot reconstruct M1
or tick paths and may change fills and drawdown. Strategy timeframes must be
multiples of the source interval. Setup explains incompatible choices before
review; for example, a 6h strategy requires 1h rather than 4h source history.
Select M1 history for detailed execution,
native Python, perpetuals, intrabar evaluation or Position Management.
Unsupported combinations fail visibly. Fees, slippage and instrument precision
remain part of each run; perpetual funding/margin/liquidation retain the detailed
path. No real exchange orders are submitted.

The catalog contains reviewed research templates, not proven profitable systems.
Losses and no-trade results remain visible. See [source review](library/SOURCES.md),
[measured integration](library/VERIFICATION.md), [navigation design](adr/0027-task-oriented-testing-workspace.md)
and [current status](STATUS.md).
