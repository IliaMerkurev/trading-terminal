# ADR 0012: Reversible editing and isolated desktop runtime

Status: implemented; native acceptance gaps are recorded in [status](../STATUS.md).

React Flow 12.11.6 remains the editor. On empty-canvas context click, `screenToFlowPosition` converts the original client coordinates once. A body portal positions/clamps the search menu independently, preventing panel overflow from changing graph coordinates. Search includes full indicator names and abbreviations, grouped empty-query results, keyboard selection and outside/Escape dismissal. The four fixed signal outputs are excluded. Creation uses fresh IDs, independent defaults, no implicit connections and selection/settings focus.

Editor history stores at most 100 graph/layout snapshots for the current strategy. A drag/deletion transaction has one undo entry; new edits invalidate redo. Loading, copying or creating another strategy resets history. Input fields retain native text shortcuts. Duplication deep-copies selected nodes and remaps their internal references; existing outside inputs remain linked explicitly and fixed outputs are not duplicated. Incomplete disconnected drafts can be saved, while invalid runs fail before a worker starts. Actionable validation selects and centers the relevant block/field.

Recorded fills are grouped by candle and side using compact markers. Full fill details and trade rows remain accessible. The backend derives exact candle association before epoch nanoseconds lose precision in JavaScript. Indicator changes preserve the chart's visible logical range when the same saved data window is displayed. Indicators always come from recorded series, not frontend recomputation. Comparison adds human labels/units while retaining raw contract identifiers.

The desktop host accepts process-only `TRADING_TERMINAL_PYTHON` and `TRADING_TERMINAL_DATA_ROOT` overrides. Data roots must be absolute; the default is this checkout's own local data directory. A versioned startup handshake reports ownership/startup errors before ordinary requests. The application acquires workspace ownership before any schema migration. Build paths and WebView storage stay within the selected checkout/data root, enabling a separate V2 build while an older build remains running.

`scripts/desktop.py` uses its calling Python environment and can build/run without PowerShell script-policy changes. It never installs or updates dependencies. `scripts/verify_migration.py` verifies migration on a new copy of a consistent backup and refuses to overwrite an existing destination. Native UI behavior and Windows scaling require actual acceptance observations; mocked component tests do not substitute for them.

References: [React Flow instance](https://reactflow.dev/api-reference/types/react-flow-instance), [context menu](https://reactflow.dev/examples/interaction/context-menu), [V1 desktop](0007-desktop.md).
