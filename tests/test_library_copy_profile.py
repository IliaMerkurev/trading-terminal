import tempfile
import unittest
from unittest.mock import patch

from terminal.library import create_copy
from terminal.profile import Profile
from terminal.service import AppService


class LibraryCopyProfileTests(unittest.TestCase):
    def test_profile_is_validated_before_persistence_and_chosen_values_are_saved(self):
        with tempfile.TemporaryDirectory() as root:
            service=AppService(root)
            request=dict(entry_id='rsi-threshold',version=1,minutes=240,parameters={})
            try:
                chosen=Profile(primary_minutes=1440,execution_minutes=1440,capital='2222',
                               sizing='percent',allocation='95',fee_rate='0.00001').snapshot()
                with patch.object(service.store,'save_strategy',wraps=service.store.save_strategy) as save:
                    reply=service.handle(dict(version=1,id='invalid',command='library_copy',params={**request,'profile':chosen}))
                    self.assertEqual(reply['type'],'error')
                    self.assertIn('multiple of execution resolution',reply['error']['message'])
                    save.assert_not_called()
                    chosen['execution_minutes']=60
                    reply=service.handle(dict(version=1,id='valid',command='library_copy',params={**request,'profile':chosen}))
                    self.assertEqual(reply['type'],'result',reply)
                    save.assert_called_once()
                saved=service.store.strategy(reply['result']['strategy_id'])['profile']
                self.assertEqual(saved,{**chosen,'primary_minutes':240,'version':2})
                self.assertEqual(saved['fee_rate'],'0.00001')
                with patch.object(service.store,'save_strategy') as save:
                    for invalid in ({**chosen,'capital':'-1'},{**chosen,'unknown':'x'}):
                        reply=service.handle(dict(version=1,id='bad-value',command='library_copy',params={**request,'profile':invalid}))
                        self.assertEqual(reply['type'],'error')
                    save.assert_not_called()
            finally:service.close()

    def test_native_override_is_refused_without_copy_or_trust(self):
        with tempfile.TemporaryDirectory() as root:
            service=AppService(root)
            try:
                with patch.object(service.store,'save_strategy') as save, patch.object(service.store,'is_trusted') as trust:
                    with self.assertRaisesRegex(ValueError,'reviewed template profile'):
                        create_copy(service.store,entry_id='native-ema-cross',version=2,minutes=240,
                                    parameters={},profile=Profile().snapshot())
                    save.assert_not_called();trust.assert_not_called()
            finally:service.close()
