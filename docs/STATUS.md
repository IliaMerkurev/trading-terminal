# Implementation status

For the current branch, navigation, portable launch routes and prioritized UX
continuation, see the [current checkpoint](CHECKPOINT.md). Entries below are
dated evidence: later checks supersede only the corresponding earlier pending
gates, not unrelated platform or owner acceptance.


## Chart indicator browser acceptance — 2026-10-11

The final Linux/browser source checkpoint `ce7e3fd` was exercised against three
isolated, explicitly labelled synthetic workspaces with exchange transports
blocked. This is application interaction evidence, not live-exchange, Windows,
strategy profitability or unaided owner acceptance.

- Added all six indicator types through the UI; an additional EMA retained an
  independent period. Invalid period 1001 disabled Apply with a clear error;
  eight draft instances disabled adding a ninth. Hide/unhide, RSI removal and
  re-addition, saved settings reopening, Fit, older-cache paging and rapid chart
  timeframe switches were exercised. BTC latest values and persisted origin
  remained stable across the observed paging/reopen sequence.
- A separate eight-close oracle displayed SMA3 11.66666667, EMA3 11.28125,
  Bollinger2/2 lower/middle/upper 8/10/12, RSI2 45.5, and MACD2/3/2
  line -0.3384059214, signal -0.3492703094, histogram 0.01086438805;
  volume was 10 source-native fixture units. These agree with independently
  authored arithmetic expectations, not exchange data.
- Actual 1180px and 718px browser checks found and corrected clipped workspace
  scrolling, JSON-key-dependent labels and compressed oscillator panes. Final
  measured pane heights were 306/124/124/125px within a 710px chart. The final
  RSI axis showed its bounded 0–100 range with 30/70 guides, without changing
  the other pane margins. Controls and readouts wrapped at the narrow width.
- An explicitly historical forming candle remained visible in price and raw
  volume (777), while its EMA value stayed unavailable. The previous confirmed
  EMA endpoint remained 11.28125; details showed eight confirmed and one unknown
  input after repeated polling/Latest. No age-based confirmation was inferred.
- A 10,001-bar saved-origin fixture visibly refused indicator replay while price
  browsing stayed usable. Switching to the small oracle recovered EMA3 11.28125.
  Read-only SQLite comparison confirmed every pre-persisted over-budget origin
  document unchanged; no silent reseed occurred. In the refusal state, details
  currently show an unavailable-result placeholder rather than the saved origin;
  the explicit error correctly explains that the origin was not changed.
- All three hosts stopped through the visible service control. Exit evidence
  showed zero external transport attempts and zero result, native-trust, live
  session/evaluation/signal or paper action rows; SQLite integrity was valid.

The aggregate checkpoints were 466 Python tests (8 explicit Windows-only skips)
and 489 frontend tests across 55 files. Later narrow corrections passed 23
backend-focused tests and the final 33-test frontend-focused set, TypeScript and
Vite. Independent review and secret scans passed. An earlier unchanged
CardOrdering timing failure was retained; focused retry and the next aggregate
passed without weakening its expectations.

Native color-picker automation was inconclusive; component, backend persistence
and series color tests passed. Browser checks did not exhaust every 1,800-bar
trim boundary, interactive provider-confirmation transition, recorded-session
combination or 390px layout; corresponding automated evidence does not become
browser evidence. Current Windows/native and actual public feed acceptance remain
separate pending work. No dependency, product version or financial formula changed.


## RSI scale padding correction — 2026-10-11

Actual browser checks at 1180px and 718px widths verified readable relative pane
heights, reachable narrow controls and remove/re-add without ghost panes. RSI
re-add exposed a remaining axis-padding issue: its fixed 0–100 autoscale range
was expanded by library-default scale margins. RSI series now apply zero top
and bottom margins to their current shared pane scale using the installed
library's supported API. Independent source review caught that this library also
updates defaults for future panes: the implementation immediately restores a
copied snapshot of the primary scale margins, preserving RSI's local setting
without leaking zero margins into MACD, volume or recorded panes. The regression
models that library behavior across shared RSI instances and pane rebuilding.
Price and all non-RSI scale margins remain unchanged.

Thirty-three focused frontend tests and TypeScript/Vite passed, including shared
multiple RSI instances and a rebuilt RSI at a different pane index. Calculations
are unchanged. Actual-browser confirmation of the corrected axis and the pending
forming/over-budget scenarios remain acceptance checks; no Windows claim follows.

## Stable relative chart pane sizing — 2026-10-11

Parent browser checks confirmed the scroll/label corrections, independent ETH
oracle values, invalid-period and instance-limit controls, retained hidden EMA
settings and stable origin/output through paging and reopening. They then found
RSI/MACD panes compressed after the canvas resized. Installed chart-library source
review confirmed that sequential pixel-height setters redistribute neighboring
panes. The correction uses persistent relative stretch factors, 320 for price
and 130 for each oscillator/volume/recorded pane, after pane reconciliation.
Actual pixel heights account for the time axis and separators.

Thirty-two focused frontend tests and TypeScript/Vite passed. Independent source
review approved the sizing change. Native color-picker automation remained
inconclusive; unchanged color handling passed draft/Apply/canonical-reopen/series
regressions and a separate synthetic backend save/reopen check. No color-handler
or numerical change was made. Actual-browser rendered sizing after this correction
still requires the parent's repeat check; no new Windows acceptance follows.

## Chart pane reachability and canonical labels — 2026-10-11

Parent browser acceptance found that the original clipped grid could hide the
price pane and toolbar after applying several display tools, and canonical
parameter-key sorting reversed BB/MACD title order. The correction gives the
Market workspace a visible, keyboard-focusable vertical scroll owner. Chart
controls and naturally sized panes remain ordinary document flow; narrow layouts
stretch the chart to available width instead of retaining a fixed chart height.
The bounded order-book/tape scrollers remain separate. Indicator names and field
order now use explicit semantic parameter ordering, independent of JSON keys.

Thirty focused frontend tests passed, including canonical BB/MACD settings,
keyboard focus and computed stylesheet rules, followed by TypeScript and Vite.
Numerical/backend code is unchanged; prior financial evidence is retained rather
than rerun. Actual-browser normal/narrow reachability after this correction still
requires the parent's repeat check; simulated DOM style checks do not prove it.

## Cache-only chart display indicators — 2026-10-11

The Market chart now offers separate SMA, EMA, Bollinger Bands, RSI, MACD and
native-volume display instances. Up to eight may be added, edited, colored,
hidden or removed atomically, including two independent EMAs. Workspace SQLite
persists configuration and timeframe-specific origins. Price overlays, fixed
0–100 RSI, MACD, volume and recorded IR have separate compatible panes. Display
controls do not start a strategy, write signals, place paper orders or modify the
execution profile. Product remains 0.6.0-dev; no dependency or license change.

Explicit confirmation metadata distinguishes closed REST/provider input, forming
observations, legacy-unknown cache and conflicts. No age-based promotion occurs.
Price and available native volume remain useful when calculated values lack
confirmed history. The calculation reuses pinned graph indicator primitives,
with independently verified seeds, warmup, gap resets and matching UTC
interval-end labels. Origins survive paging/trim/reopen; explicit reanchoring
creates a new generation. Over-budget replay refuses without silent reseeding.
One bounded coalesced worker keeps numerical replay off service dispatch;
forming volume cannot repeatedly cancel unchanged confirmed work. See
[ADR 0040](adr/0040-cache-only-chart-indicators.md).

Independent Fraction goldens cover SMA/EMA/BB/RSI/MACD and native-volume edge
values. Independent source review found and verified fixes for confirmation
corrections, delayed closes, duplicate watermarks, corrupted settings, work caps,
responsiveness and forming-tick starvation. An external synthetic fixture
self-check verified baseline, historical-time forming and over-budget scenarios,
all with zero external transport attempts, zero trading/journal records and clean
shutdown. These are service checks, not actual-browser acceptance.

After readability cleanup, the complete Python suite passed **466 tests in
208.420s, with 8 explicit Windows-only skips**; **489 frontend tests / 55 files**
passed in the final run in 17.88s. TypeScript and production Vite build passed. Linux runtime
verification and `pip check` passed. Existing Pandas deprecation and bundle-size
advisories remain nonfatal. The initial aggregate exposed an outdated shutdown
test double missing the new worker; the corrected test also asserts its cleanup.

A later narrow correction adds an explicit whitespace break at a gapped join
between pre-origin finite windows and the saved-origin segment, including
period-1 SMA/BB. Its final focused indicator/market/shutdown regression passed
**23 tests**. The earlier complete aggregate is retained separately and is not
represented as a full rerun after this final correction. A subsequent frontend
aggregate had one intermittent failure in the unchanged CardOrdering alert-timing
test; a 16-test focused retry and the final 489-test aggregate both passed, without
changing that test or its expectations. Staged and outgoing
secret/privacy/license checks cover the final deliverable; an initial scanner
false positive on compressed program syntax was resolved by normal multiline
formatting without scanner suppression.

Actual-browser pane removal/readdition, numeric readouts, normal/narrow layouts
and owner usability remain parent acceptance gates. No Windows/native/live
acceptance, source acquisition, empirical profitability, main merge, release or
publication claim follows from this local implementation checkpoint.

## Observation-to-Lab resolution correction and browser evidence — 2026-10-11

Parent-led production-browser checks on `d9f9640` completed both daily strategy
runs and their passive controls: six completed reports in two completed batches.
C12 fills 115.5/118.5, quantity 0.8, fees 0.1872 and net PnL 2.2128; C13
fills 113.5/128.5, quantity 0.8, fees 0.1936 and net PnL 11.8064 matched independent
expectations. These GUI runs used **10% allocation of initial 1000 USDT**, not
the automated fixed 100 USDT profile. Their one-entry quantities coincide; this
is not general sizing-model equivalence. All data remained synthetic/local.

The browser found that transferring a daily observation updated source execution
to 1440 minutes but retained the shared draft's hidden primary 60. Backend profile
validation correctly rejected that incompatible pair before applying selected
card timeframes. Explicitly toggling resolution repaired the draft for the above
runs. The narrow frontend correction now preserves an already compatible shared
primary or adopts source resolution when incompatible. It changes no strategy
rules, backend validation, financial execution or saved report.

An App-to-real-Lab request regression covers 15/60/240/1440-minute observations,
including direct daily Review without the workaround, unchanged source/dates,
costs/capital and supported per-card signal timeframe. Independent read-only
review approved the correction. Focused 44 frontend tests passed; the first
attempt had only a text-matcher mismatch against the preview's checkmark prefix,
corrected without changing expected request values. Final aggregate: **485 frontend tests / 54 files** passed, followed by successful
TypeScript and production Vite build. The existing chunk-size warning remains
nonfatal. Staged diff/privacy review and pinned secret scans cover this change.

Read-only closed-workspace reconciliation verified all six raw result hashes,
matching snapshots/summaries, **195 exact normalized rows across all eight
series**, two completed batch snapshots, SQLite integrity/foreign keys and zero
native trust. Existing run artifacts were preserved; no financial reruns were
performed for this frontend-only correction. The earlier 454-test backend result
is retained for unchanged Python source, not represented as a new backend run.

The same browser pass verified that a reviewed three-test setup survived modal
close, Z–A card order and search changes, and reopened Start worked. An R2 copy
created from Lab settings rejected lag 1001 for Save/Run; restoring 2 saved it.
Final parent browser checks on `ef8f29c` reopened the saved R2 copy with its
SMA200, RSI2 and lag1/lag2 graph, and a fresh app state transferred the daily
observation directly to a successful three-row Review without toggling resolution.
No financial rerun was needed. Test all retained both 4h and 1d selections; this
daily-only GUI fixture correctly blocked mixed-resolution review with an explicit
4h-versus-1d source message. Candidate-specific unavailable-row rendering remains
automated coverage rather than a claimed full GUI preview on H4 history. Actual
card screenshots were inspected, and the service stopped cleanly. No Windows/
native, narrow-screen or empirical profitability acceptance follows.

## C12/C13 daily reversion engineering slice — 2026-10-11

Added **Double 7's daily reversion (C12)** and **Improved R2 daily reversion
(C13)** as daily spot long/flat clean-room graph templates. Current-inclusive
rolling minimum/maximum and completed-primary-bar lag nodes have bounded typed
parameters, null-slot retention, clone/commit causality, editor support and
experiment warmup. Catalog copies/research enforce closed evaluation, rejected
gaps and no position-management overlay. Existing seven templates/defaults and
old archives remain unchanged. Full-catalog 4h/1d defaults retain explicit
unavailable daily-candidate 4h rows; local card timeframe edits still work after
closing batch setup. See [ADR 0039](adr/0039-daily-reversion-candidates.md).

Source cards disclose primary author/URL/publication/review date, source versus
local settings, execution/RSI adaptations, exact project-authored rule-summary
hash scope and implementation evidence. Their status is **Synthetic implementation
verified; empirical validation not performed**. Referenced articles retain their
own rights. No source profitability claim, copied external code or private
market history is included.

Final-source automated verification on Linux:

- `.venv/bin/python -m unittest discover -s tests -v`: **454 tests**, **8 expected
  platform skips**, zero failures/errors, 191.842 seconds.
- `node node_modules/vitest/vitest.mjs run`: **481 tests / 53 files**, all passed.
- `node scripts/frontend.mjs build`: TypeScript and production Vite build passed.
- Runtime validation confirms Python 3.12.14 / NautilusTrader 1.231.0;
  `python -m pip check` reports no broken requirements.
- Independent read-only financial/source review approved the final rules,
  numerical fixtures, gap admission, catalog compatibility and card-state fixes.
  Pinned Gitleaks 8.30.1 staged-diff scan found no secrets; privacy/license and
  diff-whitespace review passed.

The new 12-test backend module independently checks rational RSI, exact source
boundaries, extrema/lag arithmetic and null slots, repeated forming updates,
future invariance, costed fills/fees/final flatten, no same-step reentry, prefix
exclusion, one-short/full/gapped admission, managed worker execution, copy/reopen,
archive preservation and the full 20-row catalog/default compatibility matrix.
Final focused compatibility gates also passed 17 backend and 10 frontend tests.
The fixture generator produced two synthetic/local histories, two graph copies
and observations, with zero initial runs/batches/native trust.

Initial failures are retained in local verification evidence: test fixtures
incorrectly assumed an absent profile field, supplied an overly broad archive
descriptor and included a legitimate later reentry day. A later prefix-stage
test expected a downstream error while public coverage admission correctly
rejected earlier; its isolation was corrected. The first aggregate therefore
reported one test-harness error (453 tests, 8 skips). An extended UI regression
needed a complete preview mock. No expected financial values were changed to
fit production output. Independent review additionally identified and closed
skip-gap profile and stale shared-timeframe UI edges before final acceptance.
The final aggregate above supersedes those failed gates. Existing upstream
Pandas timestamp deprecation and Vite chunk-size warnings remain nonfatal.

Parent-led real-browser workflow is prepared but not claimed by this automated
slice; no shared browser was used. Windows/native, owner interpretation, original
M1/untouched-holdout limitations and empirical C12/C13 validation remain separate.
No Supertrend, chart-display indicator controls, exchange acquisition, live
orders, merge or release is delivered here. The prior TT13 exact six-row load
and completed TT17/TT18 evidence below retain their original source identities;
this slice does not rerun or rewrite those frozen programs.

## Bounded TT17/TT18 research completed — 2026-10-11

The predeclared H4 research remainder is complete: all 291 observations finished and passed the independent saved-result reopening gate, comprising 228 TT17 neighbor/reference/control observations and 63 TT18 own-adaptation/control observations. No failed/canceled rows, financial retries, extra parameter variants, altered windows or post-result candidate selection were introduced. The original seven-batch campaign remains closed and unchanged.

Execution and verification used commit `1b532796707aa3cf39af681f64148bfabf4b1c86`. Subsequent branch alignment to published commit `9239d53de8ab973d171f6b8e4a2a6d76e9def997` occurred only after the complete campaign, sweep and report finished. Both commits have the identical tested tree `fe6d86fc5709aa70f4b201b7ba5c7bdc0f930ccf`; frozen research identities and saved results were not rewritten.

The fixed model uses retained native H4 BTC-USDT spot history, confirmed H4/UTC D1 signals, independent 1,000 USDT accounts, long/flat graphs, declared fees/slippage and terminal liquidation. Precision, limits and cost rates are explicit manual assumptions, not verified historical venue rules. Graph profile 2 observed-close execution and passive profile 1 scheduled-open execution are disclosed as unmatched execution/risk-capital alternatives.

- **TT17:** six strategy families, two signal intervals and one-axis reference/neighbor settings across the fixed splits and cost scenarios. Ten of twelve family/timeframe robustness conclusions are inconclusive under the fixed observation-count criterion; one is sensitive and one locally consistent. Nine exhibit descriptive screen/PnL-sign sensitivity. The locally consistent historical-return H4 group is consistently loss-making across its 18 reference/neighbor cells. No neighbor is promoted by this program.
- **TT18:** the six independently authored slow-ROC/deadband graphs passed the implementation gate. None qualifies for retrospective promotion; all remain sparse/inconclusive under the fixed candidate rule. The paired 1% deadband descriptive turnover/cost criterion is supported at lookback 180, but not at 30 or 90; that limited observation does not satisfy the overall candidate gate or establish profitability.
- **Path check:** all nine A18 OLHC/OHLC pairs have identical fills and reported metrics. Their H4-close account states and within-H4 equity-value multisets agree; raw equity ordering differs with the modeled intrabar path. This does not substitute for native M1 or tick evidence.

Negative and sparse conclusions are valid completion outcomes. No strategy was adopted for production/live orders and no additional strategy family was opened after these results. The twenty-position screen remains a descriptive heuristic, not statistical significance or a profitability guarantee.

### Exact-source verification

The independent TT18 fixture gate covered all six graphs and twelve required check categories, including selected-bar warmup, fractional ROC and exact threshold ties, deadband retention/no pyramiding, UTC D1 aggregation from heterogeneous H4 inputs, incomplete-day suppression, future-data perturbation, zero-denominator failure, independent costed fills/terminal close and h=0 control parity.

After all empirical panels ended and workspace ownership closed, an independent read-only sweep reopened all 291 unique saved results and verified:

- complete planned-row/admission/run mapping, immutable strategy/profile/dataset/runtime identity and raw result/snapshot checksums;
- every saved summary field and all eight normalized series, including exact indexes/order/counts/content and saved candles against source history;
- terminal finalization ownership, receipt sequence/content hashes/chains, byte/row totals and bounded staging rules;
- independent signed-fill cash/fee reconciliation, final flat inventory, trade PnL/count/win rate, equity-derived drawdown, fill rounding/timing, warmup exclusion, passive schedules and annualization conventions;
- dataset source/file/content identities, SQLite integrity, and exactly 291 new freezes/admissions/completions, separately from retained prior research evidence.

No raw source data or full fill/equity outputs are included in the repository or release. Saved-result verification is distinct from UI display evidence and unaided owner interpretation.

### Remaining conditional or deferred acceptance

- **M1 detail probe:** not executed. The required complete native-minute history prefix is unavailable. The original fixed window remains unchanged; no shortening, synthetic repair or higher-timeframe substitution is treated as a pass.
- **Untouched/prospective holdout:** none established. All historical windows were previously exposed. A later genuinely prospective study would require a separately frozen observation/release rule; no qualifying candidate was promoted or future program scheduled here.
- **Windows:** native Windows runtime/lifecycle/transport acceptance remains deferred and is not established by Linux/browser or research measurements.
- **Owner interpretation:** automated execution/report reopening does not replace the separately retained unaided-owner acceptance task.

This closes the bounded H4 TT17 neighbor deliverable and the single predeclared TT18 own-adaptation program. Conditional M1/future-data gaps and deferred platform/owner acceptance must remain explicitly labeled; they are not silently marked passed.


## TT13 exact-source combined acceptance — 2026-10-11

Measured production source: `9a9c3e92a90887b67865314c6ec047949769a25d`, tree
`e8e46643bc6e5391e2720322b2e59364ebcadf90`. The one frozen Linux campaign
refreshed the exact six-row, **2,000,000 modeled source-candle** preview and ran
all six rows through ordinary admitted batch execution, without reuse. Four
strategy runs and two spot passive runs completed. This is independently
invented synthetic engineering data, not exchange research or profitability
acceptance. No source/build change or parallel load campaign occurred.

The workload, including concurrent reads and completed-report page probes,
took **1,352.731 seconds**; total with sequential full verification and cleanup
was **1,393.810 seconds**. All six worker/result hashes and all **3,672,046** new
normalized rows matched exact ordered values. Result JSON totaled
**610,239,551 bytes** before duplicate artifacts/database storage. The preserved
old report's 720,274 rows, artifacts and evidence remained unchanged. Expected
first/middle/last candles and recorded indicators/equity/nanosecond fill boundaries
passed for actual reports, including new shared-source reports. Database integrity,
foreign keys, zero native trust, source invariance and clean shutdown passed.

- **41,897 ordinary HTTP requests** succeeded. Maximum was a graph save at
  **1.998035 seconds**, below the two-second target with little margin. Chart
  start/status/cancel acknowledgement maxima were **0.460121 / 0.828532 /
  0.479245 seconds**. Note-save start maximum was **0.002865 seconds**.
- All **30 cancellation probes actually cancelled**, maximum terminal time
  **0.571451 seconds**, below five seconds. A report cancellation during real
  calculation finalization took **0.052592 seconds**. Two explicit note saves
  completed in **1.084302 / 1.239928 seconds**; two were cancelled. Completion-
  winning races are accepted by the oracle but none occurred in this campaign.
- READY is measured separately: report first/middle/last pages took
  **0.228860–1.667432 seconds**; observation pages **1.033331–2.164473 seconds**.
  Another **1,386 sustained reads** alternated both surfaces during calculation:
  report **0.229432–0.855390 seconds**, observation **0.981046–1.459313 seconds**.
  Actual finalization overlap passed; the independent reader lane stayed usable.
- Peak summed parent/client/service and managed-descendant RSS was
  **4,351,184,896 bytes** (about 4.35 GB), sampled every 50 ms over 25,975 samples.
  Minimum system MemAvailable was **3,921,707,008 bytes**. Shared pages may be
  counted more than once and brief peaks may be missed. Browser-process memory
  and later sequential full-result verification are excluded; this is not a
  universal runtime memory ceiling. The source-materialization admission estimate
  is a separate bound. Retained campaign workspace/evidence occupied about 2.9 GB.

Parent-led production-browser acceptance on the same source passed both explicit
chart Cancel/Retry flows, released verified 500-slot observation READY, neutral
note-cancel draft retention and report reopening with recorded `channel.upper`.
The forced reader gate proves lifecycle behavior, not natural latency. Final
closed reconciliation preserved original results and evidence. The Lab reviewed-
setup close/reopen journey passed the aggregate automated test; its GUI preview
was blocked by missing fixture instrument metadata and is **not** claimed as a
browser pass. Aggregate source coverage remains 442 backend tests (8 skipped),
476 frontend tests, TypeScript/build/runtime validation and independent review.

This closes the bounded Linux/browser TT13 chart-read and combined six-row gate.
Windows/native acceptance, live exchange work and the separate remaining research
plan are still pending. No whole-plan completion, merge or release is implied.
The following documentation-only checkpoint does not alter measured runtime bytes.

## TT13 chart controls and aggregate integration — 2026-10-11

The production-browser first pass verified pending report navigation, actual
500-slot observation pages, cancelled note draft retention, one durable saved
revision after leaving the view, and report indicator/window/pagination. Closed
workspace reconciliation preserved the original 720,274 normalized rows and
artifacts, old evidence, and zero native trust; new viewed events came from UI
presentation. This was a preserved report and deterministic reader gate, with
no simultaneous financial workload or browser-memory measurement.

Both charts now provide explicit Cancel reading, terminal Retry reading and
same-request Inspect reading for uncertain cancellation delivery. Pending
cancellation does not fabricate a terminal state or attach a stale page.
Intentional note cancellation is neutral and preserves the draft. A narrow
pre-existing Lab defect found by aggregate tests was also corrected: completed
reviews survive unchanged setup-modal close/reopen, while substantive input and
source invalidation remains. Existing card-order journey assertions remain.

The full backend suite completed **442 tests in 180.665 seconds: OK, 8 skipped**
on Linux. The full frontend suite passed **476 tests across 53 files**. The final production
build includes TypeScript checking and passed with the existing bundle-size
advisory. Runtime verification and `pip check` passed. Initial failing aggregate
logs were retained: older tests needed additive reader/receipt mocks and an
explicit wait for real worker cleanup; those changes do not weaken financial
expectations. The setup-modal defect was an application fix, separate from those
test-contract updates. Independent source review found no outstanding blocker.

Corrected-control browser verification and the single exact-source six-row 2M
combined workload remain pending. Normal start/status/cancel acknowledgements
and bounded writes target two seconds; READY duration is separately measured.
Windows/native acceptance, live exchange work and browser-process peak memory
remain unverified by these Linux checks.


