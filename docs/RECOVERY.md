# Post-preset milestone reconstruction

## Scope and evidence

Recovery starts from the verified `codex/terminal-mvp` commit
`5674a6031a4c6bee8e51f4e70adac3546d2d30d2`, whose source tree is
`ae1b27c494dede389a4505976dfab3111350a4ab`. Named indicator presets
and all earlier committed capabilities remain the baseline.

Later local source commits are unavailable. This work reconstructs documented
behavior; it does not claim byte-identical recovery of those commits or transfer
their historical test results to new code. Previously saved application data
and historical archives require separate compatibility evidence wherever they
are available. Their existence or recovery is not implied by source recovery.

## Ordered checkpoints

1. Persistent compatible chart pane layout, atomic indicator/layout drafts and
   preset round trips.
2. Frozen local indicator rules, explicit arming, runtime safety, durable event
   journal and local user interface.
3. Immutable historical rule research and event-to-chart navigation.
4. Explainable current indicator agreement with documented grouping, directional
   classifications, coverage and unavailable states.
5. Frozen agreement alert conditions and full historical group timelines.

Each checkpoint needs fresh focused tests, review of affected regressions,
privacy/license and pinned secret-scanner review, and verified remote publication
before dependent expansion. A local commit alone is not a delivered checkpoint.
Compare the reconstructed behavior with the documented acceptance contracts and
record remaining gaps explicitly before declaring recovery complete.

## Boundaries

Product version stays `0.6-dev`. No new dependency, provider, strategy conversion,
order, PAPER action, live-source acceptance, merge, release or deployment is part
of this recovery. Existing unrelated functionality is preserved. Windows/native,
live external sources and independent owner acceptance remain separate checks.
Synthetic browser evidence must be identified as such. A missing remote CI
configuration is not a successful CI result.

## Current status

The pane checkpoint has passed fresh focused, independent and actual-browser
synthetic verification as recorded below. Publication is verified separately.
The isolated frozen-alert core is restored as a partial second-stage checkpoint;
its runtime and user interface remain pending. Historical research and agreement
features are not yet restored. This is not full product or owner acceptance.


## Pane reconstruction: independent acceptance checkpoint

Reviewed source: `6ac491976aa304582a36a8abf2cd09d911af172e`.
Tree: `98bce87b01bb5625488f17f4a8d6e785b4a41b7c`.

The independent pass found and verified correction of one compatibility blocker:
`chart_indicator_save` had accidentally required `pane_layout` for legacy
requests. The corrected Service accepts a legacy save before custom layout is
present, rejects an old client that would discard an existing custom layout,
and accepts an explicit null layout reset.

Nine independently authored Python tests and three TypeScript challenge tests
passed on this exact frozen source. The TypeScript scenarios exercise physical
series-creation requests through a strict chart double; they are not a substitute
for the actual browser chart. A preliminary harness configuration failed to
resolve its external Vitest import; correcting the harness import produced the
reported three-test pass without a product-source change.

| Criterion | Independent result and remaining boundary |
|---|---|
| PANE-01 | Exact versioned membership, strict weight validation, revision conflicts and atomic rejected writes checked; current-format round trips checked. Authentic missing-version database migration remains unverified. |
| PANE-02 | RSI/Stochastic and ATR/stddev compatibility plus incompatible-unit rejection checked. Other supported pairings reviewed and covered by author tests. |
| PANE-03 | VMC B seven-series placement and separation reviewed in implementation and author tests; actual bipolar rendering verified below. |
| PANE-04 | Creation-order permutations, hidden first pane, Price first and Recorded IR last checked with strict chart model; actual library geometry verified below. |
| PANE-05 | Relative weights, all sixteen visibility subsets and restored membership checked; browser relative-weight/visibility behavior verified below; many-pane performance unmeasured. |
| PANE-06 | Linear auxiliary settings, retained manual/log price settings and independent volume-scale requests checked; price/auxiliary browser scaling verified below; volume remains automated-only. |
| PANE-07 | Atomic backend saves checked; draft retention and Apply/Cancel paths reviewed with author component evidence. Cross-context browser draft scenario verified below. |
| PANE-08 | Preset capture and identity preservation reviewed; baseline retains instance IDs, so remapping is unnecessary. Stage/Apply/Cancel, reload and Service restart verified below. |
| PANE-09 | Unknown preset extension preservation through rename/duplicate/trash/restore, unsupported saved layout refusal and no fallback capture checked. Author tests cover unsupported Stage and reanchor preservation. |
| PANE-10 | No fixed pane cap checked with 513 synthetic panes; formula/origin identity inspected in author tests. This is not a performance claim for 513 visible panes. |

