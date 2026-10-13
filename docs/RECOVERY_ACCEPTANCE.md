# Recovery completeness and acceptance

## Conclusion

All 88 documented acceptance rows have recorded reconstruction evidence within the scopes below. No known documented functional omission remains in the scoped reconstruction.

This is functional reconstruction from the published baseline and preserved specifications. It does not establish byte-for-byte identity with the unavailable original source, or interoperability with authentic unavailable old-format databases. Synthetic recovery work did not establish any loss of the owner’s local Windows data.

## Final integrated evidence

- Tested commit: `741ad08b6465447e5716928ba5ee042677f8327c`; tree `a7d658ffd6980e1b29aa250d1bc116a1574efe5d`.
- Python: confirmation: 812 discovered, 804 passed, 8 Windows-only skipped, zero errors; 258.773 seconds; exit 0. TypeScript tests: 1,008 passed across 83 files on 0a115f1; 83.66 seconds; unchanged frontend source reused. Build: TypeScript no-emit and Vite production build passed on 0a115f1; unchanged frontend source and all three dist hashes match the actual-GUI seal.
- Earlier checkpoint hashes, exact commands, discovered defects and corrective evidence remain in [the recovery record](RECOVERY.md). Counts from overlapping runs are not added together.

## Complete verification chronology

- Initial full Python sweep on `0a115f1ca7b8b237dcfd3982b733a8f342f174c3`: 804 tests, 792 passed, four shutdown errors, eight Windows-only skips. It was a failed run, not retrospectively relabeled.
- Shutdown persistence/cancellation ordering was corrected. Frozen `001acc049b78a8b9b9f887b42d73410deba6ec77` passed 53 distinct author-focused checks and six independent fault/timeout/idempotence checks. These counts overlap and are not summed.
- The authorized full backend confirmation on the final tested commit above passed: 812 discovered, 804 passed, eight Windows-only skipped, zero errors, 258.773 seconds, exit 0. The publisher verified equivalent remote commit `48eaf298472df62231f0ddde5ec140e15e4fcb69` against the exact same tree.
- The complete frontend suite remained 1,008/1,008 across 83 files. Frontend source was byte-unchanged by the shutdown correction, so its successful TypeScript/build and actual-browser evidence were reused rather than rerun.
- Seven skipped checks require Windows Job Object containment; the eighth is Windows worker lifecycle acceptance. They remain unverified, not passing tests.

## Evidence limits

- Actual browser work used an isolated synthetic Service workspace. It included real rendered charts and genuinely observed synthetic close receipts; it did not exercise real exchange connectivity or place orders.
- Recorded IR/overlaid volume placement, cancellation/network uncertainty, queue overflow, shutdown races, missing-target fallback and some formula boundary combinations are automated-only. The final baseline suite is broader than the manual walkthroughs.
- Native Windows packaging, owner-led acceptance, real providers, original-source byte identity and authentic old-database migration remain unverified. These are separate from a known missing documented feature.
- Previously accepted reconstructed v1 definitions and complete replay hashes were preserved across the additive agreement extension. That compatibility proof does not substitute for original database fixtures.
- No new strategy conversion, notification transport, dependency, license or product-version change was part of recovery.

## All 88 acceptance rows

“Recorded scope” means the automated/browser evidence named for that section, with the limits above. A row is not a claim that every possible combination was manually exercised.

### Pane layouts

[Pane layout ADR](adr/0054-compatible-chart-pane-layout.md)

Independent 9 Python + 3 TypeScript; applied layouts, presets, drafts, hide/show and restart checked in the actual browser. Recorded IR and volume placement are automated-only.

| ID | Required behavior | Status |
|---|---|---|
| PANE-01 | Schema 1 stores relative price/recorded weights, stable pane order and memberships; atomic revision with indicator settings. | Accepted in recorded scope |
| PANE-02 | Unit-compatible grouping: RSI/Stoch 0–100; MACD/Momentum price differences; ATR/stddev separate price-distance unit. | Accepted in recorded scope |
| PANE-03 | VMC B is independent bipolar pane, all seven series move together. | Accepted in recorded scope |
| PANE-04 | Price first; Recorded IR independent and last; physical Lightweight Charts creation order obeys saved order. | Accepted in recorded scope |
| PANE-05 | Price400/B240 are relative weights; hidden panes free space and restore prior order/weight. | Accepted in recorded scope |
| PANE-06 | Additional panes linear; price log/manual mode and overlaid volume independent scale remain intact. | Accepted in recorded scope |
| PANE-07 | Apply/Cancel jointly handle layout and indicators; draft survives context navigation. | Accepted in recorded scope |
| PANE-08 | Preset captures layout and preserves correct membership identity; remap membership only if staging remaps instance IDs. | Accepted in recorded scope |
| PANE-09 | Preset extension compatibility and metadata preservation follow ADR0053; invalid stored settings cannot become Save current fallback defaults. | Accepted in recorded scope |
| PANE-10 | Layout-only edits cannot change origins/formula outputs or create fixed quantity cap. | Accepted in recorded scope |

