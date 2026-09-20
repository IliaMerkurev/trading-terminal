import json
import tempfile
import unittest
from terminal.service import AppService


class HistoryPagingTests(unittest.TestCase):
    def test_ipc_pages_all_runs_with_ties_and_concurrent_insertion_without_mutation(self):
        with tempfile.TemporaryDirectory() as root:
            service=AppService(root)
            try:
                def call(before=None,limit=50):
                    return service.handle({'version':1,'id':'history','command':'run_history',
                                           'params':{'before':before,'limit':limit}})
                self.assertEqual(call()['result'],{'rows':[],'next':None})
                stamp='2026-01-01T00:00:00+00:00'
                records=[(f'{n:032x}',stamp,'completed','{}',json.dumps({'metrics':{'net_pnl':n}})) for n in range(1,126)]
                with service.store.connect() as db:
                    db.executemany('INSERT INTO runs(id,created_at,status,manifest,summary) VALUES(?,?,?,?,?)',records)
                first=call()['result'];self.assertEqual(len(first['rows']),50)
                with service.store.connect() as db:
                    db.execute('INSERT INTO runs(id,created_at,status,manifest) VALUES(?,?,?,?)',('f'*32,'2026-02-01T00:00:00+00:00','created','{}'))
                second=call(first['next'])['result'];third=call(second['next'])['result']
                rows=first['rows']+second['rows']+third['rows']
                self.assertEqual([r['id'] for r in rows],[f'{n:032x}' for n in range(125,0,-1)])
                self.assertIsNone(third['next']);self.assertEqual(len({r['id'] for r in rows}),125)
                self.assertEqual(call()['result']['rows'][0]['id'],'f'*32)
                self.assertEqual(call(limit=101)['type'],'error')
                self.assertEqual(call({'created_at':stamp,'id':'bad'})['type'],'error')
                with service.store.connect() as db:
                    actual=[tuple(r) for r in db.execute('SELECT id,created_at,status,manifest,summary FROM runs WHERE id!=? ORDER BY id',('f'*32,))]
                self.assertEqual(actual,records)
            finally:service.close()
