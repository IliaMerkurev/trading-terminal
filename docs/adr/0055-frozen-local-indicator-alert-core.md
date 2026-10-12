# ADR 0055: Frozen local indicator-alert core

Date: 2026-10-12

Status: Implemented core-only partial restoration; runtime, Service, UI and
historical research integration are not implemented by this checkpoint.
Product version remains 0.6-dev. This does not establish product acceptance.

## Context and boundaries

The available source contains display formulas and named presets but not the
later locally reported alert implementation. This checkpoint reconstructs a
small independently testable core from the authorized behavior, rather than
claiming recovery of unavailable original source or database schemas. No old
alert database fixture is available; old-alert migration compatibility is not
claimed. New tables are additive and preserve unrelated workspace data.

There is no new formula engine, strategy conversion, user-code evaluator,
provider request, order, PAPER action, external notification or background
monitor. The new modules are not imported by Service. Existing licensed VMC
formulas remain unchanged in their MPL-2.0 module; this original orchestration
code calls the existing display calculation API.

## Frozen definition

`terminal.indicator_alerts.freeze_rule(settings, source, market, symbol,
minutes, conditions, combine='ALL')` returns a detached normalized JSON v1
snapshot. `validate_definition`, `definition_hash`, `encode` and `decode` are
the validation/serialization boundary. Unknown keys, versions, formula
contracts, nonfinite numbers, invalid ports, duplicate JSON keys, non-JSON
objects and mismatched units fail visibly. No imported code is executed.

The definition contains:

- `context`: exact source, market, symbol and supported native minute interval
- `settings_revision`: the applied revision reviewed at capture
- `origin`: exact saved raw-open time, generation and display seed contract
- `instances`: only referenced IDs, types, normalized parameters and formula
  contracts, sorted by ID; each formula contract retains display/VMC versions
  and a digest of its existing metadata/seed description
- `conditions`: 1–16 conditions; one `ALL` or `ANY` group
- Alert schema, alert semantic and display-event contract versions

Appearance, pane layout and visibility are not calculation identity. Hidden or
deleted graph originals cannot rewrite the snapshot. `changed_dependencies`
reports only surviving IDs whose type/normalized parameters/formula contract
changed. Runtime integration must pause these rules until explicitly reviewed
rebind. Changing chart origins does not silently reseed frozen rules.

A rule is limited to 256 KiB of serialized definition, and
`validate_active_set` limits the complete enabled set to 256 KiB. These are byte
resource budgets, not saved-rule quotas. Saved-rule listing is keyset-paged;
130 saved synthetic rules and 129 small active definitions are covered by tests.
Neither count is a promised maximum or minimum for arbitrary-sized rules.

## Operands and predicates

An operand is exactly one of:

- `{kind: 'series', instance_id: '...', port: '...'}`
- `{kind: 'price', port: 'open' | 'high' | 'low' | 'close'}`
- `{kind: 'level', value: finite_number, unit: '...'}`

Numeric conditions have `predicate`, `left` and `right`. Supported predicates
are `above`, `below`, `cross_above` and `cross_below`. Above/below require a level
on the right. Crosses support compatible series, raw prices or levels. The
left operand must be a series or raw price. Semantic unit families are exact:
price, price difference, price distance, bounded 0–100, bounded −100–0, signed
percent, band-width percent, flow ratio, band ratio, CCI, native volume,
direction, VMC oscillator and VMC body flow. RSI/Stochastic comparisons are
compatible; RSI/Williams %R, RSI/ROC and price/ATR are not silently mixed.
`port_units(type)` is the authoritative map. Ichimoku projected/chikou geometry
is excluded; only causal Tenkan/Kijun numeric ports are accepted.

Divergence conditions have `predicate: 'divergence'`, `instance_id`,
`event_kind` and `oscillator`. They require frozen VMC B and regular/hidden
bullish/bearish divergence on WT, secondary WT, RSI or Stochastic. They consume
confirmed display events from the existing calculator. Optional formula
switches remain exactly as frozen; disabled divergence families do not invent
signals.

## Three-state logic and hit semantics

Truth is `true`, `false` or `null` (unknown). Missing values are never changed
to false. In ALL, false dominates unknown; otherwise any unknown yields
unknown. In ANY, true dominates unknown; otherwise any unknown yields unknown.
An unknown required ALL input prevents a hit. A known true ANY input can
establish truth despite another unknown input.

A cross above requires previous left ≤ previous right and current left >
current right. A cross below uses previous ≥ and current <. Current equality
never crosses; previous equality is an eligible starting boundary. Both
current and previous pairs must be known. Crosses and divergences are impulses
at their own confirmed close, with no accumulation over older closes.

`transition(conditions, combine, previous_truth, previous_state_truth)` defines
one shared runtime/history transition contract:

- A state-only group emits only on consecutive known false → true. Initial
  true, unknown → true and repeated true do not emit.
- ALL containing impulses emits only when every condition is true at this
  same close. An impulse from a previous close cannot satisfy it.
