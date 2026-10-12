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
The remaining four stages are not yet restored; this is not full product or
owner acceptance.


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
| PANE-03 | VMC B seven-series placement and separation reviewed in implementation and author tests; actual bipolar rendering pending browser acceptance. |
| PANE-04 | Creation-order permutations, hidden first pane, Price first and Recorded IR last checked with strict chart model; actual library geometry pending browser. |
| PANE-05 | Relative weights, all sixteen visibility subsets and restored membership checked; measured browser heights and scrolling pending. |
| PANE-06 | Linear auxiliary settings, retained manual/log price settings and independent volume-scale requests checked; actual chart scaling pending browser. |
| PANE-07 | Atomic backend saves checked; draft retention and Apply/Cancel paths reviewed with author component evidence. Cross-context browser draft scenario pending. |
| PANE-08 | Preset capture and identity preservation reviewed; baseline retains instance IDs, so remapping is unnecessary. Stage/Apply/Cancel and reload browser walkthrough pending. |
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