## Original-plan TT13: verified background chart reads — 2026-10-11

Based on published `d1dcb4b`, with no product-version/license or financial-output
change. Both saved chart routes now use a separate managed reader lane, bounded
observable request/generation lifecycle and full same-descriptor streamed trade
verification. Note-save verification uses the same lane with separate explicit
intent, durable exactly-once receipt and a guarded small revision commit.
[ADR 0038](adr/0038-verified-background-chart-reads.md) records the contracts.

Focused Linux verification passed 50 backend tests (`test_chart_reads`,
`test_observations`, `test_displayed_evidence`, `test_jobs`,
`test_library_batches`, `test_linux_lifecycle`). Independent source review found
and corrected postcommit cancellation, failed-start queue, dirty-draft receipt
navigation, lost acknowledgement and descriptor-delivery races. No outstanding
review blocker remains. Existing Pandas deprecation warnings remain unchanged.

The targeted frontend pass covered 97 cases across eight files; 96 passed in the
combined pass and a test-only unsupported matcher was corrected and its two-case
file reverified. TypeScript/production build passed; the existing large-bundle
advisory remains. These are focused checks, not a full regression or browser QA.

Supported-load READY latency, combined reader/calculation memory, exact-source
six-row 2M workload and production-browser acceptance remain pending. No real
market acquisition or near-limit financial workload was run for this entry.


## Original-plan TT13: managed local result finalization — 2026-10-11

Based on published `1ac84faa677a9185bc3aae788812bf66bcf391bd`; product remains
`0.6.0-dev`, MIT licensed. The frozen measured runtime implementation hash is
`e28c6758e5394798fa4e363a3cbf0b6a339cfd6af5d78cc4a2b4f3a793a7f3a7`.
Managed finalization, local generation authority, preencoded normalized staging,
independent ordered verification, mutation-epoch publication, requested-versus-
reaped cancellation, restart interruption and quarantine are implemented. The
original monitor remains alive through finalizer cleanup, including for batch
waiters. Engine progress and finalization rows/bytes are separate in the UI.
See [ADR 0037](adr/0037-managed-local-result-finalization.md).

The original published monitor was measured in a separate exact-source checkout
against the independently authored 67,036,481-byte normalized fixture. Its
lock-held completion after releasing the test gate took **2.599 s**; queued
scheduler and ordinary save requests took **2.631 s** and **2.604 s**. These waits
exclude the initial worker JSON decode, which had already occurred. This is a
blocking-path comparison, not a comparison of total financial runtime.

Verification with the same retained Linux/runtime toolchain as the export slice:

- Frozen-source `.venv/bin/python -m unittest tests.test_result_finalization
  tests.test_experiments tests.test_archive_async tests.test_archive_receipts -q`
  passed **80 tests**. A separate serialized-HTTP gate and strengthened composed
  closed-copy restore passed; two overlapping cancellation cases were repeated
  only to retain exact latency measurements. Earlier nearest regression checks
  covered jobs, storage resilience, legacy closed copies and Linux lifetime
  ownership. An intermediate wider run had one failed solo-run comparison while
  implementation files were still changing; the subsequent frozen-source
  experiment suite passed. That intermediate run is not a clean acceptance pass.
- Deterministic coverage includes first/middle/last staging gates, artifact and
  final cutoff, exact values/order/counts, old valid non-object/oversized rows,
  foreign/imported/orphan ownership, row relocation, receipt damage, mutations
  after verification, bootstrap cancellation, postcommit exit-74 faults,
  storage-marker/cancellation exit-130 races, failed fault-marker persistence,
  no fallback writes after cancellation persistence failure, reaped terminal
  acknowledgement, retained cleanup ownership and restart without promotion.
- Additive legacy migration and composed closed-copy restore preserve historical
  local/imported rows, import attempts/reserved IDs, snapshots/result hashes,
  normalized content and new local receipt tables. The copied pending local run
  becomes interrupted; completed local/imported content and original admission
  evidence remain unchanged. Integrity and foreign-key checks pass; trust remains
  empty. No import continuation capability grants local provenance.
- `node node_modules/vitest/vitest.mjs run frontend/src/RunProgress.test.tsx
  frontend/src/BrowserServiceControls.test.tsx frontend/src/AppStorageSafety.test.tsx
  frontend/src/App.test.tsx frontend/src/Experiments.test.tsx
  frontend/src/LibraryResearch.test.tsx --reporter=dot` passed **55 tests**.
  TypeScript and `node scripts/frontend.mjs build` passed, retaining the existing
  bundle-size advisory. Component tests are not production-browser acceptance.

Supported-load evidence uses only independently invented synthetic data and new
isolated workspaces. No limits were changed:

- Actual full eager loading passed for linear **440,000 trade + 440,000 mark +
  917 funding rows**, in **4.446 s**, single-child high-water **726.74 MiB**;
  independent spot **440,000 rows** in **2.241 s**, **414.18 MiB**. The linear
  metadata estimate remains **1,032,313,706 bytes**, 96.14% of the unchanged 1-GiB
  source guard. That guard is not a whole-engine memory limit.
- Refreshed six-row preview is exactly **2,000,000 modeled source candles** with
  all six errors null. One actual Donchian M1 graph row was then admitted through
  the ordinary `start_window_run` service route: 320,000 prefix + 120,000 evaluation
  candles. Its real engine-to-finalizer path completed in **306.659 s**, with
  finalization observable for approximately **16 s**. It published **720,274
  normalized rows / 126,100,809 result bytes** across 5,630 bounded staging batches.
  Worker-result and published hashes match exactly; a separate postmeasurement
  pass independently compared every normalized kind/index/value and count.
  This is one real row, not execution of the complete six-row/2M batch.
- During that M1 run, 1,499 samples each of run status, scheduler and ordinary
  `save_graph` writes had maxima **11.55 ms**, **3.90 ms**, **35.85 ms** and p95
  **3.53 ms**, **0.76 ms**, **1.95 ms**. Start returned in **18.97 ms**. Maximum
  measured ownership critical section was **2.79 ms**; maximum write attempt
  was **5.00 ms**. Sampled parent/client plus managed descendants peaked at
  **4,124,823,552 bytes**. RSS is summed at 50-ms cadence, may double-count shared
  pages and can miss shorter peaks; later full verification is excluded.
- The independent normalized-entry fixture completed **62,344 rows /
  67,036,481 bytes** in **5.319 s**; ordinary request maximum **3.15 ms**,
  maximum write attempt **4.32 ms**, sampled combined RSS **734,568,448 bytes**.
- The compatible oversized-row fixture retained its **67,034,893-byte** single
  numeric indicator row (three total normalized rows, 67,035,994 result bytes).
  Completion took **5.638 s**; the explicitly isolated oversized write attempt
  took **292.25 ms**, maximum ordinary HTTP write **330.75 ms**, sampled combined
  RSS **1,247,031,296 bytes**. This is a measured single-row exception to the
  ordinary 256-KiB batch byte target, not a narrowed schema or a hard byte bound.
  Both independent fixtures received exact artifact and full normalized-content
  comparison. They prove persistence load, not financial engine behavior.
- A managed finalizer paused while holding a real SQLite write transaction
  acknowledged cancellation in **251.57 ms** and reached verified quiescence in
  **259.51 ms**. The serialized HTTP gate with a separate 250-ms writer returned
  status/cancel/ordinary-write requests within **255.99 ms**. A deliberately
  stopped supervisor retained ownership; after explicit release, cleanup took
  **26.49 ms**. No terminal cancellation was claimed during the forced stall.

All ordinary request samples satisfy the predeclared 2-second goal and ordinary
cancellation satisfies 5 seconds. Write-attempt timings include connection,
lock acquisition and commit, rather than only write-lock holding time. Financial
values, original local/synthetic admission and result hashes are unchanged;
no native trust or viewed evidence was created by verification. Every measured
host closed and released ownership. The separate GUI scaffold passed direct
HTTP pending/release/completion/shutdown checks. Parent-led production-browser
finalization acceptance, current Windows/native verification, asynchronous
verified chart reads, combined full TT13 acceptance and later research remain
separate gates. No live exchange acquisition or financial conclusion is claimed.


### Initial finalization browser checks and narrow correction — 2026-10-11

Parent-led production-browser inspection on `68503bf` verified the gated
synthetic finalizer at `artifact`, 0/1,202 rows and 0 staged bytes, with no invented
completion percentage. Test running opened Backtest; an ordinary named strategy
save succeeded while finalization remained active. Cancellation settled without
a completed report and released the worker. A separate success path survived
reload, showed the active-work shutdown warning, then automatically opened the
saved zero-trade fixture only after gate release, durable publication and cleanup.
The fixture deliberately represents normalized persistence, not market execution.

That inspection found adjacent status/progress text, a misleading preparation
fallback after cancellation, and active history selection collapsing into an
empty report. The narrow frontend correction separates the status paragraph,
provides terminal outcome/cleanup-specific copy and routes only active history
entries to Backtest/status polling. Completed report selection is unchanged.
The corrected focused pass of RunProgress, AppFinalization, App,
AppStorageSafety and BrowserServiceControls passed **37 tests across five files**;
TypeScript/production build passed. Initial new history tests used an unsuitable
accessible-name match; using the established run-list button selector corrected
the fixture without changing behavior. Existing mocked App duplicate-key warnings
and the bundle-size advisory remain non-failing.

Query-only post-browser reconciliation confirmed the cancellation and completion
outcomes, the completed fixture artifact hash, and an unowned workspace. The
original actual M1 run's complete record, all three artifact hashes, all **720,274
normalized rows** and its original admission evidence remain unchanged; integrity
and foreign-key checks pass and native trust remains empty. Backend/runtime
sources are byte-identical to the measured finalization checkpoint, so no heavy
calculation was repeated.

Parent-led corrected-build browser spot checking on `ff6da73` passed: selecting
active finalizing history opened Backtest directly, detailed progress occupied a
separate paragraph, cancellation displayed its terminal outcome without a running
indicator, and selecting the completed fixture still opened Saved report. The
host was stopped normally. One transient before the first detailed poll still
said “Worker preparation”; the subsequent text-only fallback now says “Loading
finalization status…”. The focused `RunProgress.test.tsx` pass covers this branch
and all eight existing progress cases (**9 tests**); TypeScript and production
build passed. This final loading-copy branch has automated coverage, not another
browser campaign. No backend, fixture or load campaign was repeated.


## Original-plan TT13: background export and bounded verified transfer — 2026-10-10

Based on published `d350be914356be9e115ded113a509646c5d89919`, on
`codex/terminal-mvp`; product remains `0.6.0-dev`, MIT licensed. Managed export
start/status/cancel, frozen identity checks, cancellation/publication cutoff,
launch-local grants, bounded authenticated chunks and final browser verification
are implemented. Import receipts/attempt history are unchanged. See
[ADR 0036](adr/0036-background-project-export.md).

Measured blocking baseline on a separate copy of the existing near-expanded
synthetic fixture: synchronous export **26.795 s**, queued scheduler **26.492 s**,
stalled whole-ZIP receiver queued scheduler **4.826 s**. No financial work or
market acquisition was performed for export acceptance.

Verification on Linux x86_64 (kernel 6.18.44, glibc 2.41, AMD EPYC 9V74,
9 visible logical CPUs), CPython 3.12.14, SQLite 3.53.1, PyArrow 25.0.1 and
Node 24.19.0, using existing pinned project environments:

- `.venv/bin/python -m unittest tests.test_archive_export tests.test_browser_host
  tests.test_archive_async tests.test_archives tests.test_linux_lifecycle -q`
  passed **59 tests** at the first combined checkpoint.
- Subsequent narrow export fault/lifecycle checks passed **16 cases**, followed
  by **2 cleanup/bootstrap cases** after the final independent-review correction.
  These overlap the earlier suite; they are not additional unique-test counts.
  Final exact-source `tests.test_archive_export tests.test_browser_host` passed
  **23 tests** after that correction.
  Coverage includes actual owner death and inherited-lock retention, immutable
  request binding, source changes, zero/eight-run limits, publication faults,
  terminal-outcome preservation across anchor cleanup retry, invalid chunks,
  session/origin boundaries, actual lost start response and paused-supervisor
  status/cancel/ordinary save_graph requests before barrier release.
- `node node_modules/vitest/vitest.mjs run frontend/src/ProjectExport.test.tsx
  frontend/src/ProjectTransfer.test.tsx frontend/src/api.test.ts
  frontend/src/ImportRecovery.test.tsx frontend/src/BrowserServiceControls.test.tsx
  frontend/src/App.test.tsx` passed **60 tests**. Later focused transport/export
  checks passed **27 tests**; export/import close-warning checks passed **21**.
  A final exact-source run of the six listed frontend files passed **64 tests**.
  These overlapping checks cover lost responses, exact-request retry, stale/
  unmounted results, invalid draft preparation, terminal cancellation notices,
  read-only recent inspection, chunk/final checksum errors, ordered chunks and
  aborting stopped transfer before any downloadable Blob is presented.
- TypeScript `--noEmit` and `node scripts/frontend.mjs build` passed. The existing
  large-bundle warning remains; no dependency or product-version change was made.
- Independent read-only review findings were corrected, including Windows
  handle/publication ordering, request-file bootstrap binding, exceptional
  lifecycle cleanup, stale notices and an absolute chunk-write deadline.

Supported-load commands, each on a new isolated synthetic destination:

- Generate with `.venv/bin/python scripts/prepare_archive_load_fixture.py
  <new-fixtures> --mode export`; measure with `.venv/bin/python
  scripts/measure_archive_export.py <new-measurement> --archive
  <new-fixtures>/export.ttproject.zip`.
- Distinct near-expanded case: same measurement command with `--workspace
  <closed-synthetic-import-workspace>`; the script copies it first. It does not
  change the original source or ordinary user workspace.

Predeclared request target **<=2 s** and ordinary cancellation quiescence
**<=5 s** passed in both cases. The near-64-MiB ZIP had **65,439,089 bytes**,
250 chunks and 568 semantic numeric indicator rows across eight runs. The
near-expanded case re-exported **28,753,929 bytes**. The measured export windows
(including the preceding small cancelled attempt) were **19.252 s / 33.282 s**;
those heavy operations no longer held the service dispatcher. Loopback transfers
were **0.301 s / 0.136 s**, excluding browser reconstruction/UI.

Across both runs: maximum start **0.00463 s**, export status **0.01396 s**,
ordinary foreground SQLite save_graph **0.00504 s**, cancel acknowledgement
**0.00590 s**, verified chunk response **0.00274 s**. Cancellation quiescence
was **0.0214 s / 0.0265 s**. An unread peer with deliberately small send/receive
buffers delayed the status-plus-write probe **0.9044 s / 0.9040 s**. This is a
forced backpressure test, not an organic browser/network measurement.

Sampled parent + test client + descendant peak RSS was **1,122,586,624 /
1,337,008,128 bytes**. Every transferred chunk and final file count/SHA matched;
result hashes, normalized row counts and import receipts stayed unchanged;
SQLite integrity was `ok`, foreign-key violations and native trust were zero.
The final cleanup-only monitor correction was checked separately after these
load passes; the measured bulk encoder/transfer paths did not change.

Parent-led production-browser acceptance subsequently passed on exact source
`3f287f700b71e595c17515b5a14defa89b30ca92` and its matching production bundle:

- Selected both independently authored small fixture reports. A deliberately
  paused supervisor left the UI usable; navigating to Lab and back recovered the
  same running operation through Recent exports. Cancellation remained requested
  until barrier release, then became terminal cancelled with no downloadable
  output and an updated history row. This was a controlled lifecycle barrier,
  not an organic slow-disk measurement.
- An unpaused operation completed and automatically presented a verified **4,155
  byte** browser download. Explicit repeat download produced identical bytes
  from the same operation, without a new export. SHA-256:
  `18449fbfd648c2a6c568d88a8488525832a340ffeecec3125676bad99beea077`.
  Query-only verification matched both results and snapshots, validated exactly
  five archive entries/privacy gates and preserved original artifact hashes.
- Normal stop/restart preserved both saved reports and the completed local ZIP,
  showed empty launch-local export history, and resumed no operation. The reopened
  host was stopped normally.
- On a new closed copy of the large synthetic fixture, selected all eight reports.
  Actual browser reconstruction/final verification presented a **65,439,135-byte**
  download, byte-for-byte identical to the generated local ZIP, SHA-256:
  `d06036cecd2f5a849c4490cd5bceb12e7540c4285c12e2ce7eaa0b80dfd1f462`.
  After normal shutdown, query-only reconciliation validated all 17 entries and
  privacy gates, exact eight result/snapshot documents, 584 normalized rows,
  unchanged import receipt and result hashes, zero native trust, SQLite integrity
  `ok` and no foreign-key violations.

Browser RSS/heap/Blob peak remains **unmeasured**, not zero: the bounded
process-resource sampler could not observe Chrome roots through the available
process namespaces, including the native-launched attempt, and produced no valid
browser samples. Earlier Linux parent/client/worker RSS remains separate evidence.
The actual near-limit browser download establishes behavior, not isolated browser
memory attribution or a universal browser memory bound. Windows/native and live
exchange work remain deferred. The separate original TT13 result-finalization and
verified asynchronous chart-read obligations are still open. No full TT13,
whole-plan or final owner product acceptance is claimed.

## Original-plan TT13: asynchronous recoverable import slice — 2026-10-10

Source: implementation commit `fbecf0017c7d26dffb9c9ce37fd9f7196e0e98bf` on
`codex/terminal-mvp`, based on `331fe47e1d60a923a45c0f6ca2c6a5fec3b677e0`.
Product stays `0.6.0-dev`. The managed import process, durable start/status/
attempt-targeted cancellation, hidden normalized staging and explicit same-ID
checksum-bound continuation are implemented. Additive execution/attempt/recovery
metadata preserves schema-1 receipts and archives. Legacy synchronous finish is
retained solely for compatibility. See [ADR 0035](adr/0035-asynchronous-recoverable-import.md).

Completed runs remain immutable. Continuation verifies every prior artifact,
summary, reservation and normalized value before new publication; missing source
bytes require a separate exact-original recovery upload. Unknown/mismatching
content is refused rather than overwritten. Attempt keys and revision claims
prevent lost-reply/concurrent continuation from executing twice. Cancellation is
requested first and acknowledged only after reaping; final strategy publication
and completion have an atomic cutoff. Storage faults retain quarantine, including
cancellation races and rolled-back claims. Startup never resumes or promotes.

Verification on Linux with the existing pinned runtime:

- Combined focused command: `.venv/bin/python -m unittest tests.test_archive_async
  tests.test_archive_receipts tests.test_archive_receipt_backup
  tests.test_archive_receipt_transport tests.test_archives
  tests.test_storage_resilience tests.test_linux_lifecycle -q` passed **71 tests**.
  This includes legacy compatibility, staged invisibility, immutable same-ID
  recovery, concurrent claims, missing-source replacement, migration/closed-copy
  preservation, process ownership and the real serialized HTTP boundary.
- Subsequent narrow correction/boundary checks passed **10 test executions**:
  failed resume claim preserving its prior attempt, bootstrap reaping ownership,
  storage-failure/cancellation quarantine, invalid-source rejection, full copied
  workspace hashes/rows, every before/after run publication boundary, actual
  service kill/restart with inherited ownership, before/after final strategy
  commit, and pre-strategy cancellation retaining all completed reports. Some
  executions deliberately repeat corrected cases; this is not 81 unique tests.
- The real HTTP barrier test was extended with a deterministic 250-ms external
  SQLite write hold and passed. Status, cancellation acknowledgement and an
  ordinary foreground write all returned before the paused worker was released,
  below the predeclared two-second target. Worker quiescence after release met
  five seconds. The old synchronous blocking transport test remains explicitly
  legacy coverage, not the new production responsiveness assertion.
- Component acceptance passed **43 tests across six files**: ProjectTransfer,
  ImportRecovery, BrowserServiceControls, AppImportRecovery, App and
  AppStorageSafety. Two additional narrow tests passed for recovery-upload
  cancellation/busy-state release and attempt-targeted desktop close ordering.
  Generation/unmount behavior, strict refresh separation, stale replies, explicit
  continuation and browser leave warnings are covered. Mocked DOM/IPC tests do
  not establish native or owner GUI acceptance.
- TypeScript checking and the production Vite build passed. The existing large
  bundle warning remains. `git diff --check` and Python compilation passed.
- Independent read-only review found prebootstrap ownership, historic settlement,
  storage-fault attribution and receiving/recovery UI state defects; corrections
  received the targeted tests above. Review is not a substitute for tests.

Parent-led production-browser inspection subsequently found two stale UI status
presentations: a prior partial-outcome notice remained after continuation, and an
already open Recent imports row retained its prior outcome after completion.
The UI-only correction replaces the historical notice when continuation is
requested and merges each accepted receipt into its matching history row only,
preserving other rows and pagination without extra list fetches. Focused import
component verification passed 20 tests, including pre-acknowledgement notice
changes and poll-driven history updates. Backend behavior and supported-load
evidence are unchanged. The bounded corrected import GUI check passed as recorded
below; broader remaining TT13 and owner acceptance are still open.

The corrected production browser build at
`54152e8251c34822fe81f153f0cd31eb7572f0da` passed the parent-led composed import
check on 2026-10-10, 23:21–23:22 UTC. From a separately seeded partial fixture,
Continue immediately replaced the historical notice and changed the already open
matching Recent imports row to publishing. Releasing the explicitly artificial
supervisor bootstrap barrier produced completed in both the receipt heading and
matching history row without manual refresh. Both original report IDs and the
reserved strategy ID were retained; progress reached 8/8. Publication completion
was briefly visible while the separate execution control still reported
running/staging cleanup, followed by terminal/terminal on inspection. That
transient does not claim reaping or confirmed cancellation before it occurs.
Normal service shutdown visibly completed at 23:22:40 UTC. The screenshot remains
outside the repository; the barrier is private acceptance scaffolding, not a
production hook or an organic slow-disk measurement.

After shutdown, query-only SQLite/file reconciliation of that fixture confirmed
completed/finished receipt and execution, revision 2, both preserved attempt
outcomes (partial/process_restart then completed/finished), unchanged original
ZIP/content identity and all reserved IDs/hashes/counts. Both imported reports
were completed with matching snapshot/result bytes, exact normalized values and
counts, and imported origin. The reserved strategy existed once. Totals were
three runs and two strategies including the original fixture sentinels, zero
native trust, integrity `ok` and no foreign-key violations. No application startup,
retry, financial calculation, backend test rerun or rebuild was used for this
documentation-only reconciliation. This closes the bounded corrected-browser
import check; Windows/native and the remaining TT13 paths stay open.

### Supported archive dimensions and measured responsiveness

The fixture generator streams independently invented numeric normalized series;
these are not padding-only files, market history or executed research. Current
64-MiB ZIP, 128-MiB expanded, 64-MiB entry and eight-run limits were preserved.
The valid eight-run shape uses 17 entries; the nominal 25-entry ceiling does not
require an invalid archive shape.

| Separate dimension | ZIP bytes | Expanded bytes | Largest entry bytes | Normalized rows | Maximum write transaction | Peak parent + descendants RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Near ZIP limit, eight runs | 66,026,635 | 66,023,697 | 8,251,011 | 61,448 | 0.00475 s | 968,687,616 bytes |
| Near expanded limit, eight runs | 28,753,771 | 133,129,105 | 16,639,186 | 123,896 | 0.01252 s | 1,089,069,056 bytes |
| Near single-entry limit | 14,455,343 | 67,039,506 | 67,036,481 | 62,344 | 0.00484 s | 1,020,862,464 bytes |
| Near individual-row limit | 16,782,347 | 67,039,011 | 67,035,994 | 3 | 0.53013 s | 1,454,608,384 bytes |

The final case contains a 67,034,894-byte normalized indicator row of numeric
values. Across this pass, maximum start was **0.00383 s**, status **0.01049 s**,
cancellation acknowledgement **0.00453 s**, and ordinary foreground SQLite write
**0.53141 s**. Expanded-import cancellation reached actual worker quiescence in
**0.02470 s**, then explicit continuation completed with the identical reserved
IDs. Upload chunks, scheduler/status/list navigation, progress and all source/
published hashes were recorded. Every case completed with exact expected row
counts, integrity `ok`, no foreign-key violations, zero source trust and no
worker left owning its workspace. Total case durations were 10.76, 29.77, 10.51
and 11.51 seconds respectively, including upload and inspection.

One initial measurement pass detected an instrumentation defect: this procfs
omits task/children, causing missing RSS samples. Those zero samples are invalid
memory evidence. A bounded corrective pass derived owned descendants from PPid;
the table above is that complete corrected pass. Later narrow control/UI fixes do
not alter the measured bulk parser, staging shape or supported limits. No load
limit or timeout was raised to manufacture a pass. Numerical targets are local
development goals, not cross-platform or all-disk guarantees.

