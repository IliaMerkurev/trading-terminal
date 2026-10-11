# ADR 0042: Bounded research-chart workspace

Date: 2026-10-11. Status: implemented and verified in aggregates and bounded offline-H4 browser
acceptance; live/Windows/native and unperformed GUI checks remain separate.

## Decision and license boundary

Retain installed Lightweight Charts 5.2.1 (Apache-2.0), React and existing
SQLite/IPC. Author the drawing layer independently as application MIT source.
No Advanced Charts, Trading Platform, widgets, Pine interpreter, community
scripts or new libraries are included. The existing chart attribution logo/link
and third-party LICENSE/NOTICE references remain. Upstream references:
[Lightweight Charts](https://github.com/tradingview/lightweight-charts) and
[free-charting-library comparison](https://www.tradingview.com/free-charting-libraries/).
The installed pinned type declarations and implementation establish pane,
price/log-scale and logical-coordinate API behavior.

## Volume and navigation

A new workspace's initial indicator settings contain one native-volume instance.
An existing saved empty list means intentional removal and remains empty.
An existing volume instance without placement normalizes to `overlay`; explicit
`pane` survives. Hidden entries are untouched. Each overlay owns a hidden
`volume-<id>` scale with normal/automatic scaling, zero histogram baseline and
80% top / 0% bottom margins, never the primary price scale. Multiple explicit
pane-volume entries retain their existing shared volume pane. Auxiliary RSI,
MACD, volume and recorded-IR scales stay normal/automatic even when primary
price is logarithmic or manual; temporary changes to v5 global scale defaults
restore primary options. Calculation math/origins/units are unchanged.

OHLC and native-volume readouts use the same UTC interval-end timestamps as the
candles and indicators. Native quick intervals and existing selectors share one
state. Fit also resets price autoscaling. Auto/log buttons control primary price
only and reflect native scale changes. Indicator search filters the six existing
kinds; settings use an internally scrollable 360px maximum panel.

## Drawings and persistence

`chart_drawings_v1` is an additive SQLite table keyed by source-aware market and
symbol. `chart_drawing_settings` reads a version-1 document;
`chart_drawing_save` validates an exact schema and compares revision within a
`BEGIN IMMEDIATE` transaction. Invalid or stale writes preserve the old document.
No price data, drawing data or revisions use shared browser localStorage.

The bounded document contains at most 100 unique-ID drawings; each contains
kind, one/two absolute time/price anchors, color, stroke width/style, printable
text, visibility and lock. Time is positive UTC seconds up to year 9999; price
is finite, positive and at most 1e15. Text is at most 200 printable characters,
rendered as React text, not HTML. No URLs, executable payloads or script imports.

An SVG layer is clipped to price pane 0, leaving price/time scales and attribution
available. Its vertical projection always uses the price series conversion API,
including logarithmic scale. Time anchors interpolate through loaded native bar
end-times and gaps, and extrapolate using the selected native interval outside
the window; only that transient logical coordinate is passed to chart projection.
This preserves stored times across prepend, source window changes and native
interval changes. Projection refreshes while active and updates React only when
coordinates change; hidden workspaces suspend projection.

Select/pan is default. Seven persistent tools plus a temporary ruler use pointer
capture, drag-to-create, body movement and endpoint handles. Snapping selects the
nearest loaded candle and OHLC by screen distance. Fib levels are 0, .236, .382,
.5, .618, .786, 1, interpolated in price and then projected (also under log mode).
Tools include labels/tooltips, pressed state, selected-object list, visible focus,
properties, hide/lock/delete and up to 50 undo/redo document snapshots. Save
success is authoritative; failures retain retry/discard information and block
new edits. Each changed gesture saves once; selection clicks do not save or add history. Namespace switches invalidate stale replies,
clear selection/gestures/history and cannot apply another source's state.
Timeframe switches cancel unfinished gestures while retaining saved drawings.
Escape cancels; Delete/undo/redo during a gesture cancel it without stale writes.
Input fields retain their normal editing keys. Ruler remains transient, restores
navigation on release and is cleared explicitly or by another tool/namespace.

## Limits and acceptance

This is a bounded chart workspace, not parity with TradingView. Overlapping
objects select the topmost painted object; the saved-object selector reaches
covered, hidden or locked objects. No multi-select, custom Fib level editor,
text wrapping, alert/order linkage, drawing export or synchronized charts.
Drawings do not extend loaded market history; extrapolated anchors are visual
coordinates, not evidence of candles. All six indicator formula semantics and
provider volume-unit disclosures are unchanged. ATR/Stochastic/OBV are deferred.

Required checks cover every persistent tool; body/endpoints; Escape, pointer
cancel and history shortcuts; input typing guards; ruler non-persistence and
navigation; namespace/save races; revision/data bounds; overlay migration,
independent scale and repeated placement; pan/zoom/resize/older-page/timeframe
continuity; normal/narrow layouts and preserved attribution. Unit/component
mocks establish contracts, not browser pointer-capture or native Windows proof.
Actual frozen-source outcomes belong in STATUS and CHECKPOINT. No public-feed
probe, credential, trading, run, trust or private-dataset modification is part of
this scope. The bounded offline saved-H4 browser review passed at `41e9dc7`; STATUS records
its exact interactions. GUI cross-timeframe/older-page continuity was not run.
Live-provider, Windows/native and owner acceptance are not implied.
