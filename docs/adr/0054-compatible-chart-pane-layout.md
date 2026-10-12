# ADR 0054: Persistent compatible chart pane layout

Date: 2026-10-12. Reconstructed development milestone; acceptance boundaries below.

## Decision

Store optional version-1 `pane_layout` alongside the indicator settings in the
existing local namespace document. Indicator and layout edits share one revision,
one Apply and one Cancel. Layout contains `price_weight`, `recorded_weight` and
an ordered `panes` array. Each pane has a stable `id`, a relative `weight` and
`instance_ids`. Weights are finite numbers from 1 to 10000; they are not promised
pixel heights. There is no fixed count quota for panes or indicators. Existing
64 MiB transport and calculation-resource limits still apply without truncation.

Every auxiliary instance, including hidden instances, belongs to exactly one
pane. Price overlays do not appear in those memberships. Same-kind instances
may share a pane. Additional compatible pairs are RSI/Stochastic (`bounded100`),
MACD/Momentum (`price_difference`) and ATR/standard deviation (`price_distance`).
Price differences and distances remain distinct. Other types retain separate
kind-specific groups. VMC B has its own signed group and all seven ports move
together; it cannot mix with RSI, MACD or other kinds.

Price is always first. Recorded IR is never part of editable membership and
stays separate and last when selected. Extra panes are linear and autoscaled;
RSI/Stochastic retain the bounded 0–100 axis. Price log/manual settings survive
rebuilds. Volume on price uses an independent, hidden, linear volume scale.
Chart series are created in physical pane-index order, rather than assuming
that an out-of-order index creates earlier panes. Relative stretch factors are
applied after the pane set exists.

A pane occupies space only while at least one member is visible. Hide retains
its membership, order and weight; Show restores those properties. Hiding a pane
sets all members hidden and Show enables all its members. Individually hidden
members can also be changed in their existing instance settings. More visible
panes increase the chart's minimum height and use the existing workspace scroll
owner. Numeric weights and move buttons are supported; divider dragging is not
part of this milestone.

## Atomic editing and persistence

The editor's session-scoped draft includes the layout and original settings
revision. A layout-only draft survives source/market/symbol remounts just like
indicator edits. An unrelated or newer authoritative settings refresh cannot
advance its revision or discard it. An acknowledged Apply matches both submitted
instances and layout before clearing the draft. Cancel returns both to the
current authoritative settings. Reloading the application does not preserve
unapplied session drafts. Pending and uncertain-save guards remain unchanged.

Settings reads validate the version, weights, unique pane IDs, exact membership
and unit compatibility. Inline and checksum-paged uploads accept the same atomic
layout document. A writer omitting layout against an already customized document
fails explicitly, rather than silently discarding a field it does not understand.
An explicit `pane_layout: null` requests legacy grouping. Old settings with no
layout remain valid and keep grouping by indicator kind with 320/130 weights.
No database migration or destructive rewrite of stored rows is needed.

Layout changes never alter indicator parameters, raw candles, calculation
origins or formulas. Existing save invalidation may recompute the same values
from the same origin; revision-bearing response envelopes correctly identify
the new settings revision. Explicit reanchoring remains the only user operation
here that changes the saved origin generation, and it preserves layout.

## Preset integration

Save current adds the supported layout as `content.extensions.pane_layout`.
The immutable snapshot retains existing instance IDs, so membership references
remain exact on Stage. Origins and execution state are never copied. Staging an
old preset without the extension explicitly restores its legacy grouping rather
than borrowing the destination's custom layout. Staging only edits the draft;
Apply/Cancel retain their existing semantics. Invalid, incompatible or unknown
extension versions cannot be staged. Rename, duplicate, Trash and Restore retain
unknown extension content unchanged under ADR 0053, permitting future clients
to read it without this client silently erasing it. Invalid stored settings
cannot be saved as fallback-default presets.

## Reconstruction and verification

This is a new implementation against the published preset baseline and retained
functional requirements. It does not claim recovery of unavailable old source,
old test artifacts or old database contents. Serialized compatibility with an
unavailable historical pane-layout database is unverified.

Focused new tests cover strict membership and units, legacy fallback, hidden
layout retention, creation-order calls, weights/scales, joint editing, retained
revision conflicts, supported/unsupported presets, service upload and persistence,
restart, and exact numerical/event/origin invariance. Existing nearby preset,
transport, lifecycle and chart tests are reused or run as recorded in STATUS.
Mocked chart/component checks do not establish actual browser geometry. Actual
production-browser, Windows/native, live-provider and owner-led acceptance are
separate gates. No new dependency, provider, strategy, PAPER or order operation,
product version, release or main merge belongs to this milestone.
