# ADR 0033: Local history observations and revision-bound test links

## Decision

Keep Market and Lab as the two primary research modes. Market's Saved history
subview reads prepared local trade candles through a dedicated endpoint and the
existing lightweight-charts dependency. It never calls the live chart history
adapter, downloads replacement data, selects a strategy or starts a calculation.
Data cards also open this route directly without mounting Live. Switching away
from Live releases its existing view ownership, not an explicitly owned strategy.

A saved observation fixes the exact dataset identity, source provenance digest,
trade/mark/funding file hashes, source resolution and half-open UTC range.
The hypothesis is required; a short falsification condition is optional. Text
edits append immutable revisions under an expected-revision guard. Changing
source or range creates a new observation. The journal uses additive local tables,
50-entry chronological keyset pages, and at most 100 displayed batch links.
Neither notes nor chart pages are recorded as proof of viewed data in the
forward-only admission registry. Its incomplete viewing coverage stays explicit.

Test observation transfers a single source/range/revision context to the existing
Lab setup. It never executes automatically. Async warmup suggestions cannot move
its dates. A user must choose compatible strategies/settings, explicitly detach
before changing dates/source, or return and make a new observation. Insufficient
warmup blocks Review. Saving more notes later cannot change the revision used by
an earlier linked test. Existing Library names, notes, search, filters and frozen
financial snapshots are retained.

The optional link is committed in the same SQLite transaction as Library batch
and row admission, before thread start. Full saved/current source identity and
exact evaluation dates must match. Link or batch persistence failure rolls back,
releases the reservation and quarantines further calculations on storage failure.
No unlinked fallback launch is permitted. Batch status exposes the separate link;
immutable run and batch snapshots contain no mutable journal content.

## Reader and verification limits

Each page covers at most 500 source-candle slots. The reader streams the entire
trade-file SHA-256 in 1 MiB chunks, then decodes at most 256 rows at a time.
It refuses files above 256 MiB, Parquet footers above 4 MiB, more than 2,000,000
rows or 8,192 row groups, or a row group above 128 MiB uncompressed. Arrow Thrift
metadata has explicit string/container limits. The fixed candle schema, inspected
timestamp ordering/alignment and selected-page OHLCV are checked. Missing slots
are returned and shown. Source bytes are checked again when saving an observation.

A late page may scan preceding rows, bounded by the stated limit; this is not an
indexed constant-time reader. Integrity checks cover the declared trade checksum
and inspected page, not complete semantic validation of all history or mark/
funding files. Existing calculation admission retains its own full dataset checks.
Unsupported or missing history stays unavailable with an explicit error; no source
substitution, silent date truncation or network fallback is allowed.

## Bounded local display intervals

Saved history keeps a local Source/1h/4h/1d display choice separate from source,
strategy and execution resolutions. The native-equivalent option is shown only
as Source. The verified page source supplies chart resolution; observation date
validation and paging retain their original source alignment. Exact-source
identity changes reset the display choice synchronously; ordinary page and
Market/Lab navigation preserve it. Existing immutable source/range/revision and
Lab handoff contracts do not change.

A dedicated frontend projection accepts explicit verified page bounds. A UTC
bucket is complete only when wholly inside that page and every aligned source
opening occurs exactly once. Complete buckets use first open, maximum high,
minimum low, last close and sum of recorded volumes. Bad timestamps fail closed
visibly; invalid prices and unavailable/non-finite/overflowing volume cannot
fabricate valid numeric aggregates. Missing and outside-page constituents are
separate counts. Incomplete buckets stay inspectable whitespace in both panes.

Only integral coarser intervals fitting within 500 source slots are available.
One-minute-to-daily display requires 1,440 slots and is explicitly unavailable.
There is no adjacent-page cache, prefetch, stitching, source substitution or
persisted aggregate. A 500-slot boundary can bisect the same UTC bucket on both
adjoining pages; this limitation is preferable to hidden read amplification or
rewriting saved dates. Completeness describes this selected verified snapshot
and page, not independently verified market completeness. Display evidence maps
back to exact contributing source rows under ADR 0034.

Live aggregation is deliberately not reused: it permits partial/forming buckets
and uses closing labels. Saved history retains opening labels and requires full
coverage. General interval selection, aligned cross-page reads and larger
projection budgets are separate scope.

## Independent exact-date navigation and page recovery

