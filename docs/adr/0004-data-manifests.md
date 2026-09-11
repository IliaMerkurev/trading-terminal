# ADR 0004: Public history client and content-addressed local datasets

Status: implemented, with synthetic error-path tests and actual Windows API /
offline checks. Scope: [PROJECT section 5](../../PROJECT.md#5-data-simulation-and-results).

Use a small standard-library HTTPS client for the required Bybit public market
endpoints. No credentials, trade endpoints, SDK account clients or persistent
server are needed. The client accepts only an endpoint allowlist, refuses HTTP
redirects, bounds each response to 4 MiB and retries transient failures at most
three times. Requests are paced and cancellable. An API error never becomes an
empty successful dataset.

Fetch UTC one-minute OHLCV and aggregate primary strategy timeframes locally.
The range is inclusive start / exclusive end. Reject unaligned or unclosed future
ranges; exclude provider-reported still-forming minutes. Page backward using the
oldest returned timestamp minus 1ms; detect non-advancing cursors and conflicting
duplicates. There is no arbitrary month/year history cap. Online instruments are
enumerated with pagination; current metadata cannot prove delisted availability.

Cache response pages by endpoint/parameters and preserve retrieval/provider times
and response hashes. Save trade, mark and funding as separate Parquet files.
Dataset identity covers normalized content, requested range, actual coverage,
source responses and metadata assumptions. File hashes and the manifest's own
content identity are verified on every load. Writes use temporary files and an
atomic Windows rename; interrupted work is not listed as a complete dataset.
Runtime implementation and key package versions, graph/settings snapshots and
dataset identity are included in a canonical run manifest. The snapshot digest
changes when its numerical inputs or runtime implementation change.

## Coverage and assumptions

Record actual first/last minute, expected/returned counts and explicit leading,
internal and trailing gaps. Intrabar runs require complete requested finer data.
Closed-mode skip can be selected explicitly; no bars are invented. Mark history
is separately required unless the selected profile explicitly uses last-price
proxy. A cached dataset can be run offline without calling metadata endpoints.

Funding events have separate times and signed rates. Compare event presence with
the **current instrument funding interval projected over the requested range**.
Missing expected events block historical-funding runs. This verifies coverage
against that stated assumption, not historical schedule changes; retain the
warning even when all expected events exist. Assumed-zero funding is a distinct
explicit profile choice. A data description without its verified Parquet files
does not guarantee that an exported project can be recalculated.

Current tick size, quantity steps, minimums, maximum market quantity and the
lowest risk tier can populate editable simulation settings. Record their source
and historical uncertainty. Do not label them verified historical exchange rules.
Risk-tier overflow still invalidates the simple profile. Source metadata and
downloaded data remain local; they are not bundled into the public repository.

## Executed checks

Eleven automated data tests cover pagination/cache replay, gaps, error responses,
non-advancing pages, incomplete provider candles, funding timing, immutable
Parquet integrity, missing funding acknowledgment, manifest independence and
path/endpoint boundaries. No network is required for these tests.

Real public API checks downloaded BTCUSDT for 2026-09-01 00:00 UTC through
2026-09-02 00:00 UTC: spot 1440 trade bars; linear 1440 trade bars, 1440 mark bars,
three funding events. No candle gaps or missing current-interval funding events
were reported for this range. The cached spot and linear datasets each produced
identical normalized results in two offline engine runs with the demo graph.
These are data/integration tests, not independent financial goldens or evidence
of a profitable strategy. Dataset IDs are environment artifacts, not hard-coded
public fixtures; fresh retrievals preserve their own provenance and identities.

Development commands (from the repository root):

```powershell
.venv/Scripts/python.exe -m terminal.cli download --market linear --symbol BTCUSDT --start 2026-09-01 --end 2026-09-02
.venv/Scripts/python.exe -m terminal.cli dataset DATASET_ID
.venv/Scripts/python.exe -m benchmarks.offline_dataset DATASET_ID
```

Primary sources: [OHLCV](https://bybit-exchange.github.io/docs/v5/market/kline),
[mark](https://bybit-exchange.github.io/docs/v5/market/mark-kline),
[funding](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate),
[instruments](https://bybit-exchange.github.io/docs/v5/market/instrument),
[risk metadata](https://bybit-exchange.github.io/docs/v5/market/risk-limit).
