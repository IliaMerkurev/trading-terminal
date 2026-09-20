# ADR 0024: Frozen later-period Library verification

Status: implemented, subject to final owner acceptance.

A completed selection row can be frozen with a declared non-overlapping later
range and matching source/market/symbol data. Its reviewed source/document,
parameters, timeframe, capital and profile remain unchanged. Freeze stores the
entire new contract before an explicit start. The same sequential Library batch
scheduler, managed workers, window warmup and passive benchmark contracts execute
one strategy and its two later-period capital alternatives. No second simulator,
new schema or automatic optimization is introduced.

The existing Experiments separation of selection, freeze and validation is
retained. Library uses its existing batch snapshot rather than the graph-only
Experiments validation table so reviewed native window adapters retain consent
and supported semantics. Data gaps, changed templates/runtime and unsupported
native combinations fail visibly. Cancellation and pending-only resume retain
the existing scheduler behavior; an attempted row never resumes mid-run.

Verification batches are explicitly labeled, excluded from selection sorting
and card results, and retain a link/hash and separate metrics for their selection
row. Distinct attempted selection documents across local research are counted;
overlapping prior frozen verification ranges increment the holdout attempt even
when a different candidate or dataset is selected. Counts are local evidence,
not proof that history was unseen externally. Pinned upstream commit dates are
recorded; both historical periods may precede a source version. No statistical
or prospective-performance claim follows from these checks.

Focused evidence: 8 Python validation/archive checks passed in 9.744s after one
SQL-string syntax correction; 6 frontend Library checks passed in 2.98s. The
fixture freezes before starting, matches a standalone run including fees/fills/
positions, rejects overlap and repeat start, retains fresh baseline run IDs,
and proves perturbed later history cannot change the frozen selection.
