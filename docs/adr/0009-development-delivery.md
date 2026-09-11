# ADR 0009: reproducible development delivery and validation boundaries

## Decision

Deliver V1 as a documented Windows development build with a one-time setup and a launch script. A relocatable installer, binary release and license assignment are deferred. Use the existing validated MSVC/SDK rather than require a system upgrade.

For the bounded Python application protocol, use dataclasses, Decimal and explicit strict field/type checks rather than add Pydantic to the proposed baseline. The Strategy IR, profile, native descriptor and archive validators have focused negative-input and correctness tests. This avoids a second validation dependency without changing product behavior. Reconsider a schema library if protocol expansion makes the handwritten checks difficult to audit.

Use the standard virtual environment and pip hash-checking installation path for the validated Windows wheels. uv remains pinned in the environment but is not required to perform installation. The full runtime lock includes installer tooling, exact versions and official wheel hashes. This keeps setup simple and permits offline reinstallation from a verified wheelhouse. Existing environments are checked, never silently replaced. Frontend and Rust use their own committed locks and project caches.

## Evidence and budgets

A new isolated Windows Python environment installed 17 exact packages from verified wheels, passed `pip check`, and passed all 79 Python tests. Setup and the launcher's build-only mode also passed in the working checkout. This is a clean Python environment check, not a claim that a fresh Windows machine was provisioned automatically.

The measured seven-day intrabar fixture took 1.464 seconds and 260.5 MiB peak worker memory. Use 10 seconds and 1 GiB as initial review thresholds for that specific fixture on the reference Windows class of machine, leaving headroom for instrumentation. A threshold exceedance triggers investigation, not an arbitrary date-range limit or silently reduced data. The UI limits a chart page to 480 minutes and regular result pages to bounded payloads. Arbitrary native code and very long history require separate measurements; no universal memory guarantee is claimed.

## Acceptance boundary

The development demo supplies independently checked synthetic cases and an actual public-data workflow. Automated financial/causality/worker/archive checks, component tests, native desktop observations and owner acceptance are reported separately. Native picker automation was unavailable and desktop cancellation clicks occurred after completion; the component cancellation ordering and Windows worker-tree cancellation are tested independently. These remaining manual observations are documented in the demo, not mislabeled as completed UI tests.

Review third-party notices before any binary distribution. Publishing original project source does not select the project's license or authorize a release.
