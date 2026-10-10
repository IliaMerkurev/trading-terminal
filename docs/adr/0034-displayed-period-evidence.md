# ADR 0034: Bounded displayed-period evidence

Status: Accepted for the bounded local research slice.

## Decision

Extend the append-only research registry with `viewed` events for actual rendered
local Observation candles, selected Saved comparison numeric rows, and selected
individual report metrics/candles. Displayed in this app is not proof of reading,
a test attempt, or a claim that other history is unseen. Keep original admission
coverage and add a separate view-coverage start marker. Existing frozen reviews,
run snapshots/results, notes, accounting, dependencies and product version stay
unchanged.

The UI observes intersecting rendered metric text/value elements or the actual candle pane,
checks hidden ancestors/document visibility and app modal occlusion, and reads
the chart's current visible time labels. Dataset lists, fetched pages, hidden
components and note saves do not themselves append views. A shared presentation
identity and durable event key deduplicate repeated callbacks without deleting
old events. A later reopening may be a distinct presentation.

The backend issues bounded references to the exact verified chart pages returned
for presentation. The 32-entry memory cache holds candle timestamps and resolved
source identity, avoiding repeated full-Parquet hashing on each pan. A reference
cannot select another source; expiration/restart fails visibly. Observation labels
are opens, RunChart labels are closes. Actual candles intersect the inclusive
viewport and become disjoint half-open ranges; missing slots and whitespace do
not create exposure. A fetched page alone creates no registry entry.

Comparison/report metrics resolve their full evaluation range and source from
an immutable local admission plus completed report. Original passive/strategy
roles and saved cohorts remain distinct. Unknown provenance remains conservative;
explicit synthetic sources retain their isolated namespaces. Imported/legacy
reports without local admission evidence are explicitly incomplete in this slice.
No external data, network research, live/replay tracking or general telemetry is
added.

Tracking failure does not block reading. It latches a visible session warning and
best-effort durable coverage caveat. Pending callbacks/writes drain before freeze
preview/confirmation; a frontend-only caveat must persist before freezing. If the
caveat cannot persist, freeze remains open with an error. Subsequent overlap and
new frozen reviews include the caveat; old frozen reviews are never recomputed.
The UI caps outstanding writes and per-presentation distinct records, warning
rather than silently discarding overflow.

## Validation and limits

Focused synthetic backend/component tests cover split gaps, open/close mapping,
zero attempts after manual chart display, source isolation, passive role,
presentation deduplication, cache bounds, legacy incompleteness, failure handling,
restart persistence, immutable JSON preservation and unchanged frozen reviews.
Browser/native acceptance is recorded separately in STATUS.md. Simulated DOM
intersection tests are not proof of actual browser or Windows visibility.