The author also reported 99 focused frontend tests, type checking and production
build passing. The first backend pass had 37 passes and one erroneous test
expectation: layout Apply must advance the settings revision while preserving
numeric payloads and origins. The corrected affected subset passed 15/15. These
runs overlap and must not be added as distinct tests or described as a fresh full
product regression.

Source contracts: ADR 0053 and ADR 0054. This reconstructs specified
functionality; it does not establish byte identity with unavailable old source.

### Actual production-browser acceptance

The integrated runtime source at `868f5a7a3f676083dbcd2d341c78ef29ec6d276a`
was checked through the real application and local Service on isolated synthetic
data. Its only difference from the independently reviewed pane source is the
initial recovery-plan document. Production build inputs and built assets were
hash-verified before reuse. Eight independent fixture arithmetic checks passed
against 300 displayed outputs from a 960-bar frozen raw origin.

The actual chart accepted and retained price weight 400, MACD first with weight
130, VMC B second with weight 240, and merged RSI/Stochastic third with weight
130. Compatible split/remerge, VMC Hide/Show with reclaimed space, and price log
mode while the negative MACD pane remained linear were checked visually.
Unapplied layout/parameter drafts survived Lab/Market and Bybit/OKX context
navigation; Cancel restored applied settings. Named preset save, Stage/Cancel
and Stage/Apply preserved existing instance IDs and pane memberships.

A full page reload and a clean Service stop/restart on the same isolated data
restored RSI period 14, all six visible indicators, the applied order/weights,
and original native scalar values. Synthetic fixture guards recorded zero real
provider, PAPER, order and external-delivery actions. The same
sealed source/build was used after restart.

These browser scenarios satisfy the corresponding GUI portions of PANE-03,
PANE-04, PANE-05, PANE-07 and PANE-08, and the price-log/linear-auxiliary portion
of PANE-06. Recorded IR placement and overlaid-volume isolation were covered by
automated checks, not separately seeded in this browser walkthrough. Many-pane
scrolling is not claimed as a measured performance test. Authentic missing old
database migration, Windows/native, live providers and owner acceptance remain
unverified. New independent tests are retained in the repository for repeatable
future checks; they do not add a second calculation engine.


## Frozen alert core/storage: independent acceptance checkpoint

Reviewed source: `e4b024ea66413a2f0aba2a7a154b474e4a725dbd`.
Tree: `c93426c8bb8f3de3a6f9f683bf95617fb68433d0`.

Nine independently authored synthetic Python tests passed on this exact frozen
source. They do not import the author's new test helpers or reuse its expected
numeric results. Portable test: `tests/test_alert_core_independent.py`.
Reproduction after including that test in the repository:

```sh
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p test_alert_core_independent.py -v
```

The independent checks establish:

- Strict frozen values and resources, missing full origin and gap rejection,
  unknown-state reset, and unchanged past evidence after future perturbation.
- Independently calculated SMA crossings and exact raw-open/confirmed-close
  clocks at both one-minute and five-minute intervals.
- All 27 three-input combinations for each ALL/ANY truth function, plus
  persistent-state and same-close impulse behavior.