Remaining original TT13 obligations: asynchronous export including download,
shared-history chart integrity/read responsiveness, and local calculation-result
finalization with the combined near-limit M1 gate. No new financial calculations,
exchange acquisition or live/data release were performed. The bounded parent-led production-browser import check passed as recorded above.
Broader acceptance of the remaining TT13 paths, Windows/native and remaining
original research/owner tasks stays open. This entry does **not** mark all TT13
or the original plan done.


## Original-plan TT10 / A2: independent spot passive contracts — 2026-10-10

Implemented the bounded independent profile/assumption contract for linear-origin
Buy & Hold and scheduled DCA. Spot costs, slippage, tick/quantity precision and
quantity/notional limits are explicit, independent inputs. UI metadata loads
from the selected spot snapshot; unavailable metadata remains visible and does
not block strategy review. Manual modeling requires a deliberate source choice,
all values and a note. Copying strategy costs is an explicit one-time action,
recorded as shared numerical assumptions rather than a live inheritance link.
Spot forms and frozen review use percentages consistently with strategy forms;
serialized contracts retain fractions.

The additive validated benchmark document contains versioned execution
assumptions. Full identity includes the independent profile and provenance;
provenance-only changes invalidate reuse. Jobs, worker and archive validation
reconstruct the same contract while retaining `research.benchmark_contract`.
Legacy spot input/document/hash shape is unchanged when the field is absent.
No execution-engine, sizing or cost-math change, dependency, database migration
or product-version change is included; product remains `0.6.0-dev`.

Matching source/symbol/resolution, capital, range and complete spot trade
coverage are required. Leverage/protection policies cannot carry over. Invalid
optional settings and missing counterpart history leave N/A passive rows and
valid strategies runnable. Optional missing-file/empty-evaluation preflight is
row-local; checksum/schema/resource/storage failures and cancellation keep the
global boundary. Later-period freeze and pending-row resume use original spot
costs/precision/provenance and new history without metadata refresh. Saved and
inherited review show these values and the non-equivalent-risk warning; old
records explicitly state that separate provenance was not recorded.

Focused evidence, not a full-suite or native-platform pass:

- Initial backend pass: **42 tests**, **41 passed**, one new fixture failed
  because it incorrectly expected maximum-order limits to reject the whole
  passive purchase. Retained passive scheduling deliberately caps maximum size
  before minimum checks. No implementation math was changed: the corrective
  fixture independently derives quantity 9 / final equity 964 for max quantity
  9, and quantity 8.9 / equity 964.4 for maximum notional 900 at ask 101/bid 99.
- The single corrective A2 pass: **8 tests passed in 9.87s**. Together with
  unchanged adjacent coverage above, **42 distinct backend tests passed**.
  Independent unconstrained fills buy/sell 9.8 units at 101/99 with fees 19.6,
  final equity 960.8; a separate 0.5-tick rounding case yields 101.5/98.5,
  quantity 9.7 and equity 951.5. Minimum limits reject as expected. Checks cover
  missing financial fields, source mismatch, missing/incomplete spot history,
  stale review, actual worker/cache reuse, provenance-only identity, frozen
  later/resume, old/new archive contracts and rehashed provenance tampering.
- Adjacent passing modules: benchmarks, benchmark jobs, library batches,
  library validation, accounting guards, workload admission, source limits and
  the legacy passive archive round-trip. A4 source/prefix accounting remains.
- **30 frontend tests passed across three files in 7.05s**: independent spot
  settings, LibraryResearch and WorkloadSummary. Coverage includes explicit
  copy-only costs, manual fallback, delayed counterpart responses, changed-input
  preview invalidation, saved/legacy provenance and existing cohort behavior.
  An initial 30-test pass preceded the parent review correction to percentage
  input/display; the final pass explicitly proves 0.1% / 0.05% copy display
  serializes 0.001 / 0.0005, and manual 0.2% serializes 0.002.
- TypeScript and production build passed. The existing non-failing large-chunk
  advisory remains. A small isolated synthetic GUI fixture is available via
  `scripts/seed_independent_spot.py`; no public-data research was started.

Independent read-only review prompted worker-side provenance comparison,
malformed optional-profile handling and correction of the metadata helper's
maximum-market-order fallback. Windows/native/live, owner acceptance and
parent-led production-browser inspection remain separate. TT13 and remaining
original research are unfinished; no release, merge or push is implied.


Subsequent production-browser review confirmed saved passive costs 1% versus
strategy costs 2%, equity 960.8 and fees 19.6, inherited frozen later-period spot
costs, and explicit-copy display 0.1% / 0.05% without automatic settings changes.
It also exposed a blocked fresh review whose legitimate missing-mark-coverage
error was not visible at the active action. The correction places one focused,
scroll-into-view alert immediately beside Review, suppresses the duplicate
background alert, discards stale failed responses and clears old preview before
retry. No financial guard or execution assumption was relaxed.

The focused correction passed **25 LibraryResearch tests in 6.98s**, followed by
TypeScript/production build. The new test proves modal alert location/focus,
no false Start, and successful retry after explicitly corrected settings. Its
initial attempt clicked while warmup was still loading; the test was corrected
to wait for the enabled Review action. This brings the frontend evidence to
**31 distinct tests** across the three A2 files; no broad backend rerun was
needed. A separate complete synthetic linear source with matching mark/funding
was added for default Lab history policies. Bounded backend previews establish
one strategy plus two N/A references without independent settings and three
ready rows with them. Existing source snapshots, saved selection and frozen
later-period records remain unchanged. Final corrected production-browser rendering and fresh complete-source preview
were subsequently verified on the corrected production build:

- Selecting the incomplete-mark source produces a visible, focused alert next to
  Review, with no Start action. Selecting the separate complete source permits
  review with one ready strategy and two N/A passive references.
- Selecting the actual matching spot source, explicitly copying 0.1% fee /
  0.05% slippage and reviewing assumptions produces three ready rows. Frozen
  fractions are 0.001 / 0.0005 with `explicit_shared` provenance.
- Manually changing spot fee to 0.2% invalidates Start until assumptions and the
  test are reviewed again; the reviewed fraction is 0.002 with `explicit_spot`
  fee provenance.
- Earlier saved/frozen checks remain unchanged: 1% passive versus 2% strategy
  costs, passive equity 960.8 and fees 19.6, with original spot assumptions
  retained for later-period verification.

No runs or freezes were created during these browser checks. This final update
is documentation only; the verified implementation/build is unchanged, so no
redundant test or rebuild was performed. Windows/native/live and owner acceptance
remain separate; TT13 and remaining original research are still unfinished.


## Original-plan TT10 / A4: modeled work and full-source admission — 2026-10-10

The owner-directed original-plan continuation reopens the remaining substantive
work after the bounded UX candidate. This slice completes only A4: accurate
modeled-work admission plus independent full-source loading limits. A2 independent
spot contracts, TT13 heavy operations/import continuation and remaining research
are separate unfinished work; no extra UI-polish program is implied.

Workload version 2 counts full strategy prefix through exclusive evaluation end,
evaluation-only passive references and zero for unavailable rows, in each row's
actual execution-candle units. The cap stays 2,000,000 with no cache discount.
Independent cases prove 600k prefix + 100k evaluation + two baselines gives
900k / 1.6M for one / two strategies, while three reject 2.3M. The small fixture
is 30 + 18 + 18 = 66, replacing the old 90. Exact-limit/+1 and H1/H4/D1 units
are covered. New contracts freeze the breakdown, workload version and separate
source-load policy. `modeled_minutes` is retained as a compatibility alias.
Legacy snapshots/counts stay unchanged and readable, with explicit legacy UI.
Preview/start exact hashes, runtime-based pending-resume invalidation and
cross-runtime cache separation remain unchanged. Linear-origin passives remain
N/A and the `spot_dataset_id` API is unchanged.

The source guard checks a bounded manifest and every full trade/mark/funding
file before eager decoding, including suffix history outside evaluation. It
checks file hashes, physical counts, footer, schema and row-group size limits,
then aggregate decoded/materialization estimates. Funding dictionary expansion
uses a pessimistic variable-width bound; encoded Parquet bytes alone are not a
safe decoded-size measure. The observation reader shares the lower-level helper.
Full normalized hashes, gap checks, retained indicators and accounting still
apply. See DEVELOPMENT.md for exact limits/formula and their deliberate
conservative refusals. These are admission estimates, not peak-RAM guarantees.
No source is silently truncated and no old snapshot is rewritten.

Verification chronology:

- Initial focused backend pass ran 56 tests: 55 passed; the sole failure was the
  prior accounting assertion explicitly expecting the old 90 workload. Its new
  expectation is independently derived as 66; no financial expectation changed.
  Modules: workload admission, source limits, library batches, coarse research,
  benchmark jobs, library validation, accounting guards, data, observations and
  library. Existing future-perturbation and coarse accounting evidence passed.
- Independent read-only review exposed funding dictionary expansion. The guard
  was tightened before completion; tests include a repeated 8,192-byte string,
  all-table rejection before any eager read, mark/funding schema/count checks,
  aggregate boundaries and manifest/file/footer/group/materialization limits.
- The single corrective focused pass passed **36 tests** in 14.14s across
  `tests.test_workload_admission`, `tests.test_source_limits`,
  `tests.test_library_batches`, `tests.test_accounting_guards` and
  `tests.test_observations`. It includes normalized checksum rejection after a
  valid physical-hash update, genuine populated-cache workload equality, and
  saved indicator/trade/metric parity with the retained full-prefix calculation.
  Combined with the unchanged adjacent tests above, this is **60 distinct
  backend tests**, not a full-suite pass on the new implementation.
- Final frontend pass passed **37 tests across three files**:
  `WorkloadSummary.test.tsx`, `LibraryResearch.test.tsx`, `UserJourneys.test.tsx`.
  `node scripts/frontend.mjs build` passed TypeScript and production build; the
  existing non-failing large-chunk advisory remains. The earlier 413-test UX
  aggregate does not validate these new backend changes.
- A bounded Linux calibration using `scripts/measure_source_load.py` loaded
  30,000 trade + 30,000 mark + 63 funding rows in **0.2646s**. Measured-process
  peak RSS was **144,164 KiB**, with pre-load high-water **73,188 KiB**.
  Fixture generation ran in a separate sibling subprocess and is excluded;
  interpreter/imports are included. An earlier harness inherited the generator's
  high-water mark and was corrected before reporting this evidence. This small
  fixture calibrates behavior, not the largest source or a universal memory cap.

Read-only review found no remaining blocker after the expansion correction.
No new dependencies, database migration, product-version bump, numerical engine
change or strategy/benchmark-profile change is included. Production-browser
inspection, native Windows, largest-load status/cancel latency, remote CI and
owner acceptance remain separate. Local commit is an engineering checkpoint,
not merge/release permission.

Subsequent production-browser inspection on the restored synthetic hourly source
confirmed **168 executions = 120 strategy (96 prefix + 24 evaluation) + 24 Buy &
Hold + 24 DCA**, with the separate source-loading details visible. No Start action
or new run occurred. Inspection found a presentation-only defect: the workload
headline and following explanation were inline without a separator. An explicit
line break now separates both current and legacy headlines from their explanation;
nearest component assertions cover that separator. This does not change the
backend, frozen contract or numerical evidence above. The same browser inspection
reopened the original linked-observation comparison with its exact **1,872 legacy
workload count**, unchanged historical explanation and no recomputation or new
run. After confirmed host shutdown, the separator correction passed all **three
WorkloadSummary tests** and TypeScript/production build; the existing chunk-size
advisory remains non-failing. No backend rerun was needed for this JSX-only fix.
A subsequent production-browser check confirmed that the saved **1,872 legacy**
headline and explanation are visually separated. The **168-execution preview**
was verified in the earlier inspection; only the text separator changed. No new
run was started during the final separator check.



## Final bounded UX candidate verification — 2026-10-10

Final corrected source is `cfe60f62ff9ba6f866219c80cc2fafbccea0b426`, tree
`3c5e8fda136e0e9a2f2f6217f5fde4d53724519a`; the subsequent checkpoint update
changes documentation only. The pre-focus-correction code checkpoint is `ace120c3b14e6a77bec2fb5f738fcc191d8e67c1`, tree
`ce8aea0dfcd0d2c9a0b4bbac308cb111c5f364bc`. One closure aggregate passed
**413 frontend tests across 45 files in 12.87s** with
`node node_modules/vitest/vitest.mjs run`. Final TypeScript and production build
passed with `node scripts/frontend.mjs build`; the existing large-chunk advisory
remains non-failing. This aggregate includes the final frozen-default equity
correction and the saved-filter clarity slice. It supersedes the earlier
399-test/44-file frontend aggregate for unchanged surfaces without erasing the
slice-level correction chronology. The subsequent composed browser inspection
found an asynchronous freeze-review focus defect: disabling the origin while
reading overlap caused Cancel to return to the document body. EvidenceFreeze
now captures that exact origin before the read and passes it explicitly to the
existing dialog surface. Ordinary dialogs retain their default active-element
capture; disconnected/hidden origins are skipped, and another open dialog keeps
its focus. Preview, freeze and execution semantics remain unchanged.

Post-correction focused evidence covers **48 distinct tests across four files**:
EvidenceFreeze, LibraryResearch, DisplayedEvidence and UserJourneys. The first
pass had two harness failures because jsdom would not blur a disabled element;
the fixture now explicitly models lost body focus. The next pass passed 47 tests
with one harness failure because Testing Library has no `fireEvent.cancel`
helper. The supported cancel Event correction then passed the single Escape
regression (one passed, four intentionally skipped), with assertions and product
code unchanged. No additional full aggregate was run. Final TypeScript/production build
passed on the corrected source. These targeted passes preserve the earlier
413-test aggregate as pre-focus-fix evidence rather than claiming a repeated full
suite.

Only frontend and documentation files changed after the preceding checkpoint.
Backend, accounting, persistence, schema and dependencies remain unchanged;
retain the verified **327 backend passes and eight Windows-only skips** rather
than claiming another backend or storage crash-suite run. Composed browser checks
before the focus correction confirmed exact observation revision 1 and its
January 5–January 13 04:00 UTC period through Lab and Return; Lab search and saved
return ordering retained the 1h/group-2 comparison; Compare equity and Back
retained the chosen row. Later-period setup → prepare history → Data → Use this
history preserved source and January 27–February 7 12:00 UTC dates. Overlap review
showed the recorded warnings; neither Confirm candidate freeze nor Start was
activated. Corrected production-browser inspection then passed both Cancel
freeze and physical Escape: each returned focus to the exact originating Freeze
later-period candidate button with zero dialogs left open. The existing RSI
report reopened with 44.16 net PnL, 1.85% maximum drawdown and one trade. The
composed Market observation → exact Lab source/revision → Saved tests → equity →
later-period data preparation → review/cancel journey completed without new
runs or freezes. These are actual browser interactions on the corrected build;
component-injected transport failures and races remain separate evidence. Current Windows/native, live-feed, remote CI and owner-led
unaided acceptance remain separate; this is a development candidate, not a
release or merge approval. No further feature work is included in this gate.


## Saved-test filter outcome clarity — 2026-10-10

The Saved tests table now has a concise, polite live summary derived from the
same filtered rows that render in the table. Valid numeric thresholds distinguish
matching strategy rows, context-only strategy rows and passive reference rows.
Zero numeric matches are explicit even when context and baselines remain visible.
Counts describe rows/variants, not distinct strategies or profitability. Blank or
invalid thresholds say only how many strategy rows are shown; unavailable or
failed rows are never described as numeric passes in that state. The existing
invalid-input error and all-or-nothing numeric-filter fallback remain unchanged.

Family, timeframe, result-state and review filters still narrow strategy rows;
baselines stay visible regardless. Context with missing required metrics or an
unfinished result remains separate from matches. The summary stays outside the
collapsed controls and labels the keyboard-focusable results region. Filtering,
cohort sorting, frozen holdout order, metrics, equity inspection, run actions and
display-evidence recording are unchanged. No backend, schema, dependency or
product-version changes were made.

The focused pass passed **57 tests across five files** with:
`node node_modules/vitest/vitest.mjs run frontend/src/SavedFilterSummary.test.tsx frontend/src/LibraryResearch.test.tsx frontend/src/SavedReview.test.tsx frontend/src/DisplayedEvidence.test.tsx frontend/src/EquityComparison.test.tsx`.
Coverage includes zero/negative finite boundaries, all strategies excluded,
retained passive references, missing/nonfinite metrics, combined category filters,
invalid/blank numeric inputs, holdout order, accessibility wiring and explicit
clear without execution or data writes. The initial build exposed a test-only
TypeScript inferred-union mismatch; an explicit filter-record type corrected it.
Final TypeScript/production build passed with `node scripts/frontend.mjs build`,
retaining the existing non-failing large-chunk advisory. This focused pass does
not replace the preceding 399-test/44-file aggregate or claim a backend rerun.
Independent read-only review found no blocker. Production-browser inspection
passed at **750px** width using an existing saved comparison: blank filters showed
14 strategy rows and two passive references; an extreme minimum return showed
zero matches, two context-only rows and two passive references. Adding the
mean-reversion family showed zero matches/context with both references retained,
and the explanation wrapped readably above the table. With the return blank,
an invalid negative minimum-position threshold retained the existing error and
neutrally counted four category-filtered strategy rows and two references.
Combined family/1d/incompatible-state filters showed the category-empty explanation
and both passive references. Clear restored all 14 strategy rows and two references.
No new runs or data were created; the host was stopped normally. Ordinary-width
inspection was not repeated for this slice. Current Windows/native and owner-led
unaided acceptance remain separate.


## Explicit saved-equity inspection — 2026-10-10

Compare equity now opens and focuses a named inline inspector for the exact
saved comparison row. It retains the strategy name, timeframe, comparison group,
original period/capital/source resolution and an expandable saved parameter,
catalog-version and run-identity disclosure. Resolved parameters come from the
frozen row contract, including defaults omitted from selection overrides. Older
rows without that contract explicitly label their saved overrides as incomplete;
current catalog defaults are never substituted. Current Lab edits do not replace
that captured identity. Back to result closes inspection and returns keyboard
focus to its original action, or the results table if filters removed that row.

Equity reads have independent loading/error/explicit-retry state. They do not
invoke the shared execution action or refresh comparison history. A new chosen
row clears the previous curve immediately; request cleanup rejects late success
and failure after row changes, close/reopen, batch switches, route suspension or
unmount. Retry keeps keyboard focus in the inspector. Returning to a route does
not reopen or reread a dismissed inspection. Existing sampled curves, saved
metrics, passive N/A states and risk/sampling caveats remain unchanged. No new
display-evidence surface, backend/schema, accounting or dependency is added.

The initial focused pass passed 46 adjacent tests and seven of eight new equity
tests; the remaining test used an unavailable matcher rather than exposing a
product defect. After the assertion correction and two independent review
improvements, all eight equity tests passed. The complete frontend pass before the browser-discovered parameter-display
correction passed **399 tests across 44 files in 12.51s** with
`node node_modules/vitest/vitest.mjs run`. Final TypeScript/production build
passed with `node scripts/frontend.mjs build`; the existing large-chunk advisory
remains non-failing. Browser inspection then identified a real empty-override
fixture whose resolved defaults were available only in the frozen contract. The
corrected display and two added regressions passed **10 focused equity tests**;
the preceding aggregate remains evidence for unchanged adjacent behavior.
The corrected final TypeScript/production build also passed. Independent
read-only review found no remaining blocker, including the parameter correction.
Unchanged backend evidence is retained rather than rerun. Current Windows,
live-feed, owner-led usability and remote CI acceptance remain separate.
Production-browser inspection passed at ordinary and **750px** widths. Explicit
Compare equity scrolled/focused the named panel; Back returned to the exact
originating action, including keyboard Enter. Distinct 4h/1d variants retained
their identity, Lab/Saved tests navigation dismissed inspection, and repeated
activation showed one current panel. The final build displayed actual frozen
resolved defaults rather than an empty override list. At 750px, viewport and
document width were both 750px; the graph, legend and caveat stayed reachable.
The host was stopped normally afterward. These checks did not start a test,
freeze a candidate or prepare new data. Slow/error/retry/stale-response races and
filtered-trigger fallback remain component evidence, not actual browser fault
injection. Existing display-evidence limits and native acceptance remain separate.


## Explicit chart-to-observation period capture — 2026-10-10

Saved history adds explicit Set observation start/end actions for unsaved notes.
Clicking a valid-price candle in either pane or using keyboard candle navigation
pins its inspection while moving to the buttons. Hover remains transient when
unpinned; gap clicks and Clear candle selection remove actionability. A start
uses the exact opening and an end the exclusive close; complete aggregates use
the whole UTC display bucket. Invalid-price or incomplete slots cannot supply
dates; unavailable volume does not invalidate an otherwise valid price candle.

Only the chosen endpoint changes. Reversed/empty periods remain visible with
existing validation and cannot save until corrected. Saved latest/historical
revision dates stay immutable and require explicit New observation. Note text,
browse page/date and Lab settings remain separate. Activation checks current
visibility before scheduled offscreen clearing, then live page/source/display
identity, epoch and note/action locks. Pinning and boundary actions add no
read, automatic save, execution or display-evidence write.

The focused pass passed **113 tests across six files**: ObservationChart,
ObservationBoundaries, Observations, ObservationsNavigation, DisplayedEvidence
and UserJourneys. The command was
`node node_modules/vitest/vitest.mjs run frontend/src/ObservationChart.test.tsx frontend/src/ObservationBoundaries.test.tsx frontend/src/Observations.test.tsx frontend/src/ObservationsNavigation.test.tsx frontend/src/DisplayedEvidence.test.tsx frontend/src/UserJourneys.test.tsx`.
TypeScript and production build passed with `node scripts/frontend.mjs build`;
the existing large-chunk advisory remains non-failing. This is focused frontend
evidence, not a new full regression claim. Backend, storage, accounting and
native trust were unchanged; the preceding integrated evidence remains applicable.

Production-browser checks passed at **1180×757 and 750×757** using isolated
synthetic history. A real 4h price-pane click retained its pin after pointer exit
and scrolling; Set start copied January 6 at 20:00 UTC without moving the opposite
endpoint. A volume-pane click at January 13 00:00 followed by Set end copied
04:00, the exclusive close. An empty 04:00–04:00 period retained both inputs,
showed inline validation and blocked Save. Home followed by Tab navigation and
Enter activated the start action. Display changes cleared eligibility without
changing dates/text, and Lab/Market return retained the draft.

One new synthetic observation was explicitly saved for January 5 00:00 through
January 13 04:00 UTC; its Lab attachment retained exact source, revision and dates
without Review/Start. Saved date actions were disabled. New observation followed
by a daily gap click cleared eligibility and showed 23/24 coverage; a complete
January 3 daily candle supplied January 4 00:00 as its exclusive end. Clearing
selection retained the date inputs. Existing fixture observations were not edited.
Stale-callback/failure races and exposure-write counts remain component evidence;
the browser checks do not independently establish those counts. Current Windows,
live-feed and owner-led unaided usability acceptance remain separate. See
[ADR 0033](adr/0033-local-history-observations.md) and the
[research workflow](RESEARCH.md) for the explicit interaction and safety limits.


## Durable archive import inspection — 2026-10-10

Archive imports now have a durable local operation identity before upload-file
creation, complete output-ID reservation before artifact writes, atomic per-run
publication/receipt updates and insert-only strategy/terminal completion. The
additive receipt ledger preserves intended mappings across lost replies and
process interruption. Startup reconciles metadata only; no upload is resumed,
artifact promoted, source executed or trust/admission granted. Old imports remain
untracked. See [ADR 0008](adr/0008-archives-comparison.md).

The UI adds explicit operation inspection and paged Recent imports under Project
archive. Only published/currently completed reports are openable; incomplete
members remain distinct. Strict import-only refresh/open callbacks retain a
completed receipt when list, run-history or strategy reads fail. Ownership checks
after awaits prevent late import/open/cancel responses from replacing newer
receipt selections or editor drafts. Targeted cancellation rejects null/empty IDs,
ignores stale valid targets and refuses cancellation after the one-shot finish
claim. No automatic POST/import retry or global action/native Rust change is added.

Storage-first verification used two independently different synthetic results and
existing run/strategy sentinels. It covers reservation rollback/post-commit error,
UUID/row/orphan/strategy collisions, before/after snapshot/result publication,
partial SERIES rollback, joint run/receipt and strategy/terminal commits, failed
failure-record persistence, malformed/inconsistent metadata, zero/eight-run
archives, content identities, deliberate duplicate imports, advisory data lookup
failure, pagination and read-only repeated inspection. Real subprocess kills at
reservation, snapshot, first-run and terminal boundaries check exact destination
mappings, expected hashes, materialized bytes, normalized rows/counts, origin,
trust/admission and unchanged sentinels after restart. Query-only connections
reject any inspection mutation.

