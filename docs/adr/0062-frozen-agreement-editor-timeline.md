# ADR 0062: Reviewed agreement conditions and immutable four-lane history

Date: 2026-10-12
Status: Reconstructed frontend; focused checks recorded in STATUS
Product version: 0.6-dev

## Decision

Extend the accepted local alert composer and detached historical research UI.
Offer agreement only when the separate capability exactly matches definition v2,
its contract, agreement/weight versions, manifest hash, direction/group domains,
fraction limits, inclusive overall threshold and strict required-group semantics.
An absent or unsupported extension leaves legacy numeric/divergence editing usable.

The editor labels its threshold as a fraction from 0 through 1, with 0.7 = 70%.
The Service compares the unrounded share inclusively. Every selected required
group must have strictly more than 50% in the chosen direction; an empty list adds
no separate group requirement. The warning remains visible: this is a descriptive
heuristic, not probability, confidence or trading advice.

Preview remains an actual read-only Service capture of visible APPLIED supported
members. Do not calculate a client-side replacement snapshot. Review displays the
native interval, normalized parameters, original member IDs, formula contracts,
origin and version/hash. The binding's member_ids identifies agreement membership
inside the union of all frozen numeric/divergence dependencies. Other dependencies
are labeled separately. Unknown v2 preview bindings cannot be saved.

Both applied revision and member composition fence the draft and late previews.
An explicit Refresh applied composition preserves condition edits, invalidates
review, and requires another server preview and reviewed Save paused. Unapplied
Market drafts never supply capture inputs. Saving/rebinding stays paused; Arm is
separate and never recaptures membership. Later hide/remove/add/layout edits do
not rewrite saved rules or history. The backend owns sticky parameter-change
rebind requirements. Existing uncertain create/Arm identities and quarantine are
preserved, including exact retries and separate paused-Arm recovery.

## Historical presentation

Render only evaluation.conditions[i].agreement and .threshold from immutable
history responses. No shared evaluator, current-panel output or frontend formula
is called by the history renderer. Multiple agreement conditions have an explicit
selector; selected-row evidence retains all agreement and generic conditions.

The compact horizontally scrollable timeline aligns Overall, Trend, Momentum and
Volume lanes on every returned raw candle. Each cell is an exact selectable row.
Saved Up/Down/Neutral shares are distinct from striped Unknown. A separate state
row distinguishes True/False/Unknown, a gold new-match dot and an orange opposing-
group-majority conflict diamond. Conflict can coexist with a hit or nonhit;
sustained True does not imply another event. Detailed evidence preserves exact
fractions, saved threshold verdicts, coverage, type/variant/member status, normalized
parameters, consumed values, reasons, exclusions and contracts. Member/raw JSON
details begin collapsed; heuristic and original current-cache warnings stay visible.

Every returned row, including nonhits, is available through an exact-candle
selector and Previous/Next candle. Adjacent-page navigation requests the exact
native close. Existing actual response cursors, independent 20-match pages,
200-row/600 KiB chart limits, byte-clipped exact-row fallback and singleton
wrapper-overflow handling remain. Missing/oversized exact rows are visible errors;
there is never a nearest substitution. The existing raw-price/saved-port chart,
lower panes and target marker are retained unchanged.

## Isolation and verification

Do not change native date input validation, dirty-field late-preview handling,
durable unknown Start recovery, cancellation/reopen epochs, StrictMode lifecycle,
modal Escape or Market draft/focus/session/Arm isolation. No new mutation route,
backend, formula, dependency, provider, order, PAPER or strategy conversion is
introduced. No release, merge, native Windows or owner acceptance is implied.

Synthetic component tests cover capability compatibility, actual backend object
shapes, fraction input, reviewed capture drift, uncertain v2 create, four lanes,
nonhits, exact fractions/threshold verdict, mixed conditions and all 482 retained
oracle rows across byte-shortened pages. Browser geometry and actual Service
interaction are separate acceptance gates; mocks cannot establish them.