- Complete keyset journal traversal for 80 genuinely computed synthetic hits
  in seven-row pages, without duplicates or lost tail.
- Rollback of both event insertion and cursor advance when a deliberately
  injected SQL trigger fails the cursor update.
- Startup, Pause and rebind fencing; duplicate re-arm delivery preserves the
  original event, read status and durable at-most-once banner claim.
- Rename exposes the current name without rewriting frozen event evidence.

Before freezing, the author corrected huge-number validation so overflow fails
as a clear ValueError before formula validation. Independent malformed-input
checks passed on the corrected source. The review also inspected exact formula
contracts/ports, causal VMC event clocks and the combined working-memory
preflight. VMC pivot+2 is covered by the author's focused fixture; this independent
nine-test pass does not claim an additional VMC GUI exercise.

### Completeness ledger status

| Criterion | Established scope | Still pending |
|---|---|---|
| ALERT-01 | Pure frozen schema, parameters, context, origins, formula contracts and strict rejection | Capturing/reviewing those definitions through the actual UI |
| ALERT-02 | Core comparison/cross/divergence API and ALL/ANY semantics | Editor and real receipt integration |
| ALERT-03 | Raw confirmed replay and independent exact clocks; causal VMC implementation reviewed | Runtime provenance/freshness and actual chart evidence |
| ALERT-04 | Durable rule revisions/archive/restore and startup-token invalidation | User-visible startup paused state and Arm UI |
| ALERT-05 | Baseline store does not emit past events | Explicit async Arm on observed MarketHub receipts |
| ALERT-06 | Frozen appearance independence and changed-dependency detection | Reviewed UI rebind and runtime fencing |
| ALERT-07 | Atomic cursor/journal transaction and cross-arm dedup | Runtime delivery integration |
| ALERT-08 | Durable at-most-once claim and read status | Actual banner display and lost-response UI |
| ALERT-09–12 | Not implemented by this core checkpoint | Receipt queue/epoch, freshness, lifecycle races, uncertain-create handling and UI reload/context fences |
| ALERT-13 | Core library/journal paging only | Same-selector UI regression and archive/restore UX |
| ALERT-14 | Current-name field separate from frozen event evidence | Correct visible labels in journal/banner |
| ALERT-15 | Reviewed modules have no external notification/trading dispatch | Integrated forbidden-action counters |

The author separately reports 45 distinct focused tests, including existing
nearest regressions. Refinement reruns overlap those cases and must not be added
again. This checkpoint is not a complete recovered alert feature: Service,
MarketHub runtime, actual UI, historical scans and agreement features remain
outside it. No original-alert database migration, Windows/native, provider,
full-product-regression, remote-CI, packaging or release claim is made.

Contract and public API: ADR 0055, Frozen local indicator-alert core.

### Publication sequencing

The pane checkpoint is remotely verified at
`e30a500b80b32da6ef356a206d77327df4f7f492`, with tree
`b1c12adc4e3dfb51e0b0d049cd24639484c28960`, matching the reviewed local source.
The isolated alert-core checkpoint follows it. Its runtime implementation and
new user-facing controls may begin only after this next source checkpoint is
remotely verified. No configured remote CI runs are present; this is not a CI
pass claim.


## Passive local alert runtime and Service checkpoint — 2026-10-12

The next backend slice adds the passive observed runtime and strict Service API
in ADR 0056, after remotely verified core `5e20e93d04d7e76c6aaf2141cdbefdbedd230044`.
It reconstructs bounded lifecycle guarantees rather than claiming byte recovery
of missing original source. The exact API is in `ALERT_RUNTIME_API.md`; author
verification is recorded in STATUS. Source/publication hashes and independent
immutable-checkpoint challenges are recorded separately when established.

