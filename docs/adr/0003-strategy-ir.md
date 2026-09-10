# ADR 0003: Typed graph IR and committed primary-bar indicator state

Status: implemented and integrated with the simulation profile. Scope:
[PROJECT sections 3, 4, 8 and 9](../../PROJECT.md). IR version 1.

## Representation

IR contains only `version`, `nodes` and `outputs`. A node contains stable `id`,
`type`, named `inputs` and `params`. Input references are `nodeId.outputPort`.
All four signal outputs are required, with null meaning disconnected. Layout,
selection and panel state belong to a separate UI document. Changing coordinates
must not change a strategy's semantic checksum.

The validator rejects unknown fields/types/ports, mismatched number/boolean
connections, missing nodes, duplicate IDs and cycles. The language has no code,
eval, exec, file or network nodes. Limit graphs to 128 nodes and indicator periods
to 1–10000 for bounded resource use; these are graph resource limits, not limits
on historical date ranges. A small explicit validator suffices for this IR and
avoids adding a dependency solely to validate these bounded shapes.

| Type | Inputs | Outputs / parameters |
| --- | --- | --- |
| price | none | value; field open/high/low/close/volume |
| constant | none | value; finite number |
| sma / ema / rsi | numeric source | value; period |
| bb | numeric source | upper/middle/lower; period, deviations |
| macd | numeric source | macd/signal/histogram; fast, slow, signal periods |
| atr | current primary OHLC | value; period |
| compare | numeric left/right | boolean value; >, >=, <, <=, ==, != |
| cross_above / cross_below | numeric left/right | boolean value |
| and / or | boolean left/right | boolean value |
| not | boolean source | boolean value |

One indicator node can feed several conditions/outputs. An indicator may consume
another numeric indicator output; it starts advancing only when its source is
defined. Boolean logic preserves unknown warm-up values; NOT unknown is unknown,
not an entry signal. Output signals require exactly true.

## Native indicators and causality

Use the pinned Nautilus indicators, including their tested copy protocol. Each
node holds state after the last **completed primary bar**. For every partial
update, clone that state and apply the current known primary bar once. Commit
the candidate state only when that primary interval closes. This avoids both
replaying the entire history for every minute and accidentally advancing an H1
EMA sixty times per hour. No second UI indicator calculation is permitted.

The evaluator processes nodes in dependency order and records every evaluated
value with its timestamp. A cross is a transition from previous **evaluation
step** left <= right to current left > right (or >= to < for cross below).
The first defined sample cannot cross without a previous defined pair. Intrabar
crosses compare consecutive partial evaluations; closed-mode crosses compare
closed primary bars. This choice is part of the saved IR/runtime semantics.

Initialization is version-specific and independently checked:

- SMA is undefined until period samples, then arithmetic rolling mean.
- EMA uses alpha 2/(period+1), seeded with the first source value; output remains
  undefined until period samples. For period 3 and 10,12,14, output is 12.5.
- RSI uses the native Wilder gain/loss recurrence (zero initial changes), scaled
  from the native 0–1 value to 0–100. Period 2 with 10,12,11 yields 50. This differs
  from packages that seed initial gains/losses with another convention.
- Bollinger uses the selected source value for all three native price inputs,
  so its mean/deviation describes that numeric source, not implicit typical price.
  Period 2 with 12,14 and two deviations yields middle 13, upper 15, lower 11.
- MACD is native fast EMA minus slow EMA. Its signal EMA begins once MACD is
  initialized; histogram is MACD minus signal and waits for signal warm-up.
- ATR uses Wilder smoothing and previous close; the first true range seeds it.
  Ranges 4,5,4 at period 2 yield 4.5 then 4.25 after warm-up.

## Integrated evidence and measured bound

Eleven graph tests cover independent indicator values, crossing equality,
three-valued boolean logic, nested indicators, immutable snapshots, invalid
graphs and repeated partial-state copies. A full engine test uses 60 minutes at
100, then 30 at 130, then 30 at 90. The partial H1 SMA(2) moves from 115 to 95:
intrabar mode trades, closed mode does not. Changing only future minutes leaves
all earlier recorded graph values and fills unchanged. Missing finer minutes
already fail the integrated intrabar simulation instead of changing modes.

Measured on Windows with Python 3.12.14/NautilusTrader 1.231.0:

```powershell
.venv/Scripts/python.exe -m benchmarks.profile_run --minutes 10080
```

A seven-day synthetic M1 fixture with intrabar H1 evaluation completed in 1.464s;
process peak working set 260.5 MiB; normalized JSON 9.13 MiB; nine closed trades.
These figures include this process's Python/native imports and are not a
guarantee for larger graphs or datasets. Initial interactive acceptance budget:
this fixture under 10s and under 1 GiB on the target Windows environment. Larger
data must use bounded UI payloads; do not send an entire run over each IPC message.
