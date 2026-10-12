# Local indicator-alert interface

This reconstructed 0.6-dev interface uses the existing strict
[Service API](ALERT_RUNTIME_API.md) and [frozen core](adr/0055-frozen-local-indicator-alert-core.md).
It adds no providers, formulas, dependencies, strategy conversion, orders,
PAPER activity, system notifications, sound, email or Telegram delivery.
Historical rule research and agreement conditions are separate milestones.

## Create, review and monitor

1. Open Market with the desired source, market, symbol and native timeframe.
   Apply indicator changes first. Unapplied indicator/preset drafts are not inputs
   to alert capture. A saved calculation origin and cached confirmed data must
   already exist; the alert interface does not acquire history.
2. Open Local alerts and choose New rule for current context. Enter a name and
   one to sixteen conditions in one ALL or ANY group. The Service catalog is
   authoritative for predicates, indicator ports and exact semantic units.
   Above/below use numeric levels; crosses accept compatible ports or levels.
   Confirmed divergence conditions are restricted to VMC B.
3. Preview frozen alert, inspect its exact context, normalized parameters,
   origin and conditions, check the reviewed-preview box, and Save alert paused.
   A successful save never arms. Unknown values remain unknown.
4. Select a saved rule, review the frozen definition and check its separate Arm
   review box, then explicitly Arm / Resume alert. The interface confirms Pause
   before issuing a new Arm identity. ARMING is distinct from ARMED. Existing
   cached history establishes a baseline and produces no historical delivery.
5. Pause selected alert or Pause all alerts explicitly. The always-visible panel
   heading warns that closing a browser tab does not stop the local Service.
   Panel collapse does not stop lifecycle registration or banner observation.

The library supports paged saved/archived views, name changes, recoverable
archive/restore and explicit definition edits through reviewed paused rebind.
The same-value library selector is a no-op, preserving loaded rows. There is no
fixed saved-rule count quota; pages and backend byte/work budgets remain bounded.
A surviving source indicator parameter change requires reviewed rebind, including
a later parameter reversal. Hiding/deleting originals does not rewrite a saved
frozen rule. Rebind and restore remain paused.

## Session and asynchronous boundaries

An App-level controller initializes one new frontend session even before Market
has been visited. Initialization pauses the old Service context. The controller
lives above source-keyed chart remounts. Each source, market, symbol, native
interval or Market visibility transition gets a strictly newer context revision;
A → B → A does not restore a former Arm capability. Leaving Market registers a
nonvisible context. The backend remains the authority for pause/Arm state.

Composer captures are tied to both context and applied settings revision.
Preview responses, selection reads and writes have lifecycle epochs. Obsolete
results cannot replace a newer context/editor; a context or settings change
invalidates preview and both review checkboxes. Saved-rule polling restarts on
these transitions so durable rebind requirements remain visible. Chart/preset
session drafts and focus behavior retain their existing ownership and lifecycle.

## Uncertain writes

Before a mutation is sent, the interface retains its exact command, parameters,
request identity where supported, context and applied revision in origin-local
browser storage. Storage failure blocks writes. An unresolved operation is shown
separately and blocks another mutation; it cannot silently populate an unrelated
editor after navigation or reload. Pause remains available.

Reconcile original alert write uses read-only request lookup and GET. An accepted
create/Arm identity resolves its original saved rule, never a new identity.
Uncertain rename/archive/restore/rebind requires GET and revision inspection
before another mutation. A Service error envelope is not alone proof of rejection:
create can commit before a failed readback. Durable lookup is checked even after
a completed error response. An exact retry's rejection cannot settle an earlier
transport-unknown create.

An absent create lookup retains the original content. Only an explicit retry of
that identical create is offered, and only in the original matching applied
context. There is no automatic retry, new-ID retry, or unsafe discard of an
unresolved create. If its original outcome cannot be established, it remains
quarantined; the UI does not fabricate success or absence.

An absent Arm lookup instead offers explicit Recover paused Arm. This acknowledges
a newer context fence, confirms Pause, then checks request and saved-rule state.
Only a confirmed paused outcome releases it. The old Arm is never replayed;
a fresh reviewed action is required. This also resolves a lost preliminary Pause
reply without silently resuming monitoring.

Browser recovery storage is tied to the application origin/profile. It is not a
portable workspace backup and cannot restore deleted browser storage. The durable
Service request ledger and rule/journal database remain authoritative.

## Journal and local banners

The paged journal exposes exact event detail and independent read/unread state.
It displays the CURRENT saved rule name plus stable rule ID separately from the
immutable frozen event evidence, raw-open/native-close clocks and observed time.
JSON null is explicitly labeled unknown, never false or zero.

An App-level observer traverses event pages, including already claimed/read
pages, while the alert panel is collapsed. A local banner attempt occurs only
after the Service returns `claimed: true`. Lost claim responses may omit a banner;
there is no exactly-once display guarantee. The journal remains durable. Current
name updates are read independently without rewriting original event evidence.

## Verification boundary

Focused deterministic tests use independent synthetic expected outcomes and
mocked Service transport; nearest regressions cover actual App focus behavior,
chart navigation and retained indicator/preset drafts. Production compilation,
independent source challenges and actual-App synthetic GUI acceptance are recorded
separately in STATUS and RECOVERY. No Windows/native, live Bybit/OKX, old-alert
schema interoperability, remote CI or owner acceptance is implied.
