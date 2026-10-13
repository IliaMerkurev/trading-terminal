# Saved backtest comparability: bounded acceptance

Status: implemented. Focused automated checks, actual production-browser
synthetic review and private regression-archive readback passed.
Product remains 0.6-dev on `codex/terminal-mvp`. This slice improves the existing
Results saved-run comparison, preserving its metrics and export selection.
Existing Lab batch comparisons, names/notes and equity overlays remain available.

## Authorized outcome

The owner approved beginning comparison improvements with a review of recorded
period, data, capital and costs on 2026-10-12. This checkpoint scopes one complete
read-only slice. Saving arbitrary new comparisons and broader graph/ranking work
remain later milestones. No merge, release or product-version change is included.

Show explicit **matched**, **different** or **unknown** for saved conditions:
source/market/instrument, actual dataset content fingerprint and coverage,
requested range versus recorded actual evaluation period/warmup, capital/currency,
fees/slippage/funding, execution profile/model/version and runtime/metric contracts.
Show each run's recorded value and what the evidence establishes. Equal missing
fields are unknown, never a match. Equal settings with different content hashes
must be visible. Distinguish saved contract metadata from independently verified
provider data; imported reports and absent historical fields retain caveats.

## Preservation and implementation boundary

Read immutable saved manifests/results only. Do not rerun strategies, fetch data,
reprice old reports with current settings, change accounting, normalize strategy
quality or imply profitability/equivalence. Show financial outcomes separately
from cost assumptions. Warnings inform rather than silently disabling an existing
comparison. Retain old archives and their original bytes; no migration required.
Keep responses bounded and avoid loading full trades/candles solely for review.

Use the existing comparison route/component. Fence obsolete reads after selection,
report navigation, Cancel, retry and unmount. Preserve selected runs and existing
metrics. Missing optional metadata must degrade visibly and safely.

## Acceptance plan

- Independent synthetic expectations for matched/different/unknown and malformed
  or absent legacy evidence; changed candle hashes despite equal parameters.
- Requested versus actual range/warmup; capital/currency; gross/net cost and
  funding signs; profile/version/venue/market distinctions.
- No mutation/re-execution and bounded payload checks; existing archive regression.
- Frontend selection, late success/failure, Cancel/retry, report switch and reload;
  focused existing regressions, TypeScript and production build.
- Actual own-cloud production-browser synthetic review and one screenshot;
  no providers, credentials, Arm, PAPER/orders, native untrusted Python or external
  notifications. Browser checks are separate from mocks and Windows acceptance.
- New tests stay outside Git in a private version-bound Drive archive: complete
  files, additive patch, final source hashes, exact commands/results and safe
  reapplication instructions. Verify download bytes/CRC, privacy and source match.
  Existing Git tests stay unchanged; checkout/CI will not imply external coverage.
- Every coherent milestone is committed, pushed and independently checked against
  the exact remote tree. Any publication failure pauses implementation and checks
  until the save path is repaired. Final documentation records actual limits.

## Implemented checkpoint

The existing Results comparison now separates Data, Period, Capital and Costs &
execution evidence, with per-condition matched/different/unknown and per-run
values/reasons. The raw metadata diff remains collapsed and bounded. There is no
overall equivalence verdict. Legacy omitted currency, venue, execution resolution
and actual readiness remain unknown rather than adopting current defaults.
Recorded graph evaluation endpoints come from two indexed archived indicator
reads; they establish neither indicator readiness nor uninterrupted evaluation.
Native/passive samples are not relabeled as graph decisions. Dataset content
fingerprints cover complete normalized trade/mark/funding inputs, possibly beyond
the evaluation window. Imported provenance and absent raw history remain explicit.

Independent semantic review caught decimal normalization rounding/resource risks
and insufficient legacy coverage validation; the corrected comparison uses exact
bounded decimal representation and rejects inconsistent ranges, gaps, domains and
unsupported evidence. Large values expose a labeled metadata fingerprint; the raw
diff is capped at 100 rows with an omitted count and a 512-KiB response guard.
Reads do not mutate artifacts, replay strategies or consult current market cache.

Focused evidence: 23 new backend tests plus two existing archive/comparison
regressions passed; 11 new frontend tests plus 19 existing neighboring tests passed.
TypeScript (including the external frontend file) and production build passed,
with the existing bundle-size advisory. New tests remain untracked and external
to this checkpoint; the private archive below is required to reproduce them. Browser evidence is
separate below. Windows/native, providers, full-product regression and remote CI
are not established by these focused checks. Product remains 0.6-dev.

