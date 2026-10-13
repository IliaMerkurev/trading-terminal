# ADR 0032: forward-only research admission evidence

## Decision

Use one additive, append-only `research_evidence` table in the existing local
SQLite database. Its coverage-start marker is durable and never reset on restart.
There is no retrospective backfill: missing evidence means unrecorded, not unseen.
Old snapshots, summaries, accounting and report files remain unchanged.

Each `JobManager.start` admission inserts one `started` event in the same
transaction as its run row, before creating or releasing any worker. This means
durable admission, not completed computation; the run retains the actual outcome.
Failed launches, cancellations and repeated identical runs retain separate
admissions. Cached passive reuse does not create a new event. Passive controls
are recorded separately from strategy variants. Custom events use their run ID
as stable owner; Library and Experiment events retain their parent IDs and row
identity. Imported reports and replay/live activity are outside this increment.

Actual Library/Experiment freezes insert a `frozen` event in the candidate's
transaction. `BEGIN IMMEDIATE` serializes its prior-overlap read and writes.
The prior review is stored only in evidence, not added to financial snapshots.
It excludes the new freeze itself and stays historical when later events arrive.
Freeze is not start. Read-only overlap preview does not record a view or reserve
the period. Both UI routes require reviewing it before their explicit freeze.

Events retain evaluation and input/warmup ranges separately, dataset/content
identity, strategy/contract identity, profile/cohort and declared source provenance.
Overlap uses half-open evaluation ranges for the same symbol across spot/linear:
calendar exposure is not performance comparability. Explicit synthetic metadata
or provenance/source labels take precedence, isolated by declared synthetic source.
A Bybit source label alone is unknown. A recorded kline endpoint, response hash
and retrieval timestamp qualify real-source provenance; this is recorded provenance,
not independent proof of candle authenticity. Unknown and real-source observations
share conservative warnings, with unknown classification visible. Synthetic
source namespaces are declarations, not inferred economic-market identities.

The total counts all matching evidence events, not unique strategies or completed
runs. Source/route/kind/role/market/cohort groups are separate; at most 50 groups
are returned with explicit truncation, while total includes all matches. Existing
execution/workload limits are unchanged. Historical Library-only saved counters
retain their values and are labeled accordingly.

## Failure and preservation

Admission persistence failure rolls back the run row and event, launches no
worker and latches the existing session storage diagnostic. The immutable snapshot
file is written before SQLite admission and may remain unreferenced after failure;
it is not a successful run and is not automatically deleted. Freeze failure rolls
back candidate and evidence together and latches the same diagnostic. Migration
failure occurs inside the existing constructor lock-cleanup boundary.

## Scope and verification

This is a partial TT11 checkpoint. Actual chart/report view tracking, manual
research journaling, external exposure and historic attempts remain unrecorded.
No result, including zero overlaps, establishes a clean or independent holdout.
No new strategy, scheduler, dependency, financial rule, product version, network
access or Windows-specific execution path is introduced.

Focused tests cover cross-route freezes, atomic rollback and no process launch,
restart/append-only protection, migration lock release, repeated admissions,
synthetic isolation, unknown provenance, cross-market calendar overlap, adjacent
ranges, warmup exclusion and unchanged report bytes. UI checks cover review,
cancellation, failed reads and double submission. Native Windows and live-source
acceptance remain separate; synthetic fixtures are not profitability evidence.


## Local-browser acceptance — 2026-10-10

Production checkpoint `0855f39` passed an actual synthetic browser walkthrough
at 1180px width. Three same-day history choices were distinguishable by source,
short dataset identity and precise UTC range. Library's 00:24–00:48 UTC review
showed custom admission 1, Experiment admission 1 and Library freeze 1; cancel
made no change. Another synthetic source showed zero with the incomplete-coverage
warning still visible. Confirming created one freeze without any new computation.
Its recorded prior count was 3; the original frozen candidate retained 2.

Experiment's 00:36–00:48 UTC review subsequently showed custom admission 1 and
Library freezes 2; cancel again made no change. Service stop/restart preserved all
three batches and the original candidate's frozen, never-started state and prior
review. There remained five completed runs, three strategy admissions, two passive
admissions and two strategy freezes. SQLite integrity was ok, and all 15 original
immutable run JSON files matched their baseline hashes.

These browser observations do not establish narrow-screen, Windows-native,
live-source, external-exposure or view-tracking acceptance. This documentation
checkpoint changes no code or build and does not require repeated automated tests.
