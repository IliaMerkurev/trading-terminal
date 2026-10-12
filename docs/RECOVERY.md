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

Pane layout passed focused, independent and actual-browser synthetic checks.
The frozen alert core, passive runtime/Service, pure agreement evaluator and
cache-only historical backend are independently checked and remotely published.
The alert interface passed focused/component and actual-browser synthetic
acceptance and is remotely verified at `23382863bb22689757df45242ee2ec229e3dda2b`.
The corrected current-agreement panel has passed focused, independent and
actual-browser synthetic checks; remote publication is verified separately. Historical research UI and frozen
agreement conditions/full group history remain in progress.
This is not full product or owner acceptance.


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
## Pure agreement evaluator: independent acceptance checkpoint

Reviewed source: `e3dc7c52ee8c77cc2c47c143bf66c8e70583bf9c`.
Tree: `2a446441205472f4c50e036f0a259a99db3a304b`.

The independent fixture contains 48 precomputed semantic cases and seven exact
threshold checks. Twenty-eight of the cases are independently selected numeric
boundaries. Expected rational shares were authored from the agreed contracts,
not generated by either evaluator. These fixtures test interpretation of existing
outputs; they are not a second indicator-formula implementation.

Independent results on the frozen source:

- Four Python tests passed, covering all 48 expected cases, seven thresholds,
  invalid/conflicted raw candles, absent exact output, OBV adjacency, detached
  prepared snapshots and future-data invariance.
- Fifty-five TypeScript tests passed: the same 48 cases and seven thresholds.
  Every complete TypeScript result also equalled the independently checked Python
  result, including exact shares, rounded display, classifications and coverage.

These counts describe test cases and wrappers explicitly; they must not be added
to the author's 67 Python/68 TypeScript totals as wholly disjoint semantic checks.

Key independent expectations include:

- Three equally weighted groups voting up/up/down produce exactly 2/3 up and
  1/3 down. An exact duplicate changes neither weights nor coverage.
- SMA-up and SMA-neutral variants average within their type. With an up EMA,
  trend is 3/4 up and 1/4 neutral; with two other up groups, overall is 11/12 up
  and 1/12 neutral, displayed as 92/0/8.
- A partially available type may contribute its available variant but is not
  fully covered. Two full types out of five suppress overall; two out of four
  with two available groups meet the inclusive coverage gate.
- One group alone cannot yield overall. Neutral remains in denominators, while
  hidden/context rows do not add votes or supported-type coverage.
- Exact 70% meets a 0.7 threshold; a threshold just above 0.7 does not. A required
  group at exactly 50% fails its strictly-greater-than-half condition.
- RSI/Stochastic/Williams flat-input guards prevent endpoint fake votes. Missing
  guard coverage remains unavailable. Numeric neutral boundaries are inclusive.

Two pre-freeze source-review findings were corrected: overflowing Python integers
now fail safely, and explicitly conflicted or invalid raw OHLC cannot vote or
qualify as a flat/adjacent guard row. The shared manifest records this contract.
The only initial shared-fixture failure was an independent fixture-builder alias:
a later scenario accidentally appended two unavailable members to an earlier
four-member input. The input was restored to its intended four members; every
expected value and all other cases remained unchanged.

Portable independent harnesses: `tests/test_agreement_independent.py` and
`frontend/src/indicatorAgreementIndependent.test.ts`. They use the retained
`tests/fixtures/indicator_agreement_v1.json`.

```sh
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p test_agreement_independent.py -v
node_modules/.bin/vitest run frontend/src/indicatorAgreementIndependent.test.ts
```

Manifest hash:
`74cc8337a2e60f56719fc584decb79427609be58450c582d3c72f512355651ff`.

This establishes the pure portions of CURRENT-06 through CURRENT-14 and the
shared-manifest/threshold portions of AGREEMENT-01 through AGREEMENT-03. It does
not establish the current-summary UI, accepted-response provenance/freshness
fences, frozen agreement-rule integration, historical timeline or notifications.
Those remain pending under the completeness ledger. Contract: ADR 0057.
## Reconstructed cache-only historical research: independent acceptance

