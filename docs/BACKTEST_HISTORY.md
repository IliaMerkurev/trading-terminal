# Compatible custom-backtest history

Custom backtests, Lab selection and the Data-to-custom handoff share one
market, instrument and execution-resolution predicate. Custom history choices
with a mismatch stay visible but disabled, with a reason. No automatic
resampling, profile adjustment or execution is performed.

Schema-1 datasets and profiles with an omitted resolution retain the existing
M1 default. Explicit invalid metadata does not become a default. Data preparation
starts at the same execution resolution; Lab's explicit hourly default remains
hourly. Native Python and backend execution/coverage checks are unchanged.

## Display and selection lifecycle

- Counts mean actual stored bars; hourly or four-hourly bars are not minutes.
- Native timeframe, source and a short dataset ID identify each choice.
- Selected history shows actual trade UTC coverage separately from the requested
  range. Endpoints are exclusive. Absent count, source, coverage or dates remain
  unknown; requested bounds never stand in for actual coverage.
- Changing market, instrument, execution resolution or the available datasets
  revalidates a retained choice. The custom snapshot button and run handler
  reject incompatible selection. Unrelated profile edits retain matching history.
- Completed downloads wait for a current list refresh before automatic selection.
  A newer explicit choice or newer list refresh wins over an older response.
- Attached Lab observations keep their fixed identity. Missing or incompatible
  current history blocks Review/Start and invalidates pending/completed previews.
- Data's estimate is total requested candles before local reuse. It does not
  claim to measure the cache-adjusted missing download count.

Compatibility in the selector is not a guarantee of full run admission. The
backend still validates source integrity, coverage, strategy semantics, native
trust and profile constraints before a worker starts.

## Verification and reproduction

Focused regression covers M1, H1, H4, legacy/invalid metadata, identity mismatches,
truthful labels, profile/list changes, both Data routes, observation invalidation,
delayed downloads and competing list refreshes. Existing coarse-history/data
checks retain backend mismatch refusal. TypeScript and production build pass;
the existing large-chunk advisory remains.

The private version-linked regression archive supplies new tests, two retained
strategy-draft test files and minimal asynchronous timing corrections for two
existing App tests. The published existing tests remain byte-identical. Those
two tests fail on the unchanged prior source because they assert before native
draft replacement resolves; the private corrections wait for the native editor,
then retain all original behavior/consent assertions. The archive records exact
commands, source/runtime hashes, baseline failures and final results.

Actual GUI/screenshot acceptance remains blocked by the previously verified
own-cloud browser loopback refusal. No new browser retry, native Windows,
full-product regression, owner acceptance or exact-commit CI success is claimed.
No providers, accounting, trust, downloads, autosave or deployment behavior was
added by this slice.