### Frozen alerts, runtime and controls

[Core ADR](adr/0055-frozen-local-indicator-alert-core.md), [runtime ADR](adr/0056-passive-local-alert-runtime.md)

Independent 9 core + 10 runtime + 9 rendered UI cases, guarded actual Service/Hub tests, genuine observed-close GUI event and restart. Overflow, uncertain-write and shutdown races are automated-only.

| ID | Required behavior | Status |
|---|---|---|
| ALERT-01 | Frozen rule captures ports, normalized finite parameters, origins, formula contracts and exact source/market/symbol/native timeframe. | Accepted in recorded scope |
| ALERT-02 | Threshold/cross-above/cross-below/confirmed VMC B divergence; ALL/ANY up to16 conditions. | Accepted in recorded scope |
| ALERT-03 | Uses confirmed raw OHLC, not HA/style/pan; VMC divergence at pivot+2 confirmation. | Accepted in recorded scope |
| ALERT-04 | Durable revisions, recoverable archive/restore, startup paused; saved rule never armed implicitly. | Accepted in recorded scope |
| ALERT-05 | Arm reviewed checkbox then explicit async Arm warms baseline, emits no historical/backfilled events. | Accepted in recorded scope |
| ALERT-06 | Hide/delete original instance does not invalidate frozen calculation; changed surviving parameter requires reviewed paused rebind. | Accepted in recorded scope |
| ALERT-07 | Journal insertion and cursor advance atomic; dedup across repeated delivery/arm/session. | Accepted in recorded scope |
| ALERT-08 | At-most-once banner claim; durable read/unread state; lost response may omit banner without losing journal. | Accepted in recorded scope |
| ALERT-09 | Immutable MarketHub receipt queue bounded3, epoch/generation/sequence/freshness/provenance fail closed. | Accepted in recorded scope |
| ALERT-10 | Cache-only full-origin replay; context/Pause/close fences join async work. | Accepted in recorded scope |
| ALERT-11 | Uncertain create quarantined across reload/context; Pause before Arm; null-context UI reload fence. | Accepted in recorded scope |
| ALERT-12 | Market exit/context change/restart stop monitoring; browser-tab closure alone does not stop Service. | Accepted in recorded scope |
| ALERT-13 | Saved/Archived same-value selector preserves rows; paged journal works. | Accepted in recorded scope |
| ALERT-14 | Banner/journal use stable rule ID plus CURRENT name, not immutable historical name. | Accepted in recorded scope |
| ALERT-15 | Local journal/banner only; no external transports, strategies, PAPER or orders. | Accepted in recorded scope |

### Original event evidence

[History backend ADR](adr/0058-cache-only-alert-history-evidence.md), [research interface ADR](adr/0060-detached-frozen-rule-research-ui.md)

Independent history backend/UI packs plus actual original-event chart, current-cache warning and frozen values. Missing/byte-clipped targets and divergence timing have automated evidence.

| ID | Required behavior | Status |
|---|---|---|
| EVIDENCE-01 | Read-only Original alert evidence has original identity, confirmation/observation times, frozen conditions, previous cross values, parameters/origins. | Accepted in recorded scope |
| EVIDENCE-02 | Exact raw open = confirmation close − native width; divergence pivot remains separate supporting evidence. | Accepted in recorded scope |
| EVIDENCE-03 | Original saved condition values authoritative; adjacent OHLC from current cache explicitly may differ. | Accepted in recorded scope |
| EVIDENCE-04 | Separate chart never changes live context, drafts, layout, Arm, journal, unread or banner. | Accepted in recorded scope |

### Immutable historical research

[History backend ADR](adr/0058-cache-only-alert-history-evidence.md), [research interface ADR](adr/0060-detached-frozen-rule-research-ui.md)

Independent 8 backend + 12 rendered UI scenarios; actual 60-hit run, three pages, exact target, native edited dates, draft preservation and restart. Cancellation and uncertain responses are automated-only.

