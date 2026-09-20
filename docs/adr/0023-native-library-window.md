# ADR 0023: Explicit native EMA warmup adapter

Status: implemented and focused verification passed, 2026-09-20.

Library EMA version 2 remains a native Python strategy importing the pinned,
unchanged installed Nautilus EMA implementation. Its independently authored
subclass returns from `on_bar` before the frozen evaluation start. Registered
engine indicators still consume preceding complete bars. Signal logic, fixed
quantity, reversals, stop-close behavior and historical-only support remain in
the upstream class. This temporal adaptation is stated on the card; it is not
silently applied to arbitrary native imports.

The source change invalidates version 1 consent. Preview/copy/reopen never loads
the module. Existing source-hash consent is checked before worker execution.
The separate-window command only accepts the exact reviewed adapter document;
modified native code remains unsupported for this path. Unwindowed ordinary
native execution is unchanged. The worker rejects a boundary mismatch or any
fill/account change before evaluation. Warmup-only flat observations are removed
from the normalized report; they contribute no costs, trades or returns.

The batch freezes the adapter config and resulting document hash. Standalone
window runs and batch runs pass the same document through the retained worker,
simulation, risk gate and accounting. Native profile 1, closed bars and linear
long/short behavior remain explicit. Graph position policies and native spot
shorts are not silently reinterpreted. This adds no generic native Live support.

Eleven focused tests passed in 19.360s, including existing native trust/import
checks, exact standalone/batch native trades and metrics, and two distinct
strategies in a synthetic batch. Independent 1m and 3m goldens warm up at
100/102/104, then buy one unit at 106 and close at 108: fees 0.214, net PnL 1.786
with a 0.001 fee rate. No warmup fill occurs. Existing RSI causality and
nontrivial synthetic trade evidence are reused.

A finite copied public-data cohort used BTCUSDT linear and actual separate spot
history from 2026-09-01. Evaluation: 12:00–24:00 UTC; preceding history warms
indicators. Native EMA and adapted RSI both completed at 1m and 5m; native
completed 31/7 positions, RSI 2/1. Losses were retained without retuning. Both
passive alternatives completed; weekly DCA has one purchase in this short
period and therefore matches Buy & Hold under the same frozen cost contract.
Annualized return is N/A. This verifies two implementations, not four strategies
and not the required five-strategy/three-family release. The full final
regression and Library later-period freeze workflow remain pending.