One integrated Linux backend run passed **325 tests with eight Windows-only skips**
(333 total) in 115.778 seconds. This run preceded the final narrow operation-ID
collision, duplicate-claim and explicit targeted-cancel validation corrections.
After those corrections, the affected archive/receipt/real-HTTP/storage-quarantine
pass passed **46 tests** in 5.074 seconds. A later final integrated regression on
the final backend source passed **327 tests with eight Windows-only skips**
(335 total) in 120.518 seconds, including those guards and both full closed-workspace
backup/restore tests. These final totals supersede the earlier pre-correction pass
for this candidate. Existing accounting, native trust and worker completion
contracts were not changed.

The final affected frontend pass passed **20 tests across three files**:
ProjectTransfer, ImportRecovery and AppImportRecovery. It covers exact File bytes
and chunk order, discarded reply → read-only inspection, recent-list/reload
recovery, partial report opening, unavailable/stale reads, separate persistence/
opening errors, strict run-history failure propagation, cancellation cutoff,
unmount and late editor reads, receipt-switch opening state and stale cancellation
feedback, explicit UTC receipt timestamps and visible imported provenance in the
main report view. The earlier API/AppStorageSafety/UserJourneys focused checks passed
**25 additional unchanged tests**. Initial test corrections fixed an empty-series
fault injector and an incorrect navigation label; later review findings added
explicit regressions. TypeScript and the production frontend build pass, retaining
the existing large-chunk advisory. The final complete frontend suite subsequently
passed **377 tests across 42 files** in 12.85 seconds on the final UI source,
including the later date-navigation and receipt slices. Simulated-DOM evidence is
not native acceptance.

A real local HTTP test discards a final response only after the ordinary handler
has committed completion. A deterministic publication barrier confirms status
cannot be served concurrently by the serialized server; after release and service
restart, inspection returns the same operation/destination IDs with unchanged
run counts. This is bounded automatic HTTP evidence, not a current browser File
upload or maximum-admitted-archive timing measurement. A separate single observed
backend finish for the 7,977-byte, two-run synthetic ZIP took 0.0074 seconds on
this Linux filesystem. It excludes startup/upload/HTTP/UI and does not establish
maximum-load latency, throughput or deadline safety.

A consistent full copy of an existing closed synthetic workspace preserved all
**26 preexisting tables and 41 non-database files** across two clean service
lifetimes. Six completed reports, two datasets and three saved observations
remained readable offline; SQLite integrity/foreign keys and every completed
result hash passed. Only the two empty receipt tables were added; the source was
unchanged. Separately, a complete and interrupted receipt workspace survived full
backup/restore with only documented interruption metadata transitions and no
resume. No ordinary user workspace was migrated or fault-injected.

Production-browser read-only receipt checks passed at 1180px and 750px widths.
Completed/partial/interrupted operations retained exact IDs across an actual
service restart. Partial exposed only its first published report; interrupted
exposed no report-opening action; completed exposed both reports and its saved
strategy. Explicit opens displayed the expected records without execution.
Receipt timestamps now show UTC, and a directly opened imported report has its
unverified/imported-origin warning in the main view. Repeated Refresh retained
the mapping and narrow-width wrapping remained usable.

Post-close read-only SQLite reconciliation preserved every operation/item field,
all seven run IDs and both strategy IDs: three receipts, nine items, zero native
trust and only two research coverage markers. The six published imported artifact
files match the hashes recorded in the pre-GUI receipt baseline, and normalized
series counts match. No full pre-GUI filesystem inventory was captured, so this
is not a claim that every workspace file received a before/after comparison.

An actual production-browser upload in a separate synthetic workspace then lost
its final HTTP reply after real completion. The UI retained the operation identity
and offered inspection without another upload. Inspection returned both completed
reports and the strategy with their exact destination IDs; explicitly opening the
second report displayed its independently expected 1.00 net PnL and imported
warning. A final message correction replaces the obsolete lost-response error with
the confirmed receipt outcome; its 11-test ImportRecovery recheck and TypeScript/
production build passed. An ordinary service restart returned the same operation,
two report IDs and strategy ID; the final confirmed-outcome message was visible,
and explicit strategy opening loaded the saved graph without execution. The
warning-clear transition itself has focused component coverage; the final browser
check reused the existing receipt rather than performing a second lost-reply upload.

Read-only post-close reconciliation against the original partial receipt and the
completed receipt captured before response loss preserved all operation/item
metadata and the exact five run/two strategy IDs. There were exactly two receipts
and six items, zero trust records and only two research coverage markers. Published
snapshot/result bytes matched receipt-bound expected hashes; normalized counts,
SQLite integrity and foreign keys passed. No second import was created by inspection,
opening or restart.

Finalization stays synchronous; no responsive in-flight status, maximum-load
deadline safety, artifact-file verification by the UI, power-loss durability,
Windows/native timeout-close recovery or owner-led acceptance is claimed. Receipt
inspection and ordinary report opening always expose artifact verification as not
checked. Native failed-transport close remains a separate follow-up.


## Independent saved-history date navigation — 2026-10-10

Saved history now has an independent **Go to UTC date** draft, explicit Go,
First/Latest pages and Return to observation start. Exact native opening times
are parsed as literal UTC with calendar round-trip validation. Invalid,
misaligned and exclusive-end targets retain the loaded chart and never issue a
read. First/Latest are anchored to 500 source slots from the saved range start;
an arbitrary jump retains its exact opening and relative Earlier/Later behavior.
The display aggregation interval never changes request bounds. Missing openings
and all-gap pages remain successful local reads with explicit explanations.

Accepted replacement reads remove the old chart/inspection immediately. A
separate failed-page state owns the exact dataset and half-open boundaries;
Retry ignores a subsequently edited date draft and repeats only that local read.
It does not retry note saving or observation-list recovery. Epoch, cleanup and
selected-declaration checks discard stale success/error/finally callbacks, and
response dataset/window and established exact-source identity are checked before
rendering. Source-unavailable state survives New observation, and note save
responses also reconcile source identity/availability. Same-ID replacement is
never silently accepted during ordinary paging. Source change/reopen is explicit.

The existing note range, revision, text, source locks and Lab handoff are retained.
Dirty notes and invalid observation dates do not block independent browsing.
Ordinary route return retains the browse draft and display choice; an explicit
exact-revision reopen returns to that observation start. No backend/schema,
strategy, accounting, API transport, dependency, version or new persistence path
changed. Existing actual-visible-chart `research_displayed` recording and its
constituent mapping remain active; typed/failed/stale targets never reach the
chart. No prefetch, live request, automatic retry, bookmark or full-source read
was introduced. The existing checksum/prefix reader is not constant-time.

Focused evidence covers **155 distinct tests across seven files**. The first
coherent pass passed **154 tests** in `observationNavigation`,
`ObservationsNavigation`, `Observations`, `ObservationsHistory`, `UserJourneys`,
`DisplayedEvidence` and `ObservationChart`. Review then retained unavailable-source
state from save responses and tightened exact First/Latest-page matching. The
affected five-file follow-up passed **96 tests**, including one added regression;
59 unchanged pure-boundary/evidence tests were reused. No full frontend/backend
suite was rerun. Tests use deterministic UTC/source-slot expectations, deferred
responses and simulated DOM/mocked IPC. An actual ObservationChart component
asserts that a scheduled old visibility callback is disposed at submission and
that successful retried aggregate visibility records only the complete source
constituents of its exact replacement page.