Source checkpoint: `32f8e3db4ca3ea6c21d98bce08f73c71a2d7d9ff`, tree
`b28f148bda1620142dfc18751a1b45475ff48ed1`. Integrated source
`40eef0a267339207d6ba249a154e3119bd4f32f1` has the identical tree. Eight
independent actual-Service scenarios passed on the frozen checkpoint in 5.231s.
The retained test `tests/test_history_independent.py` also passed its portability
run (eight tests, 5.222s). The final missing-target assertions were then retained
and their affected test passed separately. These are the same eight scenarios,
not additional coverage.

| Criteria | Independently challenged behavior | Limit |
| --- | --- | --- |
| HISTORY-01, 03, 08, 10 | Independent 362-row SMA(2) tape yields 360 known rows, two unknown rows and exactly 60 crossings. Three pages contain twenty hits each, with independently derived raw-open/confirmation-close times and SMA values. | Synthetic local inputs, not an original saved dataset. |
| HISTORY-01, 07 | Raw candles, calculated values and frozen rule identity remain identical after current cache replacement, current rule rename and clean Service restart. | Authentic old-format run migration remains unverified. |
| HISTORY-05 | Identical request-ID/content returns the same durable run; different content rejects; unknown readback is read-only. | Lost-response frontend reconciliation is a later UI gate. |
| HISTORY-03, 04 | Later Start cannot evade the 10,000 full-origin input budget or hide an early cache gap; ninth unfinished job rejects. | The 256 MiB estimate is also reviewed/author-tested, not a measured memory benchmark here. |
| HISTORY-08, 09 | Forced byte-shortening before a selected target returns the actual last-row cursor and truthful target-omitted state. Exact-row fallback reaches the precise raw candle; next page starts at the actual next index. | Real chart rendering and target navigation are later GUI gates. |
| EVIDENCE-01–03, HISTORY-07 | Historical reads/scans leave live cursor, journal evidence, unread state and banner claim unchanged. Current-cache OHLC may differ, while original condition evidence remains authoritative. Missing exact target is visible and never replaced with a nearby candle. | Does not yet test frontend draft/layout isolation. |
| HISTORY-05, 06 | Running cancellation remains pending until the worker clears it; queued cancellation is terminal. Cancelled results survive restart. | Frontend late-poll cancellation handling is still pending. |
| HISTORY-05, REGRESSION safety | Deliberately blocked shutdown retains dependent services and worker ownership, marks the scan interrupted and preserves that state after restart without automatic resume. | Tests use bounded controlled worker delays. |

All provider, PAPER/order and external-notification guards remained zero in these independent Service tests. This backend checkpoint does not complete historical date-field behavior, compact hit-list layout, detached chart rendering, or agreement-history integration. No original-byte or old-database compatibility claim is made.


## Local alert interface reconstruction

The reconstructed interface uses the published runtime without changing its
formula/storage/MarketHub contracts. App-level session fencing, exact applied
context previews, explicit reviewed async Arm/Pause, paged rule CRUD and journal,
paused rebind and durable uncertain-write recovery are implemented. The complete
workflow and recovery limits are in [ALERT_UI](ALERT_UI.md). Historical alert
research and agreement integration remain separate milestones.

Author verification: 66 first-pass frontend checks and a final 23-check focused
correction pass, with 68 distinct checks after overlap is removed. TypeScript
and production build pass; the existing bundle-size advisory remains. Tests
include unknown-create persistence/reload, post-commit error readback, exact-retry
quarantine, absent-Arm fence recovery, stale previews, same-value filters, selected
rebind polling, claim-page traversal, immutable unknown evidence and read state.
Nearest regressions preserve chart navigation, focus and indicator/preset drafts.
Independent review and actual-App GUI outcomes must be attached to the immutable
checkpoint separately; these author tests do not substitute for them. No old
source byte identity, unavailable database schema compatibility, native Windows,
live provider, full-product suite, remote CI or owner acceptance is claimed.
## Reconstructed alert controls and journal: independent acceptance

Source checkpoint: `85a6db533f8a6696daf03ee41e808b6c8d9c43e7`; tree `0870397c5868dbeda7d642682692f34cd7d24d31`. Independent frozen run: **9/9 passed** in 3.09 seconds, with no tracked source changes. Portable tests: `frontend/src/alertUiIndependent.test.tsx`. Run with `pnpm exec vitest run frontend/src/alertUiIndependent.test.tsx` from the repository root.

