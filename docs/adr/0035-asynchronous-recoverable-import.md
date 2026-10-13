# ADR 0035: managed, explicitly recoverable archive imports

## Scope and decision

This is the import vertical slice of original-plan TT13. Export construction and
download, shared-history chart reads, and local calculation-result finalization
remain separate unfinished TT13 paths. Product version stays `0.6.0-dev`.
No new dependencies, general job framework, financial execution, imported-source
trust, automatic retry, automatic recovery or archive-format changes are added.

The production UI uploads in bounded chunks, calls `archive_import_start`, and
sequentially polls the existing receipt endpoint. Validation, canonical hashing,
artifact verification and normalized-row staging run in an application-owned
process. The existing Linux supervisor/lifetime pipe, inherited workspace lock
and Windows worker lifecycle are reused. This is not a security sandbox. Current
Windows/native acceptance is deferred; Linux evidence cannot establish it.

The existing sequential scheduler reservation is held from durable claim through
process reaping and terminal settlement. Calculations, replay and batches cannot
start in that interval. No scheduler lock is held over bulk work, joins or waits.
A failed bootstrap retains process ownership until reaping. Shutdown stops the
archive process before releasing workspace ownership. Startup performs metadata
reconciliation only after exclusive ownership; retained uploads are not parsed,
outputs are not promoted, and attempts are not restarted.

## Durable protocol and compatibility

Receipt schema 1 and archive schema 1 remain intact. Additive version-1 companion
tables store execution control, append-only attempt identities/prior receipt
snapshots, and explicit replacement-upload references. The receipt remains the
operation identity; its reserved run and strategy IDs survive every attempt.
A new intentional import of identical bytes still receives new IDs.

- `archive_import_start(operation_id)` claims a fully received operation once.
  Repeated calls inspect it; they never reserve or execute it again.
- `archive_import_resume(operation_id, expected_revision, attempt_key)` is an
  explicit compare-and-swap continuation. Repeating an existing key returns its
  `acknowledged_attempt`, even if a newer attempt exists. A different concurrent
  key cannot claim the same revision. A further intentional retry needs a new
  key and current revision. Completed receipts are immutable no-ops.
- `archive_import_cancel(operation_id, attempt_key)` records a cancellation
  request and revokes worker lifetime. Stale keys are harmless. Calls without an
  attempt key retain receiving-only compatibility; an asynchronous attempt
  returns `attempt_required`. `cancel_requested` is not stopped. Only after
  reaping is cancellation acknowledged and the scheduler reservation released.
- `archive_import_status` includes bounded metadata, execution progress, revision
  and the latest ten attempt summaries. The full attempt history is retained in
  SQLite. Inspection does not hash large artifacts or authenticate reports.
- Legacy `archive_finish` is deliberately retained as synchronous compatibility.
  It shares sequential scheduler exclusion, but is outside responsiveness claims.
  Production UI no longer calls it. Legacy untargeted cancellation still affects
  only the receiving transfer. Lost `archive_begin` replies are not idempotent;
  inspect Recent imports rather than claiming a client key that does not exist.

The final strategy insertion, receipt completion and exact-attempt control check
share one short transaction. Cancellation and completion therefore have a clear
commit winner. Cancellation never rolls back published reports: outcome is partial
when any report was published, otherwise cancelled. Schema-1 reason constraints
are preserved; companion metadata carries user cancellation attribution. Only
extension-backed cancelled reservations receive the corresponding narrow
consistency exception. A recorded storage failure latches quarantine even if a
cancellation request races with worker settlement; restart remains the boundary.

## Hidden staging and publication

All IDs and expected content identities are reserved together before output files.
Expensive canonical bytes/hashes are computed before the reservation transaction.
Rows are staged in at most 128-row / 256-KiB encoded batches, while the run remains
importing. A single admitted row can exceed the byte target; existing archive
limits are deliberately unchanged and that case is measured separately.

Per-batch and per-item transitions check the exact attempt, cancellation state,
receipt phase, reservation identity and placeholder state. Final normalized counts
and completed run/publication state commit together. The completed status is the
visibility switch; staged rows may exist, but result/page/chart/comparison readers
must reject the incomplete run. Imported results never acquire local batch or
research-admission provenance. Existing synchronous publication tests remain
legacy compatibility evidence, not a claim that asynchronous staging rolls back
all rows on failure.

## Explicit continuation and conflicting content

Before any continuation publication, the worker revalidates exact original ZIP
SHA-256, canonical content identity, source order, every reservation/hash/count,
all published artifacts and imported summaries, and every existing normalized
kind/index/value. Existing incomplete artifacts must match exact expected bytes;
staged rows are verified and reused at their original indices. Missing rows alone
are inserted. Completed runs are never rewritten. Unknown states, mismatching
content, foreign destinations and symbolic-link artifact paths fail closed.
No rows/files are deleted to force a repair. A corrupt published report is a
blocker, not a resumable partial success.

If the original upload is missing, `archive_recovery_begin` creates a separate
bounded upload, ordinary append sends its chunks, and `archive_recovery_finish`
retains it for verification. `archive_recovery_cancel` abandons only that exact
transfer while retaining bytes and the original receipt. Replacement is allowed
only for a checksum-bound incomplete import and never overwrites the original
file. Merely retaining replacement bytes does not grant publication: explicit
resume verifies both original hashes first. Unbound historical operations cannot
claim checksum-bound replacement identity.

## UI and evidence boundary

Inspection and cancellation stay available during background work; receiving
upload controls preserve their separate generation. Poll failures mean status
unavailable, not import failure. Reload discovers receipts without restarting
work. Explicit continuation retains progress and IDs. Generation/unmount guards
prevent stale completion/opening from replacing a newer selection. Durable
completion stays separate from list refresh and editor opening errors. Browser
leave/service-stop and desktop close checks include archive ownership.

Linux development targets were declared before load measurement: start, status
and cancellation acknowledgement at most two seconds; actual cancellation
quiescence at most five seconds on ordinary load. Near-limit maxima are reported,
not silently converted into a universal SLA. Measurements include an ordinary
foreground SQLite writer through the unchanged serialized HTTP host, write
transaction duration, source/row/hash identity, memory, integrity and cleanup.
See STATUS.md for exact commands, measured values and remaining acceptance.