TypeScript and the production build passed on the final implementation with the
existing large-chunk advisory. An intervening fixture-only callback cleanup was
caught by TypeScript and restored before that final successful build; no runtime
change was needed. Reproduce the focused pass with the
[navigation checks](DEVELOPMENT.md#saved-history-date-navigation-checks).

Production-browser inspection passed at **1180×757** and **750×757** using the
existing isolated 900-hour synthetic source and its gap variant:

- Latest loaded January 21 20:00–February 7 12:00 UTC, exactly 400 source slots.
  Enter on January 15 03:00 loaded that exact opening through February 4 23:00,
  exactly 500 slots, without changing the observation range.
- February 7 12:00 (exclusive end) and a 03:01 misaligned opening were rejected.
  First remained usable with an invalid draft and retained 4h display. The last
  valid February 7 11:00 opening produced a one-candle page; Home inspection
  showed that exact opening.
- The gap source jump to January 2 00:00 loaded 499 recorded candles with the
  direct missing-requested-opening explanation. No later candle was implicitly
  selected or fabricated.
- A saved January 26–27 revision-2 note retained its unsaved text, exact dates,
  revision and 4h display through a January 15 jump, Return to observation start
  and ordinary Lab/Market returns. The temporary text edit was explicitly
  discarded without saving. Returning from a linked test to historical revision
  1 and then navigating Latest retained locked notes.
- Controls wrapped and remained reachable at both widths with no horizontal
  overflow. At 1180 pixels, the content client/scroll widths both measured 1165
  pixels. Tab moved from the UTC input to Go, Shift+Tab returned, and Enter kept
  focus in the input. No Save, Review or Start action was initiated.

Controlled read failure/retry, races and persisted exposure counts remain
component evidence; the production browser pass did not inject a transport
fault or recount database writes. Current Windows/native, live-feed/reconnect
and owner-led unaided acceptance remain separate.

## Natural Lab catalog scrolling — 2026-10-10

Desktop Lab now uses the existing outer content region as one scroll surface.
Heading, search, ordering and current test context can scroll out of view so
complete card actions and expanded parameters can occupy the working area.
Three Lab-only desktop overrides remove the inherited hidden outer/body overflow
and full-height inner grid scroller. The card grid keeps its focus-outline
padding and natural row height. Narrow single-column rules and Saved tests
layout are unchanged. The two mounted views retain independent in-memory scroll
offsets; restoring a view does not move keyboard focus or recreate cards. Hidden
route scroll events cannot replace those offsets. This is session-local view
state, with no storage, API call or persistence promise after reload.

The pre-change production-browser baseline at **1180×757**, without a selected
comparison, measured a 551-pixel outer content region with hidden overflow,
a 239-pixel clipped body and a **161-pixel card scroller** containing 1,452 pixels
of content. At **750×757**, the existing outer scroller measured 550 client /
3,522 scroll pixels; body and grid used visible overflow, the grid was 2,988
pixels high, and no horizontal overflow was observed. These are direct browser
measurements, rather than the earlier approximately 180-pixel comparison view.

The initial focused pass passed **33 tests across four files**:
`CardOrdering`, `StrategyLibrary`, `UserJourneys` and `DisplayedEvidence`.
Existing checks cover retained card identity, parameter/timeframe drafts,
inclusion, saved ordering, catalog-order Test all requests, explicit setup and
dialog focus return, plus finite visible metric recording and hidden/offscreen/
modal exclusions. `node scripts/frontend.mjs build` passed TypeScript and the
production build with the existing large-chunk advisory. These checks use
simulated DOM/mocked IPC and do not establish browser geometry.

The first production-browser check confirmed the desktop change: the outer
region remained 551 pixels high with 1,843 scroll pixels and automatic overflow;
the body and grid used visible overflow with natural heights of 1,530 and 1,452
pixels. Wheel scrolling exposed expanded EMA parameters; editing fast from 15
to 16 and including the card retained the draft. It also reproduced a route
regression: the shared outer element returned from Saved tests at zero instead
of the prior 465-pixel Lab offset. The bounded correction adds only independent
catalog/saved offsets and restore-on-reappearance handling. Its focused
`StrategyLibrary` / `UserJourneys` pass passed **19 tests**, including the new
offset/hidden-route/card-retention regression. TypeScript and production build
passed again with the same advisory.

Final production-browser checks passed at **1180×757** and **750×757**. The
wide outer/grid measurements remained 551 / 1,843 and 1,452 pixels. After editing
EMA fast to 16 and including it, Saved tests-to-Lab returned to the exact prior
465-pixel offset with both changes retained. Market-to-Lab retained the later
246-pixel offset. Escape from setup returned focus to the actual card trigger.
A saved comparison's return ordering applied its unique 1h / Group 2 context
while preserving the edited draft and inclusion. With an EMA search showing
only two cards, Test all still showed **14 tests / 7 strategies / 2 timeframes**;
Escape returned focus to Test all. No Review or Start was initiated.

At 750 pixels, the content's client and scroll widths were both 735 pixels,
with no horizontal overflow. The expanded EMA parameter view returned from
Saved tests at its exact 679-pixel offset. Tab moved from fast to slow and
Shift+Tab returned to fast; Escape from narrow setup returned to the EMA trigger.
Independent source review found no additional layout, lifecycle, state or
display-observer blocker. Browser layout/navigation checks did not recount
persisted display events; existing component coverage remains that evidence.

After the browser correction and acceptance, one combined final frontend pass
(`node node_modules/vitest/vitest.mjs run`) passed **285 tests across 38 files**
in 11.31 seconds. It includes the prior chart/display, ordering, saved-review
and observation slices plus this scroll-retention regression. The final code's
TypeScript/production build had already passed; only documentation changed
after that build and the browser check. This is frontend regression evidence,
not a new backend or Windows/native acceptance total.

No backend, schema, accounting, immutable results, data, strategies, API,
dependencies or product version changed. Unchanged backend evidence was reused.
Current Windows/native and owner-led unaided usability acceptance remain
separate.

## Saved-history display intervals — 2026-10-10

Saved history now defaults to exact native Source candles and supports compatible
local 1h/4h/1d display projections, omitting the native duplicate. The selector
never reads or prepares more data. Each complete UTC bucket uses every expected
source opening exactly once and lies wholly inside the verified loaded page.
OHLC uses first/max/min/last; volume sums recorded values without inferring units.
Zero, unavailable volume, non-finite sums and invalid price remain distinct.
Malformed timestamps fail closed visibly. Incomplete and wholly missing buckets
remain whitespace in both synchronized panes, with striped bands and inspectable
missing-versus-outside-page counts, never partial OHLCV.

The inspector separates display and source intervals, opening/exclusive closing
times, source coverage and contributing opens. Keyboard navigation skips
incomplete/unavailable candles, reveals an offscreen target before inspection,
and retains the prior pointer/synthetic-redraw lifecycle correction. Page/source/
display replacement clears selection and listeners. Display choice survives
same-source paging and Market/Lab return, but a different verified source identity
resets it even when the dataset ID is unchanged. Source-aligned observation dates,
unsaved text, locked historical revisions and selected Lab strategy timeframes
are unchanged.

All displayed aggregate constituents map back through the existing verified
reference to separate inclusive source-opening viewports. The final constituent
is included and valid rows hidden in an incomplete aggregate are excluded.
There is one actual-visibility observer for both panes; hidden, offscreen,
background and modal-covered surfaces do not record. Hover deduplicates, and
pending-budget overflow retains the existing visible incomplete-tracking warning.
Shared RunChart close-label semantics and the backend recorder are untouched.

The 500-source-slot page/read bounds remain unchanged. Finer, non-divisible or
over-budget choices show explicit reasons. Daily display from one-minute source
needs 1,440 slots and is unavailable. Adjacent pages are not prefetched or
stitched: a 500-slot boundary can leave a UTC bucket incomplete on both pages.
A compatible choice remains selected with an explanation when no complete bucket
fits. Completeness concerns the selected snapshot/page, not market completeness
or human reading. No new backend/schema, live/network route, accounting,
dependency, strategy or product version is introduced.

Focused automated evidence covers **106 distinct tests across five files**:
`observationChartData`, `ObservationChart`, `Observations`, `DisplayedEvidence`
and `UserJourneys`. The initial pass had 103 passes and one new test that queried
a prior chart before its asynchronous reopen finished. After fixing that wait,
the two-file ObservationChart/Observations corrective pass passed **53 tests**,
including added same-ID exact-source reset and already-full pending-budget
regressions. The other three files' 53 passing tests were not repeated.
Initial production-browser inspection exposed a pre-existing striped-band
rendering defect: the pinned chart API returns coordinate zero for fractional
logical indices, unlike the earlier test mock. Bands now derive their edges
from adjacent integer centers in the full slot list, including whitespace and
single-slot pages. The corrected real-API mock and chart-only pass passed all
**23 tests**; an explicit single-incomplete-slot width assertion also passed in
its focused check. TypeScript and the production assets were rebuilt after the band correction.
Independent expectations cover native identity, four-hour and UTC month-boundary
daily OHLCV goldens, complete source evidence through the last constituent,
incomplete/missing/edge buckets, duplicates/alignment, invalid values, budget
limits, future perturbation, visibility/cleanup, retained context and no extra
reads/mutation calls. TypeScript and the production Vite build passed, with the
existing large-chunk advisory. These are pure/component/App tests using simulated
DOM and mocked chart/IPC, not a new full-regression total. Reproduce with the
[focused commands](DEVELOPMENT.md#saved-history-display-projection-checks).

Corrected production-browser inspection passed at **1180px and 750px widths**
using the existing isolated hourly synthetic sources:

- The first 4h bar showed O100/H105/L99/C103.5 and volume 40; the first full day
  showed O100/H125/L99/C123.5 and volume 240. Source/4h/1d changes and page
  navigation retained the documented values and reset stale inspection.
- Daily display survived Later navigation. The next page's leading January 21
  bucket explained 4/24 retained source slots, zero missing and 20 outside-page
  slots. It remained whitespace rather than an invented partial daily candle.
- The January 2 daily gap explained 23/24 source coverage, one missing and zero
  outside-page slots. Home then Right skipped that incomplete day; clicking its
  whitespace displayed the explanation. After the correction, striped bands
  were visibly present across both price and volume, in Source and daily modes,
  at both widths. A clipped page-edge band also remained visible.
- Home/End/Right navigation, page selection reset and source reset passed.
  Ordinary Market/Lab/Market navigation retained daily display and the exact gap
  source. No new history, note or strategy run was created for this check.

The browser pass did not recount persisted exposure writes; constituent mapping,
visibility suppression and bounded failure behavior remain component evidence.
Locked exact-revision return, non-display-aligned dates and independent Lab
strategy/timeframe preservation are covered by the focused App/component tests.
Existing backend, RunChart and live evidence are reused rather than rerun;
owner-led unaided usability and current Windows/native acceptance remain separate.

## Saved-comparison card ordering — 2026-10-10

Lab cards now support Name A–Z/Z–A and bidirectional saved period-return,
drawdown and completed-position ordering. The selected comparison's saved name
or short identity and exact UTC evaluation interval remain visible. Numeric
ordering requires an explicit saved timeframe and compatible cohort; only a
unique available choice is filled automatically. Cohort numbering uses the full
sorted saved cohort-key list, matching the Saved tests table. Group labels show
market/instrument, source/execution resolution, capital and model version.
Secondary comparison/timeframe/cohort controls use a compact native disclosure.
Its closed summary keeps the applied context and exact UTC period visible beside
the metric/direction controls. Missing choices open it automatically; completing
a choice leaves keyboard focus visible until the user closes the summary.

Ranking uses only that comparison and an exact catalog ID/version/timeframe/
cohort match. Multiple frozen parameter variants stay ambiguous, including a
completed variant alongside a failed or pending one. Missing, incompatible,
unfinished and non-finite results retain specific N/A reasons and sort last in
both directions. Losses and zero remain valid; ties use deterministic name and
identity order. Passive baselines and later-period verification never become
selection-card scores. Existing historical rows remain visible, and the exact
ranked row shows its saved timeframe/group, metric and completed positions.
Changed draft inputs retain the prior-run warning rather than changing the
saved evidence being ranked.

All cards retain stable identity keys and remain mounted under filtering.
Selection payloads use original catalog order, independently of presentation
order or inclusion timing. Test all still includes the complete catalog with
each card's current parameters and the shared batch timeframes. Sorting neither
invalidates an already reviewed draft nor starts, copies or trusts a strategy.
Saved tests/Lab navigation preserves view and draft state; only a different
comparison identity resets saved timeframe/group context, including a route
through an excluded later-period report and back to the original comparison.

Finite card summary return/drawdown/position cells and ordering badges reuse
`comparison_metrics` display references; the older expanded source/details
metrics are not separately instrumented. New finite cells rebind observers
without replacing the existing presentation recorder. Metric changes and direction changes keep badge DOM
identity; hidden/filter-excluded, offscreen and modal-covered values do not
record exposure. Lab now presents the existing tracking-failure notice visibly.
No backend/schema, strategy, financial calculation, saved artifact, dependency
or product-version changes are included.

Focused automated evidence covers **70 distinct tests across six files**:
`cardOrdering`, `CardOrdering`, `StrategyLibrary`, `LibraryResearch`,
`DisplayedEvidence` and `UserJourneys`. The initial focused command passed 67
tests with one failure in a new App fixture that omitted its asserted net PnL.
After supplying the independently specified fixture value, all 11 UserJourneys
tests passed. Review then tightened recorder stability for metric availability
changes and added a direct regression; the final two-file CardOrdering /
DisplayedEvidence pass passed **14 tests**. A browser-discovered overly tall
control panel was then compacted, and strict selection-to-holdout-to-selection
identity reset was added. The final CardOrdering / LibraryResearch /
UserJourneys pass passed **40 tests**, including disclosure/focus preservation
and holdout exclusion/reset. Unaffected passing files were not repeated.
These are pure, component and App-integration checks with simulated
DOM/mocked IPC, not a new full-regression total.

`node scripts/frontend.mjs build` passed TypeScript and the production Vite
build, retaining the existing large-chunk advisory. Unchanged backend evidence
was reused rather than rerun.

Actual production-browser inspection passed at **1180×757** and **750×757**
using an existing saved matrix without starting new work. Descending and
ascending return ordering retained losses and kept unavailable native results
last. Editing a card parameter, including the card and changing order preserved
the draft. Under a one-card search filter, Test all still showed **14 tests / 7
strategies** in catalog order with the edited parameter; Escape restored focus
to its trigger. No preview or start was initiated.

The initial wide panel left only about 76 pixels of card viewport. After the
bounded disclosure correction, the closed panel was about 72 rather than 180
pixels tall and the card viewport about 180 pixels, exposing card headings and
descriptions again. Required choices opened the disclosure; Enter closed and
reopened the completed context while preserving the visible comparison,
timeframe, group and exact UTC period. Subsequent Tab navigation reached the
saved-timeframe selector. Changing timeframe cleared an ambiguous cohort,
visibly disabled metric ordering and restored name order; selecting the intended
context reapplied ordering. Saved tests-to-Lab return retained metric,
direction, timeframe/group and the closed summary. Both tested widths remained
usable without horizontal page overflow.

The holdout-return reset and display-event deduplication/failure counts are
automated component evidence only; this browser pass did not add a holdout or
recount display writes. Current Windows/native and owner-led unaided usability
acceptance remain separate checks.

## Saved-history OHLCV inspection — 2026-10-10

Saved history now presents price and recorded volume in two synchronized panes
on one original UTC opening-time scale. The inspector shows the exact source
interval, opening timestamp and recorded OHLCV values. Volume units are explicitly
unspecified: the UI does not infer base/quote currency or contracts. Recorded zero
remains `0`; unavailable/non-finite inspector values are `N/A`, and missing volume
is not drawn as zero. The existing verified reader normally rejects malformed
OHLCV before it reaches the UI; the component also handles unavailable values
defensively.

Backend-supplied missing slots occupy whitespace in both panes, including page
edges, with visible striped bands. Hovering a gap replaces earlier candle values
with an explicit missing-slot explanation. Previous/Next and focused-chart
Left/Right navigation step through actual candles; Home/End select page boundaries.
An offscreen keyboard target is brought into the chart window before its inspector
appears. A marker identifies the selected candle, panning it out of view clears
selection, and replacing the source/page clears old values and chart listeners.
Keyboard selection survives unrelated pointer movement outside the chart.

Both panes retain one display-evidence observer and recorder, with only original
actual candles as evidence inputs. Whitespace contributes no exposure; volume
adds no second record. Hidden tabs/ancestors and open-modal suppression are
unchanged. Selection neither saves an observation nor starts a strategy. The
500-source-slot page bound, hash-verified reader, immutable observation revisions,
source/date forms and explicit Lab Review/Start route remain unchanged. There is
no resampling, display-timeframe expansion, live/network/backend/schema,
dependency, accounting or product-version change.

Focused automated verification covered **64 distinct tests across six files**:
`ObservationChart`, `Observations`, `ObservationsHistory`, `DisplayedEvidence`,
`UserJourneys` and `chartWindow`. The first pass had 61 passes and one hidden-DOM
test-query error; after correcting that query, the dedicated chart file passed
all 13 then-existing tests. Production-browser inspection then found that a
chart redraw could replay the old hover and replace a keyboard selection. A
bounded lifecycle correction ignores synthetic redraw callbacks while keyboard
selection/reveal is active but still accepts genuine pointer and gap clicks.
Gap bands also follow fractional logical-range changes. The expanded chart file
passed **15 tests**, including these two regressions; the other five files' 49
passing tests were not rerun.
The chart tests independently specify exact OHLCV/zero/unavailable data, shared
unshifted timestamps, UTC labels, edge/internal gaps, pointer and keyboard
selection, viewport reveal, page replacement, cleanup and original-candle
visibility evidence. The observation integration test verifies the exact verified
payload and reference reach the chart without extra reads.

Reproduce the focused scope with:

```sh
node node_modules/vitest/vitest.mjs run frontend/src/ObservationChart.test.tsx frontend/src/Observations.test.tsx frontend/src/ObservationsHistory.test.tsx frontend/src/DisplayedEvidence.test.tsx frontend/src/UserJourneys.test.tsx frontend/src/chartWindow.test.ts
node scripts/frontend.mjs build
```

TypeScript and the corrected production Vite build passed, with the existing
large-chunk advisory. Component checks use jsdom, mocked chart APIs and mocked
IPC; actual production-browser reinspection separately passed at **1180×757**
and **750×757** using the existing isolated synthetic hourly gap fixture:

- Home selected 2024-01-01 00:00 UTC with independently known O100/H102/L99/C100.5
  and recorded volume 10. After a price-pane click selected January 11 03:00,
  Home correctly returned to January 1 and disabled Previous. End selected
  January 21 19:00 and disabled Next; Right advanced one source hour.
- Zooming to the missing January 2 00:00 slot and clicking its whitespace showed
  the missing-slot explanation with no earlier OHLCV values or invented zero
  bar. End from the zoomed window revealed the last actual candle while price
  and volume remained synchronized.
- Loading the later page reset the inspector to No candle selected / N/A.
  The narrow layout remained readable; clicking the volume pane selected
  January 29 22:00 and Right advanced to January 29 23:00.
- Opening the saved observation cleared selection. Test observation opened Lab;
  Escape and Return to observation reopened exact revision 2 and its locked
  January 26–27 period. No note save, review or run was initiated.

The browser pass did not independently count database exposure writes or inspect
a zero-volume fixture candle; those checks are component evidence only. The
unchanged backend and complete frontend suite were not repeated; the preceding
full frontend result is recorded below. Owner-led unaided usability and current
Windows/native acceptance remain separate.

## Combined UX-series verification — 2026-10-10

The preceding UX-series UI code is `fba0e5c4c3e0f316c55209738c255976c11e5501`, tree
`06f96249c960b000a60c439e6858e7da25058ce7`. One complete frontend pass using
`node node_modules/vitest/vitest.mjs run` passed **197 tests across 34 files**
in **9.67 seconds**, with no failures. This aggregate covers the combined compact
Saved tests review, attached Lab observation context, compact pre-review test
selection, observation-date validation and saved-observation read recovery.
It is the latest complete frontend pass before the OHLCV inspection slice, not
a sum of overlapping focused passes.

The latest read-recovery slice already passed `node scripts/frontend.mjs build`
(TypeScript and production Vite build), with the existing large-chunk advisory.
No runtime files changed during this verification/documentation checkpoint, and
that build was not repeated. The suite's jsdom environment performance advisory
is not a failure; component/App integration checks still use a simulated DOM and
mocked IPC. Failed reads, retry/cursor retention, post-save refresh failure and
stale-response exclusion are covered there, not by browser fault injection.

Actual production-browser normal-list smoke on the same code passed at
**1180×757** in a restored synthetic workspace. **Data → Observe this history**
loaded three saved observations without a false empty state. Opening the latest
note showed revision 2 and **2024-01-26 → 2024-01-27 UTC** (end exclusive).
Its linked test reopened the completed three-row comparison with its original
revision-1 observation context. **Return to linked observation** restored exactly
revision 1, the locked dates, historical-revision notice and disabled Save
action. No save, preview or start was initiated. This checks the ordinary
production-browser read/navigation path; it does not claim a browser-injected
read failure or retry test. Earlier slice entries retain their separate narrow-
and ordinary-width layout/keyboard evidence.

The unchanged backend evidence remains **304 Python tests passed and eight
Windows-only skips** from the preceding bounded MVP baseline. It was not rerun
for this UI-only series. No backend, accounting, immutable reports, schema,
dependency or product-version changes are included. Prior offline restore and
partial-import/restart acceptance remain evidence for those unchanged surfaces.
Current Windows/native, live-feed and owner-led unaided usability acceptance
remain separate gates.

## Saved-observation read recovery — 2026-10-10

Saved observations now distinguish loading, failed reads, confirmed empty
history and loaded records. A failed initial read no longer claims that no
notes exist. The scoped error survives choosing local history, and **Retry
saved observations** repeats only the failed list/cursor read. Already loaded
notes remain visible on pagination or refresh failure; repeated clicks are
guarded and overlapping IDs are deduplicated. Retry leaves source, exact dates,
current revision, unsaved text and Lab selection unchanged.

A confirmed note save followed by a failed list refresh explicitly says the
note was saved. Retry cannot repeat that write. The saved revision stays
selected; an older in-flight read cannot replace the refreshed list or report
a stale failure. Empty history is shown only after a successful empty response.
Date validation, saved-note guards, exact-revision links and the separate local
candle reader are unchanged. No backend, schema, dependency, product version
or financial artifact changed.

A pre-fix component test reproduced the initial false empty state. The focused
verification passed **37 tests in three files**:
`node node_modules/vitest/vitest.mjs run frontend/src/ObservationsHistory.test.tsx frontend/src/Observations.test.tsx frontend/src/UserJourneys.test.tsx`.
Coverage includes initial read failure and explicit recovery/open, empty-only
success, pagination and repeated-retry failure retention, exact cursor reuse,
duplicate clicks/IDs, dirty current-revision preservation, post-save refresh
failure without another write, stale success/failure exclusion, and an App
journey preserving an unsaved period/text and selected Lab strategy across tab
changes. Existing date, warmup, historical-lock and explicit-start guards pass.
The repeated-retry assertion was added after the initial pass; the affected
six-test file then passed again. These failure paths use deterministic mocked
IPC in component/App integration tests, not browser network fault injection.

`node scripts/frontend.mjs build` passed TypeScript and the production build
with the existing large-chunk advisory. The slice did not repeat the broad suite
or unchanged backend checks; the later combined frontend result is recorded
above, together with actual production-browser normal-list and revision-return
inspection. Error/retry cases remain component/App integration evidence only;
owner-led unaided usability and current Windows/native acceptance remain separate.

## Observation date guidance — 2026-10-10

Observation dates now show an inline reason for missing/invalid values,
non-increasing periods, dates outside the saved source, and boundaries that do
not align with its candle interval. The affected fields expose `aria-invalid`
and reference the explanation and exact available UTC range; updates use a
polite live region. Guidance labels the exclusive end and gives a source-candle
boundary example. Inputs keep their exact times: no snapping, page request,
save, preview or execution is triggered by editing or correcting dates.

The same validity result gates chart navigation and saving, and is included in
the existing saved/clean-note Lab gate. A valid unsaved note still cannot open
Lab; historical notes retain locked dates/text and exact-revision handoff.
Backend validation, note revision rules, source verification, immutable reports,
schema, dependencies and product version are unchanged. This slice does not
change saved-observation list loading/recovery or disabled-button styling.

Focused verification passed **30 tests across two files**. The initial command
was `node node_modules/vitest/vitest.mjs run frontend/src/Observations.test.tsx frontend/src/UserJourneys.test.tsx`.
One new test initially expected a seconds string without jsdom's normalized
`.000` suffix. Correcting that fixture retained the identical timestamp; rerun
of `frontend/src/Observations.test.tsx` passed all 21 tests, and the nine passing
UserJourneys tests were not repeated. Coverage checks field-specific accessible
errors, invalid-to-corrected ranges, 1m/1h/4h alignment, both source bounds, an
exact final candle with the source's exclusive end, draft retention, no implicit
actions, explicit save/handoff payloads, historical locks and existing dirty-note
and warmup guards.

`node scripts/frontend.mjs build` passed TypeScript and the production build
with the existing large-chunk advisory. Unchanged backend checks and the broad
suite were not repeated.

Actual production-browser checks on `82a5d6b` passed at **750×757 and 1180×757**.
With the synthetic 1h history, a new observation starting at **2024-01-01 00:30
UTC** showed the precise start-alignment reason and available UTC bounds with
the exclusive end, retaining the typed value while Show and Save stayed disabled.
Moving the start before history to **2023-12-31 23:00 UTC** showed the source-range
reason; setting it equal to the end at **2024-02-07 12:00 UTC** showed the
non-increasing-period reason. Correcting it to **2024-01-01 00:00 UTC** cleared
the error and enabled Show and Save, preserving the synthetic draft text.
The unsaved note's Lab button remained disabled. No Show, Save, Lab, preview or
run action was initiated. This documentation-only evidence update did not
repeat the build or tests. Owner-led unaided usability and current Windows/native
acceptance remain separate checks.

## Compact test-selection setup — 2026-10-10

The existing single-card and all-catalog setup now collapses only the pre-review
selected-test list. Its native disclosure shows computed test, distinct-strategy
and timeframe counts. Expanding retains the ordered names/timeframes and exposes
their already-selected IDs, versions and parameter values in the existing
bounded scroll area, which now accepts keyboard focus. Closing setup resets only
the disclosure presentation; the test draft remains intact. Batch timeframe
controls, observation context, setup errors and compatibility warnings remain
outside it. The pre-Start reviewed contract, ready/unavailable counts and every
unavailable-row reason remain expanded as before. Test all selection semantics,
review/start payloads and backend/trust/accounting behavior are unchanged.

Focused verification passed **39 tests in three files**: StrategyLibrary,
LibraryResearch and UserJourneys. The new assertions cover single/all entry,
14/7/2 and 21/7/3 selection counts, ordered identities and current parameters,
native disclosure state/focus, cancel-event/Back focus restoration, retained
history/dates/capital/costs, visible reviewed warnings and unchanged explicit
preview/Start requests. Command:
`node node_modules/vitest/vitest.mjs run frontend/src/StrategyLibrary.test.tsx frontend/src/LibraryResearch.test.tsx frontend/src/UserJourneys.test.tsx`.
The first pass found two test-harness assertions assuming jsdom hides closed
native-details descendants. Those assertions were corrected to check the closed
disclosure boundary; the affected StrategyLibrary file then passed all seven
tests. The other 32 passing tests were not repeated. Native visibility, keyboard
activation and layout require actual browser verification separately.

`node scripts/frontend.mjs build` passed TypeScript and the production build,
with the existing large-chunk advisory. No dependencies, schema, product version,
backend or immutable results changed; the broad suite was not repeated.

Actual production-browser checks on `719ca19` passed at **1180×757 and 750×757**.
The collapsed selection put market, capital and simulation inputs in the first
viewport. Enter expanded the 14-test/7-strategy/2-timeframe disclosure; Tab
focused its scroll region and End reached the final RSI rows. Space collapsed
it, after which Tab skipped the hidden list and reached Market. Adding 1h
updated the summary to 21/7/3. Escape returned focus to **Test all strategies**
while preserving all 21 selections; **Edit test setup** reopened the collapsed
21-test summary.

With complete synthetic 1h history and an explicit UTC evaluation period,
insufficient preceding warmup for the daily tests remained visible and kept
Review disabled. Removing 1d with Space restored a 14/7/2 selection and enabled
Review. An explicit Review displayed the full reviewed contract outside the
selection disclosure, 14 ready and two native-unavailable rows across the
strategy/passive-comparison review, and **Start 14 tests**. Start was not clicked.
These checks establish the bounded browser layout, keyboard and review flow;
current Windows/native and owner-led unaided usability remain separate. This
evidence update changes documentation only, so no build or tests were repeated.

## Visible Lab observation context — 2026-10-10

When an observation is attached, the compact Lab strip now retains a labeled
**Attached to draft test** row even after setup closes: short observation ID,
exact revision, fixed UTC range with exclusive end, and **Return to observation**.
The return reuses the existing exact-ID/revision callback and busy/active guards.
No hypothesis is duplicated in the strip. Unattached Lab drafts gain no extra
controls; saved comparisons keep their separate immutable observation context.
The existing setup, explicit detach action, date locks and warmup guards remain
unchanged. No new persistence, backend, dependency or version change is involved.

One focused pass passed **18 tests in two files**:
`node node_modules/vitest/vitest.mjs run frontend/src/Observations.test.tsx frontend/src/UserJourneys.test.tsx`.
New cases cover closed-setup draft identity/range, historical-revision return,
absence of attachment controls for ordinary drafts, preserved strategy selection
through Data/Lab/observation navigation, unchanged source/dates and no implicit
save, execution, preview or detach. Existing cases retain explicit-start linkage,
admission failure, late warmup, unavailable-source and observation edit coverage.
`node scripts/frontend.mjs build` passed TypeScript and production build with the
existing large-chunk advisory. No full regression suite or unchanged backend
checks were repeated.

Actual production-browser checks on `3748c13` passed at **750×757 and 1180×757**:
the attached-context row remained readable without clipping. Opening **Test
observation in Lab** for a saved synthetic observation at revision 2 retained
its fixed **2024-01-26 → 2024-01-27 UTC** period (end exclusive). Escape closed
setup while the cue remained visible. After selecting one Donchian test,
**Return to observation** reopened exactly revision 2 with the expected
hypothesis and locked dates. Navigating back to Lab preserved that selected
test and the attached period. No save, preview or execution was initiated.
This establishes the bounded browser flow and layout; owner-led unaided
usability and current Windows/native acceptance remain separate.

## Compact Saved tests review — 2026-10-10

Saved comparisons now keep the chooser, compact original market/capital/period,
source resolution, exact declared costs, instrument assumptions, outcome counts,
saved-versus-draft state, linked observation return and sorting ahead of results.
Catalog search and detailed assumptions use native disclosures. Filter inputs
are collapsed initially; their active count, Clear filters and invalid numeric
warning remain visible when closed. Clear filters affects viewing filters only.
Search still covers the complete catalog with server pagination and a retained
selection outside the current search page. Help and later-period setup follow
the table; later-period warnings and run controls remain outside disclosures.
Saved notes now have an explicit disclosure beside the compact saved name and
Edit details action; name/notes editing and dirty-state protection are unchanged.
The redundant inner heading and outer subtitle are removed in Saved tests only.

Focused verification passed **44 tests in five files**: LibraryResearch,
SavedReview, SavedComparisonDetails, UserJourneys and DisplayedEvidence. The
new coverage exercises disclosure state/focus, retained context/warnings,
invalid thresholds, reset without changing sort/selection/draft source, linked
return, and disclosure toggles versus actually displayed numeric-cell exposure.
Existing cases cover search pagination/outside selection, saved report return,
cohort ordering, passive/N/A context, losses and metadata protection. Command:
`node node_modules/vitest/vitest.mjs run frontend/src/LibraryResearch.test.tsx frontend/src/SavedReview.test.tsx frontend/src/SavedComparisonDetails.test.tsx frontend/src/UserJourneys.test.tsx frontend/src/DisplayedEvidence.test.tsx`.
`node scripts/frontend.mjs build` passed TypeScript and the production build,
with the existing large-chunk advisory. No backend, schema, dependencies,
accounting or immutable reports changed; broad regression was not repeated.

The first production-browser inspection found results still below the initial
1180×757 viewport. One bounded correction compacted headings and metadata,
disclosed saved notes, and removed the old text-width cap on essential context.
The affected four component files then passed **37 tests**, including the new
saved-note disclosure case; TypeScript and production build passed again with
the same chunk advisory. DisplayedEvidence's unchanged focused evidence was
reused rather than repeating that file or a broad suite.

Actual production-browser checks of the corrected build at **1180×757 and
750px** found the **table header reaches the first viewport**, with usable narrow
wrapping. The first full data row still requires a small scroll; this slice does
not claim the original first-row-above-fold target. Saved identity, period,
costs, instrument warning and outcome status remained visible. Enter toggled
Filter results. An invalid minimum completed-position value of -1 retained
“1 active”, the invalid-input indication and its visible error after collapse.
Clear filters reset the count to zero and disabled itself without changing the
selected comparison. No new run was started. This is a bounded improvement,
not owner-led unaided usability or current Windows/native acceptance. Long
warnings, running work and later-period safety context can still increase the
pre-table height.

## Historical bounded MVP verification — 2026-10-10

Before the subsequent UX series, the bounded MVP baseline was local commit
`1da24d8`, published as `bc10a4c` with identical tree
`4bd2fae2aecd7c8e6a2bc95f7c5dde012a6db4ac`. This is historical UI evidence, not
the current source checkpoint. Its combined Linux verification passed runtime
validation, dependency checks, 304 Python tests
with eight Windows-only skips (312 total), all 170 frontend tests across 32
files, TypeScript and the production build. There were no test failures or
errors. Existing deprecation, simulated-DOM and large-chunk advisories remain.

TT15 full offline restore passed using complete closed synthetic workspaces,
including datasets, SQLite records, immutable reports, comparisons, saved
metadata, observation revisions/links and research evidence. Source/copy hashes,
integrity, foreign keys and reopened API values were checked across clean
service lifetimes without network access or new backtests. Actual production
browser reopening then verified local candles, latest-versus-linked historical
observation revisions, completed comparison metadata, keyboard trade-to-chart
navigation and name-to-notes focus at 750px width. Escape cancelled a later-period
overlap review without admitting or freezing work. Post-close reconciliation
preserved every non-database file and every non-evidence table; original research
events were unchanged and exactly six expected viewed events were appended.

TT13 actual browser upload into an isolated synthetic workspace reproduced a
second-run storage failure. The UI showed the correct completed/importing IDs,
strategy save not attempted and non-atomic/no-blind-retry/no-resume guidance,
without stale transfer progress. After removing only the fixture fault trigger,
an ordinary application restart retained exactly two records, recovered the
unfinished record as interrupted and reopened the completed imported report.
Missing-history and imported/untracked-evidence caveats remained visible. Final
storage checks confirmed unchanged immutable JSON hashes, zero saved strategies
or new trust, intact built-in triggers and valid SQLite integrity/foreign keys.

These checks close the bounded offline restore and archive browser gates; they
do not establish owner-led unaided usability, Windows/native or live-feed
acceptance. Archive persistence remains non-atomic and displayed evidence remains
incomplete. This final evidence update changes documentation only, so the build
and broad suites were not repeated.

## Archive partial-failure disclosure — 2026-10-10

A two-run injected failure independently reproduced one completed report and one
importing record behind a generic error. Archive persistence now reports known
local IDs and re-read statuses, including created/importing/completed/unknown,
without exposing storage exception details. Unknown create and strategy-save
outcomes remain explicit. The UI clears stale transfer progress and displays
no-blind-retry guidance through the existing error envelope. Blank strategy
names and oversized documents are rejected before run writes, matching existing
strategy-storage constraints. Successful import bytes, IDs, nonexecution/trust
boundaries and immutable earlier records are preserved.

Focused verification passed 16 archive/backend tests, including file-before-DB
failure, post-commit failure, unreadable status, strategy-save uncertainty,
prevalidation with no writes, preserved bytes and service error propagation.
ProjectTransfer/API verification passed 14 tests across two files, covering
both desktop and browser error presentation and existing no-retry behavior.
TypeScript and the production Vite build passed with the existing large-chunk
advisory. Independent source review found no blocker. No broad suite or Windows
build was repeated; browser/manual acceptance remains separate.

Imports remain sequential and non-atomic. Partial files/records are retained;
there is no safe retry/resume, rollback or durable outcome receipt for a lost
response or process exit. See [archive contract](adr/0008-archives-comparison.md).

## Real-market matrix and status clarity — 2026-10-10

A bounded, isolated integration matrix used real BTCUSDT spot history at its
native 4h resolution. All 12 supported graph strategy/timeframe variants and
both passive controls completed: 14 completed, two native rows explicitly
unavailable, and zero supported-row failures. Full required warmup, retained
costs, frozen source/result identity and saved-result reopening checks passed.
No raw market data, private source files or financial results are published.
This is technical integration evidence, not economic validation or evidence of
profitable strategies. The source classification remains unknown; venue
constraints remain manually specified assumptions. Windows acceptance is deferred.

Saved comparison presentation now separates completed, unavailable and failed
row counts. Incompatible native rows no longer make an otherwise completed
comparison appear to have execution failures. History entries without detailed
rows retain the conservative label “Finished with unavailable or failed rows.”
Running, preparing, pending, frozen, cancelled, interrupted, failed and unknown
states remain distinct; partial or missing row details cannot imply completion.
Persisted machine statuses, immutable results, losses, N/A values, accounting,
strategy execution and data adapters are unchanged.

The focused status/LibraryResearch/UserJourneys pass passed all 40 tests across
three files in 7.22s. The initial pass found two test expectations requiring the
new capitalization and correct saved-versus-draft context; these were corrected.
TypeScript and the production Vite build passed with the existing large-chunk
advisory. No broad regression suite or Windows build was repeated for this
presentation-only change. Simulated DOM coverage is separate from browser and
native acceptance.

The final production-browser check reopened the saved real-market matrix without
recomputation: the picker showed “Finished with unavailable or failed rows” and
the header showed “Completed · 14 completed · 2 unavailable · 0 failed.”

## MIT project license — 2026-10-10

The owner authorized the standard [MIT License](../LICENSE) for Trading Terminal,
with copyright (c) 2026 Ilia Merkurev. README, current specification, development
guidance, third-party notice scope and npm/Cargo metadata now reflect MIT.
Historical license-undecided and scope-exclusion records below describe their
original milestones and are superseded only for this license decision.

The license text was checked against the [OSI MIT text](https://opensource.org/license/mit);
JSON/TOML metadata parsing and a bounded diff/privacy/license review passed.
Third-party notices, dependency licenses and data-provider terms remain applicable.
No dependencies, lockfiles, product version or runtime behavior changed; no
application build or broad test suite was run for this documentation/metadata change.

## Bounded displayed-period evidence — 2026-10-10

The append-only registry now separates displayed ranges from admissions and
freezes. It covers visible local Observation candles, selected Saved comparison
numeric rows, and selected individual report metrics/candle panes. Metric views
expose their full evaluation range; chart views intersect verified actual candle
timestamps and preserve gaps. Original admission coverage and historical frozen
reviews remain intact, with a separate display-coverage marker. Backend-issued
bounded page references preserve rendered source identity without re-reading the
full Parquet on each pan. See [ADR 0034](adr/0034-displayed-period-evidence.md).

Hidden/prefetched surfaces, dataset lists and saving a note do not create display
evidence. Repeated callbacks deduplicate within a presentation. Synthetic sources
remain isolated; passive and strategy report views retain separate labels.
Reading continues on a tracking failure, with a latched incomplete warning and
durable caveat. Freeze drains pending display writes and persists any frontend
caveat first; a persistence failure keeps confirmation open with an error.

The focused corrected backend pass passed 23 tests in 7.962s across displayed,
admission and observation evidence. The initial pass found an old one-marker
migration assertion and a test retaining a completed worker through its cleared
active slot; both test contracts were corrected. The focused corrected UI pass
passed 47 tests across six files in 7.28s. Its initial pass had one assertion that
needed to await the new asynchronous freeze drain. Subsequent narrow modal/failure
checks passed all 10 tests in 1.32s. TypeScript and production Vite build passed
with the existing large-chunk advisory. Final source review found no remaining
blocking issue. One additional IPC-only test passed in 0.014s: page fetch appends
no view, failed caveat persistence returns an error, and a later zero-overlap
review retains the caveat. The frontend caveat test also passed standalone after
removing its dependence on earlier test state.

Actual browser inspection caught a finer visibility boundary: an intersecting
tall table cell could expose blank space while its numeric text remained below
the viewport. Tracking now observes tight metric text/value elements and excludes
N/A-only annualized cells and passive delta dashes. The corresponding simulated
DOM regression checks blank cell intersection separately from numeric text.
The corrected DisplayedEvidence/LibraryResearch/UserJourneys pass passed all
38 tests in 6.82s, followed by a successful final TypeScript/production build.

The production-browser walkthrough verified zero view events on Data, Lab and a
selected comparison before numeric rows reached the viewport; actual local chart
display, narrower zoom/pan ranges and a missing-hour split; and no extra chart
events on a hidden route. Selected report metrics and close-labeled candles both
recorded the exact half-open evaluation period. A never-run later period showed
zero admissions, zero freezes and two manual displayed ranges. Confirmation saved
a frozen candidate with that exact two-view prior review without starting a run.
The fixture retained three runs, two batches, one observation/revision and zero
links; all nine original immutable JSON hashes were unchanged and SQLite integrity
was ok. After rebuilding and restarting, the exact numeric-boundary recheck
recorded only Buy & Hold when its values were visible and only the DCA name/action
was onscreen. Scrolling actual DCA/RSI values into view then produced their records;
repeated up/down scrolling did not duplicate those three presentation records.
The frozen candidate reopened with zero of three rows completed and its original
zero-admission/zero-freeze/two-display prior review. All nine original immutable
JSON hashes, three-run count and SQLite integrity remained unchanged.

The fixture uses independent invented hourly candles, one three-row completed
comparison, one never-run interval and a separate gapped source. Its manifest
records initial counts and immutable JSON hashes. No fresh market source or
profitability acceptance is claimed. Legacy/imported reports without original
local admissions, replay/live, other display surfaces and external exposure remain
incomplete; displayed does not mean read. No broad suite was repeated. Actual
browser and Windows acceptance are separate; Windows remains deferred.

## Local manual-research observations — 2026-10-10

Market now has a Saved history subview and Data cards can open a local snapshot
without visiting Live. Bounded prepared-candle pages show provenance, synthetic
warnings and actual missing slots. Users enter a UTC observation range and short
hypothesis, optionally add a falsification condition, then save/reopen that exact
source. Note edits append revision-guarded history; source and dates remain fixed.

Test observation opens the existing Lab setup without executing. Its atomic
source/range/revision context survives async warmup and mismatched/restored
settings. Dates cannot change until explicit detachment. A successfully admitted
Library batch links transactionally to the exact note revision outside immutable
results, with return navigation in both directions. Later note edits cannot become
retroactive evidence. Admission storage failures roll back and prevent launch.
Existing saved comparison metadata/search/filters remain in place.

The initial backend focused pass had one incorrect mock target; the corrected
observations/evidence/storage pass passed 24 tests in 5.674s. After reader caps,
optional falsification and chronological paging, all 10 observation tests passed
in 0.214s. The initial UI pass had 35 passes and one duplicate-alert selector
failure; its corrected final Observations/UserJourneys pass passed 12 tests.
The unchanged LibraryResearch/HistoryWorkspace tests passed in the initial pass.
TypeScript and production Vite build passed with the existing large-chunk advisory.
Independent source review found two contract gaps (full source identity during
link admission, and restoration after mismatched Lab settings); both were fixed
and re-reviewed with no remaining blocking data/storage issue.

The new-only synthetic fixture script creates 900 independently invented hourly
candles plus a separate one-gap snapshot, one observation and no runs. It uses
invented instrument metadata and makes no market/profitability claim. Reader
limits, exact source checks, note/link write failure, revision preservation,
chronological pagination, warmup races and direct offline navigation are covered.
See [ADR 0033](adr/0033-local-history-observations.md).

Final focused validation passed all 11 observation/backend fixture tests in
0.862s and all 37 tests across Observations, LibraryResearch, HistoryWorkspace
and UserJourneys. Final TypeScript/production build passed. An actual synthetic
manager run completed one linked batch with three completed rows/runs. Editing
the note to revision 2 retained its batch link to revision 1; a service restart
preserved the link, all nine immutable JSON hashes and SQLite integrity. The
fixture's admitted-run count remained three after reopening.

Initial production-browser acceptance confirmed 500/400-candle paging, the
499-candle gap page, optional blank falsification, exact handoff dates and one
admitted batch despite a double Start click. Returning to the same observation
then exposed a reader-effect bug: clearing its page did not change any load
dependency. The bounded correction adds an explicit reopen/retry generation and
record identity, preserving stale-response cleanup and avoiding note-keystroke
rereads. The provenance line now uses the verified page classification. Seven
focused component tests passed, including same-record return followed by note
save and rejection of a late older page. Independent review found no blocker.

One combined cumulative Linux acceptance pass on the corrected code completed
297 Python tests in 114.521s: 289 passed and eight Windows-only native/lifecycle
checks were skipped, with no errors or failures. The prior thread-mock teardown
errors did not recur. All 150 frontend tests across 30 files passed in 11.53s.
Final TypeScript/production build passed with the existing large-chunk advisory.
No full suite was repeated for this documentation-only evidence update.

Subsequent actual browser checks verified that same-record return reloads its
252-candle local page. A post-test note edit saved revision 2; its linked batch
still returns historical revision 1. A separate first-day observation with an
empty optional falsification field kept its exact dates and blocked RSI Review
for insufficient preceding warmup, without adding a batch. The synthetic
workspace then retained six runs, two batches, three observations, five note
revisions and two links. The original nine immutable JSON hashes were unchanged
and SQLite integrity remained ok.

Ordinary wheel navigation then exposed a layout blocker at both 750px and
1180px widths: the Saved history wrapper did not bound its inner content scroller.
The minimal correction reuses the established workspace flex/min-height/hidden
host contract. All eight focused UserJourneys tests and TypeScript/production
build passed; no backend changes or repeated full-suite run were needed. The
structural component check alone does not establish actual browser scrolling.
After restarting the production browser host for the rebuilt static inventory,
actual wheel checks passed at both 1180px and 750px widths: scrolling outside the
chart reaches the note, controls, linked test and saved observations; scrolling
up returns to the chart while the header stays fixed. At 750px the fields and
buttons fit, lists stack, and no horizontal overflow was visible. Independent
source review found no blocking layout/state concern.

TT16 is a bounded manual-observation slice, not full research-journal acceptance.
Chart/report view tracking remains explicitly incomplete. The recorded browser
checks use the isolated synthetic local service, not native Windows or live
market data. Windows-native and live-source acceptance remain deferred; the
browser observations supplement, rather than replace, Linux and simulated-DOM
regression evidence.

## Forward-only research admission evidence — 2026-10-10

A new additive append-only registry records durable custom, Library and Experiment
run admissions, passive controls and actual frozen candidates. Admission commits
with the run before worker creation; freeze and its prior-overlap review commit
with the candidate. Failed persistence rolls back the database transaction and
uses the existing storage quarantine. Records retain owner/contract/dataset,
actual evaluation versus input/warmup ranges, and declared provenance/cohort.

Both freeze actions now open a bounded review dialog before confirmation. It
shows cross-route same-symbol calendar overlap, distinguishing spot/linear
cohorts, frozen candidates and passive controls. Explicit synthetic evidence is
isolated by declared source; unknown provenance remains visible and conservative.
The recorded prior review excludes its own freeze and does not change on later
admission or reopening. Old saved Library counters are labeled Library-only.

TT11 remains partial: chart/report views, replay/live activity, old/imported
attempts and external exposure are unrecorded. A durable coverage-start marker
makes the boundary explicit; no zero-result warning claims untouched history.
Snapshots, financial reports, accounting and product version are unchanged.
See [ADR 0032](adr/0032-research-admission-evidence.md).

Focused backend validation passed 15 tests across research evidence and storage
resilience (4.953s), plus the existing Library later-period parity test in the
initial pass. That initial command also named a nonexistent storage test module;
the corrected command above passed. Evidence covers real tiny synthetic workers,
cross-route freezes, no-worker admission failure, transactional freeze rollback,
append-only/restart preservation, migration lock release, repeated admissions,
unknown/real/synthetic classification, adjacent ranges and warmup exclusion.
The independent preservation assertions retain original snapshot/report bytes.

The first UI pass had 25 passes and one existing test missing the new confirmation
click. Its corrected focused pass and the final modal refinement each passed all
23 tests in LibraryResearch and EvidenceFreeze; the three unchanged Experiment
tests passed initially. Actual browser inspection then found ambiguous same-day
history choices. All Library history selectors now include declared source,
short dataset ID and precise UTC range; the overlap review also shows its exact
evaluation range. This refinement passed 24 focused UI tests and final
TypeScript/production build, retaining the existing large-chunk advisory. A separate tiny authentic synthetic fixture
completed custom, Library and Experiment runs and saved a never-started freeze.
Independent initial and final source review found no blocking lifecycle,
immutability or UI issue.

Actual local-browser acceptance on production code `0855f39` verified that the
source, short ID and full UTC labels distinguish three same-day datasets. Library
review for 2024-01-01 00:24–00:48 UTC showed three recorded events: one custom
admission, one Experiment admission and one Library freeze, with explicit partial
coverage. Cancel created no freeze. A separately declared synthetic source showed
zero overlap while retaining the warning that this does not establish unseen data.
Confirm created exactly one new frozen batch and no runs/admissions; its saved
prior review was three, while the original frozen candidate retained two.

The Experiment freeze review for 00:36–00:48 UTC then showed three events: one
custom admission and two Library freezes. Cancel changed nothing. After Stop
local service and restarting the same launcher, all three batches persisted; the
original candidate retained its prior count of two, frozen status, 0/3 completed
rows and explicit Run action. SQLite integrity was ok. The five completed runs
and admission counts stayed unchanged (three strategy, two passive); there were
two strategy freezes. All 15 original immutable run JSON files retained their
hashes. The final overlap dialog was visually checked at 1180px width.

This is synthetic local-browser/restart acceptance supplementing focused Linux
and simulated-DOM checks. Narrow-screen acceptance for this slice, full-suite,
Windows-native and live-source checks remain uncompleted. View tracking remains
partial, and synthetic fixtures provide no profitability evidence.

## Saved research details and numeric thresholds — 2026-10-10

Actual browser checks on the functional checkpoint verified reopening a legacy
matrix, saving a name and Unicode notes, finding it with uppercase Cyrillic
search, and locking comparison selection while details are unsaved. Thresholds
of 0% drawdown and 1,000 positions retained passive references and N/A context;
a negative minimum-position value displayed the validation warning.

Final local-browser acceptance on production code `b859f5a` verified persistence
after Stop local service and restarting the same launcher: the named legacy
comparison and exact Unicode note reopened, and uppercase Cyrillic search found
it. Edit details reopened the saved text; an unsaved change disabled comparison
switching and Hide details; explicit discard restored the saved name. A subsequent
rename and Save details collapsed the editor and updated the selector. Opening
the RSI report and returning with Back retained search, selection and numeric
filters on the feature checkpoints. The legacy matrix remained at 14 completed
and two unavailable rows, with two total saved comparisons and no rerun. SQLite
integrity_check returned ok; all 42 original report/snapshot files retained their
hashes. These are synthetic local-browser workflow and preservation checks.
Narrow-screen visual acceptance of this latest refinement remains pending.

That walkthrough also identified excessive explanatory text above the results.
The bounded presentation refinement moves detailed filter/cohort guidance into
a disclosure while retaining a visible scope/baseline/context summary. Saved
details initially show the name, a short note preview and Edit details; a
successful save collapses the editor. Drafts, pending saves and errors cannot be
hidden through that control. This presentation-only change passed all 23 tests
in the two affected UI files, plus production TypeScript/build with the existing
large-chunk advisory. Independent source review found no blocking issue.

Saved Library comparisons now support editable names and research notes in a
separate additive metadata table. Revision-checked transactional writes preserve
immutable batch snapshots, run summaries and report files. Legacy comparisons
remain readable with empty details. Failed writes retain editor text; polling
cannot replace drafts, and switching comparisons requires save or discard.

Literal, Unicode-case-insensitive search covers names, notes, IDs and creation
dates across the full saved catalog before the existing bounded keyset paging.
Search does not include strategy names or metrics. Selected reports remain
available outside the current search page; reset requests invalidate pending
older-page responses. Numeric drawdown, completed-position and period-return
thresholds apply only to the selected comparison. Cohort sorting and holdout
order are unchanged. Passive references bypass thresholds; N/A and unfinished
rows are labeled context, never passing measurements. See
[ADR 0031](adr/0031-saved-comparison-details.md).

Focused backend verification passed 10 tests across `test_library_history`,
`test_library_batches` and `test_library_validation`. After the final unknown-ID
read guard and a new API/file-preservation fixture, four history tests passed;
the new test initially expected the wrong IPC envelope key. Its corrected
assertion passed in a one-test rerun. These are overlapping focused passes,
not a combined full-suite count. Evidence includes 125-record pagination,
old-record literal/Unicode search, restart, revision conflicts, rollback after
an injected write failure and unchanged independently supplied report bytes.

The focused UI rerun passed 29 tests in `LibraryResearch`,
`SavedComparisonDetails` and `StrategyLibrary`; the first pass found a JSX
syntax typo and passed the two independent metadata-editor tests before the
correction. Production TypeScript/build passed with the existing large-chunk
advisory. Independent source review caught and resolved a concurrent paging
reset race and floating-point percentage-boundary comparison before this final
pass. No dependency, accounting, network or security change was made. The
browser/restart results above supplement these focused passes, not a new full
regression suite. Windows-native and live-public-data gates remain uncompleted.
Synthetic fixtures are not profitability evidence.

## Saved-result presentation refinement — 2026-10-10

Saved comparisons now distinguish their immutable settings from the current
editable draft without requiring a rerun to view reports. The strategy/cohort
column and its Open report action stay pinned while scrolling across metrics;
a keyboard-focusable region and visible horizontal-scroll guidance retain access
to every metric and action. Losses, N/A values and cohort rules are unchanged.
Opening an individual report collapses the loaded run history and puts the
selected report, metrics and chart ahead of comparison/export tools. History,
paging and run selection remain available; Back retains the saved comparison
and its filters.

Focused presentation verification passed 36 existing/updated frontend tests in
three files, plus one new 17-run report/history/back-navigation regression. The
new fixture initially assumed input ordering for equal timestamps; unique dates
corrected the fixture, and its focused rerun passed. Production TypeScript/build
passed with the existing large-JavaScript-chunk advisory. Backend calculations,
accounting, data, schemas and dependencies are unchanged. Actual browser checks
at 1180px and 750px verified pinned row identity, horizontal scrolling, collapsed
history and report-first layout. Those checks found that the run-status response
may omit its creation date. The heading now falls back to a valid timestamp from
the matching history row, or explicitly says the date is unavailable. Two focused
regressions and production TypeScript/build passed for this correction. Its
actual browser recheck passed as recorded below.

At the preceding functional checkpoint, actual local-browser checks verified
that a double Start produced one three-row batch with all rows completed, copy
cancellation created no strategy, both copy-setting choices retained their
selected capital, and a saved report reopened after restart. All 42 immutable
original report files retained identical hashes, and SQLite integrity was ok.
This is synthetic browser acceptance, separate from Windows-native acceptance.

## Final local-browser acceptance — 2026-10-10

Actual browser checks on the final source checkpoint passed at 1180×757 and
750×757: the selected report remains primary, the 17-row run history starts
collapsed and remains accessible, and narrow-screen metrics use two columns.
The strategy identity and Open report action remain visible when the comparison
table is scrolled fully right. Saved-versus-draft wording does not require a
rerun to view results. Opening a report from its saved batch displays the real
10 October creation timestamp through the history fallback, never Invalid Date.

The earlier actual functional checks remain applicable: preparing Data returned
to the preserved test setup; a double Start created exactly one batch with three
completed rows; copy cancellation and both explicit settings choices behaved as
selected; and saved results reopened after restart. Final integrity checks found
two saved batches, unchanged hashes for all 42 original immutable report files,
and SQLite integrity ok. This documentation-only checkpoint changes no source,
data or dependencies and requires no repeated test/build pass.

These are synthetic local-browser workflow and preservation checks, not evidence
of real-market profitability. Windows-native acceptance, native display scaling,
and live public-feed acceptance remain separate, uncompleted gates.

## Storage finalization and safe shutdown — 2026-10-10

Failed final storage writes now release calculation/scheduler ownership and set
one shared, non-durable diagnostic. Further run, replay, grid, Library and frozen
validation starts are blocked in that application session. Saved statuses and
completed metrics remain distinct from the diagnostic. A global notice reads
memory-only scheduler state, including actual worker/reservation ownership;
it is visible across connected transports even when SQLite cannot be opened.
Native close and replay controls no longer confuse an unfinished saved status
with a still-running worker. Independent active downloads retain their close
confirmation and cancellation flow. Restart retains existing interruption
recovery; it neither retries calculations nor proves that storage is repaired.

Shutdown now attempts all owned resource cleanup despite failed live-journal or
cancellation writes, preserves the original failure evidence, and retains the
workspace lock while workers, scheduler threads, live warmup, market/chart,
notification or download threads remain active. Cancellation still terminates
the owned process when its status write fails. No completed result is fabricated.
The existing native host's ten-second forced-backend fallback is unchanged;
slow cleanup may still reach that fallback. Graceful Windows disk-failure
shutdown is not established by Linux fault injection.

Migration verification traverses bounded keyset history pages (at most 100 rows)
and checks every completed report against an independent SQL count. The report
includes the verified count; corruption in the oldest of 101 reports is rejected.

Focused integrated Linux evidence: 13 backend fault tests and 11 selected UI
close/notice tests passed. Separately, four existing calculation regressions and
two nearest live/blocked-warmup regressions passed. Tests use injected SQLite/
filesystem failures, isolated workspaces and independently specified outcomes;
they do not fill or remount the host disk.

The combined candidate pass ran 277 Python tests in 102.417s: 260 passed, eight
Windows-only checks were skipped, and nine legacy manual-paper fixtures failed
only during teardown because their mocked live thread stayed alive after join.
Two fixture lifecycle mocks were corrected without changing production code or
financial assertions. All nine affected tests plus four shutdown ownership guards
then passed in a focused 13-test rerun (3.062s); the full suite was not repeated.
The same candidate passed all 132 frontend tests in 27 files and production
TypeScript/build. The existing large-JavaScript-chunk warning remains. Actual
final-candidate browser acceptance and Windows acceptance remain separate.

## Card-to-saved-test journey — 2026-10-10

Lab setup now retains its origin when preparing data. Custom-backtest history
returns to its editor route, while later-period preparation returns to the
selected frozen candidate. Global Data navigation does not invent a later-period
candidate. Wrong instruments, resolutions, dates, warmup and incomplete metadata
have specific remedies; backend preflight remains authoritative.

Graph customization explicitly chooses Lab or editor settings, exposes differing
costs and assumptions, and discloses the graph's model-2 contract. Invalid
transfers are rejected before any strategy is saved. Native copies retain their
reviewed template settings and never grant trust or load Python. Missing metadata
raises an actionable data error; explicitly synthetic metadata cannot claim
current exchange precision.

Review and saved settings show exact declared cost fractions, separate from
rounded performance metrics. Synthetic instrument assumptions remain visible in
saved comparison and individual report views. Saved-card empty states distinguish
no selected comparison from absent rows in that comparison. Losses, zero-trade
rows and unavailable metrics remain visible; passive rows survive candidate
filters. Existing compatible-cohort sorting and passive calculation semantics
are unchanged. Later-period guidance explicitly notes incomplete exposure records.

Saved comparisons have fixed 50-row keyset pages with a bounded response budget,
including continuation when the byte limit shortens a page. Reopening older work
is read-only. The copy API extension and history endpoint do not change schemas,
engine versions, dependencies, financial formulas or existing report bytes.

Fresh focused verification passed 49 frontend tests in seven files and 32 backend
tests covering atomic copy, native trust, metadata, fixture preparation, coarse
execution and history pagination. Independent review found a small-cost display
rounding issue; its correction passed 20 targeted tests across two files. These
counts overlap and are not a full-suite total. Production TypeScript/build passed;
the existing large-bundle advisory remains (about 757 kB JavaScript).

A separate independently generated 4,032-hour BTCUSDT spot fixture executed the
existing seven-template H4/D1 matrix: 12 graph variants and two passive alternatives
completed; two native/spot variants remained explicitly unavailable. Model-2 graph
and model-1 passive reports retained measurable deltas and losing outcomes.
All 14 completed reports reopened after service restart, 42 immutable JSON files
kept identical hashes, and SQLite integrity was ok. This is synthetic integration
evidence, not market-performance or Windows-native acceptance. Actual browser
acceptance of this journey and final combined regression remain pending.


## Conservative historical accounting gates — freshly verified 2026-10-10

Historical linear runs with historical funding require complete trade coverage,
including leading and trailing coverage in the dataset's declared range.
Dataset preflight refuses incomplete history; the direct simulator also refuses
internal gaps or supplied funding events without matching trade candles before
constructing the engine. The remedy is complete history or a verified continuous
range. No synthetic prices or automatic zero-funding substitution are introduced.
Old profile snapshots and saved reports remain readable.

Linear-origin Library comparisons retain Buy & Hold and Scheduled DCA as
explicitly unavailable until an independent spot execution profile and explicit
spot fee assumption are available. Linear constraints are not copied into new
purported spot alternatives. Spot-origin comparisons retain their declared manual
contract and full cache identity. Unavailable baseline rows have no run or metrics
and do not block a valid strategy's frozen later-period test; strategy preflight
errors still block it. Completed batches with unavailable rows retain the existing
`completed_with_errors` status.

The recovered focused tests cover profile versions 1/2, long/short and both
funding signs (quantity 1, mark 100, rate ±0.01), internal/leading/trailing gaps,
Position Management, continuous controls, explicit assumed-zero/spot controls,
managed-worker refusal without successful output, byte-identical saved-result
reopening, baseline N/A counts, spot contract invalidation and later-period
strategy rejection/acceptance. Fresh integrated Linux verification passed all
**48 tests in 20.804 seconds** across `test_accounting_guards`, `test_simulation`,
`test_position_execution`, `test_library_batches`, `test_benchmarks`,
`test_benchmark_jobs` and `test_library_validation`. The command was
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests .venv/bin/python -m unittest test_accounting_guards test_simulation test_position_execution test_library_batches test_benchmarks test_benchmark_jobs test_library_validation -v`.
Pinned Python 3.12.14 / NautilusTrader 1.231.0 runtime verification and `pip check`
also passed. Upstream Pandas Timestamp.utcnow deprecation warnings remain.
No full-suite or Windows-native acceptance is claimed.

The conservative 2,000,000-source-candle workload cap and existing warmup
accounting remain unchanged. Benchmark warmup overcount is deferred: reducing
modeled counts must first preserve a separate source-load memory bound. This
patch does not repair the funding timeline, introduce independently configured
cross-market benchmarks, revise schemas/versions, or rewrite historical results.
Direct callers without a declared dataset range cannot establish missing edge
coverage from absent information; dataset preflight remains authoritative for
that range, while every supplied unmatched funding event is refused directly.

## Recovered Market / Lab workspace — 2026-10-10

The accepted Market/Lab source was reconstructed against the recovered browser
frontend. This is a new verified source reconstruction, not recovery of the lost
Git commit or reuse of its historical test results.

- Market and Lab are peer tasks. Market has an independent draft profile and no
  editor chrome. Its chart stays mounted across navigation, retaining display
  interval, candles and fitted viewport; hidden market status/chart polling stops.
  Leaving Market releases viewing without pausing an explicitly active strategy.
- Advanced strategy/paper controls and diagnostics start collapsed. Replay and
  paper lifecycle panels mount only when visible and selected. Frozen active
  session instruments label the screen correctly, including non-BTC instruments.
- Lab retains its controller state while closed setup fields are unmounted.
  Current context stays visible; card actions precede optional metadata. History
  preparation returns to the preserved setup. Hidden completed batches stop
  polling; active batches continue until completion.
- The restored CSS stacks a full-width 420px chart above depth/tape at widths
  at or below 900px and places the no-data explanation above chart canvases.

Fresh focused validation on Linux used nine affected frontend test files. The
first pass had 60 passes and three outdated-test failures (63 total). One
corrective pass updated explicit modal interaction and a duplicate-label query,
added two batch lifecycle cases, and passed all 20 tests in the three affected
files. Together with the unchanged six files from the first pass, all 65 distinct
focused tests pass. TypeScript and the production Vite build pass; the existing
747.64 kB JavaScript size advisory remains. Final test edits also pass TypeScript.

These checks use simulated DOM and mocked IPC. Fresh real-browser geometry,
public candles and Windows native/scaling/keyboard acceptance are not established
by this patch. Browser service shutdown logic, backend accounting, schema and
Windows integration files are unchanged. Integrated release validation remains
separate.

## Recovered local browser mode — 2026-10-10

The browser transport has been reintegrated on the independently verified Linux
checkpoint. The six frontend production files match their original Git blob
hashes; the host and tests were reconstructed from retained source. One fresh
review fix keeps the service reference available if cleanup raises, allowing a
later close attempt to finish. Historical graphical acceptance below remains
separate from current evidence.

Fresh focused verification on this recovered source:

- **6 browser-host tests passed in 2.907 seconds**. Coverage includes exact
  Host/Origin/fetch metadata, authenticated bootstrap and bounded commands,
  static traversal/symlinks, archive export/download/import, exclusive workspace
  ownership, real worker cancellation and active shutdown with SQLite integrity.
  Same-port POSIX restart now sends an old token over HTTP and verifies rejection,
  then verifies a new bootstrap token works. A failed cleanup retains its service
  reference and a later close releases the workspace.
- **36 frontend tests across 7 files passed in 4.41 seconds**, covering desktop
  transport preservation, browser bootstrap/capabilities, run/download recovery,
  leave warnings, confirmed shutdown, archive transfer and whole-response
  timeout/unknown-outcome behavior without automatic POST retries.
- TypeScript and production build passed. The existing bundle-size advisory
  remains (approximately 744 KiB JavaScript).
- The real `scripts/browser.py` launcher passed runtime verification, readiness,
  serving built HTML, SIGTERM exit code 0, workspace reopening and SQLite
  integrity. The smoke harness was corrected to skip the expected runtime-check
  banner before looking for readiness; this was a harness parsing correction.

Fresh graphical browser acceptance is still pending. These focused checks are
not another full Python regression, Windows native pass, merge, or release.
Windows/Tauri launch and IPC, engine version, calculations and storage schemas
remain unchanged. Linux native execution and protected secret integrations
retain their fail-closed restrictions. See
[ADR 0030](adr/0030-local-browser-research.md) and
[browser launch instructions](DEVELOPMENT.md#local-browser-research-mode).

## Historical browser adapter acceptance — before source recovery

All results in this section were observed before the validation VM was lost.
They are preserved as historical evidence, not fresh verification of the
recovered source or environment. Fresh recovery checks are recorded separately.

The owner-authorized browser transport uses the existing AppService and managed
workers behind a numeric loopback-only HTTP host. Windows/Tauri launch and
IPC remain available. There is no storage migration, product/engine version
change, financial formula change, new dependency or public deployment.
See [ADR 0030](adr/0030-local-browser-research.md).

- Five focused backend tests passed, covering strict Host/Origin/fetch metadata,
  bootstrap/session authentication, missing and duplicate security headers,
  unsupported CORS, bounded JSON, unknown commands and static traversal/symlink
  rejection. An independent nine-case hostile-boundary probe also passed.
- Authenticated archive export/download/import, repeat session bootstrap, saved
  strategy recovery and changed-export rejection passed against real AppService.
- Real managed-worker cancellation and shutdown with active work passed;
  subsequent reopening recovered cancelled statuses, exclusive ownership was
  released and SQLite integrity was `ok`. Desktop/browser concurrent workspace
  ownership is rejected by the existing shared lock.
- Closing/reloading browser tabs deliberately keeps the host and workers alive.
  Service shutdown is explicit; interrupted writes are never automatically
  retried. Linux native execution and protected secret integrations retain their
  fail-closed limitations.

Frontend focused verification passed **34 tests across 7 files**. A subsequent
whole-response timeout correction passed **13 targeted tests across 2 files**,
including stalled/truncated response bodies and the no-retry contract; these
counts overlap and must not be added. TypeScript and the production build passed
in both the isolated frontend worktree and integrated checkout. The existing
bundle advisory remains (about 744 KiB JavaScript). Independent safety review
reported no remaining blocking issue after the correction. The actual launcher
passed runtime verification, readiness, SIGTERM exit and workspace reopening.

Actual Chromium acceptance on the separate Linux validation workspace passed
launch, catalog loading, four saved reports, reopening the losing forming-H1
report (entry 130, exit 90, quantity 0.769, net PnL -30.76), visible charts/fills,
and reload/reconnection. A new run was started using the visible route
**Synthetic: spot fees golden case → More tools → Custom backtest → Prepared
dataset (three-minute spot fixture) → Run immutable snapshot**. Worker preparation
was displayed, then a new completed report persisted with one trade, entry 100,
exit 110, quantity 1, fees 0.2100 and net PnL 9.79. Existing reports remained
unchanged. The first graphical shutdown succeeded, but immediate restart
revealed a same-port TIME_WAIT bind failure. The host now enables POSIX address
reuse without port sharing; Windows retains its non-reuse setting. The added
same-port restart test verifies a fresh token, workspace reopening, active
listener rejection and no creation of a conflicting workspace. The corrected
five-test host pass succeeded. Independent review additionally verified an old
session token is rejected after restart and the new token works. The corrected
Chromium cycle then passed UI stop, same-port launcher restart after 12 seconds,
reconnection, all five saved reports and reopening the new 9.79 / 0.21-fee report
with the same chart and trade. The host and browser were left open after this
verification.

The legacy tiny synthetic fixtures have no exchange instrument metadata.
Market data's **Use this history** routes to the Library research selection,
not the independent custom editor dataset. Library's existing automatic
metadata request exposes an `instrument` error for these fixtures; this is a
retained fixture/UX limitation, not evidence of a successful Library workflow.
The custom backtest path above remains valid. Origin-aware selection and clearer
metadata errors belong to the subsequent workspace UX slice.

These focused adapter checks reuse the prior verified backend/Windows dispatch
implementation; they are not a new full regression or Windows native pass.


## Recovered Linux adaptation — 2026-10-10

The initial Linux checkpoint was lost with its validation VM. The original
upstream baseline was restored and the bounded adaptation reconstructed. The
backend patch and original Rust host patch match their pre-loss SHA-256 hashes
exactly. Integration files were recreated from recorded edits; documentation now
separates fresh verification from historical observations. This is a new source
checkpoint, not a claim that the lost commit or environment still exists.

Fresh checks on the recovered checkout:

- Official hash-pinned Linux Python wheels installed; `pip check` and platform
  runtime verification passed with Python 3.12.14/NautilusTrader 1.231.0.
- Frozen pnpm 11.19.0 installation passed with install scripts disabled.
- All 88 frontend tests in 21 files passed; TypeScript and production build
  passed. The existing approximately 739 KiB JavaScript advisory remains.
- Four standalone Rust 1.98.1 portability tests passed (platform Python path,
  safe exports arguments, relative-path rejection, unavailable Windows toast).
- Full Python regression: **243 tests in 98.175 seconds**, with **235 passed,
  8 explicit Windows-only skips, no failures or errors**. The skips retain seven
  native-execution acceptance cases and the Windows Job Object lifecycle test.
  Pinned upstream Pandas Timestamp.utcnow deprecation warnings remain.

Native Tauri compilation and the real Rust-to-Python host test passed in the
original environment, but were **not rerun after recovery**. They are historical
evidence only. The original supported-desktop launch failed before a native
window appeared: `/usr/lib/x86_64-linux-gnu/webkit2gtk-4.1/WebKitNetworkProcess`
was absent. A normal system WebKitGTK runtime installation remains necessary;
project-local shared libraries alone do not supply its absolute helper paths.
No sandbox-disabling flags, binary patching or system-security changes are used.

Windows setup scripts, wheel hashes, Cargo.lock and Job Object implementation
remain unchanged. Windows native regression has not been run on this adaptation.
Native Python execution and Windows/sound/Telegram protected-storage integration
are explicitly unavailable on Linux. The Linux supervisor handles service/host
death while the supervisor stays alive; killing the supervisor or escaping its
process group is outside the guarantee. This is not a security sandbox.

Financial formulas, storage schemas and engine version remain unchanged.
See [ADR 0029](adr/0029-linux-research-preview.md) and [Linux setup](DEVELOPMENT.md#linux-source-checkout-research-preview).

## Catalog-wide batch comparison — verified, owner review pending

**Test all strategies** opens every catalog strategy at a common selected set of
timeframes, default 4h and 1d, regardless of search/family filters. All variants
share history, evaluation dates, initial capital, sizing and costs. Each
strategy's current indicator parameters stay fixed across timeframes. Preview
counts ready and unavailable rows separately. Results and frozen inputs use the
existing SQLite batch/run storage; no migration or new dependency is required.
Saved tests adds a shared-settings summary, comparison groups and ascending or
descending metric order. Losses and incompatible rows remain visible.

Windows verification on 2026-09-30:

- `node node_modules/vitest/vitest.mjs run frontend/src/StrategyLibrary.test.tsx frontend/src/LibraryResearch.test.tsx frontend/src/UserJourneys.test.tsx frontend/src/App.test.tsx`:
  **29 passed in 4.60s**, including all seven cards despite filters, shared
  timeframe changes, retained parameters, both sort directions and prior flows.
- `.venv/Scripts/python.exe -W ignore -m unittest tests.test_library_batches tests.test_library_validation tests.test_archives -q`:
  **14 passed in 23.516s**. Covers durable all-catalog matrix contracts,
  cancellation/resume, unavailable native preparation, archive ordinals 11/95
  and rejected 96, saved metrics and later-period validation.
- TypeScript/Vite passed. Review found the batch button inherited a hidden
  stats container at narrow widths; corrected that CSS and rebuilt successfully.
  Final locked offline Windows build passed in 3.57s, with verified pinned
  Python/Nautilus runtime. Existing 738.82 kB bundle advisory remains.
- Native batch selected seven strategies at 4h/daily, reused BTCUSDT spot H4
  history, reserved a common 2024-02-26—2026-09-01 evaluation period, and reviewed
  1,000 USDT / 0.10% fee / 0.05% slippage. Preview showed 16 rows, 14 ready and
  2 unavailable. All twelve graph variants and both passive alternatives
  completed. The two native rows remained incompatible with spot, with reasons;
  final status was `completed_with_errors`, not sixteen successful tests.
- Native Lowest first reordered losses correctly within execution-model groups.
  The application was rebuilt/restarted and the same saved comparison reopened
  with its metrics and original settings, without another test or download.

Selection/archived strategy ordinal bounds are now 96; the 2,000,000 modeled
source-candle budget is unchanged. All eleven timeframes at once may exceed that
budget. Native trust, execution accounting, old results and holdout exclusion
remain unchanged. Full regression and display-scaling sweeps were not repeated;
native evidence used the ordinary wide window, not the narrow CSS breakpoint.
See [ADR 0028](adr/0028-catalog-batch-comparison.md).

## Visible strategy test action — verified, owner review pending

Every **Test this strategy** click opens an explicit backtest setup dialog,
including repeated clicks on the same card. Settings survive dismissal and
history navigation; Start closes setup and opens Saved tests. Changing a
timeframe alone does not run a backtest. Incompatible source intervals now show
an explanation and a compatible resolution before review. Active-work exit
confirmation temporarily suspends setup and restores it on Return.

Windows evidence on 2026-09-30:

- Focused command: `node node_modules/vitest/vitest.mjs run frontend/src/StrategyLibrary.test.tsx frontend/src/LibraryResearch.test.tsx frontend/src/UserJourneys.test.tsx frontend/src/App.test.tsx`.
  Initial 26 checks passed in 4.60s; review identified the native-dialog/exit
  prompt interaction. After its correction and regression test, **27 checks
  passed in 4.61s**. Coverage includes repeated open/close, input retention,
  incompatible timeframes, history return, exactly one explicit batch start,
  navigation and active-work exit handling. IPC is mocked in these tests.
- `node scripts/frontend.mjs build` passed TypeScript/Vite. Locked offline
  Windows Rust build passed in 3.64s; Python 3.12.14 / NautilusTrader 1.231.0
  runtime verification passed. Existing bundle advisory remains (736.28 kB JS).
- Native Windows walkthrough confirmed visible setup, Escape dismissal with
  focus returned to the card, repeated opening, cached H4 history selection
  returning to setup, warmup reservation, Review and Start. A daily Donchian
  batch reached **3/3 completed** and displayed results in Saved tests and on
  its card. Donchian executed; passive rows reused verified cached results.
  No market-history download was needed. The active-work exit/suspend case was
  checked automatically, not repeated as a native cancellation run.

No new dependency, backend computation, schema, version or trust change.
Unchanged broader regression evidence below is retained; no full backend suite
or display-scaling sweep was repeated. Owner usability acceptance remains open.

## Task-oriented usability refinement — verified, owner review pending

Research/Pro navigation is replaced by Strategy library, Market data, Saved tests
and Strategy editor. Cards offer direct testing and explicit comparison;
prepared history returns to preserved selections. Review shows dates, capital
and costs before start. Saved comparisons remain mounted during navigation for
progress/cancellation. Later-period verification has independent data/date
controls; incomplete downloaded coverage cannot enable Continue. Keyboard focus,
plain task labels and bounded catalog/setup panes improve navigation.

Windows evidence on 2026-09-30:

- Focused UI and neighboring checks passed 28 entries in 3.84s after correcting
  an old Results-label assertion. The first pass had 24 passes and that one
  failure. Review corrections added later-period and incomplete-history checks.
- `node node_modules/vitest/vitest.mjs run` passed all 83 entries across 21 files
  in 6.43s. Inspection then removed one accidentally duplicated coverage case;
  the remaining three HistoryWorkspace checks passed in 1.27s. Evidence covers
  **82 distinct frontend tests**, including complete first-test, timeframe,
  saved-result, independent-copy and navigation/cancellation journeys.
- `node scripts/frontend.mjs build` passed TypeScript/Vite after rendering the
  capital summary through its string representation. Locked offline Windows
  Rust builds passed; final shell rebuild took 3.58s. The existing chunk advisory
  remains (734.47 kB JavaScript). No application dependency changed.
- Native inspection exposed a setup pane extending below the viewport; cards
  and setup now scroll independently within the available desktop space. The
  corrected compiled window displayed the full Review and Start actions.
- Native flow selected daily Donchian, reused the existing complete BTCUSDT H4
  snapshot, preserved selection, reserved warmup to 2024-02-26, reviewed 1,000
  USDT / 0.10% fee / 0.05% slippage, and started three real tests. All three
  completed through 2026-09-01. The saved table showed Donchian, Buy & Hold and
  DCA including the negative DCA result. Donchian's report reopened with eight
  trades, its recorded candles and equity; returning preserved the comparison.

Backend calculations and schemas are unchanged from the 222-test checkpoint
below. New UI tests mock IPC and do not establish native cancellation timing or
new-download transport behavior. No additional full backend/live acceptance or
Windows scaling sweep was repeated. Owner usability acceptance remains open.
Reviewed text-only authoring skills and their pins/licenses are recorded in
[ADR 0027](adr/0027-task-oriented-testing-workspace.md).

## Research workspace extension — implementation verified, owner review pending

Branch `codex/research-studio` starts from merged main `a5bb197` (0.6 PR #7).
Product version remains 0.6-dev. Historical acceptance wording below is retained
as checkpoint evidence; this extension is a separate owner review.

Strategy library opens with cards, explicit timeframe comparisons and compact
capital/cost controls. Market data and Saved tests are separate tasks. Strategy
editor retains its independent draft/profile and native trust. Parameter
experiments and live/replay remain under More tools. New
EMA trend and prior-bar Donchian breakout graphs bring the catalog to seven
templates across four families. Source review and test evidence are separate
from profitability; see [Research guide](RESEARCH.md),
[ADR 0025](adr/0025-research-resolution.md),
[ADR 0026](adr/0026-research-workspace-and-trend-candidates.md) and
[all cohort results](library/VERIFICATION.md).

Explicit native 5m/15m/1h/4h/daily spot history drives closed-bar graph backtests
and passive alternatives through retained Nautilus accounting. Dataset coverage,
bar paths, source resolution, fees/slippage and precision are recorded. Exact
complete history reuse is offline; updates reuse checked immutable overlaps and
download missing spans into new snapshots. Contradictory overlaps fail. Charts
page by source candles and preserve recorded indicator/fill times. Native Python,
perpetuals, intrabar evaluation, Position Management, live/paper and parameter
experiments retain M1 where their coarse semantics have not been validated.

Windows validation on 2026-09-30:

- Focused new strategy/graph/coarse checks: 23 passed in 4.473s. The original
  backend checkpoint's seven new tests and financial/data/native neighbors also
  passed after preserving the legacy M1 download mock call shape.
- Combined Python regression: **222 passed in 146.279s** using
  `.venv/Scripts/python.exe -W ignore -m unittest discover -s tests -q`.
- Frontend acceptance covers **77 tests across 20 files**. The combined run passed
  76 and exposed a new test's incorrect history-sort assumption; selecting fixture
  rows by ID corrected it, and all nine App tests passed in 3.75s. Earlier focused
  checks exposed the intentional Donchian catalog count and unsupported test-only
  `exact` query typing, both corrected. No assertions were weakened.
- After a native-observed sticky-panel overlap correction and the saved-comparison
  shortcut, all 11 affected Library/StrategyLibrary tests passed in 3.15s.
- TypeScript/Vite and locked offline Windows/Rust builds passed. The latest Rust
  build took 3.76s. The non-failing frontend chunk-size warning remains (729 kB).
- Public BTCUSDT spot H4 history preparation: 5,844 candles in 3.59s; exact verified
  offline reopening in 0.047s. Six graph strategies at 4h/daily plus two baselines
  all completed over the common 918-day period in **87.72s**. Losing rows are
  retained. Baseline reuse, saved checksums, chart intervals and equity comparison
  passed. This is not an M1-equivalent fill model or a claimed M1 speedup ratio.
- Compiled Windows inspection confirmed Research-first layout, seven cards,
  History coverage, H4 selection and automatic prior warmup. The saved 14-row
  comparison reopened, the Donchian report displayed candles, fills, equity and
  recorded channels, and the independent graph editor opened. Component tests
  use mocked IPC and do not substitute for owner acceptance.

No dependency, product version, database schema or ordinary owner dataset was
changed by this extension. No merge, binary release, Telegram investigation or
new long-running live acceptance is included. Coarse execution changes path
fidelity; it does not establish superior investment returns. Source commit dates
postdate the measured market period; the cohort is retrospective integration.

## Product 0.6-dev — five-strategy candidate awaiting owner acceptance

The authorized Library core contains five independently verified implementations
across trend, mean reversion and momentum: Native EMA trend v2, and explicit graph
adaptations RSI threshold reversion, Bollinger RSI reversion, MACD normalized
momentum and Historical return direction. Thirteen primary-source candidates
were reviewed. Native EMA remains historical/linear-only with explicit source-
bound consent and a disclosed warmup adapter; the four graphs support spot and
linear closed-bar research. No author-recommended interval is invented. See the
[source matrix](library/SOURCES.md) and [strategy evidence](library/VERIFICATION.md).

Library controls freeze source/parameter/timeframe/profile/runtime/data contracts,
preflight asynchronously, and use the existing sequential managed-job slot.
Cancellation retains completed rows; explicit resume runs pending rows only.
Independent accounts use common initial capital and dates. Actual spot Buy & Hold
and scheduled DCA execute through retained Nautilus accounting, with full close,
fees/precision and cash included. Annualization is N/A below 365 days; losses and
no-trade results are retained. Baselines reuse only exact immutable contracts.
See [ADR 0021](adr/0021-passive-benchmarks.md), [ADR 0022](adr/0022-library-batches.md)
and [ADR 0023](adr/0023-native-library-window.md).

Cards/table expose saved metrics, prior-run state, cohort-aware sorting/filtering,
ordinary reports, copy actions and a sampled three-curve equity comparison.
Later-period verification freezes a completed selection before an explicit start,
restarts accounts/baselines on non-overlapping dates, and stays outside selection
ranking/card results. It records attempted variants, holdout reuse and pinned
source dates; it cannot prove external authors had not seen that history.
See [ADR 0024](adr/0024-library-later-period-validation.md).

Final combined verification on the five-strategy/later-period implementation:
**210 Python tests passed in 151.599s; 67 frontend tests across 19 files passed
in 6.81s.** TypeScript/Vite passed; locked offline Windows/Rust build passed in
4.81s with verified Python 3.12.14/NautilusTrader 1.231.0. Final review completed
missing card metrics and filter/delta-sort controls; the affected 7 frontend
checks passed in 3.13s. The affected TypeScript/Vite and Windows build passed (Rust 4.08s) after adding
the filter helper return type required by strict test compilation. Unchanged
Python tests were not repeated for that frontend-only change.

Copied-data compatibility preserved all 20 existing tables and 1,428,407 rows
with matching logical hashes and SQLite integrity. Library tables are additive;
later-period metadata uses existing snapshots. Normal owner data, immutable
artifacts and the experimental runtime lock were not modified. Accepted 0.5.1
source/runtime/executable remain independently runnable.

The bounded common cached BTCUSDT spot cohort (2026-09-01 12:00–24:00 UTC) completed
all four graph strategies at 1m/5m and both alternatives. Native EMA's verified
linear runs on the same dates retain actual separate spot alternatives. Existing
independent benchmark/accounting, native trust, batch parity and cancellation/
resume checks are included in the regression suite. No tuning, new endurance
session or optional sixth strategy was attempted. Compiled Windows smoke displayed all five cards, opened the predeclared frozen
later-period contract, completed its strategy and two baselines, and retained
separate verification labels and disabled selection ranking. The corrected
compiled UI reopened the completed 10-row cohort, displayed full prior-run card
metrics, and filtered momentum rows without hiding their losses/no-trade states.
Earlier compiled copy/stale/equity/report smoke and focused backend chart evidence
are retained for unchanged paths. Remaining non-failing advisories are the
frontend bundle size and native Pandas deprecation; this is not a release or
investment-performance claim.

Maintenance PR #6 was conditionally squash-merged as
`1d6918c939ffa9db7480ee179b12cca6a9ca3368`, with a tree identical to approved head
`69741c7cb990cf94861eef27512b4227d1a4f3e4`. Fresh isolated accepted startup passed.
The following maintenance sections retain the evidence recorded before that merge.

## Product 0.5.1-dev — maintenance candidate awaiting owner acceptance

The authorized ILI-134 maintenance scope is implemented on `codex/051`; owner acceptance and merge remain pending. See [acceptance steps](DEMO_051.md) and [ADR 0020](adr/0020-maintenance-paging-replay.md). No new dependencies, financial execution rules or stored result formats were introduced.

- **ILI-135:** chart paging distinguishes loading, retryable failure, ready and confirmed exhaustion. Failure retains current candles and permits a successful viewport-preserving retry. Focused verification: 6 Python tests passed (11.250s), 8 frontend tests passed (4.49s after one fixture correction).
- **ILI-136:** Results exposes bounded keyset pagination in deterministic newest-first order, with loading/error/empty/end states. A 125-record fixture covers timestamp ties and concurrent newer insertion without duplicates. Focused verification: 2 Python tests passed (1.061s), 7 frontend tests passed (2.93s after one fixture correction). Experiments and saved Live session paging remain outside this maintenance scope.
- **ILI-137:** Replay uses the existing managed worker slot with start/status/progress/completion/error/cancellation and persisted lifecycle. A deliberately slow worker exceeds the old 30-second request duration while ordinary service commands remain responsive. Cancellation never publishes a successful result. Initial focused verification: 10 Python tests passed (39.000s), 24 frontend tests passed (3.13s).
- **ILI-138 combined Windows verification:** `python -m unittest discover -s tests -v` passed **187 tests in 134.687s**; `node node_modules/vitest/vitest.mjs run` passed **60 tests across 17 files in 6.17s**. The pinned CPython 3.12.14 / NautilusTrader 1.231.0 runtime verified. TypeScript/Vite passed (1.41s); a fresh isolated locked/offline Windows/Rust build passed (1m 28s). Existing bundle-size and native Pandas advisories remain non-failing.
- Compiled Windows launch displayed `0.5.1-dev`. Native synthetic smoke verified chart failure followed by successful retry with anchored viewport/current market retained, and Results loading older pages to the end of a 125-record fixture. Background Replay progress and panel navigation remained responsive; the close confirmation exposed return/cancel-and-exit controls.
- The final native cancellation smoke exposed a Windows SQLite WAL lifetime failure. One corrective change keeps a service connection alive through worker termination and terminal-state publication. The affected Python regression rerun passed **10 tests in 38.903s**, including cancellation inside an actual read transaction and SQLite integrity. The corrected diagnostic IPC check ended cancelled without a result or stderr error, and corrected compiled Windows UI smoke displayed `Replay: cancelled`. The full suites and native build above preceded this Python-only correction; only its affected surface was rerun.
- Copied migration verification preserved **19 preexisting tables, 21 runs, 8 strategies and 105 immutable run artifacts**, with SQLite integrity intact. `replay_jobs` is additive. Subsequent read-only comparison confirmed the ordinary data's 19 tables and 105 artifacts unchanged; the experimental Windows lockfile remained unchanged. Destructive checks used isolated synthetic data only.

The corrected native short Replay also completed with **MATCH and 3 independently expected recorded signal events**. The isolated application then closed normally. Publication checks use pinned Gitleaks 8.30.1 on staged changes, the tracked tree and all outgoing commits; no secret findings were detected.

These are automated regression and synthetic Windows lifecycle observations, not owner acceptance, natural-network endurance or production readiness. Valid 0.5 financial and public-market evidence below is retained. No additional 30-minute public-market test or real Telegram delivery test was performed; ILI-37 remains untouched. No authorized issue required deferral to Backlog, no new Linear tasks were created, and product 0.6 was not started.

## Product 0.5-dev — owner-accepted development build

The owner manually accepted the current 0.5-dev build at `c7aae69005df81a5cee09f6ed1c6373c29ddee98` and authorized squash merge through [PR #5](https://github.com/IliaMerkurev/trading-terminal/pull/5). Remaining UI/UX issues are accepted as non-blocking and intentionally deferred; no redesign is part of this merge. Telegram delivery remains outside acceptance. This is an early development build, not stable or production-ready. See [demonstration](DEMO_05.md), [0.5 requirements](../PROJECT.md#21-product-05-independent-market-terminal-and-position-management), [market lifecycle](adr/0018-independent-market-lifecycle.md) and [position policy](adr/0019-shared-position-management.md).

- Market socket ownership is independent from optional strategy history and PAPER. Native 1m/5m/15m/1H/4H/1D chart pages have a confirmed-history cache, bounded recent history, incremental updates and viewport-preserving prepend. The chart never derives coarse history from a partially warmed M1 strategy.
- Optional policy schema 1 shares bounded scaling/DCA, partial TP, trailing, cost-aware break-even, confirmed-primary ATR protections and risk constraints across retained-engine Backtest/Paper. Legacy profiles without the policy retain their old snapshots and behavior.
- Explicit read-only position nodes use pre-decision account context; live records that context for replay. Manual PAPER may start without a strategy, and Add/Reduce25/Reduce50/Close share the same account/journal. Settings, backend protection lines and paged position lifecycle views are integrated.
- Experiments expose validated position axes with fixed risk caps and the same ordinary worker execution. Actual grid candidates equal standalone runs across metrics/fills/trades/indicators/equity; frozen later-period validation retains the policy.
- Merge regression rerun: **182 Python tests passed in 101.558s; 54 frontend tests across 16 files passed in 4.48s.** TypeScript/Vite passed; fresh isolated locked Windows/Rust build passed in **1m 24s**. Existing frontend bundle-size and native Pandas advisories remain non-failing. No dependency or license was changed.
- ATR readiness has a dedicated regression: an initialized value from partial historical warmup cannot enable protected manual actions; current history must finish first. Independent financial/temporal goldens verify weighted long/short entries, scaling after reduction, partial/full exits, fees/funding, cash/equity/margin/liquidation, rounding/rejections, trailing/ATR/cost-aware break-even, historical crossings, observed gaps and future perturbation. Full regressions retain native historical, editor, live/replay/recovery and notification behavior. Mocked notification tests do not establish native delivery.
- Fresh copied additive migration preserved all preexisting table records, result checksums and SQLite integrity. Ordinary user data was not used for tests. The separate synthetic demo completes two managed candidates and one frozen later-period validation.

### Startup evidence and native acceptance boundary

An isolated H1 service reproduction measured the old subscription delay at 88.609s. The first market milestone measured cold chart 1.625s, ticker/book 2.25s and trades 2.578s while causal warmup continued; warm cached chart appeared at 0.047s. These are bounded service timings with PAPER disabled, not UI latency guarantees. Earlier native Windows checks observed no-strategy chart/book/tape, H1 progress with current market retained, historical page prepend and independent market after monitoring pause.

The final automated Windows UI inspection could not complete because the automation helper returned `foreground window did not report a process id`. This is an automation limitation, not evidence of a product failure. Subsequent owner manual acceptance supersedes that blocker for this merge. It does not turn process launch or the service endurance check into automated native control/viewport/responsiveness evidence. No completed automated integrated native 30-minute session is claimed.

### Final public-data service evidence — 2026-09-13

A **31m 0.8s service-only run**, 07:27:53–07:58:54 UTC, observed one public connection, 2,833 ticker updates, 956 forming-M1 updates, 31 finalized M1 candles, 26,360 book updates and 4,818 trades. No natural reconnect or connection error occurred. Deterministic reconnect/reset/gap tests are separate evidence. The recent-trades buffer stayed at 100 rows; the log reached 35 rows. After warmup, interpreter working set stayed at **206.74–207.28 MiB**; one service interpreter with no direct child was sampled, with 26 OS threads (7 Python threads after warmup). This does not measure React/WebView memory or native UI responsiveness. Notifications were disabled in this probe; it does not establish native delivery or notification-storm behavior.

Cold service timing with non-ATR managed PAPER: chart 1.594s, ticker/book/PAPER ready 2.125s, trades 4.328s, H1 strategy ready 93.235s. Required causal history was retained. The recorded virtual lifecycle executed Buy 0.012, Add 0.012, Reduce25 0.006, Reduce50 0.009 and Close 0.009. A smaller preliminary fixture visibly rejected a below-minimum reduction; request processing is labeled separately from fills/rejections in the UI.

A bounded restart restored the same closed PAPER balance, initially required revalidation, and passed explicit revalidation. Cached chart appeared at 0.015s, market at 1.953s and strategy at 2.812s. Market updates continued after strategy pause. Recorded replay matched with **zero new H1 signal events** because the interval contained no new primary-hour close. Nonzero transition/context/future-perturbation proof comes from deterministic tests, not this zero-event comparison.

Actual REST paging also passed on all six supported intervals: 300 recent + 300 older candles each, ordered/contiguous/unique, 12 requests total. Reopening older pages reused the cache without new requests. Owner manual acceptance permits publication of the implementation through PR #5; the measured service evidence remains distinct from unperformed automated native measurements.

Telegram ILI-37 remains intentionally deferred/open. Windows/sound acceptance from 0.4 is retained; Telegram delivery is not claimed. The owner authorized only the 0.5 squash merge and verification, without a release or product 0.6 development.

## Product 0.4 development build — accepted and merged

The owner accepted product **0.4-dev** with real Telegram delivery explicitly unverified. [PR #4](https://github.com/IliaMerkurev/trading-terminal/pull/4) was squash-merged into `main` on 2026-09-12 as `f26cec685d9ef0bf6bd5ac53962ae4935e2604bd`, from the exact accepted head `348fce7324eaf89c14ee8da82aa53f3e19242a65`.

The pre-merge rerun passed **142 Python tests in 74.862s**, **40 frontend tests in 29.26s**, targeted **46 Python tests in 16.043s** and **20 frontend tests in 2.18s**. TypeScript/Vite and the locked offline Windows/Rust build passed (Rust **24.13s**). Gitleaks 8.30.1 found no leaks in the complete tracked tree or all four outgoing commits. The targets cover Live Terminal/chart/editor behavior, live/replay, reconnect/book recovery, manual paper accounting and notification diagnostics. Telegram mocked transport results do not establish delivery.

After merge, the normal main checkout rebuilt successfully (Windows/Rust **6.39s**) and launched as Trading Terminal **0.4-dev** on the ordinary user data root. A fresh backup, copied migration check and post-launch comparison preserved all preexisting table rows, **8 strategies, 21 saved runs and 105 result files**, with SQLite integrity and result checksums intact. Separate demo/live journals were not imported or replaced. No dependency on a temporary acceptance root is required.

Product **0.4-dev** adds the chart-led Live Terminal over the accepted 0.3 engine and shared Strategy IR. It is an early development build, not stable or production-ready. See the [0.4 demonstration](DEMO_04.md), [scope](../PROJECT.md#20-product-04-live-terminal), [shared market state](adr/0016-shared-market-terminal.md) and [manual PAPER semantics](adr/0017-manual-paper-source.md).

Implemented: one centrally owned public ticker/M1/order-book/trade pipeline; fresh/stale market header; forming/final candlestick chart and recorded IR overlays; independent display intervals; snapshot/delta book with 15 displayed levels per side; bounded recent-trades tape; compact settings and switchable terminal panels; manual virtual Buy/Sell/full Close through the retained paper account. Reconnect invalidates the old book/tape and retains confirmed-minute recovery and paper revalidation.

Final regression evidence: **142 Python tests passed in 72.663s**, **40 frontend tests across 13 files passed in 4.14s**. TypeScript/Vite production build and locked offline Windows/Rust build passed (final Rust build 4.17s). The opt-in native toast-history test passed. No dependency version or license was changed. Existing Pandas deprecation and frontend bundle-size advisories remain non-failing.

Deterministic checks include book snapshot/delta/zero removal/order/reset, one subscription set per connection, bounded tape, display interval/IR independence, stored-value and future-perturbation checks, manual spot/perpetual accounting, protection prices, no strategy orders in Manual mode, request deduplication/expiry/restart, restored paper accounting and existing live/replay/recovery regressions. Independent manual spot equity is 1009.79 after 0.21 fees; the perpetual short golden ends at 1019.62 after 0.38 fees. Native checks observed virtual long/short entry/full close, a 5m chart with unchanged 1m/closed strategy and connection, recorded SMA values, panel/settings navigation, minimize/restore and normal paused reopening.

### Real public-market measurement

The compiled Windows terminal monitored public linear BTCUSDT for a **32-minute measurement on 2026-09-11**, starting at 20:36:36 UTC. Its 127 resource samples span 20:36:36–21:08:32 UTC (31.923 minutes between first/last sample); monitoring continued until the final UI capture at 21:09:27 UTC, then paused normally. Final cumulative subscription counters were **34 finalized candles, 1,400 forming updates, 13,248 ticker updates, 63,377 book updates and 27,304 trades**. The subscription began shortly before measurement, so these are cumulative totals rather than exact measurement-window deltas. Strategy evaluation reached 21:09 UTC, chart/book/tape continued updating and the interface remained responsive.

- There was exactly **one successful subscription set** and **no natural disconnect** in this run. A separate deterministic reconnect recovered two missing candles, invalidated old book/tape state and opened exactly two subscription sets. An actual normal restart before measurement recovered one missing candle and required paper continuity revalidation. Missing tape/ticks were not invented.
- Application plus descendant process count stayed **11**. Combined working set was **702.37 → 768.85 MiB**, maximum **776.86 MiB**; combined private memory was **979.61 → 1033.02 MiB**. Python working set was **213.36 → 219.08 MiB**, maximum **219.09 MiB**, and stabilized during the run. Most additional working memory was in WebView. This finite measurement does not prove indefinite memory stability; longer sessions remain an acceptance boundary.
- Chart history, book, trade IDs/tape, event/signal displays, notification queue and manual request history have explicit bounds. No duplicate subscription, retry loop or service error was observed. Automatic notification channels were disabled during the measured session; one explicit native sound Test dispatched successfully. Anti-spam semantics are covered by durable transition/claim tests, not a claim of sustained real notification delivery.
- Paused replay reported **MATCH for all 22 recorded signal events**. A separate consistent journal copy reconstructed **12,387 committed paper observations exactly** and matched its then-current 15 signals. Real manual actions ended flat; recording and replay did not alter ordinary user data. A separate 12.02-second real spot probe also observed ticker, forming candle, book and trade updates; it is not the long-run evidence.
- The prolonged run used integration commit `6313c09`. Follow-up `277d822` changes only chart projection/formatting and strengthens tests: omit a truncated leading coarse candle, constrain indicator samples to visible history, preserve the evaluation timestamp and format funding precisely. The final executable was rebuilt afterward and reopened the saved paused session. Native checks observed its 5m chart, recorded SMA and fresh funding display after recovery; the backend/transport/account used in the prolonged run is unchanged.

The owner accepted the non-Telegram 0.4 functionality. This does not turn unperformed automated checks into measurements: no controlled 100%/125%/150% DPI matrix, physical sleep/wake measurement or multi-hour resource guarantee is claimed. Native Windows toast history was checked; Telegram real delivery was not. Product 0.4 is now in `main` and remains an early development build, not stable or production-ready.

Additive migration on a consistent copy preserved all preexisting records, result checksums and SQLite integrity (8 strategies, 21 saved runs). All public-market/demo work uses isolated data, not the ordinary user database.

**Telegram remains a known acceptance issue (ILI-37).** The request matches the official Bot API; no real delivery root cause was established. Safe actionable HTTP/API/network/TLS diagnostics were added and malicious-response tests pass. Credentials remain in Windows Credential Manager. No real Telegram delivery success is claimed; a new owner Test notification is required. Windows and sound behavior retain their separate accepted baseline.

## Product 0.3 development build — acceptance evidence

Product **0.3-dev** is accepted by the owner with Telegram delivery as an explicit exception. It is an early development build, not stable or production-ready. See the [0.3 demonstration](DEMO_03.md) and [scope](../PROJECT.md#19-product-03-live-monitoring-and-paper-trading).

**Verified:** Live Bybit monitoring, reconnect/recovery, Windows notifications, sound notifications, paper trading, Live/Replay consistency and node deletion. The owner completed manual acceptance of the non-Telegram functionality in addition to the automated evidence below.

**Known issue — Telegram:** notification integration is implemented, but owner acceptance is currently failing. Test notification did not deliver despite credentials configured through the UI. Windows notifications and sound are verified. Telegram delivery remains open for investigation in [ILI-37](https://linear.app/ilia-merkurev/issue/ILI-37/fix-telegram-notification-delivery-after-03-owner-acceptance); ILI-30 remains In Review. Automated transport tests do not establish successful delivery.

Pre-merge regression rerun: **121 Python tests passed in 54.336s**, **28 frontend tests passed in 24.32s**, TypeScript/Vite production build passed, and the locked offline Windows/Rust build passed in **19.91s**. Targeted runs passed **29 Python tests** covering shared signals/replay, deduplication, recovery, paper accounting and notification isolation, plus **14 frontend tests** covering deletion/Undo/Redo and Live. The opt-in native Windows toast-history test passed again. Sound audibility is verified by owner acceptance, separately from automated dispatch checks. The existing frontend bundle-size advisory remains non-failing.

- Shared historical/live/replay Strategy IR, confirmed-minute closed/forming evaluation, false-to-true event transitions, atomic recording and durable at-most-once notification claims are implemented. Independent goldens and future-perturbation checks pass.
- Public Bybit spot/linear ticker and M1 subscriptions, stale/duplicate/out-of-order checks, heartbeat, bounded reconnect backoff and complete REST gap reconstruction are implemented. A 10-minute actual linear session recovered two missing candles after an interruption injected only into its own socket. Exactly two successful subscription sets were opened (initial and reconnect).
- That session recorded **4,105 observed paper inputs** and **6 signal events**; fresh replay matched all six. Paper entry/exit and explicit post-gap revalidation ran. Sampled Python working set increased from **199.9 to 204.1 MiB**, with a 204.1 MiB maximum; this bounded observation is not an always-on memory guarantee. The worker stopped normally.
- Paper uses the retained Nautilus account/risk/protection and position policy with later observed executable quotes, explicit costs, mark and confirmed funding. Tests verify independent long/short balances, fees/slippage, gap stops/takes, mark liquidation, delayed funding, restart without double charging and write-failure safety. Missing ticks are never manufactured from historical candles.
- Live dashboard, frozen session settings, saved-session selection, signal/event history, paper account/fills, recovery controls and replay verification are implemented. Native Windows checks observed actual spot updates, signal state, a virtual position, minimize/restore, normal shutdown and paused state on reopening.
- Windows toast/sound and direct Telegram dispatch have separate controls and bounded error isolation. A real Windows Credential Manager synthetic write/read/clear passed. The opt-in Rust test confirmed a real toast was retained in **this application's** Windows notification history. Subsequent owner acceptance verified Windows and sound, but Telegram Test did not deliver.
- Delete/context Delete share one operation, preserve fixed outputs, clean edges and support Undo/Redo. Component tests cover multiple selection and typing guards. Native Delete, Undo/Redo buttons, both context menus and restored connections were checked. Controlled node measurements are preserved to prevent an initially blank canvas.
- **121 Python tests passed in 51.809s; 28 frontend tests passed.** TypeScript/Vite and the locked offline Windows Rust build passed (4.13s). Seven focused transport/manager tests passed after tightening stale-ticker/forming-order validation. Existing native Pandas deprecation and frontend bundle-size advisories remain non-failing.
- Additive migration on a consistent copy preserved every preexisting table row/hash, immutable result checksums and SQLite integrity. Ordinary user data was not used for experiments. New live/paper tables do not rewrite 0.1/0.2 records.
- The isolated offline demo checks three signal timelines (2/2/1 events), replay equality and independently expected paper equity **1009.79**. Synthetic labels and data roots remain distinct from public market recordings and user data.

### Owner acceptance and evidence limits

The owner accepted non-Telegram functionality; Telegram Test remains failed and requires a later delivery check. Earlier automation did not demonstrate localized physical keyboard chords, a controlled 100%/125%/150% scale matrix or physical sleep/wake. Owner acceptance does not retroactively turn those into measured automated checks. Stale/gap reconstruction is covered deterministically and by the isolated public-connection interruption. No system setting was changed to manufacture a pass.

Live accepts visual IR only; compatible native Python remains historical-only and fails visibly if selected for Live. Forming-primary semantics advance at confirmed M1 boundaries, not every live tick. Funding-history delays can pause account processing while observed quotes queue; missing funding continuity or exhausted retries require review. At-most-once notifications can be missed after an uncertain crash outcome. This is one active instrument/strategy session, without real orders, exchange trading credentials, cloud service, background daemon or installer.

## Historical accepted main baseline: 0.2 development build

Product milestones previously called V1 and V2 are now 0.1 and 0.2. These names never meant stable 1.0/2.0 releases. Protocol/schema/profile integers and ADR numbers are unchanged. The normal main checkout builds and launches `Trading Terminal`, with `0.2-dev` shown separately from the permanent window title. Product version comes from Cargo package metadata; no temporary parallel checkout is required.

The versioning/housekeeping verification passed **92 Python tests in 43.867s**, **20 frontend tests in 23.57s**, TypeScript/Vite and the offline locked Windows/Rust build (**30.29s**). The compiled main application opened with the ordinary data root and the expected title/version badge. A fresh backup and copied migration check preserved **17 runs and 8 strategies**; the ordinary additive migration also preserved all rows and result checksums. Synthetic demonstration data stayed separate. The frontend bundle-size advisory remains; no dependency upgrade, installer or release binary was introduced.

## Accepted 0.2 milestone history

0.2 passed owner acceptance and was squash-merged into main through [PR #2](https://github.com/IliaMerkurev/trading-terminal/pull/2), commit `1309b4a1f97e2cb889240f510abf707ee94e6740`, on 2026-09-11. 0.1 behavior and data remain supported. The [product specification](../PROJECT.md) remains authoritative. The [0.2 demonstration](DEMO_V2.md) and [retained 0.1 demonstration](DEMO.md) distinguish automated verification from native/manual acceptance.

The mandatory pre-merge checks were rerun on the exact accepted 0.2 head: **92 Python tests passed in 73.457s**, **20 frontend tests passed in 34.68s**, TypeScript/Vite passed, and a separate offline locked Windows/Rust build passed in **1m 35s**. Runtime verification and `pip check` passed. Gitleaks 8.30.1 found no secrets in either outgoing 0.2 commit. The existing frontend bundle-size advisory remains. No installed dependency, user database or running build was replaced.

The owner reported successful manual 0.2 verification and accepted the remaining review items. The observations below retain the original automated/native evidence and its limitations; owner acceptance does not retroactively turn unperformed automation scenarios into executed tests. No installer, release or 0.3 scope is included.

## 0.2 evidence — 2026-09-11

- Profile version 2 adds continuous intraminute protection crossings; version 1 retains discrete observations. Independent long/short 95/105 versus 80/120 goldens, gaps, fees/slippage, funding/mark liquidation and partial-H1 future perturbations pass. See [execution model](adr/0010-execution-v2.md).
- Sequential parameter grids, immutable editor/runtime/data snapshots, cancellation/errors/interruption and frozen later-period validation use the same worker service. Actual Windows tests compare a 2×2 grid with four independent runs, and OOS with a standalone window run. Altering only future OOS candles leaves IS metrics/ranking and frozen graph/parameters unchanged. Shared source candles are not duplicated per combination; archives retain research provenance. See [experiments](adr/0011-experiments.md).
- Context-menu search, keyboard selection, graph history/duplication/validation, compact fill groups, viewport preservation and comparison labels are implemented. Component tests use mocked React Flow transforms/IPC and do not establish native Windows scaling or picker behavior.
- The full Python suite passed **92 tests in 41.302s**. The final frontend suite passed **20 tests across 10 files in 16.96s**. TypeScript, production Vite build and offline locked Windows Cargo build passed using the existing tools. No dependency was added or updated. The approximately 651 KiB JavaScript bundle still produces a size advisory.
- Additive migration on a separate consistent 0.1 copy preserved **17 runs and 8 strategies**, all existing records/result checksums and SQLite integrity. Existing environments and the running older build were preserved; no destructive migration is required.
- The synthetic 16-combination demonstration plus one frozen OOS validation and matching standalone run completed in **28.194s**, with **140.0 MiB sampled combined service/worker working set**. This is a bounded 240-minute fixture, not a guarantee at the maximum grid/history size. The limits are validated before materializing a grid: 256 combinations and 2,000,000 minute-runs including warmup. No date range is silently truncated to satisfy a budget.

The final compiled 0.2 window opened with its separate synthetic workspace and a working service connection. Actual native checks verified full-name context search, Enter creating exactly one selected node at the original click, Undo/Redo, independent node duplication and visible disconnected-input validation. The saved 16/16 experiment reopened, its candidate report displayed candles, fill markers and equity, and its frozen candidate displayed separate IS/OOS metrics matching the recorded demo. Two automation drag attempts produced no visible movement; native dragging and one-drag Undo remain unverified. Native Windows picker import, visibly active cancel-and-exit, and actual 100%/125%/150% scaling also remain manual 0.2 acceptance checks. No other application or system scaling was changed for testing. The separate development build/demo is ready for those checks; no installer, binary release or 0.3 work is included.

## Retained 0.1 evidence

## Implemented and tested

| Area | Evidence |
| --- | --- |
| Engine and account model | [ADR 0001](adr/0001-engine.md), [ADR 0002](adr/0002-simulation-profile.md); independent spot/perpetual long/short, sizing, costs, funding, mark liquidation and protection fixtures |
| Causal strategy graphs | [ADR 0003](adr/0003-strategy-ir.md); all 0.1 indicators/operators, typed acyclic IR, partial H1 and future perturbation tests |
| Public history and replay | [ADR 0004](adr/0004-data-manifests.md); separate trade/mark/funding, hashes, coverage/gaps and repeated offline results |
| Managed calculations | [ADR 0005](adr/0005-workers-storage.md); snapshots, SQLite history, bounded IPC, actual Windows worker-tree cancellation |
| Native Python | [ADR 0006](adr/0006-native-import.md); AST-only preview, source-bound consent, installed licensed EMA example, declared multiple native bar timeframes and visible unsupported behavior |
| Desktop research UI | [ADR 0007](adr/0007-desktop.md); editor/settings, downloads, real workers, saved charts/indicators, trade navigation and window lifecycle |
| Comparison and archives | [ADR 0008](adr/0008-archives-comparison.md); input/version differences, JSON-only bounded archive, fresh imported IDs, nonexecuting import and omitted history |

## Executed Windows checks

On 2026-09-11, `.venv/Scripts/python.exe -m unittest discover -s tests -v` passed **79 tests in 14.818s**. A separate newly created Windows Python environment installed all **17 hash-pinned packages** from verified wheels, passed `pip check`, and passed the same 79-test suite in 14.937s. The existing environment was preserved.

`node node_modules/vitest/vitest.mjs run` passed **8 tests across 6 files**. These cover typed graph wiring, save/native consent behavior, stored-value chart projection, comparison, exact archive File chunk transfer, sequential polling, and cancellation-before-desktop-exit ordering. Component tests mock IPC and are not native desktop automation.

`./scripts/setup.ps1` completed with the configured toolchain. `./scripts/launch.ps1 -NoLaunch` passed TypeScript, the production frontend build and locked offline Windows Rust build using existing MSVC/SDK. The frontend emits a 500 KiB chunk-size advisory (approximately 630 KiB JavaScript before compression); it is not a build failure.

Actual compiled desktop checks verified graph save into SQLite, a real cached BTCUSDT spot run, restart/reopening, visible candles/fill markers/equity, trade-to-chart navigation, comparison and export. A fresh public BTCUSDT spot day downloaded through the UI with **1,440 candles and complete requested coverage**. Active minimize/restore continued the worker to completion. Closing while active displayed the return/cancel dialog; returning preserved work. Completed-run exit closed the application.

One real BTCUSDT day for each market was previously downloaded and replayed twice offline with identical normalized results. The integrated spot example produced five completed trades, final equity 999.31274578 and fees 0.99993082 USDT; this is verification evidence, not a recommendation. The four offline demo cases separately pass hard-coded independent PnL/trade expectations.

## Performance and limits

A seven-day, 10,080-minute synthetic intrabar fixture measured **1.464s**, **260.5 MiB peak working set**, and **9.13 MiB normalized JSON** on Windows. A 30-day synthetic dataset also completed in the compiled desktop lifecycle checks. These are bounded measurements, not a guarantee for arbitrary native strategies or long histories. Run one calculation at a time; chart windows and IPC pages are bounded. Larger-scale memory budgets need further measurement before expanding supported workloads.

The model implements one single-position cross-margin profile, not full Bybit UTA or isolated margin. Minute paths and historical precision/risk-tier assumptions are explicit. Historical tier changes remain unknown. Native workers are not security sandboxes. Unsupported orders/feeds or unavailable dependencies fail visibly. Archives omit raw history and logs; checksums do not authenticate imported performance claims. No installer or binary release is provided; the project license remains undecided.

## Historical 0.1 acceptance notes

The native Windows file-picker import and a cancel-and-exit click before a desktop calculation finishes remain manual acceptance checks. The automation helper could not address the WebView-owned picker; bounded calculations completed before the exit click. Backend archive roundtrip, browser File transfer, close-dialog IPC ordering and actual worker cancellation pass independently. These observations do not establish that the unperformed native actions were tested.

Review the complete [demonstration](DEMO.md), including source trust, edited strategy wiring, indicator display and usability. Owner acceptance is distinct from implementation and automated checks. Deferred live trading, AI, optimization, DCA, multiple instruments and other post-0.1 features remain outside this build.
