# Strategy testing workspace

**Market** and **Lab** are the two primary journeys. **Data** prepares or updates
history; **Saved tests** reopens comparisons. **Strategy editor** creates or
customizes strategies. **More tools** contains Custom backtest and Parameter
experiments; live/paper/replay controls belong to Market. See the
[current checkpoint](CHECKPOINT.md) for evidence and remaining acceptance.

## Manual observation and explicit test

In Market, choose **Saved history · local**, or use **Observe this history**
from Data. Open a prepared local chart, select a period and save a hypothesis
with an optional falsification condition. Saving does not start a test.

The chart starts with **Source**, showing exact recorded price and volume on a
shared UTC opening-time scale. **Display interval** also offers compatible 1h,
4h and 1d projections, omitting a duplicate of the native interval. Aggregation
uses only the verified loaded page: first open, highest high, lowest low, final
close and summed recorded volume. Daily buckets start at UTC midnight. Switching
display intervals does not read more history, change observation dates or test
settings, save notes or start a strategy. The choice survives same-source page
and Market/Lab navigation; another exact source resets it to Source.

Hover or click either pane to inspect OHLCV, separate display/source intervals,
opening and exclusive closing times, and underlying source coverage. **Previous
candle** / **Next candle** also work without a pointer. Focus the chart to use
Left/Right; Home/End select the first/last rendered price candle in the page.
Navigation reveals an offscreen target before showing its values and skips
incomplete or unavailable candles. Panning the selection out of view clears it;
changing source, page or display interval resets it. **Fit page** returns to the
loaded page.

**Go to UTC date** browses independently of the observation period. Enter
`YYYY-MM-DDTHH:mm` (optionally `:ss`) and choose **Go** or press Enter. The literal
fields are interpreted as UTC, regardless of the computer timezone. An exact
native opening is required: invalid calendar dates, fractional seconds, timezone
suffixes, out-of-range values and unaligned times are rejected without rounding
or replacing the current page. The exclusive source end is not an opening;
the last valid opening is one source interval earlier. Typing alone reads nothing.

Every requested page starts exactly at its target and covers up to 500 original
source slots, including gaps. **First saved page** and **Latest saved page** use
500-slot pages counted from the saved range's beginning. A 900-slot snapshot
therefore has a 500-slot first page and a 400-slot latest page. Latest means the
end of this saved snapshot. **Earlier candles** / **Later candles** move relative
to the loaded page; after an arbitrary-date jump they need not share the
first/latest page grid. **Return to observation start** returns to the saved
revision's start, or the current valid unsaved observation start, without
changing its dates, text or revision. Invalid note dates or dirty note text do
not disable independent Go/First/Latest browsing.

Loading and failure show the requested half-open UTC page. Only a verified
response is labelled Loaded page. A missing requested opening is a valid gap,
not a read failure; no later candle is selected automatically. A failed page
removes the old chart and inspection. **Retry saved-history page** repeats the
failed source and exact numeric boundaries, even if the browse field has since
been edited. It is independent of saved-observation-list recovery and does not
repeat a note save. Recovery is explicit, with no automatic retry, prefetch,
live fallback or persisted bookmark. The existing local transport must still
be available; Retry cannot repair a failed native transport.

Ordinary Market/Lab returns retain the browse draft, verified page, compatible
display choice and note edits. Explicitly reopening an observation returns to
that exact revision's start. A changed exact source fails closed; existing note
edits stay intact until the existing explicit discard/source/reopen flow.
Reads still verify the trade-file checksum and may decode a prefix for a late
page, so a bounded response is not a constant-time-read promise.

Every aggregate requires the entire UTC bucket and every expected source opening
in that page. Incomplete buckets remain blank in both panes with striped bands.
Their inspector distinguishes missing source slots inside the page from slots
outside its bounds, without displaying partial OHLCV. A compatible interval
stays selected even if the page has no complete bucket. Source mode exposes the
actual retained candles and original gaps. Page-edge buckets are not stitched
across pages: the 500-hour boundary can leave the same daily bucket incomplete
on both adjacent pages. Observation dates are never moved to complete a bucket.

Finer or non-divisible intervals are unavailable with reasons. Daily display
from one-minute history requires 1,440 source slots, exceeding this slice's
500-slot bound; there is no automatic read, download or source substitution.
Five-minute history can provide a day from 288 slots when that entire day is in
the loaded page. Volume remains in unspecified recorded source units. `0` is
recorded zero; missing/non-finite volume or an overflowing sum is `N/A` and
histogram whitespace, never a partial sum. Invalid prices stay unavailable
independently of volume. No indicators or live data are computed/fetched here.

