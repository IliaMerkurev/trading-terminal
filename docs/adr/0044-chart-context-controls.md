# ADR 0044: In-flow chart context controls and indicator legend

Date: 2026-10-11. Status: implemented; focused and initial frozen frontend
aggregate passed, with post-correction focused tests, typecheck and build.
Bounded offline browser-wrapper acceptance passed on corrected commit 021994d;
exact failure/retest evidence and full-app/live/Windows limits are in STATUS.md.

## Decision and alternatives

Keep the drawing context immediately before the plot, outside the canvas and
all auxiliary panes. A compact header retains the saved-object selector and
collapse/expand control. Selecting a saved drawing or choosing a tool exposes
its existing properties. Close selection cancels the transient gesture/ruler,
clears selection and restores focus to the properties toggle. Collapsing retains
local name/Fib drafts; explicit close/deselection does not save those drafts.
Save status and failed-write retry/discard remain outside the collapsed content.
The properties area scrolls at a 220px maximum height (190px below 760px).

Unlocked pointer selection is committed to the context only after release:
changing selection or expanding the editor during capture would move the SVG
and potentially change chart conversions. A cancelled drag leaves the previous
context selection; a locked selection may open immediately because it starts
no gesture. The SVG receives keyboard focus with `preventScroll: true`: ordinary
focus can scroll a partially visible chart after the start anchor is sampled,
changing the subsequent pointer coordinate frame even without a vertical drag. Existing anchors, atomic gesture/save, undo, lock and keyboard
text-input guards remain unchanged. No floating overlay is used: it could cover
handles, chart attribution, candles or axis values. A permanent side inspector
would consume scarce plot width in the production Market two-column layout.

Render a wrapping, outside-plot indicator legend with each saved instance's
number, type, ordered named parameters, color, visibility and settings shortcut.
Volume placement and OBV zero origin remain visible. Settings shortcuts focus
the matching editor fieldset. Quick visibility uses the existing revisioned
whole-settings save; it is disabled during loading/saving, while the editor is
open, or while collapsed unsaved edits exist. Collapsing retains drafts and
shows a retained-edits notice. Cancel/Close explicitly discard drafts and restore
focus. Launch controls and editor fieldsets are disabled during saves, preventing
new edits from being overwritten by the canonical save response. The existing
source-generation stale-response guard remains unchanged.

Remove verbose titles from display-series price-axis labels; keep numeric
last-value labels and unchanged series colors, price formats, pane assignments,
scales and calculations. Full names and ordered parameters remain in the legend,
settings and existing readout. A nearby expandable units/seed note discloses
source-native volume units, zero-origin OBV and display ATR's SMA/Wilder seed
versus graph/recorded IR. Full calculation provenance remains below the chart.
Recorded IR and PAPER price-line titles are unchanged.

## Boundaries and verification

This is a frontend-only ergonomics slice using existing React and Lightweight
Charts 5.2.1. No dependency, backend, formula, schema, persistence mechanism,
network acquisition, strategy/trading, version or release change. All 8-instance,
100-drawing and existing replay/save limits remain. The controls are in document
flow, not sticky over the chart; the workspace still scrolls when many panes are
visible. No mobile touch, native or full TradingView-parity claim is made.

Component tests cover draft retention, cancel/reopen, focused settings access,
quick-save busy/error behavior, compact numeric axis labels, source unit notes,
context ordering in the production MarketChart component, collapsed failed-save
recovery, keyboard input protection and stable context during collapsed and
cross-kind drawing gestures. Existing pointer cancellation, source-switch stale
responses, separate panes and financial presentation tests remain applicable.
DOM mocks do not establish real browser geometry. The corrected offline browser
wrapper verified horizontal-drag stability and a measured 718px narrow layout;
this does not imply a separate 703px pass or full-application acceptance. No
backend regression rerun is required for this frontend-only change; unchanged backend evidence remains historical evidence.
