# Third-party dependencies

Trading Terminal original project code is covered by the [MIT License](LICENSE),
except the explicitly identified MPL-2.0 derived formula module below.
Dependencies remain covered by their own licenses; the project license does not
relicense third-party components or market data. Data provider terms still apply.
Package locks identify exact versions; dependency source is not vendored in this
repository.

| Component | Version | License |
| --- | --- | --- |
| NautilusTrader | 1.231.0 | LGPL-3.0-or-later |
| websockets | 15.0.1 | BSD-3-Clause |
| uvloop (Linux runtime only) | 0.22.1 | MIT |
| Tauri / Tauri build | 2.11.5 / 2.6.3 | MIT OR Apache-2.0 |
| Tauri JavaScript API / CLI | 2.11.1 / 2.11.4 | MIT OR Apache-2.0 |
| React / React DOM | 19.3.0 | MIT |
| React Flow | 12.11.6 | MIT |
| Lightweight Charts | 5.2.1 | Apache-2.0 |
| Vite / React plugin | 8.2.2 / 6.1.1 | MIT |
| TypeScript | 7.0.2 | Apache-2.0 |
| Vitest / jsdom / Testing Library React | 5.0.0 / 30.0.1 / 16.3.3 | MIT |
| Serde / serde_json | 1.0.229 / 1.0.151 | MIT OR Apache-2.0 |

## Lightweight Charts notice

TradingView Lightweight Charts™

Copyright (с) 2025 TradingView, Inc. https://www.tradingview.com/