Actual visible aggregates participate in the existing partial displayed-period
evidence through all their contributing source candles, including the last
constituent. Separate ranges exclude retained rows hidden in an incomplete
aggregate. Both panes share one visibility observer and recorder; inspecting
or hovering does not create a second exposure record. Displayed in this app is
not proof of human reading or independent market-history completeness.

The saved-observation list distinguishes loading, read failure and confirmed
empty history. **Retry saved observations** repeats only the failed list read;
it preserves the selected source, exact period, note revision and unsaved text.
Loaded notes remain visible after a failed older-page read. If a note saves but
the list refresh fails, the message confirms the save; retrying does not save
another revision or start a test.
The date fields show the available UTC history range and its candle interval;
the end is exclusive. Inline guidance explains missing, reversed, out-of-range
or unaligned dates. Correct the marked fields to enable saving or returning to
the observation start; your dates and draft text are never adjusted automatically.
Lab requires an explicitly saved observation with no unsaved note edits.
**Test observation** opens Lab setup with the exact source, period and note
revision. Closing setup keeps a compact **Attached to draft test** row visible
in Lab, with the observation identity, revision and fixed UTC period (end
exclusive). **Return to observation** opens that exact revision without saving,
starting a test or detaching it. This is the current draft attachment; saved
comparisons retain their own immutable observation links. Ordinary navigation
keeps selected strategies and the attachment. Source/date changes still require
explicit detachment in setup.
Select compatible strategies and settings, then explicitly Review and Start.
Insufficient preceding warmup blocks Review rather than moving the dates.
Reopen a linked saved test and return to its original observation revision; later
note edits do not rewrite that link or the result. This route uses local candles,
not a claim of verified current live-feed behavior.

## Catalog testing, filtering and comparison

Lab uses one main scrolling surface for its controls, current test context and
cards. Scroll past the controls to bring card actions and expanded **Parameters
& source review** into the working area; the desktop catalog no longer has a
separate fixed-height card well. Narrow screens retain their single-column flow.
Lab and Saved tests keep independent scroll positions while the workspace stays
open, including returns through another route; these positions are not saved
across an application reload.
Opening setup still uses the explicit dialog, and Escape or **Back to strategies**
returns keyboard focus to its trigger.

**Order cards** starts with Name A–Z. Choose a saved selection comparison through
**Choose saved comparison**, then return to Lab to order by saved period return,
maximum drawdown or completed positions in either direction. The comparison name
and exact UTC evaluation interval stay visible. Choose its **Saved timeframe**
and **Compatible group**; each is filled automatically only when it has one
valid choice. Group numbers match Saved tests, and the label identifies the
market, source/execution resolution, capital and model version.
The compact comparison disclosure keeps the applied comparison, timeframe,
group and exact period visible beside the metric and direction. Expand it to
change the context. Missing numeric-ordering choices open it automatically;
once complete, close it with its summary to restore more room for cards. It
does not automatically hide a focused selector after a choice.

Only one completed saved row matching the card's catalog version, timeframe and
group supplies a finite ordering value. Its row is marked **used for card order**.
Different parameter variants remain **N/A · multiple saved variants**, even if
only one completed. Missing, unfinished, unavailable and other-group results
stay at the end in both directions with their reason. Losses and recorded zero
are valid values; zero completed positions is labeled **no trades**. Historical
rows stay visible, including older catalog versions. Later-period verification
results are excluded from card selection ranking.

Ordering and filters change the view only: card parameters, chosen test
timeframes, selection and reviewed setup remain intact. Editing a card retains
its saved evidence and **Prior run — changed inputs** label. Opening a different
comparison resets the timeframe/group context; refreshing or renaming the same
comparison does not. Switching through an excluded later-period comparison also
resets the selection context. **Test all strategies** still includes every catalog card,
regardless of its visible position or filters.

Visible finite card summary return, drawdown and position cells and ordering
badges use the same recorded comparison-period evidence as Saved tests.
The older expanded source/details metrics are not separately instrumented.
Hidden, offscreen and modal-covered cells do not count;
reordering alone does not create another presentation. A recording failure is
visible in Lab while reading remains available. This remains bounded in-app
display evidence, not proof of human reading or complete exposure history.

