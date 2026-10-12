# ADR 0057: Pure versioned indicator agreement

Date: 2026-10-12
Status: Implemented pure evaluator checkpoint; presentation and alert/history integration pending

## Context and scope

The current chart summary and a future frozen agreement condition need identical
interpretation of existing display indicator outputs. This milestone reconstructs
that interpretation from preserved functional requirements. It does not recover
historical source, test results, persisted state, or prior acceptance.

This is an independently usable pure core. It adds no indicator formulas, UI,
provider calls, backfill, automatic monitoring, condition schema changes, alerts,
notifications, history storage, strategy conversion, PAPER behavior or orders.
Product and dependency versions remain unchanged.

## Shared declarative source

`terminal/indicator_agreement_v1.json` is the single manifest. It declares
`indicator-agreement-v1`, `equal-group-type-variant-v1`, classifications, groups,
parameter fields, output ports, rules, thresholds, flat guards, duplicate policy,
coverage, weighting, rounding and threshold semantics. Python reads it with
standard-library `importlib.resources` from the existing `terminal` package.
TypeScript imports that same file through the existing Vite/TypeScript JSON
resolver. There is no copied frontend manifest and no new dependency. The current
source-checkout backend therefore includes the resource; a frontend consumer
imports the pure module normally. Since this slice has no production consumer,
Vite can tree-shake the unused evaluator rather than attaching it to the UI.

The manifest hash is SHA-256 over sorted-key, compact, ASCII JSON. Python computes
it at import; TypeScript pins the hash, independently rehashed in tests. Any
manifest change must update the version when semantics change and the pinned
hash. Results carry both versions and the hash. Tests use independently authored
expected fractions, not one language's results as semantic truth. A separate
full-result parity test compares the two implementations.

## Input and caller boundary

Python exposes `prepare_agreement(snapshot).evaluate(close_time)` and
`evaluate_agreement(input)`. TypeScript exposes `prepareAgreement(snapshot)` and
`evaluateAgreement(input)` with the same JSON fields:

- `instances`: applied `{id, type, params, visible}` members; appearance, pane and
  placement fields have no scoring effect
- `candles`: existing raw source candles with OPEN `time`, `open`, `high`, `low`,
  `close`, and existing `confirmation`; optional explicit `conflict`
- `display`: existing display `{times, columns}`; times are confirmation CLOSE
  timestamps and columns are keyed by member ID then existing formula port
- `interval_seconds`: positive safe-integer native interval
- `close_time`: one explicitly requested aligned confirmation close

Raw and display timestamp sequences must be aligned, unique and increasing.
Invalid structure/parameters are rejected. Missing target/output data is
unavailable, never replaced with an older value. Eligible raw data must be
confirmed (`closed_rest`, `provider_confirmed`, or `synthetic_closed`), have finite
OHLC and valid high/low containment of open and close, and have no explicit
conflict. Invalid, forming or missing rows cannot support flat guards or OBV
predecessors. Forming and future values cannot affect an earlier result.

The caller must first establish exact source, market, instrument, interval,
applied revision, calculation origin, formula contracts, requested window,
generation and snapshot freshness. The pure core cannot authenticate these
identities from bare arrays. Current-summary freshness, pause/loading/error and
historical-buffer suppression are deliberately not implemented here. A frozen
consumer must supply its own frozen member list and verified outputs, rather
than treating current graph membership as frozen membership. This contract is
not proof that either integration exists.

Preparation detaches the snapshot and builds raw/output timestamp indexes once.
It also records contiguous valid-close/range and equal-close/zero-range run
lengths. Flat guards and each member lookup are then constant-time per requested
close; historical callers reuse one prepared object. Evaluation does not scan or
replay an ever-growing raw prefix and never calculates a formula. Input indexes
and prepared members are reused; returned evidence is detached from them.

## Direction rules

The three voting outcomes are up, down and neutral. Unavailable, context,
unsupported and hidden are separate non-voting statuses.

- Trend SMA/EMA/WMA/RMA/VWMA/HMA/VWAP/SAR compare raw close with `value`;
  BB/Donchian/Keltner compare raw close with `middle`. Equality is neutral.
- Supertrend consumes existing `direction`: only +1 and -1 are available.
- DMI is neutral for ADX below 20; ADX at least 20 requires finite `plus_di`
  and `minus_di` and compares them. Equality is neutral.
