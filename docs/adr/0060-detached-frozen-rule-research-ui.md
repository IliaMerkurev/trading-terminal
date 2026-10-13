# ADR 0060: Detached frozen-rule research and original-event interface

Date: 2026-10-12

Status: Reconstructed UI with focused component evidence. Actual-browser,
Windows/native, live-provider, old-database and owner acceptance remain separate.
Product remains 0.6-dev, with no dependency or formula change.

## Decision

Mount one App-level research provider outside the keyed Market chart. Rule and
journal entry buttons open a native modal with independent scan/evidence state.
Use only the strict routes in [ALERT_HISTORY_API](../ALERT_HISTORY_API.md), with
no live context registration, monitor mutation, journal/read/banner action or
MarketChart reuse. Native modal focus and a capture-phase Escape boundary keep
research dismissal separate from Market focus and draft ownership.

Keep request retention above the disposable modal. Persist exact Start identity
and content before mutation. Reconcile through read-only request lookup even
when the Service returned an error, because commit may precede readback failure.
An absent unknown request is not permission for an automatic fresh ID. Only an
explicit exact retry is offered. A rejected retry cannot erase earlier uncertainty.
Local browser storage failure prevents new scans; the Service remains the durable
authority. Do not treat this browser-local state as a workspace backup.

Use independent per-field dirty refs for late preview defaults and interpret
native datetime fields explicitly as UTC inclusive confirmed-close bounds.
Native date input/blur handlers synchronize state, but correctness does not rely
on those events firing first. Before preview defaults, detect actual DOM value
drift and native badInput, including partially edited values exposed as empty.
At submission, require both mounted inputs and snapshot their actual values and
validity before any state update. Validate format/alignment/order, then retain
and submit precisely that visible range; never substitute older controlled state.
Effect lifecycle refs must reset during setup as well as invalidate during
cleanup, including React StrictMode's setup/cleanup/setup sequence.

Fence status reads around cancellation and retain immutable terminal metadata.
Use keyed run and view lifecycles so stale responses cannot replace newer results.
Do not resume unfinished jobs; preserve the backend's interrupted state and
explicit lack of complete coverage.

## Snapshot charts and exact targets

Render the returned raw OPEN-axis candles and saved indicator-port values through
the existing chart library, with no current settings/cache query or recomputation.
Render all returned window markers independently of the current 20-match page.
Metadata and match navigation uses actual returned cursors, and chart navigation
uses actual next_index rather than requested page width. Keep the match list
compact and independently scrollable.

Target lookup first retains up to 40 earlier rows. If byte clipping omits the
exact target, use exact-row lookup and an exact-index chart window. A standalone
exact row may fit when the chart wrapper does not: render only that returned
row and label unavailable adjacent context. Derive its marker only from its own
saved in-range hit. Missing exact evidence remains missing, never nearest.

Original-event evidence is a distinct view. Its frozen numerical evidence is
authoritative; adjacent current-cache price context explicitly may differ.
Raw target OPEN is confirmation minus interval width, while earlier divergence
pivot geometry remains supporting evidence. Never silently substitute a nearby,
unconfirmed or conflicting target.

## Alternatives and limits

Reusing MarketChart would couple research to Market context, settings, drafts and
live lifecycle. Recalculating saved indicators would break immutable provenance.
Reissuing Start under a new identity after a lost response could duplicate scans.
These alternatives are rejected. The existing 10,000 full-origin input, 256 MiB,
eight-unfinished, 600 KiB response and 20/200 page budgets remain visible.

This reconstruction restores the bounded historical research and original-event
UI, not agreement predicates/timeline, strategy conversion or trading. Synthetic
component tests establish lifecycle/payload/rendering behavior using transport
and chart mocks; they do not establish real canvas geometry, provider operation,
old-schema interoperability, native platform behavior or owner acceptance.
See [the user workflow](../ALERT_RESEARCH_UI.md) and STATUS for exact checks.
