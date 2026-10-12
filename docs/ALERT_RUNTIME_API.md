# Local alert Service API

The normal version-1 Service envelope and one-MiB request/response budget apply.
Every identifier named `request_id`, `session_id` or `rule_id` is 32 lowercase
hexadecimal characters. `event_id` is the journal's 64-character hash. Optional
fields below may be omitted; unknown fields are rejected. No command opens a
provider or starts a strategy/PAPER session. Preview and reads cannot arm.

| Command | Required parameters | Optional parameters |
| --- | --- | --- |
| `alert_catalog` | — | — |
| `alert_request` | `request_id` | — |
| `alert_session_init` | `session_id` | — |
| `alert_context` | `session_id, context_revision, source, market, symbol, minutes, visible` | — |
| `alert_preview` | `source, market, symbol, minutes, settings_revision, conditions` | `combine` (ALL) |
| `alert_create` | `request_id, name, definition, definition_hash, settings_revision` | — |
| `alert_list` | — | `trashed` (false), `after` (null), `limit` (20, max 100) |
| `alert_get` | `rule_id` | `revision` |
| `alert_rebind` | `rule_id, revision, definition, definition_hash, settings_revision` | — |
| `alert_rename` | `rule_id, revision, name` | — |
| `alert_archive`, `alert_restore` | `rule_id, revision` | — |
| `alert_arm` | `request_id, rule_id, revision, definition_hash, session_id, context_revision, reviewed` | — |
| `alert_status`, `alert_pause` | — | `rule_id` (omit for all) |
| `alert_events` | — | `after` (0), `limit` (20, max 100), `unread_only` (false) |
| `alert_event` | `event_id` | — |
| `alert_mark_read` | `event_id` | `is_read` (true) |
| `alert_claim_banner` | `event_id` | — |

`alert_catalog` returns `{version:1, ports, predicates, divergences, oscillators,
combine, max_conditions, price_ports, price_unit}` directly from the core.
`ports` maps indicator type to `{port: semantic_unit}`. Use exact unit equality
for numeric compatibility; only VMC B has divergence conditions. This catalog is
read-only and does not load or execute imported code.

Initialize once with a newly generated frontend `session_id`; a new session
pauses all prior alert work and starts with null context/revision 0. Register the
visible Market context with a strictly increasing positive integer
`context_revision`; each new revision pauses prior work, including A → B → A.
The same revision/context is idempotent. Register `visible:false` when leaving
Market. A superseded session cannot change context. Native minutes are
1/5/15/60/240/1440; source, market and symbol follow the existing chart contract.
Session init returns `{session_id, context_revision}`; context registration also
returns `context` (null when not visible).

Preview freezes applied settings at `settings_revision`, requires an existing
saved calculation origin, and returns `{definition, definition_hash,
settings_revision}`. Conditions and frozen definition follow ADR 0055. Create
and rebind accept that exact reviewed snapshot/hash; stale applied revisions or
changed origin/dependencies fail. A successful save never arms. A library page
returns `{rules, next_cursor}`. Get/create/edit return a saved rule with `id,
name, revision, definition_revision, deleted, definition_hash, definition` and
`runtime, rebind_required`. A detected surviving-parameter change durably requires
reviewed rebind, even after parameter reversal or Service restart. List metadata excludes the definition and includes runtime.

Arm requires `reviewed:true`, the saved metadata revision/hash, and the current
session/context revision. It returns promptly with runtime status while the
worker establishes a full-origin baseline. Poll `alert_status {rule_id}`;
`phase` is `PAUSED`, `ARMING` or `ARMED`, accompanied by `rule_id, reason,
confirmed_at, request_id`. A successful baseline does not insert historical
hits. Source freshness, observed native confirmation and full contiguous cached
coverage are required. No source is opened or history fetched to satisfy Arm.

`alert_request {request_id}` is read-only reconciliation: null means no accepted
request, otherwise `{request_id, kind, rule_id, runtime}` identifies the original
operation. Fetch that rule before deciding the next action.

Keep a create request ID and its exact content until the result is known.
Repeating that ID reconciles the original saved rule, even after a later chart
revision or Service restart; changing its content fails. Arm request identities
are also durable: replaying a previously accepted Arm request only reports
current status and cannot re-enable a paused/restarted rule. After an uncertain
rename/rebind/archive/restore response, GET the rule and inspect its revision
before taking another action. Do not automatically retry with a new identity or
new optimistic revision. Pause is idempotent.

Journal/event shapes, immutable evidence, native close timestamps and separate
UTC-second `observed_at` follow ADR 0055. `alert_claim_banner` returns
`{claimed:boolean}`. Only true authorizes one local banner attempt; a lost claim
reply may omit that attempt, so never retry display assuming delivery failed.
Mark read is independent of claiming. Journal pages are byte bounded as well as
count bounded.

Closing only a browser tab does not stop the local Service. The local UI must
warn users to Pause before closing a tab. Service shutdown pauses and joins the
worker; a join timeout retains its dependencies and workspace ownership. The [UI contract](ALERT_UI.md),
history scans, external notifications, Windows/native and live-provider
acceptance are separate checkpoints.
