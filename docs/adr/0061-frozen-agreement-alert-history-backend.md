# ADR 0061: Frozen agreement conditions and full historical evidence

Date: 2026-10-12
Status: Bounded backend reconstruction; agreement editor/timeline UI separate
Product version: 0.6-dev

## Scope and compatibility

Reconstruct the reported agreement-state condition on the accepted frozen local
alert, passive runtime and immutable historical research backends. This is new
source reconstruction, not original-byte recovery. No authentic old database is
available; roundtrips of this schema do not prove original database migration.
No frontend, provider, formula, dependency, strategy, PAPER/order, external
notification, merge or release change belongs to this checkpoint.

Ordinary numeric/divergence definitions continue to emit and accept exactly the
existing version 1 / `frozen-indicator-alert-v1` canonical shape. Their hashes and
default replay rows remain unchanged. Agreement-containing definitions use
version 2 / `frozen-indicator-alert-v2`, preserving every existing field and adding
one `agreement` binding. Version 2 requires an agreement condition. Unknown
versions, keys, contracts, groups and duplicate group/member IDs are rejected.
SQLite tables and the Service protocol envelope remain version 1: their existing
strict JSON definition/evidence payloads already retain the new versioned
snapshot without a table migration. Historical/event envelope versions do not
claim a change in their existing clocks, IDs, paging or lifecycle semantics.

The condition discriminator is `predicate: "agreement"`, consistent with the
existing reconstructed condition API. It also requires `direction` (`up` or
`down`), numeric `threshold` (0 through 1), and `required_groups` (possibly empty,
with distinct `trend`, `momentum`, `volume` entries). Required groups normalize
in sorted order. Overall comparison is inclusive on the exact unrounded share.
Each required group must be strictly above one half. Unknown overall or a
required group is unknown even if another test would fail.

`alert_catalog.predicates` remains the legacy numeric/divergence list, so the
currently published editor never offers an unsupported choice. The separate
`agreement_capability` object is version 1 and describes the new predicate,
definition version/contract, direction/group domains, threshold semantics and
shared evaluator versions/hash. An agreement-aware client can discover it
explicitly. Existing generic JSON evidence viewers retain all new fields; an
agreement-specific editor and plotted group timeline are not claimed here.

## Capture, review and durable identity

The added binding contains `version: "indicator-agreement-v1"`,
`weight_version: "equal-group-type-variant-v1"`, `manifest_hash` and sorted
`member_ids`. The hash is the unchanged shared manifest's SHA-256:
`74cc8337a2e60f56719fc584decb79427609be58450c582d3c72f512355651ff`.
The frozen instances retain the normalized parameters and existing formula
contracts for the union of agreement membership and explicit numeric/divergence
dependencies. Existing context, source IDs, native interval, applied revision,
origin time/generation/contract and event contract remain authoritative.

Agreement membership captures only applied, visible, manifest-supported
directional members. Hidden/context-only/unsupported instances cannot join its
coverage denominator, even if referenced by an independent numeric condition.
Exact copies remain listed by original ID but share a single weighted variant.
The accepted hierarchy remains equal available variants within type, types
within group, and groups overall, including neutral in every denominator.

Preview and create/rebind compare the applied revision and newly reconstructed
composition/origin against the reviewed definition hash. A stale applied
revision or changed composition cannot save an old preview. Arm uses the saved
snapshot and never captures current membership. Later hidden/deleted originals,
new members and layout changes do not rewrite it. Surviving parameter changes
are synchronously persisted as review-required, including paused and archived
saved rules. The saved library is paged, with one definition inspected at a time.
An unusable saved definition is paused and marked review-required without
interrupting healthy rules in the same scan. Change then revert cannot erase
the marker, including after restart. Reviewed
rebind clears it and stays paused. No historical run is rewritten by rebind.

## One evaluator and complete evidence

A replay calls the existing display calculator once on the full-origin tape.
Version 2 deduplicates identical type/normalized-parameter formula dependencies,
aliases values back to every original member ID, and uses the existing event
collector to retain per-source divergence event identities. Version 1 follows
its unchanged calculation path. No numeric formula is duplicated here.

Prepare the accepted shared agreement evaluator once from those values and the
verified raw tape, then evaluate each native close once. Its indexed snapshots
and rolling raw guards prevent quadratic prefix evaluation inside a replay.
The passive live runtime retains its existing one full-origin replay per newly
observed close; this change does not introduce a streaming formula engine.

Each agreement condition's existing `index`, `predicate`, `kind: "state"`,
`truth` and `reason` is augmented by `agreement` (the complete shared evaluator
result) and `threshold` (the shared exact threshold evidence). The result has
all overall/group/type/variant distributions, exact rational fractions,
percentages, coverage, members/statuses/consumed values/reasons, exclusions,
manifest identity, raw-open and confirmed-close clocks, and group conflict.
Opposite directional majorities in different groups define conflict. Unknown
stays distinct from neutral and false.

State-only known false-to-true edges fire once; initial/unknown-to-true and
sustained true do not. Unknown resets the baseline. Existing mixed ALL/ANY
impulse behavior is unchanged. Live event evidence uses the real observed UTC
clock and the exact same frozen result; Arm warmup never delivers past hits.

Historical jobs retain every full-origin row: unknown, false, sustained true,
hit and group disagreement. Existing immutable raw/rule/row snapshots,
transactional publication, cancellation, restart interruption and byte-aware
paging are reused unchanged. Historical work does not touch runtime cursors,
journal, unread state, banner claims, context or Arm. Selected Start filters
results; it never moves the frozen origin or discards warmup.

## Resource contracts and evidence limits

The full-origin maximum remains 10,000 inputs. Working preflight remains a
conservative 256 MiB cap, now including prepared indexes, per-bar complete
member/type/variant/group dictionaries, ID/parameter byte costs, condition
copies, retained hit copies and historical value snapshots. Duplicate formulas
do not eliminate original-member evidence cost. The 256 KiB definition/active
aggregate and 600 KiB response budgets remain. No arbitrary member quota,
silent membership truncation or skipped candle is introduced. Large evidence
can make the memory budget bind before 10,000 inputs; smaller End, not merely a
later Start, reduces full-origin work. Oversized single responses fail visibly.

Focused core/runtime/history and compatibility evidence is recorded in STATUS.
Offline synthetic tests are not proof of current GUI usability, native Windows,
live providers, owner acceptance, remote CI, old-schema compatibility or release.
