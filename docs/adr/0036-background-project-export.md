# ADR 0036: managed project export and bounded verified download

- Date: 2026-10-10
- Status: implemented; bounded production-browser export acceptance passed; native and whole-product owner acceptance pending
- Product: 0.6.0-dev
- Scope: original-plan TT13 export and transfer only

## Context and baseline

Export previously read and verified every result, serialized/privacy-checked all
JSON, compressed and revalidated a ZIP, and wrote it within serialized service
IPC. The browser endpoint then read/hash-checked the whole ZIP and synchronously
wrote it. A copied independent near-expanded fixture measured 26.795 seconds for
export, 26.492 seconds for a queued scheduler request, and 4.826 seconds of
scheduler delay behind a deliberately unread response. A longer browser timeout
or moving only compression to a thread would not repair those paths.

## Decision

`archive_export_start` takes an explicit 32-hex `request_id`, freezes canonical
strategy/profile/run IDs and stored immutable result/snapshot identities, and
returns a launch-local operation. The request file's SHA-256 is carried in the
small supervised bootstrap; the worker checks the same opened file before using
it. Repeating the same identity and inputs inspects the same operation. Changed
inputs conflict. At 128 retained operations the session rejects new identities;
it never evicts an identity and accidentally executes it twice.

One managed process uses the existing sequential heavy-work reservation, with
read/verify, encode/privacy, compress/validate and publish phases. Neither graph
nor native strategy code executes. Full archive validation and privacy gates,
eight-run/64-MiB ZIP/128-MiB expanded/64-MiB entry limits, original canonical
content hashes, and candle/log/consent exclusion remain unchanged. The old
synchronous helper remains internal; synchronous export is no longer IPC.
There is no generic job framework, parallel mutation dispatcher or new queue.

The process stages a fully validated ZIP and an ordered 256-KiB chunk descriptor.
The monitor first reaps the owned process, then publishes to a generated basename
under the same short lock used for cancellation. POSIX uses an exclusive hard
link; Windows uses its no-replace rename, with file handles closed first. File
identity is verified again after publication. Cancellation before this cutoff
leaves no successful download; completed wins afterward. An error after successful
completion or during cleanup cannot erase the completed outcome. Scheduler and
workspace ownership remain held while process/resource cleanup is unconfirmed.

Export operations/grants are deliberately **launch-local**. Completed ZIPs stay
in the exports folder. Restart never resumes unfinished work or promotes staging,
and it revokes every download grant. Abandoned staging or a ZIP left by a
post-link failure is not a completed operation and cannot be downloaded through
this API. Imports retain their existing durable receipts and continuation rules.

## Transport and browser

Only an actual completed server operation grants `/api/export/chunk` access.
Clients supply operation ID, exact generated filename, aligned offset and exact
bounded size, not grant hashes. The endpoint checks a regular non-symlink file,
opened descriptor/path identity, size/timestamps and the requested chunk's
SHA-256. It rejects truncation, replacement and changed bytes; no full-ZIP rehash
occurs per chunk. Existing loopback, same-origin/Origin, session-header, no-store
and no-session-in-URL/log rules are preserved. This remains a local-user tool,
not a security boundary against an adversary controlling that same OS account.

Serialized HTTP remains intentional. Each chunk response has one absolute
one-second headers-plus-body write budget. An unread/slow receiver may lose the
response, but cannot extend that transfer's write hold without bound. Existing
non-export request-read timeout behavior is unchanged. Sequential browser chunk
fetches yield between requests. The browser verifies chunk lengths/hashes and
final count/SHA-256 before constructing a downloadable Blob. No automatic POST
retry follows a lost response. Retrying download uses the completed operation;
a stopped/unmounted transfer aborts its current fetch and cannot present a Blob.

UI exposes start/status/cancel, explicit same-request retry after an uncertain
start, recent session exports, read-only inspection, verified download and stop
transfer. Cancellation request and reaped terminal state are distinct. Both
browser leave warnings and native close/cancel inspect export reservations.
Invalid draft preparation, stale callbacks and late cancellation replies are
handled without altering import receipts or silently starting another export.

## Validation and limitations

See [STATUS](../STATUS.md) for exact commands and measurements. Independent cases
cover immutable content/round-trip/privacy, zero/one/eight runs, duplicate/conflict
and capacity behavior, frozen file mutation, source/hash/manifest changes,
pre/post-publication faults, anchor/bootstrap cleanup retry, owner death and
restart, stale UI generations, cancellation notices and transfer aborts, chunk
bounds/identity/checksums, authenticated real HTTP and foreground SQLite writes.

`scripts/prepare_archive_load_fixture.py --mode export` extends the existing
independent generator with 4,096 stable synthetic numeric-series identities and
71 points per run. SHA-derived finite 52-bit values are exactly representable in
JavaScript. These are semantic numeric rows, not string padding or market data.
The generated eight-run source has 101,831,516 expanded bytes, 12,727,478 maximum
entry bytes and 179,338 maximum normalized row bytes. The actual re-exported ZIP
is 65,439,089 bytes (97.5% of 64 MiB). A distinct copied near-expanded fixture
covers 133,129,105 expanded bytes. Neither fixture changes production limits.

Linux direct-HTTP tests do not establish Windows/native behavior or real market
research. Sampled parent + local test client + descendants RSS omits filesystem
cache and the browser. Browser allocation includes a full reconstruction buffer,
a WebCrypto digest input and Blob/browser-managed copies; 64 MiB archive size is
not a 64 MiB browser-memory claim. Parent-led production-browser cancellation, recovery-by-inspection, restart and
near-limit verified download acceptance passed on source `3f287f7`; see STATUS.
Browser RSS/heap/Blob peak is unmeasured: the bounded process-only sampler could
not observe Chrome roots through available namespaces and correctly refused a
zero measurement. This resource-observation limitation does not invalidate the
verified export/download behavior. Slow or stalled disk cannot have a universal success or
cancellation guarantee: unconfirmed cleanup must retain ownership honestly.

Local result finalization and asynchronous verified report/observation chart reads
remain unfinished TT13 obligations. This slice does not close all TT13.
