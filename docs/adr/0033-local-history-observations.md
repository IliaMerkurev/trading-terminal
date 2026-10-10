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

## Alternatives and deferred scope

Reusing live MarketChart would risk network access and wrong provenance. Loading
DatasetStore.load would materialize full history for a small page. Both were
rejected. No dependency, new dashboard framework, rich text, chart drawings,
strategy, accounting model or product-version change is introduced. Indexed
history, manual-view telemetry and deeper evidence-journal features remain
separate work. Browser/component evidence does not establish Windows acceptance.
