# 0031 — Saved comparison details and scoped filtering

Status: implemented; local-browser workflow and restart acceptance verified on
production code `b859f5a`. Narrow-screen visual acceptance remains pending.

## Decision

Keep editable names (120 characters) and notes (4,000 characters) in an additive
`library_batch_metadata` table, keyed by comparison ID. Legacy comparisons read
empty metadata at revision zero. Writes use a transaction and expected revision;
conflicts and storage failures return errors without touching batch snapshots,
row states, run summaries or immutable report files. The UI retains a failed
save's draft and offers explicit discard/reload. Polling never resets the editor.
No dependency, financial model or product-version change is needed.

Extend the existing 50-row, 512-KiB keyset history endpoint with optional literal
Unicode-casefold substring search over names, notes, IDs and creation dates.
SQL applies the query before pagination, including old comparisons. Empty search
means the entire catalog; `%` and `_` are ordinary characters. History uses the
server cursor, and search replaces the loaded page set. A selected report outside
the search stays accessible. Search is a bounded-response full catalog scan,
not a claim of indexed full-text performance or snapshot-consistent pagination
across concurrent annotation edits. It does not search strategy names or metrics.

Numeric thresholds apply only to the selected comparison: maximum drawdown in
percentage points, minimum completed position lifecycles, and minimum period
return in percent. Empty fields do not filter. Invalid numeric input disables
numeric thresholds with a visible explanation. Unknown or unfinished results
remain labeled context; passive references bypass candidate thresholds. Category
filters retain their earlier semantics. Sorting remains cohort-local, and frozen
later-period rows retain their non-ranking order. These filters cannot establish
profitability or comparability between execution models.

## Alternatives

Editing the frozen snapshot was rejected because it would change evidence.
Filtering only the loaded history page was rejected because it hides old work.
A new full-text engine or global metric ranking is unnecessary for this bounded
usability milestone and would broaden dependencies or research semantics.


## Acceptance evidence

Actual local-browser checks verified legacy comparison reopening, name and
Unicode-note saves, uppercase Cyrillic search, dirty-editor selection protection,
and explicit discard. On `b859f5a`, stopping the local service and restarting the
same launcher preserved the exact saved details. A subsequent rename/save
collapsed the editor and updated its selector. Report Back navigation retained
search, selection and numeric filters. Numeric 0% drawdown/1,000-position filters
retained passive references and N/A context; a negative position minimum showed
the validation warning.

The synthetic legacy matrix remained at 14 completed and two unavailable rows;
two total comparisons remained, without rerunning calculations. SQLite integrity
was ok, and all 42 original report/snapshot file hashes were unchanged. See
[status](../STATUS.md) for focused automated evidence and its correction history.
These checks do not establish profitability, Windows-native acceptance, live
public-data behavior or a new complete regression-suite pass. The documentation
checkpoint adds no code/build changes; narrow-screen visual review is separate.