| ID | Required behavior | Status |
|---|---|---|
| HISTORY-01 | Separate asynchronous cache-only scan freezes rule revision, raw prefix and formula outputs in durable run. | Accepted in recorded scope |
| HISTORY-02 | Inclusive UTC confirmation-close range; visible edited dates survive late coverage response. | Accepted in recorded scope |
| HISTORY-03 | Full replay from origin includes warmup; missing origin/gap/unconfirmed/conflicting/version data fails visibly. | Accepted in recorded scope |
| HISTORY-04 | Resource preflight10000 raw inputs/256MiB; max8 unfinished tasks. | Accepted in recorded scope |
| HISTORY-05 | Cancellable jobs, request-ID readback after uncertain response; restart marks unfinished interrupted. | Accepted in recorded scope |
| HISTORY-06 | Cancel pending clears only authoritative cancel_requested=false. | Accepted in recorded scope |
| HISTORY-07 | Immutable stored result independent of live journal/cursor/unread/banner/Arm. | Accepted in recorded scope |
| HISTORY-08 | Hits pages20; chart windows≤200 under byte limit; chart markers include all hits in chart window. | Accepted in recorded scope |
| HISTORY-09 | Target jump preserves40 preceding context or exact fallback when byte-shortened page excludes target. | Accepted in recorded scope |
| HISTORY-10 | Compact hit list180px; exact UTC/open/confirmation and lower frozen indicator pane. | Accepted in recorded scope |
| HISTORY-11 | Saved scans reopen without recomputation; cancelled/failed/interrupted never advertised full coverage. | Accepted in recorded scope |
| HISTORY-12 | Known-cross fixture is specification, not inherited pass. | Accepted in recorded scope |

### Current indicator agreement

[Shared evaluator ADR](adr/0057-pure-indicator-agreement-core.md), [current panel ADR](adr/0059-current-indicator-agreement-panel.md)

Independent 48 vectors including 28 boundaries, 7 threshold cases and cross-language parity; 8 panel checks; actual raw-clock, grouping, draft/hidden/duplicate, historical suppression and recent-pan GUI. Pending-page defect was corrected and rechecked.

| ID | Required behavior | Status |
|---|---|---|
| CURRENT-01 | Compact below-chart summary always visible; details initially collapsed, keyboard operable, per-row reasons. | Accepted in recorded scope |
| CURRENT-02 | Only visible applied instances vote; hidden entries excluded; drafts ignored. | Accepted in recorded scope |
| CURRENT-03 | Common latest confirmed RAW close; no forming/hover/pan/HA influence; no fallback older value. | Accepted in recorded scope |
| CURRENT-04 | Detached history suppresses current scores with Return to latest; no hidden latest fetch. | Accepted in recorded scope |
| CURRENT-05 | Pause/stale/loading/error/inactive/unsaved operation/context/revision/origin/time mismatch suppresses. | Accepted in recorded scope |
| CURRENT-06 | Exact type+normalized-parameter duplicates count once; variants equal within type; types equal within group; groups equal overall. | Accepted in recorded scope |
| CURRENT-07 | Neutral in denominator; unavailable/hidden/context/unsupported excluded; overall≥2 groups and≥50% fully available supported visible types. | Accepted in recorded scope |
| CURRENT-08 | Type and variant coverage distinct; largest-remainder integer display totals100. | Accepted in recorded scope |
| CURRENT-09 | Trend close vs SMA/EMA/WMA/RMA/VWMA/HMA/VWAP/SAR and BB/Donchian/Keltner middle; equality neutral. | Accepted in recorded scope |
| CURRENT-10 | Supertrend ±1 only; DMI DI comparison only ADX≥20 otherwise neutral. | Accepted in recorded scope |
| CURRENT-11 | Momentum RSI/StochK >55/<45; MACD histogram/ROC/Momentum signs; CCI >100/<−100; %R>−45/<−55; BB%B>.55/<.45. | Accepted in recorded scope |
| CURRENT-12 | Volume MFI>55/<45; CMF>.05/<−.05; OBV change from directly preceding close. | Accepted in recorded scope |
| CURRENT-13 | Flat raw guards: RSI period+1 closes; Stoch period+smooth−1; Williams period high/low. | Accepted in recorded scope |
| CURRENT-14 | ATR/stddev/BBwidth/Volume context; Ichimoku/StochRSI/threeVMC types directional unsupported only. | Accepted in recorded scope |
| CURRENT-15 | Uses existing display-formula response, no second engine/provider/history monitoring. | Accepted in recorded scope |

### Frozen agreement alerts and timelines

[Frozen agreement backend ADR](adr/0061-frozen-agreement-alert-history-backend.md), [editor/timeline ADR](adr/0062-frozen-agreement-editor-timeline.md)

Independent 8 backend + 8 rendered UI cases; arithmetic oracle checks all 482 rows, 60 Up and 60 Down edges; actual four lanes, exact selection, conflict, observed live edge/sustained truth and restart. Corrupt-rule fence and resource admission have automated evidence.

