# Frozen-rule historical research and original event evidence API

These routes use the existing strict version-1 Service envelope. Unknown keys,
wrong scalar types and excessive ranges fail with `type: "error"`, code
`REQUEST_FAILED`, and a visible message. IDs (`request_id`, `run_id`, `rule_id`)
are 32 lowercase hexadecimal characters; event/hash IDs are 64 lowercase hex.
All times are integer UTC seconds. `start` and `end` are inclusive native
confirmed CLOSE times, while raw candle `time` is OPEN. No route below starts
Market, changes alert session/context, arms a rule or requests provider data.

| Command | Required parameters | Optional parameters |
| --- | --- | --- |
| `alert_history_preview` | `rule_id, revision` | — |
| `alert_history_start` | `request_id, rule_id, revision, definition_hash, start, end` | — |
| `alert_history_request` | `request_id` | — |
| `alert_history_get` | `run_id` | — |
| `alert_history_cancel` | `run_id` | — |
| `alert_history_list` | — | `after` (null), `limit` (20, max 20) |
| `alert_history_matches` | `run_id` | `after` (0), `limit` (20, max 20) |
| `alert_history_chart` | `run_id` | `start_index` (see below), `limit` (200, max 200), `target_confirmed_at` |
| `alert_history_row` | `run_id` and exactly one of `confirmed_at, raw_open_time` | — |
| `alert_event_evidence` | `event_id` | `before` (40), `after` (40) |

## Preview, admission and identity

Preview returns `{rule, cached_start, cached_end, cached_count, origin_raw_open,
max_inputs:10000, max_working_bytes:268435456, max_unfinished:8, note}`.
Cache bounds are declared confirmed CLOSE bounds from the saved native context;
null means no such cache. They do not prove continuity or integrity: admission
checks every raw candle, confirmation and content hash. The UI must retain each
manually edited date when a late preview arrives.

Start requires the reviewed metadata revision and definition hash. Within one
SQLite transaction it checks the exact saved revision, captures the frozen rule
and every raw cached candle from its saved origin through `end`, and records the
request identity and queued run. It neither captures transient Hub rows nor
fetches/fills/truncates missing inputs. A gap, missing origin/end, unconfirmed or
conflicting candle, unsupported contract, over-budget tape or invalid range
fails admission visibly and creates no run. There must be 1–10,000 input candles,
INCLUDING all pre-range replay, and the conservative working estimate must fit
256 MiB. Moving only Start later never reduces that input count. Earlier End can.

The same accepted request ID and payload returns the original run without
restarting it, even after rule/cache edits, cancellation or restart. Reusing the
ID for different content fails. Request readback is strictly read-only and returns
`{request_id, found, run}`; `run` is null when no admission was committed. Retain
uncertain IDs, reconcile before changing intent, and never automatically issue a
fresh request ID after a lost response. Concurrent admissions are serialized;
queued, running and cancel-requested scans together are limited to eight.

## Durable metadata and coverage

Start/list/request return run metadata. Get adds the immutable `definition`.
Metadata fields are `id, sequence, request_id, created_at, status,
cancel_requested, rule_id, rule_name, rule_revision, definition_revision,
definition_hash, context, origin, start, end, input_count, input_hash,
coverage_complete, summary, error`. The title is frozen at start. `input_hash`
identifies the actual annotated raw snapshot, including its confirmation state.

Statuses are `queued`, `running`, `cancel_requested`, `completed`, `cancelled`,
`error`, `interrupted`. Cancel on a queued run immediately returns cancelled;
on a running run it retains `cancel_requested:true` until cancellation settles.
A terminal cancellation response has `cancel_requested:false`. The client must
not clear pending cancellation because an earlier poll arrived late. Shutdown
and startup durably mark unfinished scans interrupted; neither resumes them.
An incomplete worker shutdown retains Service dependencies/workspace ownership.

Only completed runs have `coverage_complete:true` and a non-null summary. Other
states have no published calculated rows and do not claim partial work as full
coverage. The completed summary contains:

- `requested_rows, evaluated_rows, known_rows, unknown_rows, match_count`
- `pre_range_rows, pre_range_unknown_rows`: replay before the requested Start
- `initial_unknown_rows`: consecutive unknown rows at the start of the requested
  range, stopping at its first known aggregate condition
- `unknown_reason:"warmup_or_missing_value"`: unknown never means false; do not
  label every unavailable formula value as definitely initialization warmup
- `input_rows, coverage_start, coverage_end`: exact entire input count and
  inclusive evaluated requested-close bounds

