# Research workspace

Start in **Research** for ready-to-test strategy cards. Use **Pro** for graph
editing, native Python, experiments and the retained live/paper tools.

1. Open **History**. Choose an instrument, date range and execution resolution.
   For longer-horizon spot research, 4h history supports 4h and daily strategies.
   Choose 1h history if comparing 1h, 4h and daily strategies together.
2. Prepare history once, then choose **Use for research**. Existing complete
   snapshots reopen offline; **Update to latest** downloads missing spans into a
   new immutable snapshot. Previous runs retain their original data.
3. Select strategy cards and optional comparison timeframes. Review capital and
   costs in the setup panel. The suggested test period reserves preceding warmup.
   Source defaults and local choices are documented in each card.
4. Choose **Preview batch**, inspect compatibility, then **Start frozen batch**.
   Up to 12 strategy/timeframe tests run sequentially with Buy & Hold and DCA.
   Cancel safely and inspect completed rows; resume explicitly runs pending rows.
5. Compare return, drawdown, positions, fees and baseline differences. Open an
   individual report or compare equity. Saved batches remain available after
   restart. Changed inputs label earlier metrics as prior results.

History resolution and strategy timeframe are different settings. Coarse spot
execution models four price points per source candle; it cannot reconstruct M1
or tick paths and may change fills and drawdown. Select M1 history for detailed
execution, native Python, perpetuals, intrabar evaluation or Position Management.
Unsupported combinations fail visibly. Fees, slippage and instrument precision
remain part of each run; perpetual funding/margin/liquidation retain the detailed
path. No real exchange orders are submitted.

The catalog contains reviewed research templates, not proven profitable systems.
Losses and no-trade results are retained. Use a separate later-period verification
for a frozen candidate; repeated use is recorded and is not independent evidence.
See [source review](library/SOURCES.md), [measured integration](library/VERIFICATION.md)
and [current status](STATUS.md).