1. On a card, choose its timeframe and any **Compare also** timeframes. Click
   **Test this strategy** to open its backtest setup dialog. Changing a timeframe
   alone does not start execution. **Add to comparison** includes other cards
   in the same setup. Testing does not require copying or editing a strategy.
2. In **Your test**, the collapsed selection summary counts selected tests,
   distinct strategies and timeframes. Expand it to inspect every selected name,
   version, timeframe and current parameter value; the list can be scrolled with
   keyboard focus. Initial capital, saved history and the other setup controls
   remain outside this disclosure. If no history matches, **Prepare market data**
   opens history preparation while preserving your selection. Using history
   returns to the dialog. Escape or **Back to strategies** closes it and keeps
   your settings.
3. Prepare history once, then **Continue with this history** or **Use this
   history**. For longer-horizon spot tests, 4h history supports 4h and daily
   strategies; 1h history supports comparing 1h, 4h and daily together. Complete
   snapshots reopen offline. **Update to latest** downloads missing spans into a
   new immutable snapshot; earlier runs retain their data.
4. Review costs and the suggested period, which reserves preceding warmup.
   Choose **Review test**, inspect dates, capital, costs and compatibility, then
   **Start N tests**. Up to 96 strategy/timeframe tests run sequentially alongside
   Buy & Hold and DCA. The app opens **Saved tests** for progress and results.
5. Compare returns, drawdown, positions, costs and passive alternatives. Open a
   row's report or compare equity. **Cancel remaining tests** retains completed
   work; resuming pending rows is explicit. **Individual run reports** includes
   custom and imported runs. Saved results retain their original settings when
   you change a new test's inputs.

**Test all strategies** opens a batch with every catalog strategy at 4h and 1d.
Change **Batch timeframes** to compare other intervals. Search and family filters
do not exclude strategies from this action. Capital, sizing, costs, source history
and evaluation dates are shared; current card indicator parameters stay fixed
across each strategy's timeframes. Review lists ready and unavailable rows,
including reasons, before **Start N tests** starts only the ready rows.

The whole comparison is saved automatically in the local database. Reopen it in
**Saved tests**; **Saved comparison settings** shows its original contract.
Choose **Sort comparable results** and **Highest first / Lowest first** beside
the retained original context. Open **Filter results** for category and numeric
threshold inputs. The active count and **Clear filters** remain visible when
closed; invalid numeric thresholds are explicitly not applied. Clearing affects
only viewing filters, preserving the saved comparison, sorting and new-test
source. Open **Search saved comparisons** to search names, notes, IDs and dates
across the complete saved catalog; **Load older comparisons** continues that
query. A selected comparison remains available outside its search page.
**Saved notes** opens the selected comparison’s saved note without entering the
editor; **Edit details** still edits its name and notes explicitly.
**Detailed saved assumptions** expands secondary execution settings; instrument
assumptions, costs, outcome counts and source resolution remain visible.
Filter help and **Verify on a later period** follow the results table. Comparison groups preserve different execution
models rather than mixing them into one ranking. Negative returns and unavailable
metrics remain visible. A completed batch can include incompatible rows without
claiming they executed. Native templates still need compatible markets/history
and explicit trust in the editor.

The batch is bounded to 96 strategy/timeframe rows and 2,000,000 modeled source
candles including warmup and benchmarks. Selecting every minute-to-daily interval
at once can exceed that workload. Choose a smaller timeframe set or a suitable
coarser history interval; do not shorten required indicator warmup.

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


## Inspect a saved archive import

Open Saved tests → Individual run reports → Project archive → Recent imports.
Select an operation to inspect its committed outcome and exact reserved report
IDs. Partial imports can contain an openable completed report and separate
incomplete destinations. Opening saved reports or a recovered strategy is explicit;
inspection never uploads, resumes, retries, grants Python consent or runs a test.

If an import's final response is lost, use Inspect this import. After reload or a
service restart, use Recent imports without selecting the original archive again.
A new import creates new IDs and may duplicate saved work. Finalization is
synchronous; inspection can wait until it finishes or require restart. Cancellation
is available only before finish is accepted and never undoes saved reports.

Receipts record publication history, not artifact-file verification or authentic
performance. Ordinary reports read saved database values; artifact verification
remains not checked. A modified saved strategy is identified separately from the
original import. Legacy imports made before receipt support have no reconstructed
receipt. Unknown/unavailable inspection must not be interpreted as nothing saved.
