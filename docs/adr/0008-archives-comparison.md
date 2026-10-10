# ADR 0008: comparison and nonexecuting project archives

The asynchronous/recoverable production import path is defined by [ADR 0035](0035-asynchronous-recoverable-import.md). The status-only and synchronous finish descriptions below remain historical/legacy compatibility contracts.

## Contract

Compare two to eight completed run records, including strategy hashes, complete
profile fields, dataset identity/coverage/range, runtime packages, engine identity
and metric definition version. Matching metadata does not prove correctness.
Imported reports carry a visible origin label and are not represented as locally
executed or independently authenticated results.

Archive schema 1 is a ZIP containing `project.json` and selected run snapshot/result
JSON documents. There are no executable archive entries. Native source is a string
in the strategy document; parsing/importing never loads its module or grants new
trust. Every imported run receives a new local identifier. Existing work is not
overwritten. Strategy settings persist with the imported or saved strategy.

The export omits raw OHLCV candles even from normalized results, as well as Parquet
history, worker logs and consent records. Derived indicators, equity, trades,
metrics and dataset descriptions remain. Candle-free reports can be viewed, but
recalculation requires the matching checked data and compatible runtime. The
application does not silently download or execute anything during archive import.

## Validation and resource limits

Transfers use sequential 256 KiB chunks over bounded IPC. Limits are 64 MiB compressed,
128 MiB expanded, 25 entries and eight selected runs. These are archive resource
limits, not historical-date limits. Unsupported compression/encryption, symbolic
links, absolute/drive/backslash/traversal paths, duplicate names, unexpected entries,
excessive expansion and checksum/schema mismatches are rejected. No ZIP path is
ever extracted to disk; only fixed local destinations receive validated objects.

An export gate rejects recognizable credential literals, private keys, provider
tokens, email addresses and private filesystem paths. It reports only the entry
and category. This conservative detector is not proof that arbitrary Python source
is safe to share; source review remains necessary. Exported files stay local until
the user chooses to share them. Checksums detect corruption, not authenticity.

## Durable status-only import receipts

Each accepted `archive_begin` commits a local operation receipt before creating
its upload file. The operation ID is also the upload ID. Exact uploaded ZIP bytes
are read once; complete validation precedes an atomic reservation transaction
that binds the raw ZIP SHA-256, a versioned canonical-content digest, every fresh
run/strategy destination and all importing run placeholders. Source run IDs remain
provenance; they never select destination paths. Intentional imports of identical
bytes get distinct operations and destinations. Neither checksum authenticates
performance or acts as an automatic deduplication key.

An import-specific publication primitive uses immutable `write_new` files and
insert-only SQL. Each run's normalized series, completed status/result hash and
published receipt item commit together. Strategy insertion, its published item
and terminal completion also commit together. Existing local worker completion
is unchanged and does not require a receipt. Identifier/directory collisions fail
closed, including a strategy row introduced after reservation. Existing artifacts
are never adopted or overwritten.

Publication is atomic **per run**, not across an archive. A failure can leave
completed reports, reserved/interrupted run placeholders and incomplete files.
The exact intended mapping remains inspectable even after a post-commit exception.
A bounded failure record cannot downgrade a committed completed receipt. Storage
finalization errors latch new imports/calculations until restart; the diagnostic
does not assert that unrelated active work stopped. If writing that diagnostic
also fails, the earlier durable phase remains and inspection may be unavailable.

The checked receiving-to-validating transition claims finish once and defines the
cancellation cutoff. Duplicate finish never publishes again. Targeted cancellation
rejects invalid IDs, cannot cancel another upload, and returns too-late after the
claim. Legacy untargeted cancellation applies only to the current receiving
transfer. Neither cancellation nor leaving the page rolls back published records.

After exclusive workspace ownership, startup reconciles nonterminal receipts from
metadata only, after ordinary run recovery. It never parses retained uploads,
repairs/promotes files, inserts results, saves strategies or starts execution.
Outcomes distinguish completed, partial, interrupted, rejected, failed, cancelled
and unknown. Contradictory metadata is unknown; a database-read failure is
inspection unavailable, never an empty successful import. Existing legacy imports
are not backfilled. There is no retry, resume, cleanup or archive-wide rollback.

`archive_import_status` returns one bounded receipt (at most nine items).
`archive_import_list` uses newest-first keyset pagination, default 25 / maximum
100 operations. These are read-only commands containing IDs, hashes, enums and
current database metadata, never imported source/document bodies or local paths.
The UI preserves a known operation after a lost final response and offers explicit
inspection. Recent imports works after reload/restart without the original File,
localStorage or an old session token. Only a published, currently completed member
can be opened from a receipt; opening a recovered strategy is also explicit.

Import persistence is separate from refresh/editor opening. Narrow import callbacks
propagate list/history/strategy read failures without changing the global action
wrapper. Generation ownership prevents delayed reads/opening/cancellation feedback
from replacing a newer selection or editor draft. Leaving during upload abandons
only that exact receiving transfer; leaving after finish never issues cancellation.
Inspection cannot invoke a new begin, finish, execution or consent request.

A later strategy edit is shown as modified-since-import without rewriting publication
history. Receipt inspection and ordinary report viewing **do not verify artifact
files**: reports read normalized database values. `artifact_verification` remains
`not_checked`; no missing/corrupt file detection is promised by this path. Full
artifact verification is outside this status-only milestone.

Finalization remains synchronous. Serialized HTTP/IPC cannot serve an in-flight
status read while finish is blocked. Lost replies may require waiting or a service
restart; there is no maximum-load timing or responsive-finalizer guarantee. Native
failed-transport close/restart recovery and the Windows picker remain separate,
unverified work. No Rust close-flow or timeout changes are included.

The two receipt tables and their index are additive. Backups must preserve the
complete closed workspace, including imports, datasets and immutable artifacts,
with a consistent SQLite backup. The receipt shares the database's failure domain.
The guarantee covers process interruption with retained healthy storage, not
independent disaster recovery, filesystem repair or verified OS/power-loss durability.
No new native trust, local research admission or imported Python execution is added.

## Evidence

Tests cover archive roundtrip without raw history, preserved metrics/trades, fresh
identifiers, source-only native import without consent, traversal/ZIP expansion/
symlink rejection, integrity failure before persistence, exact chunk offsets,
redacted privacy errors, and changed fee/runtime comparison fields.
Actual desktop comparison identified the closed/intrabar profile difference and
export produced a validated five-entry archive with two results. Component tests
verify exact File bytes, sequential chunk offsets and import completion. The
Windows native picker remains an owner acceptance check; backend roundtrip and
nonexecuting import are automated and must not be confused with picker testing.


The receipt-specific fault matrix uses distinct independent two-run documents,
preexisting sentinels, real transaction rollback/post-commit exceptions and child
termination at reservation, snapshot publication, first-run commit and terminal
commit. Reopened mappings, hashes, artifact bytes, normalized rows, imported origin,
trust/evidence and sentinels are compared exactly. Read-only inspection is exercised
with SQLite query-only connections. Real HTTP checks discard a completed reply,
demonstrate serialized in-flight blocking, then inspect the same IDs after restart.
Full synthetic backup/restore and copied legacy-workspace preservation have separate
evidence. Current counts and browser-versus-native limits are recorded in
[implementation status](../STATUS.md#durable-archive-import-inspection--2026-10-10).
