# ADR 0059: Current applied-indicator agreement panel

Date: 2026-10-12
Status: Implemented bounded current-panel reconstruction; actual-app acceptance separate

## Decision and scope

Place a compact current agreement panel immediately below the Market chart.
Only applied visible members vote. An expandable native HTML disclosure shows
all applied members, including hidden, context-only, unsupported and unavailable
members, their parameters, direction convention, observed values and reasons.
The disclosure is initially closed on mount and is not keyed to polling, chart
focus, style or data changes. The concise heuristic warning remains outside it.
There is no indicator-count quota; member details have a scrollable viewport.

The panel imports the accepted ADR 0057 evaluator and shared manifest. It does
not calculate indicators, request data, fetch older history, create alerts,
monitor sources, convert strategies, or change PAPER/orders. Dependencies and
product version remain unchanged. This is a new functional reconstruction, not
recovery of historical source, databases, or acceptance evidence.

## Caller boundary

`useChartIndicators` provides an in-memory response receipt only after its
existing request/raw-snapshot, namespace, window and calculation-epoch fences.
The receipt identifies the exact response object, output revision, origin,
request context and applied settings revision. It becomes unavailable on
supersession, reanchor or a pending/uncertain settings write. No new API is added.

`currentAgreement` rejects stale or mismatched receipts and responses visibly.
It validates source, market, symbol, native interval, applied member signature
and revision, response identity, origin contract/time/generation, both existing
projection and event contexts, requested inclusive raw-open bounds and close
horizon. The projection's raw-time domain must exactly match current raw rows.
Raw and output timestamps must be valid aligned UTC seconds in strict order;
output arrays must share their declared clock and length. Raw conflict states
suppress the panel. Missing exact-close output stays unavailable, never older.

The response's settings record owns the calculation origin. First establishment
and explicit reanchor may change origins without changing the applied member
revision, so comparing permanently against the initial settings-read origin
would incorrectly suppress valid results. The accepted response origin must
instead agree with its settings and both output envelopes.

This envelope also relies on the existing immutable confirmed-cache contract:
`ChartHistory.fetch` and `capture_hub` preserve existing candles, mark conflicting
corrections, and never overwrite confirmed OHLCV. `annotate` checks the saved
content hash; `DisplayIndicators.read` rejects conflicts before replay/cache
publication, and its revision key includes annotated raw inputs. Existing tests
`test_metadata_no_age_promotion_conflict_and_idempotence` and
`test_rest_correction_persists_conflict_without_overwriting_price` cover these
paths. This change does not introduce a new raw-hash protocol or alter cache
writes. Arbitrary external database rewriting is not an accepted input contract.

Before preparing any evaluator, the panel suppresses inactive, stale/paused,
loading, saving, settings-unloaded, error and detached-historical states.
Detached history uses the chart's historical-buffer flag, not its following
flag: ordinary panning inside the recent buffer leaves the reference unchanged.
Return to latest guidance refers to the existing chart action. The panel never
performs a hidden latest read. Existing chart polling remains unchanged.

The target is the newest confirmed raw close in the accepted recent buffer.
Forming values, Heikin Ashi prices and hover coordinates never become inputs.
The prepared evaluator indexes the snapshot once; component memoization avoids
preparation on hover/disclosure/focus-only renders. No formula work is added.

## Presentation semantics

Up, down and neutral distributions, exact UTC confirmation time, available
groups, fully covered supported visible types, available/total parameter
variants, and opposing group majorities come directly from evaluator evidence.
Overall is suppressed unless the manifest's two-group and 50%-fully-covered-type
gates pass. Available group breakdowns remain visible. Neutral is known and is
never a substitute for missing information. Exact duplicates share one variant;
parameters do not increase their type's weight. Correlated indicators are not
independent evidence. Percentages describe a heuristic, not probabilities,
confidence, price strength or trading recommendations.

## Verification boundary

Focused adapter tests use independently expected values and adversarial envelope
mutations; component tests cover visible warnings, exact UTC, coverage, reasons,
state suppression and disclosure retention/remount. Market navigation tests
exercise applied-versus-draft settings, panning, hover, focus, Heikin Ashi, stale
state, detached history/Return and unchanged read routes. Nearest settings and
transport tests are reused/run separately from the already accepted evaluator
corpus. Exact commands and executed outcomes are recorded in STATUS.

DOM tests are not actual-browser, Windows/native, live-provider or owner-led
acceptance. Agreement alert conditions and historical agreement integration are
not delivered by this panel. Publication, merge, packaging and release remain
separate operations.

## Nonterminal older-page navigation

A pending older-page request is a loading state until ready/end/error even if
its latest server reply says `loading=false` (for example, a full acquisition
queue with an `idle` page). It must not expose current scores from the retained
recent buffer while the recent subscription is waiting on that older cursor.
Return cancels that pending navigation through the existing epoch fence.
Ordinary panning that starts no older request continues to update the current
reference and preserves the user's viewport.