## Final acceptance — 2026-10-12

Own-cloud Chromium reviewed the real production App/Service on four isolated,
explicitly synthetic saved runs. Two identical inputs showed 21 matched and seven
unknown conditions; different normalized candles/commission assumptions plus a
legacy-shaped candle-free record showed three different, 12 unknown and 13 matched.
The missing legacy fingerprint did not hide a conflict between the other runs.
Original net PnL/fees stayed 97.9/2.10 and 145.7/4.30 USDT for the two synthetic
variants, with no recalculation during comparison. These are fixtures, not market
results or profitability evidence. The legacy-shaped record is deliberately
constructed compatibility evidence, not an authentic old-owner database/archive.

Actual Cancel/retry, disabled repeat submission, selection change and report
switch while a read was delayed rejected obsolete responses. Reload retained all
saved runs; transient checkbox selection reset and could be selected again.
This slice does not persist arbitrary comparison selections. Normal 1180-pixel
and 150%-zoom 787-pixel viewports kept comparison/disclosure controls reachable
without body overflow; normal zoom was restored. A production screenshot was
captured. Ten original snapshot/result/dataset JSON artifacts remained unchanged.
Eight comparison reads invoked no execution, provider, PAPER/order or notification
routes. The owned service was explicitly stopped and owned tabs were closed.

The UI intentionally separates recorded graph evaluation endpoints from a verified
readiness boundary. It cannot establish actual whole-strategy warmup completion,
continuous evaluation, provider authenticity, or absent old currency/venue fields.
No new runtime evidence is invented or backfilled. Matching full-dataset content
may include warmup/unused suffix; a differing hash does not locate the difference
inside the evaluated period. Existing Lab batch overlays/names/notes are unchanged.

## Private regression archive and reproduction

Archive: `TradingTerminal_comparability_tests_2026-10-12_5414820.zip`.
Size: 22,471 bytes. SHA-256:
`1f93e87893e87feeeb5422378557b4ea4cf424da699620a46e954900a1db720d`.
It is stored owner-only, unshared, in the owner's existing private research folder.
Downloaded bytes matched exactly, ZIP CRC passed, and all 205 runtime fingerprints
plus both complete test-file hashes matched source commit
`5414820db1aabd262ef7946d039534c6f0d47874` (tree
`878afc953969eb9ea8834196c85415a444b4ccca`). The final documentation checkpoint
must preserve this exact runtime map.

The five archive entries are `tests/test_backtest_comparability.py`,
`frontend/src/BacktestComparability.test.tsx`, an additive `test-changes.patch`,
`manifest.json` and `README.md`. They contain no databases, raw market datasets,
credentials, user data or browser state. Existing Git tests remain unchanged.
Checkout/CI does not automatically include these 23 backend and 11 frontend tests.

In an isolated checkout at the source commit, verify manifest source/test hashes,
back up local edits, run `git apply --check test-changes.patch`, then `git apply`
only if the check succeeds. The patch check passed against an isolated source
checkout. Do not force a mismatch. Verify installed test hashes before running:

```sh
PYTHONPATH=.:tests .venv/bin/python -m unittest -v tests.test_backtest_comparability tests.test_archives.ArchiveTests.test_comparison_exposes_changed_costs_strategy_data_and_runtime_contracts tests.test_archives.ArchiveTests.test_roundtrip_preserves_metrics_but_never_bundles_history_or_overwrites_runs
node node_modules/vitest/vitest.mjs run frontend/src/BacktestComparability.test.tsx frontend/src/ComparisonPanel.test.tsx frontend/src/SavedReview.test.tsx frontend/src/App.test.tsx
node node_modules/typescript/bin/tsc --noEmit
node scripts/frontend.mjs build
```

The measured backend file ran externally as `test_backtest_comparability` via
PYTHONPATH; the installed command above is equivalent. Exact commands/durations
and environment are retained in the archive. CPython 3.12.14 and Node 24.19.0 were
used with hash-pinned Linux binaries and frozen frontend dependencies; actual pnpm
was 11.25.0. No lockfile/dependency changes were introduced. Remote implementation
commit had no reported statuses or workflow runs; local passes do not imply CI.