Browsing has its own UTC text draft and tagged idle/loading/ready/error page
state. It never rewrites an observation range, revision or text, and never
changes Lab selection/profile or starts a test. Literal date fields use an
exact UTC calendar round-trip; no local timezone, normalized invalid calendar,
fractional timestamp, native-boundary rounding or display-bucket alignment is
accepted. Safe integral source bounds and native resolution are checked before
formatting dates or constructing requests. The exclusive source end is invalid
as a target opening.

For source `[S,E)`, native step `s` and `N=(E-S)/s`, a valid target `T` reads
exactly `[T,min(E,T+500*s))`. First targets `S`; Latest targets
`S+floor((N-1)/500)*500*s`. Thus 500 and 1000 slots have full final pages, while
501, 900 and 1200 have final pages of 1, 400 and 200 slots respectively. An
arbitrary slot-613 jump in a 1200-slot source reads `[613,1113)`; Later reads
`[1113,1200)`, while Latest remains `[1000,1200)`. Earlier is relative to the
loaded start and clamps only at S. No adjacent pages or full-source table are
loaded. The verified source, not display aggregation width, supplies navigation
arithmetic after the initial read.

Each accepted request captures its dataset, selected-declaration fingerprint,
source identity, exact boundaries and epoch. Acceptance immediately removes the
old chart, selection and error. Cleanup plus epoch/declaration guards exclude
stale success, rejection and finalization. Returned dataset/window ownership is
checked before presentation. A list manifest fingerprint is not compared with
the reduced verified source identity; exact saved/established verified identities
are compared separately. Unexpected same-ID identity replacement, changed
selected declarations and unavailable saved sources fail closed without silently
replacing a note. Explicit source selection/reopen can establish a new source;
ordinary paging cannot. Save responses also reconcile exact source identity and
retain source-unavailable state when starting a new draft.

Failure owns immutable numeric request parameters and a captured source label,
including the full snapshot identifier. Explicit Retry repeats those parameters,
not the current text draft. Repeated failure remains retryable when the exact
source is still available. Input editing neither queues a read nor changes its
result ownership. Synchronous pending guards prevent duplicate submissions;
save/open operations block navigation. No automatic retry or transport timeout
change is introduced. Native transport failure can require a separate restart.

Missing openings and all-gap pages are successful bounded reads. Incomplete
display buckets keep the chosen compatible interval and their missing/outside-
page explanation. Typing, validation, submission, failed and stale requests do
not produce displayed evidence. The unchanged actual-visibility recorder may
record a verified chart only after it is rendered and visible, with the existing
exact constituent mapping and hidden/modal/offscreen exclusions. Display tracking
failure remains separate from page-read failure. There is no new durable write,
automatic note revision, dataset preparation, bookmark or settings persistence.

## Alternatives and deferred scope

Reusing live MarketChart would risk network access and wrong provenance. Loading
DatasetStore.load would materialize full history for a small page. Both were
rejected. No dependency, new dashboard framework, rich text, chart drawings,
strategy, accounting model or product-version change is introduced. Indexed
history and deeper evidence-journal features remain separate work; bounded
actual-display evidence is described in ADR 0034. Browser/component evidence does not establish Windows acceptance.


## Explicit chart-to-observation boundary capture

An explicit click on a valid-price source or complete display candle, or existing
keyboard navigation, pins that candle while the pointer moves to action controls.
Transient hover does not replace the pin or edit a note. Clicking a gap removes
actionability; clear, page/source/display replacement and out-of-view navigation
remove the selection. Missing volume alone does not prevent using verified price
candle times; invalid price and incomplete source coverage do.

The start action copies the selected slot opening, and the end action copies its
exclusive close. Aggregates retain their complete UTC bucket boundaries. Only
one endpoint of an unsaved observation is updated functionally; an invalid pair
is retained with ordinary range validation rather than silently repaired. Saved
ranges and revisions remain immutable, including while a save is pending.

At activation the chart rechecks its current pin, valid price, complete coverage,
current visible time range and presentation identity. The observation owner
checks the live page epoch, exact verified source/display identity, page bounds,
native alignment, current record and action locks. Old chart callbacks cannot
change a replacement page or an already saved observation. The actions perform
no read, save, Lab admission or display-evidence write; existing actual-visibility
recording remains the only chart exposure path.
