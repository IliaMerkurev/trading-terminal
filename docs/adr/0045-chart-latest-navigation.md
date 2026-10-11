# ADR 0045: Explicit latest-following and bounded history navigation

Date: 2026-10-11. Status: implemented candidate; focused component/unit checks,
TypeScript, production build and independent source review passed. Bounded
offline browser acceptance passed on frozen source 9847b51; exact evidence and
full-app/live-provider/native/Windows limits are recorded in STATUS.md.

## Decision

Replace the destructive Latest market reload with Return to latest and explicit
Following latest / Browsing history labels. Navigation state is separate from
feed freshness: following a paused/stale feed does not claim fresh prices.

When the mounted buffer is recent, Return moves its right edge into view without
clearing data or issuing a special history request. Preserve the exact logical
range width, with a right gutter of up to two bars. Existing ordinary polling
continues. While following, forming updates keep the range; appended bars translate it by
the change in buffer length; the capped 1,800-bar rollover retains its latest
logical edge. Disable the chart library's independent new-bar shift and manage
this translation explicitly. Initial data and the explicit Fit chart control
may fit content; ordinary updates and Return never fit or reset price scales.
Manual chart navigation away from the latest candle stops following. Returning
to the right edge manually does not silently re-enable following.

Older-page acquisition retains exclusive cursors, deterministic deduplication,
retryable failure, success-only exhaustion and the existing oldest-1,800 retention
policy. A successful older page makes the buffer historical, even when its right
edge happens to contain the newest candle. Ordinary overlapping recent updates
may refresh that buffer under the same oldest-first cap; disjoint recent pages
cannot replace it. Its right edge and Fit remain history browsing.

Return from a historical buffer starts an ordinary recent market_chart request.
Keep the visible history and zoom while loading. Only a nonempty response without
loading or error replaces the buffer, bounded to the existing maximum; an empty
or failed response preserves the graph and offers Retry return to latest. The
replacement switches to following and places its newest edge at the same zoom.
Repeated pending clicks are disabled. A navigation epoch invalidates late older
or recent responses after a new intent. Source/market/symbol/timeframe switches,
hidden navigation, explicit Fit and newer manual chart movement cancel obsolete
Return work.
The sequential polling subscription is disposed before starting its replacement;
already issued transport reads may finish, but their responses are ignored.

Keep the same mounted chart, indicator editor and drawing workspace throughout
Return. It does not save settings, change indicator origins, rebuild annotations,
reset drawing revisions/undo, discard drafts or alter log/manual price options.
A successful buffer replacement clears hover and old auxiliary/recorded series
before assigning the new shared logical range. Display reads carry a window
identity in addition to their existing settings/source/timeframe/candle guards.
Accepted indicator points and whitespace are clipped to current candle timestamps;
rolled-off points cannot extend the logical domain while another read is pending.
Readouts use the selected candle's timestamp, not a stale result's last index.
Ordinary price polling does not invalidate accepted display calculations.

## Alternatives and limits

Reloading and fitting was simpler but discarded the user's zoom and temporarily
emptied a useful history view. Automatically following the right edge of an old
buffer would confuse a capped historical endpoint with current market data.
Keeping all history or fetching arbitrary wider recent windows would change
memory/acquisition contracts, so neither is introduced. Use the already pinned
Lightweight Charts 5.2.1 APIs; no new dependency, subscription or proprietary
chart runtime is needed. MIT application licensing and existing Apache-2.0
attribution remain unchanged.

A preserved wide zoom can include blank space when the recent response contains
fewer candles than the previous historical buffer. Return preserves width rather
than silently fetching extra pages or fitting. Fit explicitly changes that zoom
and restores automatic price scaling. The unchanged oldest-first cap can also
leave mostly whitespace when older acquisition discards the newest candles the
user was viewing; pan or Return to latest restores a populated view. No
backend/provider/schema/key, formula, strategy/accounting/trading, release,
version or deployment changes are included.

## Verification

Focused verification covers 61 passing tests across MarketChartNavigation,
chartWindow, LiveChart, ChartIndicators and ChartDrawings. New independent expectations cover
80-bar zoom, forming/new bars, the 1,800 rollover, historical cap/no-jump behavior,
disjoint atomic replacement, loading/error/empty retry, repeated clicks, delayed
older/recent races, namespace/timeframe/active cancellation, stale indicator
timestamps and hover, settings/drawing drafts, revisions/undo and retained
indicator values across ordinary polls. Existing older retry and hidden-chart
regressions remain covered. After review refinements, the new recorded-IR gap
fixture initially lacked the required signal `type`; one fixture correction
passed the 15-test navigation file while reusing the other 46 passed cases.
TypeScript --noEmit and the production Vite build passed; the existing >500 kB
bundle advisory remains non-failing.

These are simulated-DOM/chart tests, not native or live-provider acceptance.
Unchanged backend evidence is reused without a redundant backend/full-suite run.
The later offline browser pass verified approximate 100-bar zoom retention,
rollover, manual browsing, a disjoint 1,800-to-300 candle Return, loading/error
preservation and retry, retained log/manual-scale mode, indicator drafts and an
unchanged drawing document/revision. A held older acquisition released after
Return did not reclaim the view; this is not an actual delayed HTTP race test.
Exact numeric manual price bounds and a narrow-layout matrix were not measured.
See STATUS.md for measurements, limitations and independent review evidence.
No source changes or additional suite runs were made for the acceptance record.
