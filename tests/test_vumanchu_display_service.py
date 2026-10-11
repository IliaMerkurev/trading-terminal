import copy
import unittest
from terminal.display_indicators import DisplayIndicators
import test_display_indicators as base
from test_vumanchu_display_integration import rows, instance


class VmcServiceTests(unittest.TestCase):
    setUp = base.DisplayCacheTests.setUp
    tearDown = base.DisplayCacheTests.tearDown
    seed = base.DisplayCacheTests.seed
    read = base.DisplayCacheTests.read

    def test_context_revision_origin_reopen_window_and_raw_under_ha(self):
        candles = rows(180); self.seed(candles)
        self.settings = self.display.save('spot', 'BTCUSDT', [instance('vmc_cipher_a')], 0)
        original = self.read(0, 179*60)
        context = original['indicator_events']['context']
        self.assertEqual(context, dict(source='bybit', market='spot', symbol='BTCUSDT', minutes=1,
            start=0, end=179*60, generation=1, origin=0, settings_revision=1))
        self.assertIn('interval-END', original['formula_metadata']['vmc_cipher_a']['event_clock'])
        ha = self.read(0, 179*60, price_style='heikin_ashi')
        self.assertEqual(original['columns'], ha['columns'])
        self.assertEqual(original['indicator_events'], ha['indicator_events'])
        moved = self.read(60*60, 140*60)
        expected = [e for e in original['indicator_events']['instances']['vmc_cipher_a'] if 61*60 <= e['confirmed_at'] <= 141*60]
        self.assertEqual(moved['indicator_events']['instances']['vmc_cipher_a'], expected)
        self.display.close(); self.display = DisplayIndicators(self.chart)
        self.assertEqual(self.read(0,179*60)['indicator_events'], original['indicator_events'])
        changed = instance('vmc_cipher_a', ema1=2)
        self.settings = self.display.save('spot','BTCUSDT',[changed],1)
        with self.assertRaisesRegex(ValueError, 'superseded'):
            self.display.read('spot','BTCUSDT',1,0,179*60,1)
        current = self.read(0,179*60)
        self.assertEqual(current['indicator_events']['context']['settings_revision'],2)
        self.assertNotEqual(current['revision'],original['revision'])
        other = self.display.settings('spot','BTCUSDT','okx')
        self.assertEqual(other['revision'],0)
        self.assertEqual(other['origins'],{})

    def test_late_correction_rejects_previous_event_snapshot(self):
        candles = rows(90); self.seed(candles)
        self.settings = self.display.save('spot','BTCUSDT',[instance('vmc_cipher_a')],0)
        original = self.read(0,89*60)
        self.assertTrue(original['indicator_events']['instances']['vmc_cipher_a'])
        with self.store.connect() as db:
            db.execute("UPDATE chart_confirmation_v1 SET conflict=1 WHERE market='spot' AND time=120")
        with self.assertRaisesRegex(ValueError,'conflict'):
            self.read(0,89*60)

    def test_preorigin_unavailable_and_explicit_reanchor_generation(self):
        candles = rows(120); self.seed(candles[40:])
        self.settings = self.display.save('spot','BTCUSDT',[instance('vmc_swing')],0)
        seeded = self.read(40*60,119*60)
        self.assertEqual(seeded['origin']['time'],40*60)
        self.seed(candles[:40])
        older = self.read(0,119*60)
        self.assertEqual(older['columns']['vmc_swing']['filter'][:40],[None]*40)
        self.assertEqual(older['regimes']['vmc_swing'][:40],[None]*40)
        self.assertEqual(older['indicator_events']['instances']['vmc_swing'],seeded['indicator_events']['instances']['vmc_swing'])
        refreshed = self.read(0,119*60,reanchor=True)
        self.assertEqual(refreshed['indicator_events']['context']['generation'],2)
        self.assertEqual(refreshed['indicator_events']['context']['origin'],0)
        self.assertIsNotNone(refreshed['columns']['vmc_swing']['filter'][0])
