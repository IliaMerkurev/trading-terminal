# ADR 0038: Verified background chart reads and note-save verification

Status: implemented; bounded Linux/browser controls and combined supported-load
acceptance passed on runtime source `9a9c3e9`. Windows/native remains deferred.
Product remains 0.6.0-dev. MIT and financial execution contracts are unchanged.

## Context

Saved report charts previously hashed a complete shared trade file and reopened
its path for eager filtered decoding in the service interpreter. Saved-history
charts used a single descriptor and bounded batches, but still hashed the file
and decoded a prefix synchronously. Saving an observation called that same
verification path before its small revision write. These operations could block
ordinary serialized service requests even while calculation used a subprocess.

## Decision

Use one separately managed verified-read subprocess lane. It does not acquire
the calculation/batch/archive reservation. Reuse the existing supervised worker
lifetime and inherited workspace ownership; this is not a generic job framework,
a security sandbox, or a change to serialized HTTP mutation dispatch.

`chart_read_start/status/cancel` expose immutable request identity, per-view
monotonic generation and actual phase. Repeated identical request IDs inspect the
same operation; reuse with different parameters is rejected. At most one worker,
one latest queued chart and one explicit queued note save are retained. Up to
128 launch-local operation records/views are bounded in memory. Obsolete chart
requests are cancelled/superseded. A new chart cannot cancel an explicit save.
Chart operation authority expires with the service; no chart job resumes.

Full physical SHA-256, Parquet bounds/schema, every trade row's finite OHLCV,
chronological/aligned/range constraints and exact declared coverage/gaps are
checked for every operation. Hashing and decoding use the same opened regular
file descriptor. Descriptor and path identity before/after decoding and before
delivery detect ordinary concurrent edits/replacements. These checks supplement
the current full hash and never become a stat-only or historical-hash cache.
The full trade stream is decoded in 256-row batches, including rows beyond the
requested page. This deliberately favors integrity over a ready-page SLA.
Other source tables are not loaded by a trade-candle chart; full dataset
materialization/canonical-content validation remains the calculation loader's
separate contract.

Run charts retain 30–480 source-unit windows, stored indicator availability,
integer-nanosecond fill bounds/association and saved equity. Observation charts
retain 500 source slots. Normalized JSON byte sizes are checked before fetching
and decoding a bounded page. The internal worker response, including its verification guard, is capped at
960 KiB; the public report page retains its 900 KiB limit and IPC stays 1 MiB. Missing
history remains distinct from checksum/order/coverage failure. No candles are
fabricated and no indicators are recalculated.

The worker never registers a display reference or writes exposure evidence.
Only a current, verified ready response delivered by the service can obtain a
bounded display reference. The frontend clears obsolete report data, aborts old
requests, guards success/error by generation and retains existing presentation
acknowledgements as the sole source of viewed events. Fetching/prefetching,
verification, saved note text and receipt history are not viewed evidence.

## Explicit observation saves

`observation_save_start` freezes the exact source identity, note fields, range,
expected revision and independent request ID. Only verification uses the reader
lane. The parent applies a bounded final revision/source check and a small note
write. A durable request receipt changes to completed in the same transaction
as the note revision. Repeated IDs cannot create another revision. A committed
receipt wins cancellation or a postcommit acknowledgement failure.

Explicit cancellation before commit prevents the save; later pan/read requests
cannot revoke it. Saved receipts and a bounded recent-request history make lost
acknowledgements inspectable after navigation/restart. Unfinished receipts become
interrupted on restart and never resume automatically. The UI preserves drafts,
distinguishes rejected admission from uncertain delivery, blocks duplicate saves
until outcome inspection, and guards late original/inspection responses by the
active save identity. Opening a receipt respects the existing dirty-draft guard.

Lane database connections use 50 ms busy timeouts. Receipt settlement retries
release the lane lock between attempts. A forced indefinitely held writer may
prevent durable settlement; cancellation remains requested and shutdown reports
retained ownership. No success/cancelled outcome is fabricated to meet a clock.
Failed launch settlement is inspectable and cannot strand a later queued chart.

## Validation and limits

Focused tests cover both page surfaces, first/middle/last contents, suffix
corruption, same-descriptor replacement, gaps, exact fill/indicator boundaries,
missing versus corrupt history, duplicate/obsolete identity, queue/cancel/close,
independence from calculation reservation, no prefetch exposure, durable note
receipts, lost/postcommit BUSY acknowledgement, cancel-after-commit, interrupted
restart, failed launch and additive migration. UI tests cover stale success and
error, aborted generations, dirty drafts, saved receipts and close warnings.

The ordinary start/status/cancel acknowledgement and bounded-write target is
2 seconds; ordinary cancellation-to-quiescence target is 5 seconds. READY total
latency and combined parent/computation/reader memory are measured separately;
no two-second ready-page promise or source-limit-as-RAM-ceiling claim is made.
The frozen-source combined six-row 2,000,000-modeled-candle campaign and
production-browser controls passed on `9a9c3e9`; see the latest STATUS entry for
exact timings, same-source aggregate coverage and memory exclusions. Windows/native
lifecycle and live exchange acquisition remain deferred.

## Explicit chart controls and integration correction

Both chart surfaces expose Cancel reading while pending and Retry reading after
a terminal cancellation/error. Cancellation retains the exact request identity,
waits for terminal cleanup, offers same-request inspection after uncertain
transport delivery, and reasserts an early request after admission. A truthful
completion-winning outcome is labeled separately; the cancelled viewport does
not expose that page. Retrying starts a newer generation. These controls never
cancel an independent note save. Intentional note cancellation is a neutral
status and retains the draft.

Aggregate integration also exposed an existing setup-review defect: closing the
Lab setup modal discarded an already completed review of unchanged inputs.
Completed reviews now survive modal close/reopen; substantive input/source and
route changes retain invalidation, and in-flight delivery still checks modal
lifecycle identity. No financial calculation or catalog-order contract changed.

## Measured acceptance boundary

The single six-row synthetic campaign completed in 1,352.731 workload seconds.
All rows executed without reuse; full hash and ordered normalized-value checks
passed. Ordinary requests peaked at 1.998035 seconds, leaving little margin to
the two-second target; cancellation-to-terminal peaked at 0.571451 seconds.
Observation READY peaked at 2.164473 seconds, measured separately rather than
weakening full-history verification. Combined summed process RSS peaked at
4,351,184,896 bytes; the 50 ms sampling excludes browser and subsequent sequential
full-result verification, can double-count shared pages and can miss short peaks.
This is a measured supported fixture, not a universal resource ceiling.

Final browser controls passed separately with a deterministic reader gate and
actual released pages. The setup-review modal correction is automatically tested;
its GUI preview lacked fixture instrument metadata, so no browser pass is claimed
for that journey. Remaining research and Windows/native/live acceptance are
separate from this engineering gate.
