# ADR 0008: comparison and nonexecuting project archives

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
