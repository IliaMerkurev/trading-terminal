# Strategy draft replacement

The mounted Strategy editor keeps its current graph, layout, name, simulation
profile and native source/configuration/dependencies while moving between tabs.
Opening a saved strategy, New, Copy, Lab customization, an experiment copy, an
imported strategy or a newly converted rule uses one replacement boundary.

- **Save and continue** saves the exact reviewed draft. Replacement proceeds only
  after an acknowledged save and while both the request and draft remain current.
- **Discard and continue** replaces only after the requested strategy loads.
  A failed load retains the previous draft and its graph Undo/Redo.
- **Cancel**, including Escape, retains the draft and Undo/Redo unchanged.
  The prompt initially focuses Cancel; graph shortcuts do not edit behind it.

A successful ordinary Save preserves graph Undo/Redo. An undo after saving can
therefore create new unsaved changes. While a save is pending or its outcome is
unknown, the old saved baseline is not trusted. Save failure never continues an
open operation. An acknowledged older save updates the known persisted baseline
for the same draft, but cannot replace newer edits or another draft's identity.
Check saved strategies before retrying an uncertain write; no automatic retry or
save-reconciliation protocol is introduced here.

New templates start clean until edited; Copy is an independent unsaved draft.
Latest replacement intent and synchronous draft revisions fence asynchronous
loads, saves, customization/copy preparation, archive completion and conversion
refresh. Edit-and-revert still invalidates a previously started load. A created
strategy remains saved independently when opening is cancelled or superseded;
conversion retains its Open created strategy receipt. Import receipts and strict
refresh errors remain inspectable. These guards do not cancel already submitted
creation/import operations or alter their persistence contracts.

## Verification and limits

Focused automated checks cover dirty fields, graph history, Cancel/Discard/Save,
failed and unknown saves, pending Save followed by Undo, competing opens,
preparation races, retained receipts, sidebar refresh and modal shortcuts.
Existing graph, Library, experiment, conversion and import/recovery checks remain
unchanged. The version-linked private regression pack supplies the added tests.
TypeScript and the production frontend build passed; the existing bundle-size
advisory remains. These are focused component checks, not the full product suite.

A current own-cloud production server started, but the supported cloud browser
returned `net::ERR_CONNECTION_REFUSED` to its loopback address. Actual browser
layout/keyboard acceptance and screenshots remain blocked, not passed. Current
Windows/native and owner acceptance remain separate.

This is session-only protection. It does not add autosave, crash/reload recovery,
a close-window draft guard, native execution/trust changes, strategy-engine
changes, a product-version bump, a release or a merge.
