import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from terminal.data import canonical, digest
from terminal.display_indicators import calculate, validate_instances
from terminal.indicator_transport import IndicatorTransport, MAX_RESULT_BYTES
from terminal.service import AppService
import test_display_indicators as display_tests
from test_display_indicators import instance, candles


class UnlimitedIndicatorsTests(unittest.TestCase):
    setUp = display_tests.DisplayCacheTests.setUp
    tearDown = display_tests.DisplayCacheTests.tearDown
    seed = display_tests.DisplayCacheTests.seed
    read = display_tests.DisplayCacheTests.read

    def test_129_visible_128_hidden_full_window_and_restart(self):
        items = [dict(instance('ema', period=2), id='i'+str(i), visible=i<129) for i in range(257)]
        self.seed(candles([100+i/19 for i in range(1800)]))
        self.settings = self.display.save('spot','BTCUSDT',items,0)
        out = self.read(0,1799*60)
        self.assertEqual(out['status'], 'ready')
        self.assertEqual(len(out['columns']),129)
        self.assertGreater(len(canonical(out)),900*1024)
        self.assertTrue(all(len(p['value'])==1800 for p in out['columns'].values()))
        transport=IndicatorTransport()
        try:
            descriptor=transport.pack(out)
            parts=[transport.page(descriptor['snapshot_id'],i) for i in range(descriptor['pages'])]
            self.assertTrue(all(len(canonical(p))<900*1024 for p in parts))
            raw=''.join(p['text'] for p in parts).encode()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),descriptor['sha256'])
            self.assertEqual(json.loads(raw),out)
        finally:transport.close()
        self.display.close()
        from terminal.display_indicators import DisplayIndicators
        self.display=DisplayIndicators(self.chart)
        self.assertEqual(self.display.settings('spot','BTCUSDT')['instances'],items)
        self.assertEqual(self.read(0,1799*60)['columns'],out['columns'])

    def test_work_budget_rejects_before_allocating_states(self):
        items=[dict(instance('bb',period=2,deviations=2),id='i'+str(i)) for i in range(5000)]
        with patch('terminal.display_indicators.indicator_for',side_effect=AssertionError('allocated before resource guard')):
            with self.assertRaisesRegex(ValueError,'working resource budget'):
                calculate(candles([100]*1800),items,1,0,1799*60)

    def test_hidden_never_instantiates_calculates_or_validates_timeframe(self):
        hidden=dict(instance('vwap',mode=1,anchor=60),visible=False)
        with patch('terminal.display_indicators.formulas.FormulaState',side_effect=AssertionError('hidden evaluated')):
            result=calculate(candles([1,2,3]),[hidden],60,0,120)
        self.assertEqual(result['columns'],{})
        many=[dict(instance('ema',period=2),id='i'+str(i)) for i in range(1025)]
        self.assertEqual(len(validate_instances(many)),1025)


class IndicatorUploadTests(unittest.TestCase):
    def test_large_service_upload_is_atomic_and_revision_guarded(self):
        with tempfile.TemporaryDirectory() as root:
            service=AppService(Path(root))
            def call(command,**params):
                result=service.handle(dict(version=1,id='test',command=command,params=params))
                self.assertLess(len(canonical(result)),1024*1024)
                return result
            try:
                items=[dict(instance('ema',period=2),id='item'+str(i),visible=False) for i in range(13000)]
                params=dict(market='spot',symbol='BTCUSDT',source='bybit',revision=0,instances=items)
                raw=canonical(params);self.assertGreater(len(raw),1024*1024)
                def upload():
                    ident=call('chart_indicator_upload_begin',size=len(raw),sha256=hashlib.sha256(raw).hexdigest())['result']['upload_id']
                    for offset in range(0,len(raw),65536):
                        result=call('chart_indicator_upload_append',upload_id=ident,offset=offset,text=raw[offset:offset+65536].decode())
                        self.assertEqual(result['type'],'result')
                    return ident
                ident=upload()
                self.assertEqual(service.display_indicators.settings('spot','BTCUSDT')['revision'],0)
                saved=call('chart_indicator_upload_finish',upload_id=ident)
                self.assertEqual(saved['type'],'result');self.assertEqual(saved['result']['status'],'paged')
                self.assertEqual(len(service.display_indicators.settings('spot','BTCUSDT')['instances']),13000)
                conflict=call('chart_indicator_upload_finish',upload_id=upload())
                self.assertEqual(conflict['type'],'error')
                self.assertIn('settings changed',conflict['error']['message'])
                self.assertEqual(service.display_indicators.settings('spot','BTCUSDT')['revision'],1)
            finally:service.close()

    def test_explicit_resource_limit_does_not_change_saved_state(self):
        t=IndicatorTransport()
        try:
            with self.assertRaisesRegex(ValueError,'resource budget'):
                t.upload_begin(MAX_RESULT_BYTES+1,'a'*64)
            with patch('terminal.indicator_transport.MAX_RESULT_BYTES',100):
                with self.assertRaisesRegex(ValueError,'resource budget'):t.pack({'data':'x'*101})
            self.assertEqual(list(Path(t.directory.name).iterdir()),[])
        finally:t.close()
