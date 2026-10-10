"""Create NEW, separate synthetic hourly spot history for offline Library UI checks.

No market data is downloaded. Prices, volumes and execution constraints are
independently invented test values, not current or historical exchange facts.
"""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from terminal.data import DatasetStore, metadata_profile_fields
from terminal.library import catalog, prepare
from terminal.profile import Profile
from terminal.series import Candle

HOUR = 3600
DAYS = 168
SOURCE = 'Synthetic: offline BTCUSDT spot Library fixture (not market data)'
ASSUMPTION = 'Invented synthetic precision and size limits for offline UI testing; no exchange metadata or profitability evidence'


def create_fixture(root):
    root = Path(root)
    if not root.is_absolute():
        raise ValueError('Use an absolute, new fixture data directory')
    # Atomic refusal includes existing directories, files and symlinks. Never
    # merge fixtures into a user workspace or an existing demonstration.
    root.mkdir(parents=True, exist_ok=False)
    store = DatasetStore(root / 'datasets')
    selections = [dict(entry_id=entry['id'], version=entry['version'], minutes=minutes, parameters={})
                  for entry in catalog() for minutes in (240, 1440)]
    warmup_seconds = max(prepare(**selection)['contract']['warmup_bars'] * selection['minutes'] * 60
                         for selection in selections)
    metadata = dict(instrument=dict(symbol='BTCUSDT', baseCoin='BTC', quoteCoin='USDT',
        priceFilter={'tickSize':'0.01'}, lotSizeFilter=dict(basePrecision='0.000001',
            minOrderQty='0.000001', minOrderAmt='1', maxMarketOrderQty='100',
            maxOrderQty='100', maxOrderAmt='1000000')),
        current_risk_tiers=[], historical_warning=ASSUMPTION, synthetic=True)
    windows = []
    for name, year, phase in [('selection', 2024, 0), ('later', 2025, 1)]:
        start = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())
        def price(i):
            return round(30000 + 4200 * math.sin(i / 190 + phase) +
                         1200 * math.sin(i / 41 + phase) + 0.5 * i, 2)
        bars = []
        for i in range(DAYS * 24):
            opening, closing = price(i), price(i + 1)
            bars.append(Candle(start + i * HOUR, opening, max(opening, closing) + 25,
                               min(opening, closing) - 25, closing, 100 + i % 20))
        dataset = store.save('spot', 'BTCUSDT', start, start + len(bars) * HOUR,
            bars, [], {}, metadata=metadata,
            provenance=[dict(source=SOURCE, generator='scripts/prepare_library_fixture.py',
                             generator_version=1, window=name, synthetic=True,
                             description='Deterministic independently authored wave/trend OHLCV; all numbers invented')],
            source=SOURCE, minutes=60)
        profile = Profile(**{**metadata_profile_fields(dataset), 'tier_assumption':ASSUMPTION,
            'primary_minutes':240, 'execution_minutes':60, 'capital':'1000',
            'sizing':'percent', 'allocation':'100', 'fee_rate':'0.001', 'slippage':'0.0005'}).snapshot()
        windows.append(dict(name=name, dataset_id=dataset['id'], source=dataset['source'],
            candles=len(bars), history_start=start, start=start + warmup_seconds,
            end=dataset['range'][1], profile=profile))
    result = dict(synthetic=True, warning=ASSUMPTION, selections=selections,
                  expected_preview=dict(rows=16, ready=14, incompatible=2),
                  interval='weekly', spot_dataset_id=None, windows=windows)
    (root / 'synthetic-library-fixture.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    (root / 'SYNTHETIC-README.txt').write_text(
        SOURCE + '\n' + ASSUMPTION + '\n\n'
        'Contains two disjoint 168-day windows with 4,032 hourly candles each.\n'
        'The common evaluation start reserves 56 complete daily warmup bars.\n'
        'Open this separate root, select the Synthetic selection history, use\n'
        'hourly execution and catalog defaults at 4h and 1d. Review before Start.\n'
        'Expected: 12 graph variants and 2 passive alternatives; 2 Native EMA\n'
        'rows are incompatible with spot and must remain visible as unavailable.\n'
        'Later-period synthetic history is prepared but not automatically run.\n'
        'Dataset and execution-profile labels identify these limits as synthetic.\n'
        'No market, native-execution or profitability acceptance.\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = create_fixture(args.data_root)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
