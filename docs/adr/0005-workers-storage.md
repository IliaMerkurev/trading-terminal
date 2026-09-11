# ADR 0005: Local IPC, managed workers and immutable run storage

Status: implemented and tested on Windows. Desktop UI integration remains open.
Scope: [PROJECT sections 5–8](../../PROJECT.md). IPC schema version 1.

The Python application service receives bounded JSON lines through the desktop
host's local pipes. There is no HTTP listener. Requests contain version, request
ID, command and exact named parameters. Unknown commands/fields fail. The initial
allowlist covers saved graphs, datasets, run start/status/cancel, manifests and
paginated results; it exposes no shell, arbitrary path, Python expression or
dynamic method dispatch. Requests/responses are limited to 1 MiB.

The service starts one separate Python worker per backtest. It persists the
immutable graph/profile/dataset/runtime snapshot **before** launching. The worker
waits at its stdin gate while the parent attaches a Windows Job Object, then
verifies the snapshot, runtime identity and dataset files before calculation.
The runtime check catches code/environment changes between snapshot creation
and worker startup. Editing a saved graph never edits an existing run snapshot.

Windows job lifetime control kills the worker's descendant process tree on
cancellation or host failure. It is not a security sandbox: trusted native code
still has user-level capabilities. Attachment failure aborts startup; the worker
is never allowed to proceed outside the managed lifetime boundary. A workspace
instance lock prevents a second service from taking over an active run.

Worker stdout/stderr go to a separately drained local log, capped at 256 KiB;
excess output is discarded while the pipe continues to drain. It is never parsed
as IPC. Progress uses append-only versioned records, avoiding Windows atomic
rename/read sharing races. Status replies expose the latest complete record.
Runtime errors, cancellation requests, cancelled, failed and completed states
are distinct. Cancellation after engine progress is tested, not inferred from
terminating an idle interpreter.

## Persistence and completion

SQLite stores run metadata, strategy documents and indexed result rows. Every
connection is closed explicitly (transaction context alone does not close a
Python SQLite connection). The database uses WAL and transactions. Immutable
files retain input snapshots, normalized full results, fills and engine order
artifacts; integrity hashes detect changed final results. Random event UUIDs are
excluded from normalized engine order artifacts so numerical repeats compare.

A worker exit code of zero is necessary but insufficient. Completion additionally
requires a complete result schema tied to the expected snapshot digest and a run
that has not been cancelled. Cancelled/interrupted artifacts are never promoted
to successful results. On a later startup, abandoned active rows become
`interrupted`; they are not automatically resumed. Completed runs cannot return
to running state or be overwritten by editing a strategy.

Result pages contain at most 1000 rows and at most 512 KiB of row content. Query
indexed rows rather than loading the whole run for every chart/table request.
The full local result remains available for integrity-checked export later.

## Windows checks

Six worker/service tests verify actual worker completion, immutable inputs,
repeated identical saved results, bounded paging, explicit cancellation, absence
of a successful partial result, rejection of mismatched result digests, command
allowlisting, strategy save/reopen and rejection of a second workspace owner.
An earlier separate engine-worker test verifies termination of its spawned child.
The complete regression inventory is now 65 tests; UI acceptance remains pending.

Development entrypoint for the pipe service:

```powershell
.venv/Scripts/python.exe -m terminal.bridge
```

This is an IPC service, not the desktop launch command. It exits and shuts down
active workers when its parent input pipe closes. The UI will prompt before
closing an active run; minimizing must not close this service.