[Upstream notice](https://github.com/tradingview/lightweight-charts/blob/v5.2.1/NOTICE)
and [Apache license](https://github.com/tradingview/lightweight-charts/blob/v5.2.1/LICENSE).
The chart displays TradingView attribution and a link.

## Local development and distribution

The developer launch uses separately installed dependencies and the project Python
environment. Installed official native strategy examples are imported from the
licensed package; their source is not copied here. No third-party strategies of
unknown provenance are included.

Transitive dependencies include LGPL (Python portion), MPL-2.0 (some Rust and
JavaScript packages), Unicode, BSD, ISC and other permissive notices. Before any
binary distribution, collect the exact packaged dependency notices and fulfill
source/relinking obligations where applicable. Local compilation is not a release
or a claim that a distributable installer has passed license review.

Linux development also uses separately installed GTK/WebKitGTK system libraries
and their transitive dependencies. They are not vendored or redistributed by
this source-checkout adaptation. Their LGPL/BSD and other package notices must
be reviewed again for any future binary distribution.

## Strategy Library source references

The independently authored RSI threshold graph is an explicitly limited adaptation referencing QuantConnect Lean RsiAlphaModel (Copyright 2014 QuantConnect Corporation, Apache-2.0). Source and differences are documented in docs/library/SOURCES.md; Apache license text is preserved in docs/library/APACHE-2.0.txt. No Lean runtime or original module is bundled. Native EMA references the installed unchanged LGPL-3.0 NautilusTrader example under existing notices; explicit trust remains required. These source references retain their original licenses.

The independently authored Bollinger/RSI graph references the reviewed LGPL-3.0
Nautech Systems example without copying its Python source. Its long-only,
close-only and sizing differences are recorded in the source matrix and card.

The independently authored normalized MACD graph references QuantConnect Lean
MACDTrendAlgorithm (Apache-2.0). It preserves the normalized tolerance decision
with disclosed engine initialization and profile-sizing differences; no Lean
runtime or original module is bundled.

The historical-return direction graph independently adapts QuantConnect Lean
HistoricalReturnsAlphaModel (Apache-2.0), with explicit long-only and insight
lifecycle differences. Source provenance and the retained license are listed above.

The independently authored EMA trend graph references QuantConnect Lean
MovingAverageCrossAlgorithm, and the prior-bar Donchian breakout references its
DonchianChannel indicator (QuantConnect Corporation, Apache-2.0). No Lean runtime
or original source module is bundled. Exact source hashes, prior-bar adaptation
and local research defaults are in docs/adr/0026-research-workspace-and-trend-candidates.md.

The independently authored C12 Double 7's and C13 Improved R2 daily spot graphs
reference rule articles by Cesar Alvarez (2016-02-10) and Larry Connors
(2007-02-21), respectively. Those articles retain their authors' rights and are
not relicensed as MIT. No article text or external source code is bundled.
Catalog SHA256 values explicitly identify project-authored bounded rule summaries,
not complete upstream webpages. See docs/adr/0039-daily-reversion-candidates.md.


## VuManChu display formulas: MPL-2.0 exception

The readable corresponding source `terminal/vumanchu_indicators.py`, including
its translated/modified formulas, is covered by Mozilla Public License 2.0,
not the root MIT license. [Full MPL-2.0 text](licences/MPL-2.0.txt) is included
unchanged from <https://www.mozilla.org/media/MPL/2.0/index.txt>. The original
terminal adapters, event transport, UI and unrelated files remain MIT. Any
binary distribution containing this module must identify and provide this
corresponding source under MPL-2.0 at the same distributed version. This source
checkout includes it directly; local builds are not a distribution approval.

Original public Pine sources retrieved 2026-10-11:

- **Cipher B + Divergences**, author **vumanchu**, publication **v17**:
  <https://www.tradingview.com/script/Msm4SjwI-VuManChu-Cipher-B-Divergences/>.
  Exact source <https://pine-facade.tradingview.com/pine-facade/get/PUB%3BuA35GeckoTA2EfgI63SD2WCSmca4njxp/17>.
  Original Pine byte SHA-256: `6d372e03a0856e3fa757e60aeb22d276cf63922b6160c1526b77616664eaf767`.
- **Cipher A**, author **vumanchu**, publication **v1**:
  <https://www.tradingview.com/script/9hWqVcG9-VuManChu-Cipher-A/>.
  Exact source <https://pine-facade.tradingview.com/pine-facade/get/PUB%3BvrOJcNRPULteowIsuP6iHn3GIxBJdXwT/1>.
  Original Pine byte SHA-256: `160c6bdfd4d07dc1868e98b47fbcc41704c46bad2d0209463d83aa3df66c9f72`.
- **VuManChu Swing Free**, author **Jazal**, publication **v1**, explicitly
  crediting **DonovanWall** for Range Filter:
  <https://www.tradingview.com/script/q23anHmP-VuManChu-Swing-Free/>.
  Exact source <https://pine-facade.tradingview.com/pine-facade/get/PUB%3BeCVFctFlqpt475hG8Qw7yYA89NxMtSGa/1>.
  Original Pine byte SHA-256: `d961f644fed2df2e0ec7ecb428fdf55ff2db444831eff712096e854f7b8887a9`.
- Underlying reference **Range Filter [DW]**, author **DonovanWall**, **v3**:
  <https://www.tradingview.com/script/lut7sBgG-Range-Filter-DW/>.
  Exact source <https://pine-facade.tradingview.com/pine-facade/get/PUB%3BpshyCmQSqlUKsVQ4FrNUAuGkurQPg3ty/3>.
  Original Pine byte SHA-256: `c2c487ca1d6ca1cc66f1d6f909070c2265caf1ae470071a488711abd68728886`.

Cipher A/B source credits retained: **dynausmaux** (A spells Dynausmaux),
**falconCoin**, **LazyBear** (WaveTrend), **RicardoSantos** (divergences),
**LucemAnb** (Stochastic divergence), **andreholanda73** (flow area), and
**TradingView**. A/B originals have no alternate source license; TradingView's
[open-source publishing policy](https://www.tradingview.com/pine-script-docs/writing/publishing/#open)
assigns MPL-2.0 by default. Swing/Range Filter originals explicitly state MPL-2.0.
No GitHub conversion with additional noncommercial/integration restrictions was
used. Original webpages, connector responses and downloaded datasets are not
included in this repository.

The adaptation is display-only and native-timeframe, with events committed at
confirmation close. B is **Core + confirmed divergences**, not full platform
parity: Sommi flags/diamonds, lookahead HTF candles, HTF MACD colors and optional
Schaff are omitted. **Fast WT (WT1−WT2)** is not volume-weighted VWAP;
**VMC flow (candle-body proxy)** uses neither volume nor standard MFI. Divergence
pivot geometry is disclosed separately from its two-bar-later confirmation.
A's eight EMA ribbon and Swing's transparent Range Filter do not claim parity
with proprietary Market Cipher, Morpheus or Scalper. These annotations do not
create strategy signals, alerts, orders or profitability promises.

## Alternative.me Fear & Greed data

The optional latest daily BTC sentiment display uses the public Alternative.me
Fear & Greed API. Its data is subject to the [provider terms and API rules](https://alternative.me/crypto/fear-and-greed-index/), not the application MIT license.
Commercial display is permitted with noticeable attribution next to the data;
the widget keeps its source link visible when expanded or collapsed. This is
a BTC-focused sentiment display, without affiliation or impersonation claims.
