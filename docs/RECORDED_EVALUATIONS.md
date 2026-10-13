# Prospective recorded graph evaluations

Product remains 0.6-dev on the current development branch. This bounded journal
records observations during new ordinary backtests; it is not a condition
debugger or an explanation of why an individual order or fill occurred.

## Supported scope and reading

In Results, use **Read recorded evaluations** below the existing run chart. The
run-level journal is independent of selected trades. Expand an evaluation for
its four graph output levels, connected source references, actual observed node
values, primary/source candle intervals and exact engine event clock. Definitions
come from the immutable run snapshot, never the current editor or current formulas.
False, unknown/null and disconnected outputs are distinct. True is an observed
output level, not necessarily a new signal transition or an order request.

Only newly executed ordinary single-graph worker runs with closed-bar evaluation
are recorded. Existing admitted spot/linear instruments, execution resolutions
and profile versions 1/2 remain supported without changing their trading rules.
Position Management, frozen rules, native Python, intrabar evaluation, benchmarks,
all research windows, experiments and Lab batches are outside this first slice.
The default direct simulation API remains uninstrumented. Old saved runs never
gain evidence by inference or replay. Imported reports retain their opaque saved
payload, but this local-only journal does not display or authenticate it.

The journal records every eligible evaluation, including false or unknown
outputs. A run with no complete primary candle has an explicitly complete empty
journal. Gaps do not manufacture missing primary candles or evaluations.
Stops, liquidation, end-of-run closes, DCA and partial reductions are not relabeled
as graph evaluations. There are no timestamp, order-ID or fill-ID joins.

## Capture and immutable extension

The worker opts in only after inspecting its frozen run snapshot. `ProfileStrategy`
observes the existing `SignalStream` result before `apply_signals`; no second
evaluation or formula calculation occurs. The existing indicator row retains its
original `values` and `signals`, with an optional `evaluation_evidence` version-1
annotation. It carries the original snapshot SHA-256, sequential ordinal, graph
availability time, actual source and primary intervals, exact engine nanoseconds
as a string, and raw output condition states.

Under the existing simulation contract, graph availability is the completed
candle's close in seconds while the engine bar event occurs one nanosecond before
that boundary. Both clocks are shown and preserved. Neither clock is rewritten
to force a causal fill association. Crossing outputs can be inspected as recorded
Booleans, but preceding operands and causal trees are not reconstructed.

An optional result-level completion header records observed/retained/omitted
counts, exact added annotation bytes and complete/truncated/recording-failed
status. The identical header is the final reserved diagnostics row, with a fixed
human-readable message. Local finalization validates the extension before the
existing transactional publication and copies only this header into the local
summary. Existing snapshots, `SERIES`, archive schema and database schema are
unchanged; old result contracts remain valid.

The recorder keeps only the first 10,000 annotations or 4 MiB of added annotation
bytes, whichever is reached first. Byte accounting includes the field name and
JSON punctuation, excluding pre-existing values; the completion header is
separately bounded to 4 KiB. Saturation or capture failure permanently stops
annotations while counting later eligible evaluations. Trading calculations and
orders continue unchanged. These are metadata limits, not a new limit or measured
peak for existing engine, indicator, candle or result memory.

## Bounded read and integrity boundary

The read-only `run_evaluation_page` returns at most 50 rows and 512 KiB. The UI
requests 25 and uses actual returned cursors, including byte-shortened pages.
Before decoding, the reader limits manifests to 256 KiB, summaries to 64 KiB,
individual receipt rows to 64 KiB and selected batch verification to 1 MiB. A
large neighboring row in the same receipt can therefore cause an explicit
inspection-limit result even when the requested row is small.

Within one SQLite read snapshot, reads require local completed finalization,
matching snapshot/result identities, the matching durable started admission and
absence of any import destination identity. The completion diagnostic and selected
rows are checked against existing finalization batch hashes. Counts, retained
prefix, truncation boundary, row ordinals, output links and clocks are validated.
Malformed or missing evidence produces no partially published page. This is
bounded consistency checking, not whole-result-file, hostile-database or provider
authentication. An actor able to rewrite all local data and receipts is outside
this integrity boundary.

Close, switching runs and newer reads fence stale responses. Retrying is a
read-only action. Reading never starts a backtest, downloads data, changes a
strategy, grants native trust or alters an old report. The ordinary chart removes
this reserved annotation only in its transport projection before its existing
payload budget; chart values, source clocks and saved bytes remain unchanged.

## Preservation and acceptance

Project ZIP export/import preserves the header and annotations as JSON content;
the existing raw-candle omission still applies. Importing does not create local
admission or finalization proof. Closed-workspace backup/isolated restore preserves
original local receipts and files. These are separate verification paths. New and modified tests are
retained in a version-linked private regression archive, not in Git; existing
published tests are unchanged.

Focused acceptance checks cover independent observed values and clocks, recording
enabled/disabled financial-result parity, future perturbation, partial/gapped
primary bars, null/false/disconnected outputs, capture failure and saturation,
worker/finalization/reopen, old/imported results, malformed local metadata,
receipt/prefix corruption, archive/restore and frontend request ownership.
Actual executed counts and remaining platform limits are recorded in STATUS.
No CI, full-product, Windows/native, actual GUI or owner acceptance is implied by
component tests or synthetic engine checks.
