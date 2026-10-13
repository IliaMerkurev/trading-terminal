# Market network and offline chart validation — 2026-10-11

This is bounded evidence, not live-provider or Windows/native acceptance.
Runtime source remains `ff12a4e`; this checkpoint changes documentation only.

## Network observations

- The earlier standalone Python `urllib` request to `www.okx.com` returned
  HTTP 200. Its saved H4 import was real public market data. A later M1 attempt
  failed with `Tunnel connection failed: 403` and `http_status: null`, then
  stopped. That tunnel failure does not prove an OKX HTTP 403 response.
- The current desktop host has no proxy environment configuration; the command
  execution environment has a standard credential-free proxy configured. No
  configuration values are published. Actual desktop OpenAPI REST and WebSocket
  attempts failed with network unreachable (`errno 101`).
- One current execution-environment M1 REST probe returned HTTP 200 and API
  `code: 0`. One Bybit REST probe returned HTTP 200 with non-JSON content;
  Bybit API operation remains unverified, and that probe was not retried.
- The normal `scripts/browser.py` service launched on loopback port 8796 in
  the execution environment, but the assistant's separate VM browser returned
  `ERR_CONNECTION_REFUSED`. The service was stopped. No bridge, forwarding or
  proxy-setting change was made.
- One new 300-candle M1 snapshot attempt returned HTTP 403 and stopped. Its
  cause is unproven; these observations do not establish universal VM blocking.

## Real-data offline display check

A private offline harness, outside production, reused the existing 300 real H4
candles covering 2026-07-13 through 2026-09-01 exclusive, with the original
2026-10-10 acquisition receipt. It used no synthetic or freshly acquired data
and makes no fresh-feed or live-connectivity claim. Raw candles, source snapshots,
receipts and private paths are not included here or published to Git or Drive.

The harness reused actual `MarketChart`, `Indicators` and `DisplayIndicators`
components. Only 4H was available; acquisition, streaming and trading were
disabled. An independent six-indicator oracle, TypeScript checks and production
build passed. Browser inspection in the assistant's VM verified:

- Readable headers and 300 confirmed candles, zero unknown and zero gaps.
- EMA 78391.24785 and RSI 52.75555044.
- Added MACD 52.26579784, signal 9.282397455 and histogram 42.98340038.
- Indicator settings retained after page reload.

The visible offline browser tab on port 8797 was left available for inspection.
This validates the bounded offline display, not production transport, sustained
live operation or owner acceptance. No runtime/frontend/test source changed,
and no broad regression suite was rerun for this documentation-only checkpoint.

## Unverified alternatives and privacy boundary

Documentation-only candidates are [KuCoin native REST klines](https://www.kucoin.com/docs-new/rest/spot-trading/market-data/get-klines)
for `BTC-USDT` (up to 1,500 candles per request) and
[Kraken OHLC](https://docs.kraken.com/api-reference/market-data/get-ohlc-data)
for `BTC/USDT` (up to 720 entries, with the last entry uncommitted).
Neither provider was probed, integrated or accepted. Changing providers alone
cannot repair a missing network route on the desktop host.

No credentials are needed for these public-data checks. Any future API keys
must remain in owner-local, isolated encrypted storage; no such storage or
authenticated integration was added in this checkpoint.