| ID | Required behavior | Status |
|---|---|---|
| AGREEMENT-01 | Shared manifest indicator-agreement-v1 / equal-group-type-variant-v1 defines rules/ports/guards/weights; frozen hash. | Accepted in recorded scope |
| AGREEMENT-02 | Additive op agreement accepts legacy strict checkpoints; direction up/down, inclusive unrounded fraction0..1. | Accepted in recorded scope |
| AGREEMENT-03 | Each selected required group must be strictly>50% chosen direction; no selection adds no group constraint. | Accepted in recorded scope |
| AGREEMENT-04 | Capture visible eligible member IDs/normalized params/same origin/formula/contracts; stale open draft blocks save until refresh. | Accepted in recorded scope |
| AGREEMENT-05 | Graph hide/move/add/delete never rewrites frozen membership/history; changed source params require paused rebind. | Accepted in recorded scope |
| AGREEMENT-06 | State-only known false→true emits once; repeated true none; unknown resets baseline; unknown→true none. | Accepted in recorded scope |
| AGREEMENT-07 | Mixed impulse/state ALL/ANY preserves existing truth semantics at same close. | Accepted in recorded scope |
| AGREEMENT-08 | Per-close frozen overall/groups/types/variants/member reasons/coverage/truth recorded beyond hits. | Accepted in recorded scope |
| AGREEMENT-09 | Four-lane overall/trend/momentum/volume chart: stacked directions, distinct unknown, hit markers, opposing-majority conflict. | Accepted in recorded scope |
| AGREEMENT-10 | Exact confirmation selector with previous/next; raw price axis labels open separately. | Accepted in recorded scope |
| AGREEMENT-11 | Definition and active rules256KiB; page≤600KiB; preflight includes each bar/condition/member cost. | Accepted in recorded scope |
| AGREEMENT-12 | Rolling raw support avoids quadratic prefix replay; identical formula dependencies deduplicated. | Accepted in recorded scope |
| AGREEMENT-13 | Known agreement fixture is specification, not inherited pass. | Accepted in recorded scope |
| AGREEMENT-14 | No new strategy conversion/probability claims/trading/external notifications. | Accepted in recorded scope |

### Preserved published functionality

[Development and tests](DEVELOPMENT.md)

The final named offline Python/TypeScript suite and production build cover the existing executable contracts. Unchanged baseline source is supporting evidence, not a substitute for executing tests. Detailed baseline map follows.

| ID | Required behavior | Status |
|---|---|---|
| REGRESSION-01 | 33 indicator types incl licensed VMC B Core/A/Swing; no fixed instance quota incl hidden. | Accepted in recorded scope |
| REGRESSION-02 | 10k replay/1800 visible rows,64MiB serialized,256MiB work estimate,64KiB checksummed transfer chunks; atomic saves. | Accepted in recorded scope |
| REGRESSION-03 | Stable calculation origins and raw formulas; hidden instances stored but not calculated/rendered. | Accepted in recorded scope |
| REGRESSION-04 | Presets immutable content, rename title only, Duplicate/Save as; Trash/Restore uniqueness, selection not apply. | Accepted in recorded scope |
| REGRESSION-05 | Drafts context-scoped in current session; applied settings survive reload; drafts do not survive full reload. | Accepted in recorded scope |
| REGRESSION-06 | Candles/HA/Line preserve drawings/zoom/drafts; style ephemeral→Candles reload; HA raw coordinate carrier even empty. | Accepted in recorded scope |
| REGRESSION-07 | Ichimoku causal projected timestamps/cloud/chikou, no fake raw candles; Supertrend gaps not bridged, SAR dots. | Accepted in recorded scope |
| REGRESSION-08 | VWAP UTC day/anchor aligned input and full origin; partial date UI handling. | Accepted in recorded scope |
| REGRESSION-09 | VMC causal pivot+2, body-flow not standard MFI, FastWT not VWAP, licensed provenance preserved. | Accepted in recorded scope |
| REGRESSION-10 | Return latest preserves width/manual/log/drawings/drafts; following distinct from freshness; stale async fences. | Accepted in recorded scope |
| REGRESSION-11 | Older-page eviction restores fully lost viewport only after success, preserves partial anchors and intentional whitespace. | Accepted in recorded scope |
| REGRESSION-12 | Focus chart keeps same chart/drawings/undo/drafts; sticky exit/source/status; Escape hierarchy. | Accepted in recorded scope |
| REGRESSION-13 | Catalog search/categories/favorites/paging9, keyboard focus, compact instance editor, atomic Apply. | Accepted in recorded scope |
| REGRESSION-14 | Seven drawing types, ruler, move/point/style/snap/hide/lock/undo/redo; names and Fib custom levels. | Accepted in recorded scope |
| REGRESSION-15 | Volume default price overlay independent scale, explicit removed indicator not auto-restored. | Accepted in recorded scope |
| REGRESSION-16 | Original Market/Lab/report/profile/observation/import data contracts remain supported by published base. | Accepted in recorded scope |
| REGRESSION-17 | Archive partial imports disclose surviving IDs; no auto retry/resume/rollback or false100% success. | Accepted in recorded scope |
| REGRESSION-18 | No provider/PAPER/order work, dependencies/version/main/PR/release changes for reconstruction. | Accepted in recorded scope |

