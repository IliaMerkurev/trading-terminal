# Closed-workspace backup and isolated restore

Project ZIP export is a **selected strategy/report exchange format**. It omits
raw datasets, logs, local consent and workspace-level alert/research records.
It is not a complete workspace backup. The migration verifier also copies only
SQLite and `runs`; its success is not full-workspace recovery acceptance.

Use `scripts/workspace_backup.py` for an offline, complete **selected data-root**
copy. It creates a directory bundle, not a project ZIP. It never opens the
application, migrates a database, starts a calculation, arms alerts or executes
native source. Use only your own trusted local bundles: hashes detect accidental
changes; they do not authenticate a backup or make imported Python safe.

## What is preserved

Every regular file and directory beneath the explicitly selected root is
inventoried, including unknown auxiliary files and empty directories. This covers:

- `terminal.sqlite3`, and existing WAL/SHM/rollback-journal sidecars
- Saved strategies/results, series, experiments/comparisons, observations,
  operation receipts, chart settings/cache, presets/trash, alert definitions,
  journal and historical research in SQLite
- `runs` (snapshots, results and logs), `datasets` (manifests and raw files),
  import/recovery staging, exports/partial exports, replays, chart-read artifacts
  and the dated Fear & Greed cache when present
- Desktop `webview` files when they are inside the selected data root
- Existing hash-bound native consent in SQLite, without executing any source

Only the root's transient `instance.lock` is excluded and recreated on restore.
A nested file of that name is preserved. File contents and directory structure
are preserved; ownership, ACLs, timestamps, alternate streams and other platform
metadata are not a backup promise. Links, Windows reparse points, special files,
nonportable names and case-colliding paths are rejected rather than skipped.

Outside this boundary: unsaved editor/session memory; external browser profiles
and origin-local pending-operation records; Windows Credential Manager secrets;
source checkout, pinned runtimes/toolchains; files outside the selected root.
Desktop WebView bytes may include origin-local records, but restoring files does
not establish WebView/profile portability. Browser-host localStorage belongs to
its browser profile and origin (including port), not this data root. An uncertain
operation must still be reconciled using durable application receipts; never
resubmit an Arm/run/import merely because browser state is missing.

Telegram credentials are protected outside the root and keyed to its absolute
path. They do not follow a restored root. Do not put secrets in commands, backup
manifests, logs or project archives. A workspace backup itself contains private
research and possibly native source/consent: keep it in a private local location.
No upload, encryption or off-device redundancy is provided by this tool.

## Procedure

1. Save intended editor changes. Identify the exact root: the default is
   `.local-data` in the checkout; a launcher `--data-root` or
   `TRADING_TERMINAL_DATA_ROOT` can select another absolute directory.
2. Close the whole desktop/browser application, host and workers. Close WebView
   processes and any other program writing this root. Do not kill an active
   writer merely to bypass the guard or delete `instance.lock`.
3. Choose a new bundle directory outside the source tree. Its parent must already
   exist. Provide enough free space for a full copy plus a temporary database-only
   verification copy. Run from the verified source checkout with its Python:

```powershell
.\.venv\Scripts\python.exe scripts\workspace_backup.py backup C:\Research\terminal-data D:\Backups\terminal-2026-10-13 --closed
.\.venv\Scripts\python.exe scripts\workspace_backup.py verify D:\Backups\terminal-2026-10-13
.\.venv\Scripts\python.exe scripts\workspace_backup.py restore D:\Backups\terminal-2026-10-13 C:\Research\terminal-restored-check
```

On Linux replace the Python executable with `.venv/bin/python` and use absolute
Linux paths. Paths containing spaces need shell quoting. Commands print JSON on
success, including manifest SHA-256, counts and completed-result verification.
Check the exit status, not just the existence of a directory. The manifest is
written only after backup verification; preserve it with its `workspace` folder.
An additional copy on another private device is still needed for device failure.

4. Restore only to a **new, isolated** root. Existing destinations and overlapping
   source/backup/destination trees are refused. Nothing is merged or overwritten.
   The restore command first verifies the entire inventory, SQLite integrity and
   foreign keys, and every completed `runs/<id>/result.json` checksum. It then
   verifies the copied bytes and database again. It does not launch anything.
5. Preserve the original root and untouched backup. If explicitly checking the
   application, launch the verified matching build with `--data-root` pointing to
   the isolated restored root. This separate step can apply additive migrations
   and mark interrupted work; it is not part of byte-for-byte restore validation.
   Review saved identities/results, observations, receipts, alerts and presets.
   Alert Arm, new jobs, live sessions and native execution remain explicit actions.
   Do not point the application at the backup's `workspace` directory.

## Safety and failure behavior

The existing OS ownership lock is held throughout inventory/copy/final source
recheck. The source database is never connected to SQLite. WAL and other database
files are copied byte-for-byte; SQLite validation is performed on a disposable
DB-only copy, so recovery/checkpointing cannot change the source or bundle.
Completed results are checked against their stored hashes without recalculation.
This verifies preserved storage, not financial accuracy, raw-data provenance,
reproducibility under another runtime, or compatibility with an older owner DB.

`--closed` is an operator assertion in addition to the lock. The lock fences
cooperating application owners, not external editors or another process replacing
parent directories. Full source hashes are rechecked after copying. Unreadable
entries, detected changes, corruption, unsupported paths and copy failures stop
with nonzero status. This is a local trusted-directory workflow, not an adversarial
filesystem sandbox; do not manipulate or synchronize inputs during the operation.

Partial destinations are retained for inspection and never automatically reused
or deleted. Do not launch them. Fix the cause, preserve the source, and retry with
a different new destination. A failed command is not a verified backup. A bundle
subsequently opened as an application root is refused by verification. Maximum
inventory is 100,000 entries and manifest size 32 MiB; files are streamed in 1 MiB
chunks. A very large database still needs matching temporary disk space.

## Evidence and limits

This offline tool has no UI change. Focused synthetic checks cover a complete
backup → verification → fresh restore, raw file identity, crash-left WAL content,
completed-result hashes, representative research/alert/history/preset/receipt
state, passive application reopening, lock contention, invalid/tampered inputs,
copy failures and source-change detection. Added checks are preserved separately
from Git as a version-linked regression archive. See [current status](STATUS.md)
for executed evidence. Linux testing does not establish Windows lock/reparse/
WebView acceptance, authentic old-owner DB compatibility or full-product acceptance.
