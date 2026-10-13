# ADR 0037: managed local result finalization

Status: accepted for this bounded TT13 slice, 2026-10-11. Product remains
`0.6.0-dev`. Windows lifecycle code is preserved; current native acceptance is
separate. This does not close chart-integrity reads or whole-plan TT13.

## Problem and decision

The computation monitor previously decoded worker JSON, encoded immutable output
and inserted every normalized row while holding the scheduler ownership lock.
Its SQLite transaction could monopolize ordinary foreground writes. A background
thread alone would still contend for the service interpreter during JSON work.

Keep the same run monitor and active identity through computation, a separately
managed local finalizer process, durable publication, and process cleanup. Batch
waiters already join that monitor, so they cannot advance on computation exit or
staged rows. During finalization, only short ownership transitions take `jobs.lock`; decoding,
canonicalization, artifact publication, staging, verification, DB waits and
process waits happen outside it. Initial admission still performs its existing
bounded persistence under that lock. The finalizer uses existing Windows Job Object
or Linux lifetime-pipe/workspace-lock ownership, not a new sandbox. Native trust
and financial execution rules are unchanged.

## Local authority and immutable output

Actual local admission registers a fresh generation and snapshot hash in the
same transaction as the run and its original admission evidence. Imported
receipts never create this control. Finalization rejects a missing/wrong
generation, an imported destination, unexpected old normalized content, or a
preexisting result artifact. The snapshot file, persisted manifest and frozen
snapshot digest must agree. The original result schema, financial values,
canonical result bytes/hash, and local summary provenance are retained.

`local_finalization` and `local_finalization_batches` are additive tables.
Staged rows use the existing normalized-series table, but every normalized-result reader
continues requiring a completed run. Status, history and logs may expose unfinished work. Ordinary batches contain at most 128 rows
and 256 KiB of preencoded values. The old schema allowed a single valid row to
exceed that byte target; such rows remain valid and are written alone, counted
explicitly as oversized, and measured. This is a disclosed single-row exception,
not a new output limit or a promise that arbitrary storage stalls are bounded.

Each batch records order, count, encoded bytes, content hash and chained receipt.
An independent ordered read transaction then compares every kind, index and
canonical value plus every receipt against the expected result. Small triggers
advance a local control's mutation epoch on series and receipt changes; a moved
series row invalidates both old and new owners. The final write transaction
checks generation, execution state, epoch, totals, receipt chain, artifact hash and frozen
manifest before publishing the unchanged summary/hash. It performs no full
series scan or encoding. The epoch protects normal concurrent database changes
between verification and publication; an actor who can rewrite the database,
schema or triggers is outside this integrity boundary. Legacy/imported runs
without local controls receive no provenance or evidence upgrade.

## Cancellation, failure and restart

`finalizing` is a distinct run phase. Status exposes actual phase, staged rows,
bytes, total rows, oversized rows, and whether owned worker cleanup remains.
Engine percentage stays separate; no estimated completion percentage or ETA is
invented. Computed output is not yet a successful durable report.

Cancellation and completed publication compete through guarded write
transactions. A completed commit wins a late cancellation. Cancellation is a
request until process reaping and durable settlement; terminal cancellation is
never published while a finalizer still owns work. The foreground cancellation
claim has a 250 ms busy timeout. Only SQLite BUSY/LOCKED may defer the durable
claim: the service retains ownership, requests termination, reports requested
cancellation with the separate durable status, and retries the generation-bound
claim after reaping. A commit that already won remains completed. A forced
stalled process retains ownership honestly; there is no promise to terminate
uninterruptible storage within a deadline.

DB/file persistence errors quarantine new work until restart. A dedicated worker
exit code and durable fault marker cover marker-write failures and cancellation
races; a parent-side cancellation fault also suppresses fallback terminal
writes. Postcommit failure never erases the completed result. Process/bootstrap
pipe failure is not automatically classified as a storage failure. Uncertain
process, log-reader or anchor cleanup retains ownership and quarantine. A
service-held SQLite anchor lasts through finalizer reaping for the retained
Windows WAL lifecycle.

Startup interrupts unfinished local finalization and preserves completed work.
It never promotes worker-result files, continues staging, retries, or executes
anything automatically. Incomplete artifacts and rows are retained, hidden,
and never reused as evidence of successful calculation.

## Alternatives and verification

A service thread was rejected because JSON/canonicalization still competes for
the parent interpreter. Reusing imported-report authority was rejected because
it could grant local provenance incorrectly. A long final verification scan
inside a write transaction was rejected because it recreates the foreground
write bottleneck. A generalized job/audit framework and automatic local-result
recovery are outside this slice.

Focused tests cover exact hashes/values/order, local/import ownership, mutation
before and after verification, receipts, cancellation at deterministic stages,
bootstrap/marker/postcommit faults, stalled write-owner cancellation, retained
cleanup ownership, real serialized HTTP requests, batch waiting, and additive
closed-copy restore. Campaign scripts report measured request/lock latency,
phase/row/byte progress, separately disclosed oversized writes and sampled
process-tree memory on synthetic-only workspaces. Write-attempt measurements
include connection and lock acquisition plus commit; they are not pure lock-held
transaction duration. See [STATUS.md](../STATUS.md) for actual evidence and
remaining platform/browser boundaries.
