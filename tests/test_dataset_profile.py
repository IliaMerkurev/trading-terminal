from pathlib import Path
import tempfile
import unittest

from terminal.data import DataError, metadata_profile_fields
from terminal.series import Candle
from terminal.service import AppService


class DatasetProfileTests(unittest.TestCase):
    def fixture(self, market='spot'):
        lot = dict(minOrderQty='0.001', basePrecision='0.001', minOrderAmt='1',
                   maxMarketOrderQty='50', maxOrderQty='100', maxOrderAmt='500000',
                   qtyStep='0.001', minNotionalValue='5', maxMktOrderQty='20')
        return dict(market=market, symbol='BTCUSDT', metadata=dict(
            instrument=dict(priceFilter={'tickSize':'0.01'}, lotSizeFilter=lot),
            current_risk_tiers=[dict(isLowestRisk=1, maintenanceMargin='0.005', riskLimitValue='100000')]))

    def test_complete_spot_and_linear_metadata_keep_exact_fields(self):
        common = dict(market='spot', symbol='BTCUSDT', tick_size='0.01', min_quantity='0.001',
                      quantity_step='0.001', min_notional='1', max_quantity='50', max_notional='500000',
                      tier_assumption='Current exchange metadata projected over the historical run; historical changes are unknown')
        self.assertEqual(metadata_profile_fields(self.fixture()), common)
        self.assertEqual(metadata_profile_fields(self.fixture('linear')),
                         dict(common, market='linear', min_notional='5', max_quantity='20',
                              max_notional='100000', maintenance_rate='0.005'))
        fallback = self.fixture()
        del fallback['metadata']['instrument']['lotSizeFilter']['maxMarketOrderQty']
        self.assertEqual(metadata_profile_fields(fallback), dict(common, max_quantity='100'))

    def test_explicit_synthetic_metadata_never_claims_exchange_limits(self):
        for market in ('spot', 'linear'):
            manifest = self.fixture(market)
            ordinary = metadata_profile_fields(manifest)
            manifest['metadata']['synthetic'] = True
            self.assertEqual(metadata_profile_fields(manifest), dict(ordinary, tier_assumption=
                'Invented synthetic precision and size limits for offline testing; not current or historical exchange metadata'))
            manifest['metadata']['synthetic'] = 'true'
            self.assertEqual(metadata_profile_fields(manifest), ordinary)

    def test_missing_or_malformed_metadata_is_actionable_data_error(self):
        paths = [('metadata',), ('metadata', 'instrument'),
                 ('metadata', 'instrument', 'priceFilter'),
                 ('metadata', 'instrument', 'priceFilter', 'tickSize'),
                 ('metadata', 'instrument', 'lotSizeFilter'),
                 ('metadata', 'instrument', 'lotSizeFilter', 'minOrderQty'),
                 ('metadata', 'current_risk_tiers')]
        for path in paths:
            for replacement in ('missing', None, []):
                with self.subTest(path=path, replacement=replacement):
                    manifest = self.fixture('linear')
                    parent = manifest
                    for key in path[:-1]:
                        parent = parent[key]
                    if replacement == 'missing':
                        del parent[path[-1]]
                    else:
                        parent[path[-1]] = replacement
                    # A present leaf value is validated by Profile, not this mapping helper.
                    if path[-1] in ('tickSize', 'minOrderQty') and replacement != 'missing':
                        continue
                    with self.assertRaisesRegex(DataError, 'metadata|lowest risk tier'):
                        metadata_profile_fields(manifest)

    def test_legacy_dataset_profile_ipc_preserves_snapshot_and_explains_remedy(self):
        with tempfile.TemporaryDirectory() as temp:
            service = AppService(temp)
            try:
                dataset = service.datasets.save('spot', 'BTCUSDT', 0, 60,
                    [Candle(0, 100, 101, 99, 100, 1)], [], {}, metadata={},
                    provenance=[{'source':'synthetic test'}], source='Synthetic test')
                path = Path(temp) / 'datasets' / dataset['id'] / 'manifest.json'
                original = path.read_bytes()
                reply = service.handle(dict(version=1, id='missing-metadata', command='dataset_profile',
                                            params={'dataset_id':dataset['id']}))
                self.assertEqual(reply['type'], 'error')
                self.assertIn('metadata is missing or incomplete', reply['error']['message'])
                self.assertIn('Strategy editor', reply['error']['message'])
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(service.datasets.describe(dataset['id']), dataset)
            finally:
                service.close()
