# ADR 0063: Fault-resilient alert shutdown and ownership fences

Date: 2026-10-12
Status: Reconstructed shutdown integration correction
Product version: 0.6-dev

## Decision

Separate in-memory shutdown from persistence. History and local alert owners
close admission and signal every cancellation token before attempting terminal
status or cursor writes. They always wake and join their worker, preserve all
write errors, and report join timeouts. A failed rule cursor write cannot skip
detaching later rules' passive observers. History checks its closed fence before
queue selection and result/error persistence, so cancellation during shutdown
does not require another database connection or publish a completed result.

Service attempts both new owners before deciding whether dependent cleanup is
safe. A genuinely live replay retains every downstream dependency and workspace
lock. A storage error after the worker has stopped is aggregated with existing
cleanup errors; it cannot strand the other background owners or prevent safe
workspace release. Missing owners on partial initialization are skipped. The
existing final ownership check still prevents unlocking for any live legacy
owner, including warmup and calculation processes.

Repeated owner close retries joining without repeating storage writes. Once
Service has stopped all owners and released its workspace lock, further close
calls do nothing. The first failed persistence attempt is reported, not hidden
or retried after another instance could acquire the workspace. Startup's existing
interrupted-run and paused-alert fences recover unfinished durable state; there
is no automatic replay, Arm or resume.

## Alternatives and verification

Failing fast on every close exception stranded independent owners on ordinary
SQLite failure. Unconditionally continuing cleanup after every exception would
destroy dependencies still used by a timed-out worker. The chosen distinction
uses actual worker liveness rather than exception type as its safety gate.

Focused synthetic tests retain the original journal/process/warmup failure
assertions and true blocked-replay tests. Added cases cover multiple-rule cursor
failure, active history cancellation with failed persistence, combined storage
failure and live replay, clean repeated close after workspace removal, and
restart interruption without automatic work. A legacy test fixture now removes
its temporary workspace only after registered Service cleanup. No formula,
dependency, provider, PAPER/order, product-version or frontend change is made.
See STATUS for executed results; these checks do not establish Windows/native
or owner acceptance.
