# ADR 0058: Cache-only frozen-rule research and original event evidence

Date: 2026-10-12

Status: Bounded backend reconstruction. UI, agreement-condition/history
integration, Windows/native, live-provider and owner acceptance remain separate.
Product remains 0.6-dev; no new dependency or formula engine is introduced.

## Decision

Use one dedicated cancellable history worker and additive SQLite snapshot tables,
reusing the published frozen alert replay and display calculator. Do not reuse
the live Arm worker, mutate its context, replay events into its journal, introduce
a strategy conversion, call a provider, or calculate indicators a second way.
The worker is intentionally separate from strategy jobs and PAPER/order paths.

The exact strict routes, returned fields, status meanings, resource limits and
UI reconciliation obligations are in [ALERT_HISTORY_API](../ALERT_HISTORY_API.md).
Historical unavailable source used a different ADR numbering context; this is a
new implementation, not a claim of byte identity or old-database compatibility.
No authentic previous history database fixture is available. New-schema
roundtrips and additive tests do not establish old-schema interoperability.

## Snapshot and lifecycle boundary

Start performs one `BEGIN IMMEDIATE` transaction: request fingerprint lookup,
eight-unfinished admission, exact rule revision/hash verification, bounded
full-origin cache read, explicit provenance/content-hash/contiguity validation,
and immutable raw/rule/request capture. The inclusive user range is in UTC native
confirmed CLOSE times. Replay always begins at the saved raw OPEN origin. Cache
capture excludes anything after End. Moving only Start later cannot lower work;
an earlier End can. Raw cache admission fails rather than fetching, filling,
reanchoring, ignoring a gap, changing interval, or truncating the prefix.

The same accepted request ID/payload returns the same durable run even after
rule edits or restart. Different payload fails. Readback never starts anything.
Queued/running/cancel-requested statuses count toward eight; completed saved
records have no fixed count quota. A single background worker runs calculations
outside dispatch and publishes the full output timeline in one transaction.
Cancelled/error/interrupted jobs have no published rows or complete-coverage
claim. Cancel checks tokens and durable state again under the commit fence.
Shutdown marks unfinished work interrupted, cancels and joins; a timed-out
worker retains dependencies and workspace ownership. Startup interrupts prior
unfinished work and never resumes it.

Inputs, metadata identity and output rows are guarded by immutable SQL triggers;
terminal runs cannot change status/summary. Later rule edits, cache corrections,
settings/layout changes or Service restart do not recalculate or alter completed
research. Retained prefix rows support subsequent explicitly scoped integration,
without implementing agreement conditions in this checkpoint.

## One calculation/evidence path

The pure alert core gains an optional `include_values=True` snapshot switch.
Default replay output remains unchanged. In the same existing display-calculator
call it retains each frozen instance's causal port values at every confirmed
close, alongside the original truth/transition/condition evidence. No repeated
prefix calculations or alternate numeric formulas are added. Historical jobs
never invent observation time; only original live events have actual observed
UTC clocks.

Both replay and admission use the same conservative core working estimate.
History accounts additionally for retained values/raw snapshot bytes. The entire
prefix is capped at 10,000 raw rows, with a 256 MiB working estimate and the
existing 256 KiB frozen definition guard. Null conditions remain unknown. The
summary distinguishes requested known/unknown observations, initial unknowns,
and pre-range input/unknown counts; unavailable values are labeled
`warmup_or_missing_value`, never indiscriminately false or definitely warmup.

## Viewing boundaries

Runs and matches are keyset-paged at 20 rows; charts at 200 rows plus a 600 KiB
response ceiling. Cursors advance from the last actual returned item, including
byte-shortened pages. Chart markers use every requested-range hit in the returned
window, irrespective of current list page. Target navigation tries 40 preceding
rows, discloses exact target presence/index, and supports an exact-row fallback
when bytes exclude the target. No nearest or other-native-interval substitute
is allowed. A single oversized row fails visibly.

Original alert evidence is a distinct read-only path. Frozen event values and
conditions are authoritative. Adjacent PRICE candles come from the current local
cache, which may have changed; the response explicitly warns about this. The
exact raw target is confirmation minus native width. A missing/unconfirmed/
conflicting target stays explicit with null target candle. Divergence targets
confirmation while earlier pivots remain supporting geometry. No read flags,
banner claims, journal rows, cursor advances, Market mutations or Arm actions
occur through these routes.

Research is stored in the workspace database, which must be backed up. Strategy
archive export does not implicitly export this separate research storage.

## Evidence and limitations

Focused actual-Service synthetic tests cover independently expected 60/150
crossings; requested/prefix boundaries; equality and native five-minute clocks;
future-input perturbation; immutable rule/raw/value snapshots after rebind,
cache rewrite and restart; default replay byte parity; original divergence
navigation; exact missing/unconfirmed/conflicting current-cache targets;
request concurrency, eight-job admission, cancellation, interruption and
shutdown ownership; 10,000-row and 256 MiB admission; byte-shortened match/chart
cursors and exact fallback; and zero forbidden provider/trading/notification/
Arm/context calls. See STATUS for exact run outcomes and overlap accounting.
These are offline Linux tests, not GUI, remote CI, old-schema, Windows or
live-provider acceptance. No frontend files, release, merge or product-version
change is part of this checkpoint.
