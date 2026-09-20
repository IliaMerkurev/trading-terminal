import copy
import sys
import tempfile
import unittest
from unittest.mock import patch

from terminal.library import catalog, prepare, create_copy
from terminal.service import AppService
from terminal.native import trust_identity
from terminal.graph import GraphEvaluator
from terminal.series import Candle


class LibraryTests(unittest.TestCase):
    def test_browse_and_copy_never_load_native_or_grant_trust(self):
        module='nautilus_trader.examples.strategies.ema_cross'
        before=sys.modules.get(module)
        with tempfile.TemporaryDirectory() as root:
            service=AppService(root)
            try:
                entry=next(e for e in catalog() if e['id']=='native-ema-cross');entry['parameters']['fast']['default']=999
                self.assertEqual(next(e for e in catalog() if e['id']=='native-ema-cross')['parameters']['fast']['default'],10)
                result=create_copy(service.store,entry_id='native-ema-cross',version=2,minutes=5,parameters={})
                document=service.store.strategy(result['strategy_id'])['document']
                self.assertEqual(document['bar_minutes'],[5])
                self.assertFalse(service.store.is_trusted(trust_identity(document)))
                self.assertIs(sys.modules.get(module),before)
                with self.assertRaisesRegex(ValueError,'Explicit trust'):
                    service.jobs.start(document,service.store.strategy(result['strategy_id'])['profile'],'0'*64)
            finally:service.close()

    def test_validation_hash_guard_and_copy_isolation(self):
        for kwargs in [dict(minutes=2),dict(parameters={'period':True}),dict(parameters={'period':2.5}),dict(parameters={'lower':90,'upper':10}),dict(parameters={'unknown':1})]:
            request=dict(entry_id='rsi-threshold',version=1,minutes=1,parameters={});request.update(kwargs)
            with self.assertRaises(ValueError):prepare(**request)
        with patch('terminal.library.Path.read_bytes',return_value=b'changed dependency'):
            with self.assertRaisesRegex(ValueError,'source changed'):prepare('native-ema-cross',2,1,{})
        first=prepare('rsi-threshold',1,1,{})
        first['document']['graph']['nodes'].clear()
        self.assertTrue(prepare('rsi-threshold',1,1,{})['document']['graph']['nodes'])

    def test_rsi_independent_threshold_sequence_and_future_perturbation(self):
        graph=prepare('rsi-threshold',1,1,{'period':2})['document']['graph']
        def evaluate(prices):
            evaluator=GraphEvaluator(graph)
            bars=[];result=[]
            for i,p in enumerate(prices):
                bars.append(Candle(i*60,p,p+1,p-1,p,1))
                result.append(evaluator(bars,(i+1)*60,True))
            return result
        # Two falling observations give RSI 0; a large rise lifts Wilder RSI above 70.
        result=evaluate([10,9,8,20,21])
        self.assertTrue(result[2]['signals']['entry_long'])
        self.assertTrue(result[3]['signals']['exit_long'])
        self.assertEqual(result[:3],evaluate([10,9,8,2,3])[:3])


if __name__=='__main__':unittest.main()