At this slice, ALERT-01–08 and ALERT-09–12 gain backend Service/receipt/session
integration, while UI creation/review, real banners, visible journal controls and
lost-reply interaction remain pending. ALERT-13–14 gain Service metadata/read
routes but not UI acceptance. ALERT-15 has actual synthetic Service/Hub negative
guards with zero provider/PAPER/order/external notification calls. History,
current/agreement summaries, Windows/native, live sources and owner acceptance
remain outside this backend checkpoint. Do not carry historical report claims
forward as newly executed tests.
## Alert runtime/Service: independent acceptance checkpoint

Reviewed source: `883b6439c407ed67d985416b7947673dd859db31`.
Tree: `dccca22cdae1c47d32e087ed9737f9d3e34ac1dd`.

Ten independently authored tests passed through the actual Service, MarketHub
fanout and runtime, using a guarded synthetic stream. Provider, PAPER, order and
external-notification guard counters stayed zero. No event was inserted manually.
Portable retained test: `tests/test_alert_runtime_independent.py`.

```sh
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p test_alert_runtime_independent.py -v
```

Established scenarios:

- Explicit Arm warms a baseline without historical events. A subsequent observed
  crossing produces its exact raw-open and confirmed-close evidence. Repeated
  identical delivery does not duplicate the journal; explicit Pause prevents
  further events.
- A healthy five-minute stream can Arm two minutes after its latest close.
  Queue freshness is not incorrectly substituted for native-interval freshness.
- A provider confirmation observed before its candle close remains ineligible
  as an Arm baseline even after wall time later passes that close.
- Context change during a deliberately blocked asynchronous Arm prevents late
  activation or events. A new frontend session leaves a null current context.
- Four distinct pending receipts overflow the bounded three-receipt observer and
  fail closed. Consecutive identical confirmations may be coalesced without
  discarding distinct or conflicting observations.
- Missing cached full-origin input pauses instead of inventing an event.
- Changed then restored original parameters retain a durable rebind requirement,
  including after Service restart.
- Read-only request lookup resolves an uncertain create; repeating the same
  request identity does not create a second rule. Different content with the
  same identity is rejected.
- A worker that cannot join within the shutdown timeout leaves dependent Service
  components alive. They are not closed underneath the still-running replay.

Independent source review found three additional safety corrections before
freeze: the three-receipt capacity, baseline observation clock check, and a
concurrent save/revert race. Settings save and dependency notification now share
the established runtime→display lock order for both inline and uploaded saves.
The author's controlled two-thread regression verifies that a second save cannot
hide the first applied parameter change. This concurrency scenario is author-test
and independent-source-review evidence, not an extra independent test count.

The author reports 56 distinct focused checks, with 25 affected checks rerun after
correction. Those overlapping runs are not additive. Pure formulas remain
unchanged. Runtime and strict Service APIs cover the backend portions of ALERT-05
through ALERT-12 and request/journal support in ALERT-13. Actual editor,
uncertain-create UI quarantine, banners, same-selector UI behavior and graphical
acceptance remain pending; backend readiness is not the complete restored alert
feature. Event/history and agreement integration are separate stages.

Contract: reconstruction ADR 0056. This new ADR number does not imply byte
identity with an unavailable historical ADR of the same number. Original-database
compatibility, Windows/native, live providers, full product regression, remote CI,
packaging and release remain outside this checkpoint.

### Observed-clock Service smoke

The integrated source `efff6ba8baa0139a0f179a24df053d1c45c57ebb` has the
same reviewed runtime tree above. A separate guarded synthetic database and the
actual BrowserServer, AppService and MarketHub were exercised without patching
the wall clock. Arm emitted no backlog. The next real minute's raw close of 22
changed SMA(3) from 10 to 14, crossing 12 and producing exactly one durable event.
Its raw open was 1791800280; confirmed and observed times were 1791800340.
Repeated delivery produced no duplicate. Explicit context Pause and clean
Service reopen retained the identical event and paused state. All six forbidden
side-effect counters remained zero. This is Service-level evidence, not browser
alert-editor acceptance. The accepted pane fixture was unchanged.
