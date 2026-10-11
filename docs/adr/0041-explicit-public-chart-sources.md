# ADR 0041: Explicit public chart sources

Status: implemented; synthetic browser acceptance passed. Actual live-provider
verification is blocked by network unreachable (errno 101); current Windows
acceptance remains pending.

## Decision

Market has an explicit persisted Bybit / OKX selector. Missing source parameters
retain the legacy Bybit IPC meaning. There is no automatic provider fallback.
OKX is display-only: starting/resuming strategy or paper monitoring requires
Bybit in both the UI and service. Recorded Bybit overlays and retained quotes
are hidden on OKX. This does not add execution, historical research acquisition,
accounts, credentials, orders or dependencies.

Existing `chart_*_v1` tables retain their primary keys and all legacy rows.
Their internal market namespace is `spot`/`linear` for Bybit and `okx:spot` /
`okx:linear` for OKX. The public IPC still uses physical market plus validated
source. Candles, confirmations, page coverage, indicator settings, replay origins
and calculation hashes therefore cannot share a source identity. The namespace
is internal and cannot be supplied as a physical market through the public API.

The OKX adapter uses native interval history and candle updates with explicit
`confirm`. The current forming candle remains unconfirmed; elapsed time never
promotes it. Daily bars use UTC opening boundaries. Spot volume is base currency;
perpetual volume is contracts. Missing mark/funding fields remain unavailable.
The order book is the public five-level snapshot, not Bybit's depth-50 delta feed.

Two required OKX sockets share the single market owner: public quotes/book/trades
and business candles. Bounded nonblocking round-robin draining avoids letting a
quiet candle connection starve public traffic. Literal ping/pong, subscription
acknowledgements, validation, stale handling and bounded reconnect remain explicit.
No regional-host fallback, proxy or access-control bypass is implemented.

Source changes serialize open/close operations, discard stale UI replies, cancel
queued pages and invalidate in-flight publication with generation tokens. A
blocking REST request can finish its bounded timeout but cannot publish into a
superseded view or delay the new view with stale error/throttle metadata. Exiting
Market cancels page acquisition while separately authorized monitoring is retained.
Errors expose category and available HTTP status only, never remote bodies,
headers, URLs, credentials or traceback contents.

## Sources and limits

Reviewed official [OKX API documentation](https://app.okx.com/docs-v5/en/):
REST `https://openapi.okx.com/api/v5/market/history-candles`, exclusive `after`
paging, maximum 300 rows; `wss://ws.okx.com/ws/v5/public` and
`wss://ws.okx.com/ws/v5/business`; tickers, books5, trades and native candles.
Port 443 follows the official [8443 discontinuation announcement](https://www.okx.com/en-eu/help/okx-websocket-port-8443-discontinuation-announcement).

The [OKX API Agreement](https://www.okx.com/en-gb/help/okx-api-agreement) applies
to public data too. The owner must personally handle applicable acceptance and
eligibility before activation. This local display adapter does not grant data
redistribution rights. Offline fixtures prove protocol and separation behavior;
they do not prove provider availability, real-time performance, agreement
acceptance, current Windows behavior or successful live-feed connectivity.

## Future authenticated adapters

Any future exchange API keys must remain only in local, isolated, encrypted
secret storage on the owner's device. Never persist them in project files,
ordinary settings/databases, logs, Git or a cloud VM. Provider-specific account
access, key-entry consent, storage design and trading authorization require a
separately scoped implementation. This public adapter neither requests nor
stores credentials and does not implement that future facility.