For an origin-start SMA-cross example, 362 requested rows can have 360 known and
2 unknown, even though `pre_range_rows` is zero. A later requested Start still
replays the unchanged frozen origin and uses earlier values for the first cross.
All calculated timeline rows, including the pre-range prefix, are saved.

## Paging and exact chart navigation

All history responses have a 600 KiB byte budget in addition to the Service
one-MiB envelope. Page limits do not delete evidence or cap saved run count.
A single item that cannot fit fails visibly instead of truncating its contents.

List is newest-first by sequence. `after` is the previous page's `next_cursor`;
the cursor is the last ACTUALLY returned sequence and is exclusive. Matches are
ascending confirmed-close order within the requested range; `after` is exclusive
confirmed close. Both return null `next_cursor` when exhausted. Match rows contain
`row_index, raw_open_time, confirmed_at, truth, state_truth, hit, conditions,
values`. Values map frozen instance ID to `{port:number|null}` and come from the
existing display calculator used in the SAME full-origin alert replay.

Chart returns `{run_id, total_rows, start_index, next_index, rows, markers,
target, byte_limited}`. Row indices refer to the full origin-based timeline.
Each row is `{row_index, candle, evaluation, in_range}`. Candle is the actual
saved annotated raw input; evaluation has the same fields as a match except its
index is outside the evaluation object. No current cache or current settings
are consulted. `markers` includes ALL requested-range hits in the returned
window, independent of the current match-list page. Prefix hits outside the
requested range remain inspectable in row evidence, not result matches.

The default start index is the requested Start's row. With an exact available
`target_confirmed_at`, the default instead tries to include 40 preceding rows.
An explicit `start_index` takes precedence. The requested window is at most 200
rows and can be shorter because of bytes. `next_index` is one after the last
ACTUALLY returned row, or null only at the saved tape's end. An out-of-range
explicit start returns an empty window.

Target metadata is `{confirmed_at, raw_open_time, row_index, included, status}`;
status is `available` or `missing`, and a missing row has null index. `included`
is true only if that exact row is actually in the response. A byte-shortened
context window can report an available but excluded target: call exact
`alert_history_row` or request its exact index. Exact lookup never substitutes a
nearest candle or another interval, and a single oversized row fails visibly.

## Original alert evidence

`alert_event_evidence` returns the original `event` plus `context, warning,
price_context_source:"current_cache", target_raw_open_time,
target_confirmed_at, target_status, target_candle, candles, byte_limited,
target_in_window`. The immutable event's numbers, earlier crossing values,
frozen conditions/versions/origin and observed time are authoritative. Current
rule names are explicitly current metadata, as in `alert_event`.

Adjacent raw price candles are read ONLY from the current cache in the original
source/market/symbol/native interval. They may have changed since the event and
are not an immutable historical calculation snapshot; the warning is mandatory.
`before` and `after` count native intervals, each 0–199, total plus target at most
200. Byte limits can shorten the adjacent window. `target_candle` is separately
retained only when the exact cached candle is confirmed and nonconflicting.
Target status is `confirmed`, `missing`, `unconfirmed` or `conflict`. Missing or
unconfirmed exact candles never become a nearby/other-interval substitute.

The target raw open always equals the event's confirmed close minus native
width. Divergence navigation targets CONFIRMATION; earlier pivot geometry stays
inside the original condition evidence. These reads do not mark events read,
claim banners, change cursors, arm/pause, mutate Market/drafts, or write the live
journal. Research uses separate additive workspace tables. Back up the workspace
database; strategy archive export does not imply research-record export.

## Agreement timelines (ADR 0061 backend)

Version-2 frozen agreement definitions use these same immutable jobs, snapshot
and paging routes. No new table or history envelope version is required. Every
calculated close, including prefix, unknown, false and sustained-true nonhits,
retains `evaluation.conditions[i].agreement` and `.threshold` for an agreement
condition. `agreement` is the full shared evaluator result: version/hash,
raw `open_time`, confirmed `close_time`, interval, overall/group/type/variant
exact distributions and percentages, coverage, member statuses/parameters/
consumed values/reasons, exclusions and `group_conflict`. Threshold evidence
retains direction, threshold, required groups, overall/group passes and nullable
truth. Unknown is not neutral or false; conflict is opposite strict directional
majorities in different groups. These fields are present on matches, chart rows
and exact-row lookup, including rows where no new event fired.

Admission includes the full per-member/per-condition evidence copies in its
256 MiB estimate before calculation. The existing 600 KiB page ceiling can yield
fewer rows than the requested limit; use the returned cursor/index. Single-item
overflow is explicit. No member, candle or group is silently omitted. Existing
research isolation and immutable results survive graph/rule edits and restart.
The plotted agreement timeline UI is separate from this backend checkpoint.
