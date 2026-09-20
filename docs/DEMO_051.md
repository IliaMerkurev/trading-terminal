# 0.5.1 maintenance acceptance

Use a separately built Windows candidate and an isolated absolute data root. Never seed or alter the ordinary owner database for smoke tests. The product badge must read `0.5.1-dev`.

1. Chart: request older history under a controlled transient provider failure. Confirm an error and retry remain available, without a false history boundary. Retry successfully; verify older candles prepend, viewport stays anchored and current candles remain present. Confirm actual successful exhaustion separately.
2. Results: prepare more than 100 synthetic saved runs. Load older pages through the existing Results workspace. Check stable order, no duplicates, loading/error/empty/end states and retained selection/comparison identifiers.
3. Replay: select a paused synthetic session, open Signals and start verification. Observe background progress while switching panels or requesting ordinary status. Cancel while active; the result must be cancelled, never MATCH. Run a short known session to completion and inspect its independently expected transition count. Close during active Replay to check the existing return/cancel-and-exit dialog.
4. Preservation: verify a consistent copy of existing data before launching against it. Compare every preexisting table and immutable result checksum; `replay_jobs` is additive. Keep native smoke data separate.

Synthetic provider faults and artificial Replay delays must be labeled as such. They demonstrate UI/IPC lifecycle, not natural network failure or market performance. Do not repeat the 0.5 30-minute public-market measurement for this maintenance release. See [STATUS.md](STATUS.md) for executed checks and unperformed owner acceptance items.
