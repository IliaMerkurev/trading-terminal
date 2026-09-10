# Development guide

Status: specification stage. No application build or launch command is available yet.

## Preparation

Read [PROJECT.md](../PROJECT.md), [architecture](ARCHITECTURE.md), [engine evaluation](ENGINE_SELECTION.md), and [status](STATUS.md). Check Git state and preserve existing changes. Verify Windows toolchain versions before installing dependencies. Use project-local pinned environments and review package provenance/licenses. Missing system prerequisites must be reported rather than silently installed or bypassed.

## Implementation sequence

1. Validate a backtesting engine with minimal Windows experiments.
2. Define accounting/event semantics and independent regression fixtures.
3. Implement versioned Strategy IR and one engine adapter.
4. Add history coverage, dataset snapshots, and run manifests.
5. Implement cancellable workers and persistent normalized results.
6. Integrate explicitly trusted native Python imports.
7. Build the Strategy / Backtest / Results research workflow.
8. Verify comparison/export, clean setup, and Windows acceptance scenarios.

A milestone must state implemented behavior, actual commands and outcomes, open requirements, and next work. Synthetic UI fixtures are not integrated backtests. User acceptance remains distinct from automated verification.

## Validation and publication

Use targeted tests with independently derived expected results, including future perturbation. Record platform and dependency versions. Validate cancellation and subprocess cleanup on Windows. Never claim a test was run based on its planned command.

Inspect exact staged files and diffs, scan outgoing history for secrets, and review license/privacy obligations before publication. Keep local datasets, logs, environments, and private execution materials untracked. Documentation changes must preserve specification requirements and valid relative links. Ordinary deletion never cleans previous commits.

The project license remains undecided. Do not copy third-party code without established rights and required notices.
