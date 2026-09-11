# ADR 0007: local Windows desktop research host

## Decision

Use pinned Tauri 2, React 19, React Flow and Lightweight Charts. The Rust host owns
a Python application service over bounded JSON-line pipes. The service owns the
single calculation worker. No HTTP application server or general shell/filesystem
plugin is exposed to the renderer. Public data downloads use a separate cancellable
thread with bounded HTTP requests, so IPC remains responsive.

The development executable embeds built frontend assets with `custom-protocol`.
It uses the compiling checkout's Python environment and local data directory;
moving the checkout requires rebuilding. A conventional relocatable installer is
deferred. The WebView profile is stored with local application data. Closing the
window ends the service, which cancels its worker; minimizing leaves it running.

React Flow coordinates are separate from typed Strategy IR. Native imports have
source-only preview and a separate consent operation. Simulation controls are
passed to backend validation; native-only semantics stay in native configuration.

Charts display bounded windows of saved M1 candles labeled at minute close,
indicators at their recorded availability times, fill markers, and the last
recorded equity in each minute. Indicator values are never recomputed by the UI.
Selecting a trade changes the chart window. Full-resolution equity remains in the
immutable result, including intraminute observations used for drawdown metrics.

## Dependencies and validation

Exact frontend/Cargo versions are in lockfiles. Installation uses the official npm
and crates.io registries. JavaScript lifecycle scripts are disabled; no release-age
exception is retained. Rust build scripts are part of the reviewed dependency
toolchain. Existing Windows MSVC and SDK compiled the host without updates.

TypeScript and frontend production build pass. UI tests cover graph connections,
save wiring, nonexecuting native selection/save, and stored-value chart projection.
The compiled Windows UI was launched and saved a graph through Rust/Python into
SQLite; this is distinct from component tests. Actual desktop checks also cover
saved-result charts, trade navigation, comparison/export, active minimize/restore,
and close/return. Component tests verify cancellation-before-exit IPC ordering;
Windows process tests verify worker-tree cancellation. Native file-dialog and
owner acceptance distinctions are recorded in the demonstration guide.

Polling permits only one in-flight request per subscription. A protocol timeout
or mismatched response puts the host connection into a visible failed state,
requiring restart and history inspection before retrying a write. It never silently
replays a possibly completed operation.

See [third-party notices](../../THIRD_PARTY_NOTICES.md). Project license and binary
release permissions remain unchanged.
