# ADR 0020: Maintenance paging and managed Replay

Status: implemented for 0.5.1-dev; acceptance evidence is in [STATUS.md](../STATUS.md).

## Paging

Chart pages explicitly distinguish loading, retryable error, ready and confirmed end. An empty cache or failed transport is not evidence of exhausted exchange history. Retry retains candle ownership and the existing viewport-preserving merge. Native intervals, cache identities, ordering and financial semantics are unchanged.

Results uses `run_history(before, limit)` with an exclusive `(created_at, id)` keyset cursor. Both fields sort descending, resolving timestamp ties deterministically. The UI requests 50 rows, the backend permits 1–100 and bounds row content to 512 KiB. Newer insertions do not shift subsequent older pages. Refresh begins a new traversal. Existing `list_runs`, record formats, snapshots and comparison/export identifiers remain supported. Experiments and saved Live session pagination are deferred rather than expanding this maintenance scope.

## Replay

`live_replay(session_id)` now returns a `replay_id`. `replay_status(replay_id)` returns lifecycle, progress and final result; a null ID selects the latest job. `replay_cancel(replay_id)` requests cancellation. The bundled frontend uses this asynchronous contract; the synchronous `LiveManager.replay` Python helper remains for existing internal callers.

Extend the existing `JobManager` and `terminal.worker`, reusing the shared single-calculation slot, stdin gate, Windows Job Object, bounded stdout log and append-only progress. This avoids both an unrelated job framework and CPU-intensive work inside the synchronous pipe handler. A service thread alone was rejected because it would share the interpreter and offer weaker cancellation. No new dependency or provider is required.

The additive `replay_jobs` table stores session identity, status, error and the existing MATCH/MISMATCH result object. Worker artifacts live under the local data root. Start verifies the session and runtime identity. The worker reads the frozen session profile and verifies candles, position contexts, indicator values and transitions in one query-only SQLite snapshot. It does not restore the live account, emit notifications or rewrite source journals. The read snapshot begins in the worker; UI verification is offered for paused sessions.

States are running, cancel_requested, cancelled, completed, failed and interrupted. Cancellation wins against a not-yet-published completion under the manager lock. A mismatch is a completed verification with `match: false`; worker failure is not a mismatch or success. Restart marks abandoned jobs interrupted without automatically resuming them. Closing uses existing process-tree cancellation and waits for the monitor before releasing workspace ownership.

The service retains an idle SQLite connection through Replay terminal publication. This anchors the WAL/shared-memory lifetime on Windows while terminating a worker that holds a read transaction. The final native smoke exposed a disk I/O error without this anchor; the corrective regression delays inside the actual snapshot and checks cancellation, restart of another job and database integrity.

The UI restores the latest job status and provides progress/cancel controls in Signals. A running Replay triggers the desktop close confirmation even when the user leaves Live. Backtests and experiments cannot overlap Replay. The host's existing uncertain-response timeout policy remains unchanged; Replay duration no longer occupies one desktop request.

## Limits and evidence

Progress is recorded at start, every 256 candles and successful completion. Its fraction describes input traversal, not profitability or account execution. Jobs retain local metadata/artifacts; automatic retention is outside this release. Previous financial goldens and public-market endurance evidence remain applicable to unchanged execution paths.

Focused tests cover chart failure/retry/viewport, 125 saved runs with timestamp ties and concurrent insertion, a deliberately delayed managed Replay exceeding 30 seconds while other service commands respond, cancellation, failure, mismatch and worker-slot reuse. Component tests are distinct from compiled Windows smoke. Final copied migration and native evidence are recorded separately.
