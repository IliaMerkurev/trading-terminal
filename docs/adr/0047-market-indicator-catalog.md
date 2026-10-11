# ADR 0047: Compact Market toolbar and indicator catalog

Historical count-limit references below are superseded by [ADR 0051](0051-uncapped-indicator-instances.md). Other contracts remain.

Date: 2026-10-11. Status: bounded UI phase implemented; initial 74 distinct
focused tests, corrected 33/33 tests, TypeScript and production build passed.
Actual-App wide/narrow/short browser acceptance passed on frozen source `1fd6a51`;
exact evidence and retained platform/owner limits are in STATUS.md.

## Decision

Keep one mounted Market chart and one indicator draft owner. Compose the compact
symbol/source/market, native timeframe and Indicators toolbar through the same
manager; keep Return visible and move secondary scale/Fit/Recorded IR actions to
an in-flow Chart options disclosure. At narrow widths show the native timeframe
selector instead of the quick buttons. Do not add inert chart-style, alert or
layout icons simply because a reference contains them.

Use a typed metadata registry for the nine existing validated formula kinds,
grouped as Trend, Volatility, Momentum and Volume. Search matches type, name and
short contract description. Favorites are a separate UI-only localStorage list
of recognized type identifiers; parse bounded input, remove unknown/duplicate
values and catch storage failures. Never put instance IDs, periods, colors,
visibility, origins, source keys or market settings into this preference.

An in-flow workbench contains the catalog and exactly one selected-instance
fieldset. Legend Settings opens only that editor, with an explicit Browse
indicators action; the top Indicators button opens the catalog. Native selection
switches between draft instances without moving keyboard focus; additions select
the new instance. Removing it selects the nearest remaining instance. The whole
draft is validated and passed unchanged to the existing atomic/revisioned save.
Hidden instances count toward the unchanged eight-instance cap. No calculation,
settings transport, persistence schema, revision semantics or source reset changes.

Opening the catalog focuses search; legend settings and added instances focus
the selected editor without scrolling the plot. Collapse and non-typing Escape
retain drafts and restore the initiator. Cancel explicitly discards. Busy saves
lock mutations but do not trap dismissal or read-only reopening. If a busy save
disables the initiating legend button, dismissal focuses the enabled main toggle. Quick legend visibility cannot replace
an open or dirty draft. Input/select/composition keep keyboard behavior. Chart
options consume their own Escape before the catalog/focus layer. The workbench
is not a dialog; it does not intercept plot gestures or cover axes/Exit. It uses
the outer terminal scroll owner, with stacked narrow layout and no nested scroll.

Units and seed notes remain outside the plot and full provenance remains below.
The ATR seed differs from graph/recorded IR; source-native volume/OBV units and
OBV zero origin remain explicit. Indicator display is separate from trading.

## Alternatives and limits

A floating catalog/dialog would compete with chart axes, gestures and focus-mode
Exit and require a separate focus trap. Expanding all eight fieldsets consumes
chart space and encourages accidental cross-instance edits. A generic plugin
framework is unnecessary for this finite registry. A global market-settings
preference would break existing source isolation. The chosen composition avoids
all four. Expanding a catalog still takes vertical space and can require scrolling
on short screens; it is not a guarantee that all controls fit above the fold.

See the [phased plan](../CHART_EXPANSION_PLAN.md) for HA/line and the finite 30-type
target. Only the existing nine kinds are exposed in this candidate. All later
formulas/transforms require separate calculation and integration evidence.

## Verification

Focused checks cover catalog filtering/favorites, malformed and inaccessible
storage, single-editor/whole-draft validation, hidden-instance cap, dismissal,
failed saves and canonical revisions. Existing chart navigation, series/panes,
source-response rejection, drawing gestures and actual App focus regression
checks remain in scope. The five-file scope passed 74 distinct tests; the initial 73/74 pass and
corrected 10/10 AppChartFocus recheck are recorded in STATUS.md. TypeScript and
production build passed with the existing non-failing bundle-size advisory.
Browser geometry, native/Windows, live-provider and owner acceptance are separate
and are not inferred from simulated-DOM tests. No dependencies are installed.

Parent-led browser acceptance on corrected source `1fd6a51` verified native
RSI → EMA → Volume keyboard selection without focus theft, editor-only legend
entry and explicit Browse, saved eight-instance cap and disabled Add actions,
Trend/empty filters, collapse/Escape, and outer-scroll reachability with sticky
Exit at 1094×757, 729×505 and 625×432 CSS pixels. Both compact focused sizes and
normal 625×432 had no document overflow. Busy-dismissal fallback remains covered
by unit/source checks rather than sustained GUI latency. Earlier frozen
`f22e5c1` supplies separately scoped save-error/retry/reload/favorite evidence.
No source edits or repeated test/build runs accompany the acceptance record.
HA/line and later formula integration remain pending.
