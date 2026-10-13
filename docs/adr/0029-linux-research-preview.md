# ADR 0029: Native Linux research preview while preserving Windows

Date: 2026-10-10. Status: recovered implementation; fresh validation recorded in STATUS.md.

## Decision and scope

Add a Linux x86_64 source-checkout Tauri launch path on a separate adaptation
branch. Retain Windows launch/setup, Windows wheel hashes, WinRT notifications
and Job Objects. Keep the existing Tauri IPC boundary and production CSP; do not
introduce a browser transport, alternative engine, product-version bump,
installer or trading integration.

Use separate official PyPI wheel hashes for CPython 3.12/glibc >= 2.35. Shared
packages retain their Windows versions, notably NautilusTrader 1.231.0.
NautilusTrader's Linux environment marker adds uvloop 0.22.1 (MIT); the Linux
lock includes this dependency explicitly. The installer requires binary wheels
and hashes and preserves mismatched existing environments rather than changing
them silently. Existing engine/data-library licenses remain unchanged; runtime
binaries are local dependencies, not distributed project artifacts.

## Platform boundaries

- Rust scopes Windows APIs/dependencies to Windows and selects the platform's
  virtual-environment executable. Linux exports use xdg-open with one absolute
  path argument, without a shell. The PNG icon is a lossless representation of
  the existing project icon, required by Linux Tauri code generation.
- Linux immutable artifact publication uses atomic no-replace semantics, never
  a pre-check followed by replacement-prone POSIX rename.
- Directory ownership and worker cleanup have explicit platform adapters.
  Windows retains its original Job Object boundary. Linux graph/replay workers
  require a lifetime supervisor; process groups are not a security sandbox and
  cannot contain arbitrary processes that escape their session. The supervisor
  handles service/host death only while it remains alive; killing the supervisor
  itself is not equivalent to Windows kernel-enforced kill-on-close. Group
  signaling is not a guarantee for arbitrary escaped descendants.
- Imported/native Python execution stays unavailable on Linux. A user consent
  hash cannot grant a lifecycle guarantee the platform adapter does not have.
  Static previews, editing, saved reports and Windows native execution remain
  supported under their existing contracts.
- Unavailable protected credentials/Windows notification integrations fail
  visibly. No secret-store substitution, key import or credential migration is
  introduced. Platform capabilities are additive to the bounded command API.

## Rejected alternatives

A browser preview does not satisfy a native desktop goal. A web bridge would
create another exposed transport and is unnecessary for this bounded native
adaptation. Copying Windows wheel hashes is not a Linux dependency lock.
Swapping Job Objects for process groups on every platform would weaken Windows
behavior. Pretending process groups contain untrusted native descendants would
overstate Linux guarantees.

## Evidence and limitations

Verification covers actual dependency imports, platform selection, no-overwrite
races, exclusive ownership, cancellation, parent-crash cleanup, bridge protocol
errors, unavailable capabilities and independent offline financial fixtures.
Record actual outcomes in STATUS.md rather than treating requirements as passed.
Windows execution cannot be verified by Linux tests.

The initial native build compiled, but the actual desktop launch failed because
Debian WebKit could not find its absolute system WebKitNetworkProcess helper.
That was not a working native window. The original local checkout and toolchain
were lost when the validation VM was replaced; this recovery must be validated
again and is not the original commit. Historical results do not prove the
recovered bytes. No sandbox-disabling flags or system-security changes are used.
