# ADR 0046: Reversible Market chart focus

Date: 2026-10-11. Status: implemented candidate; focused frontend checks,
TypeScript, production build and independent source review passed. Bounded
actual-App offline browser acceptance passed on frozen source 51b75fb;
exact evidence and retained live-provider/native/Windows limits are in STATUS.md.

## Decision

App owns a session-local focus flag for Market / Live market only. Focus chart
and Exit chart focus toggle layout without moving or remounting the terminal,
chart, indicator manager or drawing workspace. Hide the App brand/service strip,
platform disclosure, route/source navigation and footer, plus the Market quote
summary, strategy/paper controls, diagnostics and book/tape. Restore their prior
state on exit; do not write a layout preference or alter their subscriptions.

The Market heading becomes a compact sticky bar with an always-labelled Exit,
source/market selectors, symbol, source, connection state, independent freshness
and No real orders. The source note, provider detail and terminal/chart/save
errors remain visible. Timeframe, navigation, indicators and drawing controls
stay in flow and reachable. The existing terminal is the single vertical scroll
owner. Expanded indicator/drawing editors relinquish their nested scrollbars in
focus; the chart grows into available space and retains its minimum pane sizes
when controls exceed a short/narrow viewport. Entry starts at the focus heading;
exit restores the previous normal scroll offset and non-scrolling toggle focus.

Focus does not call Fit, change price-scale options, save or reload chart state,
reset indicator origins or restart a pending Return. The same Lightweight Charts
instance handles the size change. Clear prior user-navigation intent before the
layout's autoSize callback so a resize cannot become an older-page gesture or
silently stop following. Ordinary manual pan/zoom keeps its existing meaning.

Escape bubbles through child interactions before the focus handler. Drawing
Escape first cancels an unfinished tool/gesture/ruler; otherwise it collapses
open properties without discarding selection/name/Fib drafts. A subsequent
neutral Escape exits focus while retaining that state. Indicator Escape from a
non-input control collapses its editor and retains unapplied edits; explicit
Close/Cancel retain their existing discard meaning. Input/select/contenteditable,
composition, prevented events and dialogs keep their own keyboard behavior.
The labelled Exit remains available regardless of keyboard focus.

Leaving Live market, including an asynchronous route change, clears focus; it
never applies to Saved history, Saved tests or run charts. A source/market/symbol
change stays focused but uses the existing namespace key/reset rules; it cannot
carry old-source drafts into a new chart. Display-timeframe changes also retain
focus and their existing chart/data behavior.

## Alternatives and limits

Browser fullscreen would add browser/OS permission and Escape semantics;
portals or a second chart risk remounting, state loss and a second data owner.
A general docking/panel manager exceeds this bounded goal. CSS plus existing
React state is sufficient. Long editors/many panes still need scrolling; focus
is not a promise to fit all controls in one viewport. Source/backend/provider,
formulas, storage/schema, dependencies, account/trading, Windows code, product
version, release and integration remain unchanged. Existing attribution remains.

## Verification

Focused scope: 84 distinct passing tests across AppChartFocus, LiveTerminal,
MarketChartNavigation, ChartIndicators and ChartDrawings. The actual App test
retains production Market/chart components while mocking transport/chart-library
geometry and unrelated route contents. It checks chrome restoration, same chart
instance/range/scales, settings/drawing drafts/selection/undo/revisions, Escape
priority, stale/source labels, timeframe/source/hidden navigation, autoSize
intent, a pending Return and focused/narrow CSS rules. Test-helper corrections
and exact runs are recorded in STATUS.md. TypeScript --noEmit and production Vite
build passed. No backend or repeated broad regression suite was run.

Simulated-DOM/CSS checks do not establish actual browser layout. The subsequent
parent-led full App → Market acceptance used the actual chart library on frozen
source 51b75fb with synthetic, source-labelled data. It passed at 1180×757,
995×688 and 625×432 CSS pixels; compact dimensions used browser zoom and had no
document-width overflow. At the short/narrow size, expanded indicator settings
and the chart remained reachable through the outer scroller with sticky
Exit/source/status accessible. Wide checks retained the mounted chart, drawing
selection/undo/redo and EMA drafts, verified layered Escape and ignored input
Escape, and covered focused Bybit → OKX namespace reset and visible degraded/
recent-error recovery. No source change or redundant tests/build accompanied
this acceptance record. Live-provider/native/Windows and owner-led unaided
acceptance remain separate.
