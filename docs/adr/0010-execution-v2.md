# ADR 0010: Versioned continuous protection paths

Status: implemented; verification recorded in [status](../STATUS.md).

## Decision

Retain NautilusTrader 1.231.0 and the existing graph, risk gateway and account model. Profile version 1 retains four discrete O/L/H/C or O/H/L/C observations. New visual strategies default to profile version 2. Saved strategies keep their recorded version until explicitly edited. Native strategies retain version 1 and their own exit semantics; selecting version 2 for native execution fails visibly.

Version 2 models linear continuous segments *inside* a minute using the chosen trade-candle path. Adjacent minute boundaries remain discontinuous observations, including opening gaps. A held position can introduce an additional crossing observation inside a segment. A new position becomes eligible only after its actual entry fill; earlier high/low values cannot trigger it. Signals still consume an M1 candle only after its close and retain the existing primary-timeframe aggregation/partial-H1 rules.

The first eligible crossing triggers a market exit. This is neither a limit order nor evidence of historical tick execution. A stop/take crossing supplies its modeled trade price; directional slippage and adverse tick rounding then determine executable bid/ask. Fees use actual execution notional. An opening gap beyond a level exits at the first available quote with those costs, not at an unavailable stop price. Full-position exits and no same-minute protective-exit re-entry are preserved.

Separate mark candles follow their own selected OHLC ordering on the same modeled timeline. Mark price determines equity, maintenance and liquidation; it never substitutes for the executable trade quote. Funding is charged once at its historical minute boundary to the held position. At one modeled timestamp, funding precedes maintenance/liquidation, which precedes stop/take. Within a segment, the earliest mark-liquidation or trade-protection crossing wins; exact ties prioritize liquidation. Constant risk-tier limits still fail visibly when exceeded. Cross-margin, one-position and precision assumptions remain unchanged.

The engine's documented streaming `run(streaming=True)`, `clear_data()` and `end()` lifecycle processes bounded path segments while preserving engine account/order state. Candidate crossing levels are calculated from the currently open engine position and balance, not from future entry signals. Crossing timestamps have nanosecond resolution; reported prices use exact decimal crossing fractions before executable tick rounding. This is an explicit synthetic path, not recovered tick history.

## Alternatives and limitations

Keeping only extreme observations preserves execution profile 1 but gives an 80 exit for an already active 95 stop on an O=100/L=80 segment. Replacing engine accounting or multiplying spot PnL by leverage would violate the agreed model. Precomputing levels from future entry prices was rejected because it could introduce observations before activation. Streaming uses the existing engine without adding another engine or dependency.

Profile version is part of immutable snapshot identity and comparisons. Existing snapshots, metrics and hashes are never migrated to version 2. Version-1 behavior is covered by the retained regression suite. Historical snapshots also contain an implementation/runtime checksum; current code is not claimed to be the identical old runtime. Viewing/exporting them does not rerun them. Run a fresh snapshot with explicit version 1 for behavioral comparison.

## Independent checks

An existing long at 100 with stop 95 and take 105, followed by O=100/L=80/H=120/C=100, exits at 95 under OLHC and 105 under OHLC before costs. Equivalent short fixtures verify the opposite reasons. Version 1 retains 80/120. Other fixtures cover opening gaps, absence of pre-entry triggers, actual fees/slippage, mark/trade separation and funding-induced liquidation. See `tests/test_execution_v2.py` and retained product 0.1 risk/causality tests.

## References

- [NautilusTrader streaming lifecycle (nightly reference; implementation verified against installed 1.231.0)](https://nautilustrader.io/docs/nightly/concepts/backtesting/apis-and-runs/)
- Installed pinned `nautilus_trader/backtest/engine.pyx` documents the streaming lifecycle used here.
- [Execution profile 1](0002-simulation-profile.md)
