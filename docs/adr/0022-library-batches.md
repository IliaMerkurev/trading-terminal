# ADR 0022: Frozen library batches reuse managed experiments

Status: partial implementation, 2026-09-20.

Library batches inherit the existing experiment reservation, sequential dispatch,
cancellation and shutdown methods. There is one global calculation slot shared
with ordinary backtests, parameter experiments and Replay. No additional worker
framework or simulator is introduced.

A bounded preview freezes up to twelve explicit strategy/timeframe selections,
source/document hashes, parameters, common account/cost inputs, evaluation range,
dataset content and runtime. Start requires the exact preview contract. Existing
asynchronous downloads prepare shared fine-grained history; batch dataset hash
and warmup checks run on the scheduler thread. The existing two-million modeled
minute limit includes warmup and the two passive alternatives.

Two additive tables preserve batch and row states. Shutdown cancels the active
worker; completed immutable reports remain ordinary Results. Explicit resume
only dispatches pending rows after source/runtime/data checks. Cancelled,
interrupted and failed rows are never presented as recovered mid-run trades or
automatically retried. A new application instance does not resume a batch.

Benchmarks use independent spot accounts, exclude strategy protection policies,
and reuse only completed local results matching their entire contract. Missing
real spot counterpart history produces an explicit unavailable row. Reports
retain benchmark/source contracts; archive validation checks library document
hashes without consulting or executing the current catalog.

The first backend checkpoint supports the RSI graph at multiple timeframes.
Native separate-window warmup is explicitly incompatible pending a reviewed
adapter; batch dispatch never grants consent. This is not yet a two-distinct-
strategy vertical slice or the five-strategy acceptance checkpoint. The existing
preview UI has no batch controls until the next bounded integration slice.

Focused verification: 13 tests passed in 15.689s, covering standalone/batch
metrics and trades at two timeframes, exact baseline reuse, cancellation,
restart/pending-only resume, reservation ownership, changed-runtime rejection,
asynchronous corrupt-history rejection, native browse/copy trust and archives.
The two timeframe rows test scheduler behavior, not two distinct strategies.

Additive migration verification on a consistent accepted database copy preserved all 20 existing tables and 1,428,407 rows exactly; SQLite integrity_check passed. The ordinary owner database was not opened for development migration.

