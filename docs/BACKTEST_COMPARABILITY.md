# Saved backtest comparability: bounded acceptance

Status: planned; implementation and acceptance pending.
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
