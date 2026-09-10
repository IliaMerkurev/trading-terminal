# Engine evaluation

Status: no engine selected; runtime experiments not yet performed. Requirements are defined in [PROJECT.md](../PROJECT.md). Freqtrade, Jesse, and NautilusTrader have no preset ranking. Other candidates require a reason for inclusion.

## Evaluation process

1. Verify Windows and Python compatibility, distribution requirements, and package/example licenses using version-specific primary sources.
2. Compare requirements using native / configuration / small adapter / deep fork / unsupported / unverified. Unverified does not mean unsupported.
3. Select one candidate for a minimal experiment; avoid building several integrations at once. Prefer a stable release. Explain any pre-release choice and rollback path.
4. Test key risks with independent expected outcomes. Move to another candidate only for a concrete limitation.
5. Record a proposed, provisional, or accepted ADR with exact versions, alternatives, matrix, commands/results, sources, adapters, limitations, and reconsideration conditions.

## Selection criteria

Windows packaging; Python ABI; infrastructure burden; native strategy API and licensed examples; unleveraged spot and perpetual long/short; fees/slippage/funding; mark price; initial/maintenance margin and liquidation; causal partial bars; cancellation; reproducibility; and the cost of avoiding a permanent fork.

## Minimum experiments

A spot trade, perpetual long and short, fees/slippage, funding timing, mark movement with unchanged last price, intrabar signals that disappear by hourly close, future-data perturbation, and Windows worker cancellation. Include one vetted licensed native example without changing strategy semantics. Do not download arbitrary community strategy collections.

Recalculating a forming H1 strategy on M1 steps must not become M1 indicator logic or only more precise execution of a fixed signal. Record every missing requirement as open. A partial experiment yields a provisional selection, not full integration evidence.

## Primary source entry points

These links are research entry points, not verified capability claims.

- [Freqtrade documentation](https://www.freqtrade.io/en/stable/) and [repository](https://github.com/freqtrade/freqtrade)
- [Jesse documentation](https://docs.jesse.trade/) and [repository](https://github.com/jesse-ai/jesse)
- [NautilusTrader documentation](https://nautilustrader.io/docs/latest/) and [repository](https://github.com/nautechsystems/nautilus_trader)
- [Bybit OHLCV](https://bybit-exchange.github.io/docs/v5/market/kline), [Mark Price](https://bybit-exchange.github.io/docs/v5/market/mark-kline), and [funding history](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate)
