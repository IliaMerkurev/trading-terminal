# ADR 0001: NautilusTrader as the first engine, with an explicit simulation adapter

Status: accepted for continued 0.1 implementation; the complete application and
exchange profile are not yet validated. Version: NautilusTrader 1.231.0,
Windows x64, CPython 3.12.14. Scope: [PROJECT sections 2–5 and 9](../../PROJECT.md).

## Decision and alternatives

Use NautilusTrader's native `Strategy` format, event processing, order execution,
position accounting and indicators. Keep the installed package unchanged. Add
an explicit single-position risk gateway and funding/mark simulation module.
Reconsider this choice if those extension points cannot pass the full profile
fixtures without a maintained engine fork or silent native strategy rewrites.

| Candidate | Evidence and adaptation cost | Decision |
| --- | --- | --- |
| Freqtrade | Native strategies and mature backtest workflow. Official Windows guidance emphasizes Docker/WSL; GPLv3 distribution obligations. Partial-primary-bar indicator reevaluation and the required margin profile remain unverified. | No runtime experiment; a less direct Windows desktop fit, not a claim of impossibility. |
| Jesse | Native strategies; MIT repository license. Full application uses PostgreSQL/Redis, while its research API can be used separately. Exact Windows/futures/partial-bar compatibility remains unverified. | No runtime experiment. Keep as a fallback if the first adapter becomes a deep fork. |
| NautilusTrader | Official CPython 3.12 Windows wheel installed with hashes. In-process native strategy API, explicit event types and simulation extensions. LGPLv3+ obligations. Tests below exercise actual Windows runtime. | First implementation candidate, with documented missing built-in risk behavior. |

No additional engine was added: no measured failure yet justifies another
integration or a second calculation engine. Installation alone was not the
selection criterion.

## Coverage classification

| Requirement | Classification and evidence |
| --- | --- |
| Spot / perpetual long and short, fills and fees | Native; independent synthetic round trips verified. |
| One-tick adverse slippage | Native FillModel configuration; changed fills/balance verified. Percentage profile still to implement. |
| Initial / maintenance margin amounts | Native StandardMarginModel configuration; independent 10 / 5 USDT fixture verified. Its rates are not divided by leverage again. |
| Initial margin admission | Adapter required. Installed risk engine returns early for margin accounts; a raw insufficient-collateral order fills. The risk gateway denies that order and emits the native denial event. |
| Funding | SimulationModule adapter proof; scheduled long debit / short credit verified once. Production history/timing contract remains open. |
| Mark-driven liquidation | SimulationModule adapter proof; mark changes close long/short at unchanged executable last-price quotes. Not a claim of full Bybit UTA liquidation. |
| Causal forming H1 | Application aggregation plus native SMA; known partial hour replaces the forming bar. Future perturbation and disappearing intrabar signal verified. Full graph adapter remains open. |
| Native Python | Installed official EMACross executed unchanged on a vetted synthetic scenario. Import trust workflow and compatibility diagnostics remain open. |
| Windows cancellation | Engine worker and its spawned child both terminate through a Windows Job Object. This is lifetime control, not security isolation. |
| Complex orders / scaling / partial exits | Outside the 0.1 profile. Unsupported commands are denied and recorded as fatal profile violations; no valid result may be published. |
| Historical tiers, data coverage, UI, persistence | Unverified; subsequent milestones, not inferred from engine tests. |

The risk gateway uses the named `RiskEngine.execute` MessageBus endpoint and
public command/event APIs. This version-sensitive integration is pinned and
must be retested on upgrade. Accepted commands continue through the original
risk engine. Immediate simulated market execution (`use_message_queue=False`)
prevents a liquidation close remaining queued into the next strategy callback.
Simulation constraints govern fills/capital; native strategy code still governs
its own decisions. Graph entry/exit semantics will be implemented separately.

## Executed evidence

Run from the repository root on Windows:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

The first suite contains 16 checks: execution (5), risk extension (5), causality
(4), native example (1), Windows worker tree (1). Test expectations include:

- Capital 1000, quantity 1, buy 100 / sell 110, 0.1% each-side fee: 1009.79.
- Perpetual short with the same prices: 989.79, without a leveraged-PnL shortcut.
- Adverse 0.01 fills: 1009.77.
- Funding at 1% of 100 notional: long pays 1, short receives 1.
- Long mark 80 from entry 100 with cash 20: equity 0, maintenance 4;
  short mark 120: equity 0, maintenance 6. Last-price execution stays at 100.
- H1 SMA(2), first close 100 and current partial close 130: 115; later close 90:
  95. Sixty minute updates append one closed H1, not sixty fictitious bars.
- Official EMACross buys 104 and closes at 108 on a rising five-bar fixture:
  realized PnL 4 with no fees. This scenario does not validate reversal behavior.

Known compatibility warning: upstream uses deprecated Pandas `Timestamp.utcnow`.
The warning is not suppressed and does not fail the current numerical checks.
The partial-SMA probe rebuilds its short input history; it is not a performance
implementation for large datasets. Wider profile, precision, gap and native
compatibility checks are still required before 0.1 acceptance.

## Sources and license boundaries

- [NautilusTrader package](https://pypi.org/project/nautilus_trader/1.231.0/),
  [engine repository](https://github.com/nautechsystems/nautilus_trader).
  Installed `risk/engine.pyx`, `backtest/engine.pyx`, margin models and module APIs
  are the version-specific evidence; latest web docs can differ.
- [Freqtrade Windows guidance](https://www.freqtrade.io/en/stable/windows_installation/)
  and [repository](https://github.com/freqtrade/freqtrade).
- [Jesse documentation](https://docs.jesse.trade/) and
  [repository/license](https://github.com/jesse-ai/jesse).
- [Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

The installed `examples/strategies/ema_cross.py` has an LGPLv3 header and SHA256
`cfdc26b76d03df6cc481d47327d64dd6c23b356236cd061bb87c691b7918d13b`.
It is imported for the test, not copied into this repository. Fixtures and
adapter code are independently authored. NautilusTrader and transitive portion
have LGPL obligations; preserve notices and review source/relinking obligations
before binary distribution. This decision does not assign the project a license.
