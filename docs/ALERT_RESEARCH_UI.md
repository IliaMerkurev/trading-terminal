# Frozen-rule research and original alert evidence

This 0.6-dev interface uses only the published
[historical research and evidence API](ALERT_HISTORY_API.md). It introduces no
provider acquisition, formula engine, dependency, strategy conversion, order,
PAPER or external notification. A match is not a trade, backtest or profitability
estimate. Agreement state evidence uses the same immutable research routes.

## Scan a frozen rule

1. Open Local alerts, select a saved rule, and choose Scan this frozen rule.
2. Inspect the saved revision, source/market/symbol/native interval, definition
   hash, frozen normalized parameters, calculation origin and conditions.
   The read-only preview displays declared cached confirmed-close bounds. These
   bounds do not establish continuous, confirmed or conflict-free coverage.
3. Enter Start and End as UTC confirmed CLOSE times. Both bounds are inclusive.
   The browser's local timezone does not change their interpretation. Defaults
   use cached bounds, with Start no earlier than the frozen origin's first close.
   Each manually edited field survives a late preview independently. Native input
   and blur events synchronize the controls; preview also checks actual DOM value
   drift and partial native edits before applying defaults. Start snapshots both
   visible native values and validity before updating state or retaining a request,
   even if React has not received a change event. Invalid dates, native
   misalignment and reversed bounds disable Start or reject the immediate click.
4. Start historical scan sends exactly the visible range with the reviewed
   revision/hash. It records the immutable cache snapshot and calculates
   asynchronously. The status distinguishes queued, running, cancel_requested,
   completed, cancelled, error and interrupted. Cancel historical scan is
   explicit; an older poll cannot erase cancellation intent or a terminal result.
5. Open the result or return through Saved scans. Reopening reads the saved
   record without issuing Start again. Metadata pages have at most 20 items;
   there is no fixed count quota on saved scans.

The input budget is 10,000 raw candles from the frozen origin through End,
including all pre-range replay, with an estimated 256 MiB working budget and
at most eight unfinished jobs. Moving only Start later cannot remove pre-range
work. An earlier End can reduce it. Missing origin, gaps, conflicts, unconfirmed
candles, unsupported contracts and byte/work budget failures remain explicit.
The interface never suggests truncating or bypassing required initialization.

## Unknown start outcomes

Before sending Start, origin-local browser storage retains the exact request ID,
rule revision/hash, dates and creation time. Storage failure blocks mutation.
A pending request blocks a new identity and remains visible after close/reopen
or reload. Reconcile original scan request performs only read-only request lookup.
An accepted request opens that same saved scan. An absent lookup retains the
original content and permits only an explicit Retry exact original scan.

A Service error envelope may follow an accepted commit. The interface checks
the durable request ledger before treating an initial rejection as settled.
A rejected exact retry cannot settle an earlier unknown attempt. No automatic
retry or fresh-ID retry is issued. Late replies can resolve their retained
identity but cannot replace an unrelated research view. Browser recovery is
origin/profile-local, not a portable backup; deleting it loses that local record.
The Service request ledger remains authoritative.

## Inspect saved results

Only completed results claim complete coverage. The summary reports requested,
evaluated, known and unknown rows, initial requested-range unknowns, pre-range
rows/unknowns, total input rows, matches and exact confirmed-close coverage.
Unknown is distinct from False. The saved reason warmup_or_missing_value does
not establish that every unavailable value was initialization warmup.
Cancelled, interrupted and failed jobs do not publish partial work as complete.
After Service restart, unfinished jobs are interrupted and never auto-resume.

Matches use independent pages of at most 20 in a scrollable 180-pixel list.
Chart windows contain at most 200 rows within the 600 KiB response ceiling.
Both use the actual returned cursor/index, including byte-shortened pages.
Every returned window marker is shown independently of the current match page.
The chart uses only saved raw candles and the same scan's saved calculated
values. Separate lower line panes retain unknown gaps without a frontend formula.
The selected row shows exact raw OPEN and confirmed CLOSE clocks, numeric port
values, current/previous condition evidence and three-state truth.

Selecting a match asks for its exact confirmation with up to 40 preceding rows.
If the byte-shortened window omits it, exact-row lookup and an exact-index window
are used. If the row fits alone but the chart wrapper does not, the returned exact
row is rendered by itself with an explicit missing-context notice. A missing or
oversized exact row fails visibly; no nearest candle is substituted.

## Open an original event

From a journal row choose Original alert evidence. The original source, market,
symbol, native interval, confirmation/observation times, frozen conditions,
current/previous values, parameters and origin are authoritative. The current
rule name is identified separately as current metadata.

Adjacent PRICE context comes from the current local cache and may have changed
since the event. Its mandatory warning remains visible. The raw target OPEN is
confirmed CLOSE minus native interval width. Divergence navigation targets
confirmation, not the earlier supporting pivot. Missing, unconfirmed or conflicting
targets remain explicit and are never replaced with a nearby or other-interval
candle. A separately returned exact target survives adjacent-window byte clipping.

## Isolation and backups

The modal is mounted above source-keyed Market remounts and has its own chart,
request epochs and lifecycle. Escape closes only research and restores focus
without changing Market chart focus. Neither view mounts MarketChart or invokes
alert session/context, Arm/Pause, mark-read, banner-claim, journal-write or live
monitoring actions. Existing live alert observation may continue independently.
Unapplied Market indicator/preset drafts and layout retain their existing owner.

Back up the workspace database, which contains the additive research records.
Strategy archive export does not export these records. Compatibility with an
unavailable older research database remains unverified; new-schema checks do not
prove it. Component mocks, actual-browser checks, native Windows, live providers,
remote CI and owner acceptance are separately recorded evidence.


## Four-lane saved agreement timeline (ADR 0062)

Choose a saved agreement condition to inspect Overall, Trend, Momentum and Volume
lanes. Up/Down/Neutral distributions come directly from saved evidence; striped ?
is unavailable/Unknown, never neutral. A separate state row shows T/F/?, gold ●
for a new rule match and orange ◆ for opposing-group-majority conflict. Conflict
is independent of a match, and sustained True does not imply a new event.

Select any lane cell or use Select exact saved candle, including nonhits. Previous
candle and Next candle target the exact native close across windows. Chart paging
uses the actual byte-shortened next index; match pages remain independently bounded
at 20. Missing/oversized exact evidence stays visible and is never substituted.
The unchanged price chart uses saved raw candles and saved lower-pane port values.

Selected-row evidence shows exact raw OPEN/confirmed CLOSE/native interval, exact
fractions, the complete saved threshold verdict, coverage and group distributions.
Initially collapsed details contain types, variants, member statuses, normalized
parameters, consumed values, reasons, exclusions and contract hashes. All agreement
and generic conditions remain available even when the timeline selector changes.
No frontend evaluator or current-panel value supplies historical evidence. Later
Market hide/remove/add/layout or rule changes cannot rewrite the result. The
heuristic warning remains visible; original event price context keeps its separate
current-cache warning. See [ADR 0062](adr/0062-frozen-agreement-editor-timeline.md).
