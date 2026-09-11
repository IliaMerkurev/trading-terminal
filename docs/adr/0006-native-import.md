# ADR 0006: Explicitly trusted native Python strategies

Status: implemented through the same managed worker/results service. Desktop
file selection and trust controls remain for UI integration. Scope:
[PROJECT sections 4 and 7](../../PROJECT.md).

The supported native format is a single Python module exposing NautilusTrader
1.231.0 `Strategy` and `StrategyConfig` classes. The source may import installed
dependencies; the application never installs them automatically. Store engine
version, exact declared distribution versions, source/dependency provenance,
class names, native config and declared external bar timeframes with the source.

Preview uses only bounded AST parsing and distribution metadata. Selecting,
previewing, saving or reopening a native document does not import it. AST
inspection is not a safety proof or a complete dynamic compatibility checker.
The UI must show that Python has user-level capabilities and that worker lifetime
control is not a security sandbox.

Explicit consent records a digest of source, engine/version and dependencies in
the local workspace database. Changing any of those invalidates consent; numeric
config editing does not pretend the same source is a new program. Confirmation
must match the previewed digest. Consent itself does not execute code. Run start
and the worker both verify consent, then module loading occurs only inside the
managed worker. Imported archives must not carry trusted status.

The native config class parses its own JSON values. Two explicit placeholders
are available: `$instrument` supplies the run instrument ID and `$bar:N` supplies
a declared N-minute external bar type. Source code is never rewritten or
converted into graph rules. Errors name missing dependencies or incompatible
features; they are not silently repaired with package installs or altered code.

## Precedence and compatibility boundary

Native source/config controls signals, quantity, explicit exits and native risk
decisions. Graph allocation settings do not resize its orders. Graph intrabar
mode and graph stop/take controls are unavailable for native inputs; nonzero or
incompatible settings fail rather than being ignored. Capital, leverage,
precision, fees, slippage, funding and the simulation's margin/one-position
constraints still govern execution. Unsupported scaling/partial exits and
complex orders invalidate the run. Native explicit full-close orders preserve
their normal semantics. A position left open by native shutdown invalidates the
result; the adapter does not secretly change the native stop hook.

The verified feed is completed external trade bars on up to six declared
timeframes. They share the same causal minute source and publish ascending
timeframes when several complete together. Two-timeframe callbacks are tested.
This does not add multiple visual timeframes. Native historical requests,
undeclared feeds, quote/trade-tick feeds and order-book feeds fail visibly; the
synthetic OHLC execution quotes are not advertised as real native quote history.

Record native registered indicator values directly after engine events, with
native initialization/scales and generated names. Unregistered/private custom
values cannot be inferred; no chart substitutes an independently recomputed
indicator. Native strategies using custom private indicators need explicit
registration to expose those values for charts. Dynamic code cannot be perfectly
audited statically; the compatibility boundary is not a promise that every
Nautilus strategy works unchanged with these historical feeds.

## Verified native example

The installed LGPL official `EMACross`/`EMACrossConfig` example runs unchanged
using external bars, `request_bars=false`, `subscribe_trade_ticks=false`, fast 2,
slow 3 and quantity 1. These are ordinary native config values, not rewritten
signal semantics. On the five-bar rising fixture it buys 104 and closes 108,
yielding gross/net PnL 4 with zero test fees. Source and license identity were
reviewed in [ADR 0001](0001-engine.md). Only an import statement is stored in the
test wrapper; the LGPL example source is not copied into the repository.

Six Windows integration tests verify a harmless import side effect remains absent
through preview/save/reopen and failed untrusted start, then occurs only during
trusted execution; changed source requires fresh consent. They also check stdout
isolation, missing dependency errors, wrong-digest rejection, native multi-bar
callbacks, unavailable data requests and partial-exit rejection. The complete
test inventory is 71. User acceptance of the desktop import workflow is pending.
