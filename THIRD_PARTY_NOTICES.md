# Third-party dependencies

The project license is undecided. This file does not grant a license to project code.
Dependencies remain covered by their own licenses. Package locks identify exact
versions; dependency source is not vendored in this repository.

| Component | Version | License |
| --- | --- | --- |
| NautilusTrader | 1.231.0 | LGPL-3.0-or-later |
| websockets | 15.0.1 | BSD-3-Clause |
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

## Strategy Library source references

The independently authored RSI threshold graph is an explicitly limited adaptation referencing QuantConnect Lean RsiAlphaModel (Copyright 2014 QuantConnect Corporation, Apache-2.0). Source and differences are documented in docs/library/SOURCES.md; Apache license text is preserved in docs/library/APACHE-2.0.txt. No Lean runtime or original module is bundled. Native EMA references the installed unchanged LGPL-3.0 NautilusTrader example under existing notices; explicit trust remains required. The project license is unchanged.