- RSI and Stochastic K use the inclusive neutral band 45–55. MACD uses the
  histogram sign; ROC and Momentum use their existing value's sign. CCI uses
  -100–100, Williams %R -55–-45 and BB %B 0.45–0.55 inclusive neutral bands.
- MFI uses 45–55, CMF -0.05–0.05. OBV compares its current value to its exact
  immediately preceding confirmed raw close's output; both raw rows and outputs
  must exist. Zero change is neutral.
- RSI additionally requires `period + 1` consecutive raw closes; an all-equal
  window is neutral. Williams requires `period` raw high/low bars; Stochastic
  requires `period + smooth - 1`, covering all K smoothing inputs. A zero range
  across that whole window is neutral. A gap, invalid row or insufficient raw
  guard history is unavailable. Missing/nonfinite formula output remains
  unavailable, including undefined MFI, and is never manufactured by a guard.
- ATR, Volume, standard deviation and BB width are context only. Ichimoku,
  Stochastic RSI and all three VuManChu types have no directional rule in v1.
  Unknown future types are explicitly unsupported.

These are descriptive interface conventions, not statistically calibrated
probabilities, confidence, price strength, reversal predictions or trade advice.

## Duplicate identity, hierarchy and coverage

Identity is the exact type plus sorted normalized scalar parameters. Numeric
integers/floats and negative zero normalize consistently. IEEE-754 bit tokens
avoid language-dependent exponent formatting in variant keys. Key and member
sorting uses Unicode code points in both languages. IDs and appearance do not
create extra weight. Hidden copies are excluded first.

Visible exact copies count as one variant and retain their member IDs in the
evidence. A contradictory or missing duplicate assessment cannot silently win by
ID ordering: the variant is unavailable unless all copies have identical status,
reason and consumed values. Its `duplicate_variant_conflict` reason is explicit.

Available variants have equal weight within their type; available types have
equal weight within their group; available groups have equal weight overall.
Neutral remains in every denominator. A partially available type can contribute
its available variants to group evidence, but is fully covered only when every
distinct visible supported variant is available.

Overall output requires at least two available groups and at least half of all
supported visible unique types fully covered. Both boundaries are inclusive.
Without sufficient coverage, overall is null and reasons explain why; available
group/type breakdowns remain visible to a future consumer. Context/unsupported/
hidden members never inflate the coverage denominator.

Results include member assessments, distinct variants, type/group membership,
coverage counts, exclusions and exact target open/close timestamps. Each
available distribution includes reduced rational string pairs, ordinary finite
numeric fractions, and largest-remainder integer percentages totaling 100.
Remainder ties use up, down, neutral order. Strings preserve arbitrary-size
integer evidence in JSON; no BigInt is serialized.

`group_conflict` means an available group has strictly more than half up and
another available group has strictly more than half down. Equality or a neutral
majority is not an opposing directional majority.

## Reusable threshold evidence

`threshold_evidence` / `thresholdEvidence` is a pure helper over a result with
the matching versions/hash. It creates no condition or event. A finite numeric
threshold in 0–1 is interpreted by its shortest decimal representation. Overall
uses exact rational `>=` comparison, so exact 7/10 meets numeric 0.7. Displayed
rounding is never used. Each requested group must have an exact directional
fraction strictly greater than 1/2. An empty group selection adds no constraint.
Missing overall or a required group produces unknown (`truth: null`), not false.
State transitions, Arm baselines and mixed impulse/state semantics remain future
integration work.

## Alternatives and verification limits

A second formula engine was rejected: the display output is authoritative.
Flattening all instances or dropping neutral votes was rejected because it
changes the declared hierarchy. Floating-point-only threshold checks were
rejected because a displayed integer or accumulated roundoff must not decide a
boundary. Prefix replay per historical close was rejected because it introduces
quadratic work.

Focused tests cover all directional ports and threshold boundaries, weight
hierarchy, deduplication, partial coverage, guards/gaps, invalid/conflicting raw
inputs, exact threshold/group boundaries, snapshot detachment, causal future
perturbations, manifest hashing and cross-language parity. Production typecheck
and build validate the import path. These checks establish only pure-core
behavior, not UI usability, runtime/history integration, Windows/native,
live-provider, remote CI or owner acceptance.