| Criteria | Independently challenged behavior | Limit |
| --- | --- | --- |
| ALERT-09–12 | A→B→A uses increasing context revisions; stale capabilities cannot return. Reviewed checkbox is required, and Arm is not sent before Pause acknowledges. | Mocked frontend transport; real Service/Hub lifecycle evidence remains in the earlier runtime checkpoint. |
| ALERT-11 | Original uncertain create survives provider remount and context change, with its exact identity/content retained. No second create is inferred from an absent readback. | Actual browser reload acceptance remains pending. |
| ALERT-11 | An absent uncertain Arm has an explicit recovery path: newer acknowledged context fence, Pause, readback, then fresh review; old Arm is never replayed. | Source review additionally checks that rejected retries do not settle an earlier unknown create. |
| ALERT-11 | A post-commit Service error resolves through original request-ID readback instead of treating the envelope as proof of failure. | The fault is injected at the frontend API boundary. |
| ALERT-01, 11 | Late preview from an older applied-settings revision is discarded; selected-rule polling still exposes durable rebind-required state after applied revision changes. | Actual indicator drafts and navigation require integrated GUI acceptance. |
| ALERT-13 | Same-value Saved selector preserves loaded rows and selected rule. | Archived/restore routes also have author tests; they are not additional independent scenarios here. |
| ALERT-07, 14 | Banner polling traverses twenty already-claimed events to reach the next unclaimed event; only that event is claimed and its current name is labelled. | Visual banner presentation and journal paging require actual GUI acceptance. |

This checkpoint does not complete detached event charts, historical research UI, current agreement UI or agreement alerts/history. Original source byte identity and authentic old-database compatibility remain unverified.

### Integrated alert interface build

The alert implementation is unchanged from its reviewed source above; integration
preserves the published agreement evaluator and historical backend. The retained
nine UI challenges passed their portability run. The initial integrated build
identified browser-TypeScript-incompatible Node imports in the previously
retained independent agreement test harness. That test-only setup now uses the
existing Vitest module loader, JSON fixture import and platform-local pinned
Python path. Its expected vectors and evaluator source are unchanged; all 55
cases passed again, followed by TypeScript and production build. The existing
large-bundle advisory remains. Actual-browser alert acceptance is still pending.


### Actual alert browser acceptance — 2026-10-12

The integrated production source `4e13977a2b23053c347e4604a444635ea7170e8a`
passed a guarded actual-App synthetic workflow. A reviewed SMA(3) cross-above-12
rule was saved paused, then explicitly armed with a 10:50 UTC baseline. Hiding
the source SMA did not rewrite or stop the frozen rule. A genuinely observed
10:52 close produced one local banner and one journal event: previous SMA 10,
current SMA 14, raw candle open 10:51, confirmed close 10:52 UTC. No event was
manually inserted and no historical backlog was delivered.

Mark-read, rename, archive/restore and leaving Market for Lab were checked;
metadata actions remained paused. Changing the surviving hidden SMA from period
3 to 4 required explicit rebind. The displayed paused reason initially lagged
the settings change; an attempted reviewed Arm was authoritatively rejected
with rebind-required, which then became visible. Reviewed rebind saved definition
revision 2/settings revision 11 paused. Full Service restart and page reload
retained the rule, current name, read flag and original event (definition revision
1/settings revision 7), without another banner or automatic Arm.

An independent fixture oracle confirmed the event evidence hash stayed
`e735a0fec27d0f0f0c1a0456d87ab08104a7901603cd97d05133a4186e76dd0f`
through rename/archive/restore/rebind/restart. Service stopped cleanly at
10:56:18 UTC; all six forbidden side-effect guards remained zero. This establishes
one real observed crossing, not a second-cross GUI scenario. Uncertain-network,
overflow and delayed-response behavior remain automated/component evidence.
Windows, live providers and owner unaided acceptance remain unverified.
## Reconstructed current agreement panel: independent acceptance

Source checkpoint: `5e00d3dc67bf07018be0a54556dec48c7b1082bd`; tree `cba1fea8c9beab7318d7a415695fb5b8cd15457a`. Independent frozen run: **8/8 passed** in 1.23 seconds, with no tracked source changes. Portable tests: `frontend/src/currentAgreementIndependent.test.tsx`. Run `pnpm exec vitest run frontend/src/currentAgreementIndependent.test.tsx` from the repository root.