- ANY containing impulses emits for any current true impulse, or a known
  false → true transition of the state-only ANY subgroup. A persistent true
  state does not suppress a new impulse or create repeated state hits.
- Unknown breaks the corresponding known-state baseline. The aggregate truth
  and state-subgroup truth are retained separately for mixed ANY behavior.

## Pure replay and evidence clocks

`replay(definition, candles, cancel=None)` requires 1–10,000 raw candles,
starting at the exact frozen origin, strictly contiguous at the native interval,
with explicit confirmed nonconflicting provenance. Missing origin, gap,
unconfirmed/conflicting row, invalid OHLC or unsupported contract fails. No
history acquisition, slicing around missing coverage, reseeding or synthetic
fill is performed. Warmup and genuinely unavailable numeric values remain
unknown. The display calculator is called once for the full tape, not once per
prefix. Replay checks cancellation and a conservative combined 256 MiB formula
and evidence working estimate before calculation.

Return shape:

- `version`, `definition_hash`
- `rows`: every close, including unknown/false/nonhit values
- `events`: copies of only hit rows

Each row has `raw_open_time`, `confirmed_at`, `truth`, `state_truth`, `hit` and
ordered `conditions`. Condition evidence includes predicate/kind/truth/reason,
current and previous numeric operands, or the original confirmed divergence
records with pivot/previous-pivot times. No complete definition is duplicated
in each replay row or hit. For a one-minute raw open 120, confirmed close is
180. Display divergence timestamps are already interval ends and are never
converted twice; a pivot+2 confirmation remains two intervals after its pivot.
No observation time is fabricated in pure or historical replay.

A later runtime must replay cached full-origin data to establish its Arm
baseline, discard all old hits for delivery, and process only subsequently
observed contiguous confirmations. It must pause on gap, stale/reconnecting
source, context changes and surviving parameter changes. This checkpoint does
not implement or claim those lifecycle guarantees.

## Durable storage seam

`IndicatorAlertStore(RunStore)` creates three local v1 tables for rules, cursors
and immutable event evidence. Construction invalidates all old cursor tokens;
there is no persisted armed state to restore automatically. Only one Service
owner should construct the store. Integration must own the active set in memory.

- `create(name, definition)`, `get(id, revision=None)`,
  `list(trashed=False, after=None, limit=20)`
- `rename(id, revision, name)`, `trash`, `restore`,
  `rebind(id, revision, definition)` use optimistic metadata revisions.
  Every edit invalidates its cursor. Rebind also increments definition revision.
- `begin_cursor(id, revision, baseline_row)` establishes a new token and the
  last reviewed close/truth without inserting any historical event. Caller
  must perform explicit Arm review, dependency checks and active-set admission.
- `invalidate_cursor(id=None)` fences Pause or shutdown. `cursor(id)` reads
  the durable baseline. Reading it is not permission to resume.
- `commit_evaluation(id, revision, token, expected_close, evaluation_row,
  observed_at=utc_seconds)` validates the contiguous close, metadata/token fence,
  observation clock and transition against the stored baseline, then commits
  event insertion and cursor advancement in one SQLite transaction.
- `event(id)`, `events(after=0, limit=20, unread_only=False)`,
  `mark_read(id, is_read=True)`, `claim_banner(id)` provide journal primitives.

Event identity is derived from rule ID, definition revision and confirmed close,
independent of Arm tokens. Renames do not create new definition identities.
Duplicate receipts and repeated Arm at the same baseline cannot duplicate a
committed event. Conflicting duplicate evidence fails. Event evidence contains
its original frozen definition/hash, exact calculation evidence and separate
observed time. A SQL trigger prevents updating those evidence fields; mutable
read/claim flags are separate. The current rule name is returned as
`current_name`, never presented as an immutable historical title.

Event insertion/cursor failure rolls back both writes. A banner claim is durable
at-most-once permission to attempt display, not proof of delivery. Losing the
claim response can omit a banner while preserving its journal event. Journal
pages are limited to 600 KiB and return the last actually returned sequence as
cursor; oversized single rows require exact event lookup rather than truncation.

## Verification and remaining work

Small independent synthetic tests cover strict definitions/units, frozen
isolation, every two-condition Kleene combination, equality crossings,
state/impulse transitions, exact close clocks, VMC pivot+2, future perturbation,
missing coverage, cancellation, resource boundaries, saved-rule paging,
restart, stale tokens/revisions, cross-Arm deduplication, injected failure
between event/cursor writes, immutable evidence and banner/read flags.

These tests establish the isolated core/storage only. Service dispatch envelopes,
actual MarketHub receipts/freshness/epoch/queue fencing, async Arm/Pause races,
UI creation/uncertain replies, banners, historical jobs/snapshots, event chart
navigation, current/agreement summaries, Windows/native and live-provider
acceptance remain outside this checkpoint. No full-suite or remote CI success is
implied. See STATUS for exact commands and results.