## Baseline regression map

| Ledger rows | Existing executable evidence to map in final run | Existing fresh evidence and limits |
| --- | --- | --- |
| REGRESSION-01–03 | `test_display_indicators.py`, `test_indicator_transport.py`, `ChartIndicators.test.tsx` | Pane checkpoint reran transport and display-adjacent checks. Independent pane tests preserve formulas/origins and reject non-atomic writes. Mapped to the final named suite. |
| REGRESSION-04 | `test_chart_presets.py`, `IndicatorPresets.test.tsx`, `ChartPanes.test.tsx` | Root pane GUI covered named Save/Stage/Cancel/Apply and stable IDs, reload/restart; independent pane checks cover extension preservation. Preset concurrency/name collision coverage is automated. |
| REGRESSION-05 | `IndicatorDraftLifecycle.test.tsx`, `ChartIndicators.test.tsx` | Root pane GUI preserved drafts across source and workspace changes, Cancel restored applied values, reload restored applied state. Alert UI author pack reran draft lifecycle. |
| REGRESSION-06 | `ChartIndicators.test.tsx`, `MarketChartNavigation.test.tsx`, `LiveChart.test.tsx` | Alert UI author pack reran navigation; historical chart-style GUI cases remain outside the pane walkthrough. |
| REGRESSION-07 | `test_ichimoku_projection.py`, `test_display_indicator_additions.py`, `ChartIndicators.test.tsx`, `MarketChartNavigation.test.tsx` | Mapped to final named formula/projection/rendering tests; no old pass claim was inherited. |
| REGRESSION-08 | `test_display_indicator_additions.py`, `ChartIndicators.test.tsx` | UTC editing and native alignment are existing executable cases; no fresh manual VWAP walkthrough claimed. |
| REGRESSION-09 | `test_vumanchu_indicators.py`, `chartIndicatorEvents.test.ts`, `test_indicator_alerts.py` | Frozen alert core exercises causal divergence semantics; history author tests cover exact divergence confirmation/target. Licensing remains a source/diff review gate. |
| REGRESSION-10–11 | `MarketChartNavigation.test.tsx`, `LiveChart.test.tsx`, display/history paging tests | Alert UI author pack reran navigation. Mapped to final integrated stale-response and paging tests. |
| REGRESSION-12 | `AppChartFocus.test.tsx`, `ChartDrawings.test.tsx`, `chartDrawings.test.ts` | Alert UI author pack reran focus. Actual small-viewport focus/drawing interactions are not inferred from component tests. |
| REGRESSION-13 | `ChartIndicators.test.tsx`, `IndicatorDraftLifecycle.test.tsx` | Pane checkpoint author pack included catalog/editor behavior; final integrated run should retain exact type count, bounded pages, unlimited instances and atomic Apply. |
| REGRESSION-14 | `test_chart_drawings.py`, `ChartDrawings.test.tsx`, `chartDrawings.test.ts` | No source restoration of the drawing engine was required; unchanged source does not replace final integration tests. |
| REGRESSION-15 | `test_display_indicators.py`, `ChartIndicators.test.tsx`, `ChartPanes.test.tsx`, independent pane tests | Price-log/linear auxiliary isolation passed actual pane GUI. Overlaid volume and Recorded IR placement were automated-only. |
| REGRESSION-16–17 | Full existing offline suite, especially `test_native_import.py`, `AppImportRecovery.test.tsx`, `ImportRecovery.test.tsx`, observation/archive/library suites | Mapped to the final combined offline run. Do not perform real imports, provider calls or trading actions as part of this check. |
| REGRESSION-18 | Package/version/license diff plus guarded synthetic core/runtime/history tests | Runtime/history independent tests and pane fixture guards recorded zero provider/PAPER/order/external-notification actions. No dependency/version change was authorized. Final package/version/license diff review retained. |
