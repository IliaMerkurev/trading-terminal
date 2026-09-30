# ADR 0026: Research workspace and longer-horizon candidates

## Context and decision

The owner authorized a simpler strategy-card workflow on 2026-09-30. Research is
the default workspace, with Strategies, History and Results. Pro retains the
visual editor, native source trust, parameter experiments and existing live
features. Its draft and profile remain independent from Research settings.

Each card has a main timeframe and explicit additional comparison timeframes.
One batch contains at most 12 strategy/timeframe selections, followed by two
passive alternatives. Parameters and reviewed source details are expandable.
Metrics come from saved runs; modified inputs label old metrics as prior results.
History preparation exposes actual execution resolution separately from strategy
timeframe. The backend reserves preceding warmup and supplies instrument precision.
Users can update saved history or select it again without losing that reservation.
See [ADR 0025](0025-research-resolution.md) for coarse execution limitations.

## Strategy sources

Add two independently authored declarative graph adaptations using the existing
engine and pinned libraries. No third-party source file, executable or new
dependency is installed or imported for these additions.

Both ideas use QuantConnect Lean commit
`985ef30ad3ac774218c5ac516b4cb0aa2655730f` (2026-09-18), Apache-2.0:

- [MovingAverageCrossAlgorithm.py](https://github.com/QuantConnect/Lean/blob/985ef30ad3ac774218c5ac516b4cb0aa2655730f/Algorithm.Python/MovingAverageCrossAlgorithm.py):
  SHA256 `1db7156684722fd9ddeefdffa2a20d5c60bb02bca39cf973027378ea0c660edf`.
  EMA trend filter defaults to daily 15/30 EMA with 0.00015 entry tolerance.
  Enter when fast EMA exceeds slow EMA times (1 + tolerance); exit below slow EMA.
  Engine initialization and profile sizing differ from upstream. This expands
  spot/coarse access to an existing trend family, not the number of unique ideas.
- [DonchianChannel.cs](https://github.com/QuantConnect/Lean/blob/985ef30ad3ac774218c5ac516b4cb0aa2655730f/Indicators/DonchianChannel.cs):
  SHA256 `89c2e61ebfd08750f67243a4ca109d041d7bb779c30ec04b9db53c3a176d65b6`.
  The source is an indicator, not a complete trading strategy. Our graph enters
  above the previous 55-bar high and exits below the previous 20-bar low. These
  periods and the daily default are local research choices, not author advice.
  Unlike upstream's current-bar channel, the new node excludes the evaluated bar
  and commits its bounded windows only after a confirmed bar. No pyramiding.

Pinned LICENSE SHA256:
`522cf0a716ce03f67d46f8fceb5bf78c5b84400ec5cd8d14bf9f02cddc1cb6ba`.
Static review found no direct credential access, shell/process invocation,
dynamic execution or filesystem writes in these source files. Framework runtime
is not loaded. License text and existing attribution remain in the repository.

## Alternatives and evidence

A single advanced form obscures the common browse/select/compare workflow.
A second execution engine would duplicate accounting. Automatically downloading
and importing community Python strategies would expand the trust boundary.
The selected design reuses explicit source review, graph IR and retained Nautilus
execution. Native Python continues to require separate source-bound consent.

Independent tests cover prior-window extrema, repeated partial updates, bounded
state, EMA recurrence, exact fees and losing trades, and future perturbation.
New strategy, graph and coarse integration checks passed: 23 tests in 4.473s.
Final combined evidence is recorded in [status](../STATUS.md) and
[library verification](../library/VERIFICATION.md). Neither source reputation nor
these tests establish future profitability. Historical source dates are disclosed.
