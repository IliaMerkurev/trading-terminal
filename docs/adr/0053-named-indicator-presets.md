# ADR 0053: Named local indicator presets

Date: 2026-10-11. Authorized development; platform and owner acceptance pending.

## Decision

Keep a reusable named preset library in the current workspace database, separate
from the applied indicator set for each source/market/symbol. A preset is an
immutable, versioned declarative content snapshot. It contains ordered indicator
instances, including identifiers, parameters, colors, visibility and placement.
It never contains calculation origins, cached candles, events, provider sessions,
credentials, enabled alerts or executable content. There are no starter trading
recommendations or automatic preset selections.

Save current captures the applied set at its expected namespace revision.
Unapplied editor changes must first be applied or cancelled. Saving creates a new
name; it never replaces existing preset content. Duplicate/Save as creates another
independent snapshot. Rename changes only metadata. Names are trimmed, bounded
to 120 characters, reject control characters and are case-insensitively unique
among active presets. Empty presets are valid.

Selecting or inspecting a preset does not change the chart. Staging a preset
previews its replacement instances in the indicator editor. Existing dirty edits
cannot be silently replaced. The user must explicitly Apply to update the
current namespace through the existing atomic revision-checked settings path.
During the mounted Market session, unapplied drafts remain scoped to their exact
source/market/symbol when switching contexts, including the original expected
revision. Returning shows the retained draft; Cancel or acknowledged Apply clears
it. Reloading the application does not persist this session-only draft cache.
The destination retains its own calculation origins; formula caches are
invalidated by the existing save operation. No history or origin is transferred
between sources, symbols, markets or workspaces. Preset metadata changes never
change already applied chart settings.

## Persistence and recovery

An additive SQLite table stores preset identity, metadata revision, content and
durable trash state. Save current reads and captures settings transactionally;
stale settings or preset revisions fail visibly rather than overwriting newer
work. Invalid or unsupported saved settings are not captured as fallback defaults.
Deletion moves an item to persistent trash, with explicit Restore. An active-name
collision blocks restoration until resolved; there is no permanent-delete action
or automatic trash expiry in this slice.

Mutation requests are never retried automatically after an uncertain response.
The UI exposes failure and explicit library refresh for inspection. Source
changes invalidate obsolete editor/library replies. Existing uncertain settings
saves retain their quarantine until an authoritative chart reload. Library reads
reuse the checksum-verified paged transport for large snapshots. There is no
preset-count or instance-count quota; existing byte/work guards still fail
explicitly without truncation. These guards do not promise unlimited hardware.

## Extension seam and alternatives

Content has version 1 and an `extensions` object reserved for future declarative
presentation fields. This slice writes an empty object. Metadata actions and
duplication preserve content, including extension fields. This client refuses
to stage unsupported nonempty extensions instead of silently losing future
layout information. A later pane-layout slice can introduce a validated
presentation extension and reference the snapshot's instance identifiers. That
slice must also extend the active chart-settings read/save contract atomically;
the extension seam alone does not make the existing active-set writer preserve
new fields it does not yet understand.
Pane customization and indicator alerts are not implemented here.

Browser localStorage was rejected for the library because it would split native
and browser workspaces and lack the existing database backup/revision semantics.
Automatic apply on selection and in-place overwrite were rejected because they
can lose dirty work or change another chart unexpectedly. Capturing draft content
directly is deferred: the applied set is the authoritative save-current source.

## Verification boundaries

Focused persistence, transport and UI lifecycle checks are recorded in
[STATUS](../STATUS.md), separately from actual browser interaction. Existing VMC
formulas, confirmed-bar timing, HA/raw separation, strategy/trading behavior and
source acquisition remain unchanged. Windows/native, live-provider and owner-led
unaided acceptance are deferred. No dependency, product-version, publication,
release or main-merge change is implied.