| Criteria | Independent evidence | Remaining boundary |
| --- | --- | --- |
| CURRENT-01, 15 | Summary and heuristic disclaimer remain visible, details start collapsed, and expansion survives an ordinary accepted-response refresh. | Actual browser geometry and keyboard interaction still require GUI acceptance. |
| CURRENT-02 | Only applied member identity/parameters/visibility are accepted. A hidden CMF changes three-group two-thirds Up into two-group all-Up only when response settings match. Draft-only changes cannot reuse the old response. | Live draft navigation is a separate GUI scenario. |
| CURRENT-03 | Exact newest confirmed RAW close is selected; forming rows and synthetic HA price candles cannot change the vote. Missing newest output is unavailable, never replaced with an older ready output. | Recent-buffer pan behavior is additionally source-reviewed; detached history uses the dedicated historical-buffer flag rather than Following state. |
| CURRENT-04–05 | Historical, inactive, stale, loading, saving, missing-settings and error states suppress before evaluator preparation. Nineteen adversarial envelope/raw/setting mutations reject. | Existing chart navigation owns Return to latest; no extra fetching or monitoring path is added. |
| CURRENT-05 | First persisted origin and internally consistent accepted reanchor work despite initially empty/stale locally loaded origins. Receipt identity, generation/window/raw-key and projection/event envelopes must match. | Backend supported cache writes preserve old candles and mark corrections conflicted; display replay rejects these conflicts. External database editing is not a supported live update path. |
| CURRENT-06–14 | The accepted shared evaluator is reused unchanged. A three-group independently specified case yields exact 2/3 Up, 1/3 Down, conflict, and 67/33/0 integer display. | Broader numeric boundary/coverage parity evidence belongs to the earlier pure evaluator checkpoint; these counts must not be added as unrelated duplicate scenarios. |

This slice does not complete agreement alert conditions or historical agreement timelines. It adds no formula engine, provider call, strategy, PAPER/order action or external notification. Authentic old-database compatibility and original-source byte identity remain unverified.


The current-panel integration preserves the published alert session bridge and
historical backend. Its retained eight independent scenarios and nine nearest
alert lifecycle scenarios passed together (17 checks, 3.33s), followed by
TypeScript and production build. These are reused scenarios, not extra distinct
coverage. The only source conflict was two additive MarketChart imports, both
retained. The existing bundle-size advisory remains.


### Actual current-agreement acceptance and navigation correction

The first integrated GUI check on `0cef242a57ed979ba4790ab4791c57b5424f32bf`
found a real pending-page defect: an older-page `idle/loading=false` reply
retained its cursor while permitting old recent-buffer percentages. This can
also occur under queue saturation. It was reproduced deterministically and
corrected by retaining the loading fence until ready/end/error. The unchanged
pure evaluator, adapter and panel retain their prior acceptance.

Corrected production source `c7373abf82648dd2e76afc01b9c062cf28c7a29e` passed
the focused actual-App synthetic navigation checks: an unresolved older page
kept percentages unavailable; truthful cache-page metadata completion resolved
that same request into a detached historical buffer, which remained suppressed.
Return restored the current 11:20 UTC result. A subsequent small pan inside the
retained recent buffer kept the viewport fixed while the reference advanced
from 11:20 to 11:21 UTC. Moving the crosshair to 10:00 did not select another
reference. Metadata completion changed neither raw OHLC nor calculated results.

Earlier unaffected GUI checks established applied-versus-draft separation; CMF
adding a third group with neutral votes retained in denominators; exact SMA
copies adding no type/variant weight; hidden CMF removing its group; native
11:06 results unchanged between Candles and Heikin Ashi; a single available
group suppressing overall while retaining its group result; and immediate
suppression of the old source during Bybit/OKX switching. Those observations
are carried only across unchanged production code.

The correction passed 89 focused author checks and four reviewed/re-executed
navigation checks, followed by four affected integrated checks and the build.
The four are existing tests, not newly authored independent coverage; overlapping
counts are not additive. Total author coverage is 146 distinct tests, with eight
independently authored adapter/component scenarios retained. Service stopped
cleanly at 11:21:27 UTC with all forbidden guards zero. Live providers, Windows
and owner unaided acceptance are not established by these synthetic checks.
