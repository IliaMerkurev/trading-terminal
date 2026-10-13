# ADR 0048: Stable chart price styles and 21-type display catalog

Historical count-limit references below are superseded by [ADR 0051](0051-uncapped-indicator-instances.md). Other contracts remain.

Date: 2026-10-11. Status: integrated candidate; focused automated checks passed.
Bounded actual-App browser acceptance passed on corrected source `7086f36`.
Independent review and platform/owner acceptance remain separately tracked.

## Decision

Extend ADR 0047 with Candles, Heikin Ashi and Line (raw close), and twelve reviewed
cache-only formulas. Keep the same chart and price series mounted. A separate
raw-close line is independent of recorded IR. It retains raw close data in every
style and remains visible to the chart engine with only its stroke hidden outside
Line. It owns drawing coordinate conversion and actual-price levels, so the
engine always has a real first value even when HA is entirely whitespace. Its
default last-value label, price line and crosshair marker are hidden. Raw closes
contribute to price autoscaling in all styles; this preserves usable coordinates
while HA is unavailable and is disclosed in the UI. Switching styles preserves logical
range, price scale choices, settings drafts, annotations and their undo history.
Event markers follow the selected price series; no trading computation changes.
Price style is transient chart state, initialized to Candles when the component
is mounted and after application reload. It is not saved in indicator settings
or favorites. Persisted indicators, origins and drawings retain their existing
contracts; style persistence is not promised by this slice.

HA is produced by the existing bounded display worker through the additive
`price_style=heikin_ashi` option on `chart_indicator_read`. The native option
returns an empty additive `price_candles` list. No second poll or worker is added.
HA requests run even with zero visible indicator instances. Responses are guarded
by source, market, symbol, timeframe, style, window and calculation generation.
No frontend recurrence or viewport-first-bar seeding is permitted.

HA close is the mean of raw OHLC. A segment's initial HA open is the raw open/close
midpoint; subsequent opens are the previous confirmed HA open/close midpoint.
High/low include raw high/low and synthetic open/close. Only confirmed candles
advance recurrence. Gaps and unknown history reset the segment; before-origin
prices remain unavailable. A current forming preview uses the last contiguous
confirmed state or a provisional midpoint, without advancing recurrence.

HA and indicators share the persisted source/timeframe calculation origin.
The explicit earlier-cache action is reachable with HA alone and states that
both synthetic prices and recursive indicator values can change. It fetches no
history. The existing 10,000-input, 1,800-output and 900 KiB response budgets,
cancellation, revision and source-confirmation contracts remain enforced.

Synthetic candles are projected only onto the current raw UTC interval-end time
domain. Missing, pending, invalid or failed HA output becomes whitespace, never
raw-candle fallback. Auxiliary price output is independently clipped on paging,
rollover and Return, even if its timestamps differ from indicator columns.
Synthetic default last-price labels are suppressed; actual Last/Mark and PAPER
levels are retained. Raw OHLC/volume readouts and candle snapping stay raw;
annotations still use axis price coordinates, explicitly disclosed near HA.

## Formula contracts

All periods are integers 1–1000. Keltner multiplier is finite, greater than zero
and at most 10. All outputs consume raw confirmed native candles, not HA prices.
Every new kind is unavailable before the persisted origin. Rolling windows are
current-inclusive; gaps/unknown inputs restart their state. No future input is
used. Contracts and seed/unit metadata are returned per instance.

| Kind | Parameters; output | Contract / warmup / exceptional cases |
| --- | --- | --- |
| WMA | period; value | N closes weighted 1…N, newest N; N bars |
| RMA | period; value | N-close SMA seed then Wilder smoothing; N bars |
| VWMA | period; value | sum(close×volume)/sum(volume); N bars; zero volume unavailable |
| Donchian | period; upper/middle/lower | N-bar high/low and midpoint; N bars |
| Keltner | period, atr_period, multiplier; upper/middle/lower | First-close EMA ± multiplier×SMA-seeded Wilder ATR; max periods |
| ROC | period; value | 100×(close/close[N]−1); N+1 bars; zero denominator unavailable |
| Momentum | period; value | close−close[N]; N+1 bars; price units |
| CCI | period; value | HLC3 mean deviation, divisor 0.015; N bars; flat window zero |
| Williams %R | period; value | −100×(highest−close)/(highest−lowest); N bars; flat zero |
| MFI | period; value | N successive HLC3 changes weighted by volume; N+1 bars; equal changes ignored; positive-only 100, negative-only 0, neither unavailable |
| CMF | period; value | N-bar volume-weighted money-flow multiplier; flat candle zero; zero total volume unavailable |
| Standard deviation | period; value | Population deviation of N closes, divisor N; N bars |

Missing/invalid volume resets the volume-dependent formula without changing price
inputs. Source-native volume does not imply cross-source equivalence. Display
Keltner ATR initialization differs from graph/recorded IR ATR, just as standalone
display ATR does. No cross-vendor or Pine equality is claimed.

WMA/RMA/VWMA and channels overlay price. Other new kinds have kind-specific
auxiliary panes, independent of price logarithmic/manual scales and recorded IR.
Williams %R uses −100…0, MFI 0…100; ROC/Williams/MFI use percentage formatting,
CMF four decimal places. Standard deviation and Momentum retain price units.

## Catalog and persistence

Expose exactly 21 implemented kinds. Paginate at nine entries; search and category
changes return to page one. Favorite changes safely clamp the current page.
Keep one outer scroll owner, wrapping pagination, one selected-instance editor,
whole-draft Apply, eight total instances including hidden ones, existing source
namespaces and revisions. Favorites remain bounded type-only UI preferences.
No dependency, provider, schema, strategy, accounting or product version changes.

The remaining nine types in the 30-type plan are not exposed. Their recursive,
shifted-time or anchored contracts require separate implementation and evidence.

## Validation and limits

See STATUS for exact focused pass/correction counts. Pure projection tests cover
whitespace, UTC timestamps and disjoint output clipping. Hook tests cover zero-
indicator HA and stale style responses. Integrated chart tests cover preserved
zoom/scales/raw values/drawings/recorded IR, marker attachment, first-value-dependent actual-level coordinates and drawing
geometry/creation through unavailable HA, Return, timeframe
changes, failure visibility and shared reanchoring. Catalog tests cover bounded
pages, all twelve ports/panes/formatting and parameter validation. Retain earlier
unchanged backend independent fixtures and review evidence; do not infer real
provider, Windows/native or owner acceptance from mocked browser components.


## Bounded actual-App browser acceptance

Parent-led acceptance on corrected source `7086f3634e67cee2504ac5915abdeb6114ba4f13`
used the actual App / Market route with an isolated synthetic fixture. Injecting
all-unavailable HA retained visible actual Last/Mark levels, the EMA overlay and
an existing horizontal drawing. A second drawing was created successfully while
synthetic candles remained blank. Candles/Line switches retained both drawings;
restoring normal calculation recovered HA. Keltner and MFI were added from pages
two and three, applied with four total indicators, and displayed real channel
bands and an oscillator pane. At a measured 729px width there was no horizontal
overflow. Reload preserved all four indicators and both drawings and reset price
style to Candles, matching its transient-state contract.

This is bounded synthetic browser evidence, not live-provider, Windows/native
or owner-led unaided acceptance. Existing focused tests/build evidence was
reused; documentation of this GUI pass required no code or dependency changes.
