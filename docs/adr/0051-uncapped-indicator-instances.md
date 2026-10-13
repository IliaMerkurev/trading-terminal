# ADR 0051: Uncapped indicator instances with atomic paged transport

Date: 2026-10-11. Accepted for the existing chart workspace.

## Decision

Remove the fixed indicator-instance limit from backend validation and frontend
Add/Apply controls. Neither visible nor hidden instances consume a count quota;
there is no replacement limit of 32, 128, or another fixed count. Hidden settings
remain persisted but create no formula state, perform no replay, and do not
prevent reads because of a hidden timeframe-specific constraint. Validation of
saved parameter structure and duplicate identifiers remains strict.

Large read/settings/save responses are immutable disk-backed snapshots. Each
64 KiB ASCII JSON page identifies its snapshot, ordered index, total byte length,
page count and SHA-256. The client assembles and verifies the complete snapshot
before publishing any result. Forming updates are part of that frozen payload;
page retrieval cannot mix separate ticks, sources, windows or revisions. Source
and window changes abort obsolete reads. Expired snapshots fail explicitly and
may be read again; no partial result is rendered.

Settings requests above 800 KiB use sequential disk-backed uploads with strict
byte offsets and a final SHA-256. Only finish invokes the original atomic,
revision-checked save. Abandoned/failed uploads do not change saved settings.
Only one pending upload is retained; a new begin supersedes it. Writes are never
retried automatically. A response failure after save may have an uncertain
outcome; the UI asks the user to reload the chart before retrying.

## Resource boundaries

Uncapped instance count does not imply unlimited hardware. The existing 10,000
cached-input and 1,800 viewport-bar guards remain, including explicit origin
handling and no silent reseeding. A conservative preallocation estimate limits
working output/state storage to 256 MiB. Actual serialized settings/results are
limited to 64 MiB. These are byte/work guards that vary with window size, ports
and formula state, not fixed instance quotas. Rejections name the resource limit;
settings are never silently truncated. Cancellation is checked during state
creation and every 32 instances within a row as well as during candle traversal.

At most two immutable result snapshots and one pending upload are retained on
disk; temporary files are removed on eviction, failed serialization, completed
upload or service close. Existing two-entry calculation caching remains. More
visible instances cost calculation/rendering work; the UI states this and the
legend/selector remain within the viewport. This is not a large-scale memory or
latency guarantee.

## Superseded contracts

The eight-instance references in ADRs 0040/0042/0043/0047/0048/0049, earlier
project/status text and their original test evidence are historical. This ADR
supersedes only their fixed instance-count requirement and the old 900 KiB total
indicator-result rejection. Existing per-message IPC limits, formula semantics,
source isolation, trading boundaries and price/history guards remain.

## Verification scope

Focused backend coverage checks 129 visible plus 128 hidden instances over 1,800
bars, output above 900 KiB, complete page reconstruction and persistence after
reopening. A 13,000-hidden-instance settings request exceeds 1 MiB and is uploaded,
committed once, and rejected atomically on stale revision. Resource preflight
rejects before state allocation. Frontend coverage checks adding instance 129,
whole-draft Apply, search retention, snapshot corruption/cancellation and chunked
save. Existing chart/presentation/projection regression checks and production
build are recorded in STATUS. Native Windows and a new owner acceptance pass are
not implied. No dependency, product version, provider connection, strategy,
trading, release or main-branch change is introduced.
