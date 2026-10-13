"""Independent reconstruction challenge tests; no market providers or user data."""
import copy,json,math,tempfile,unittest
from pathlib import Path
from terminal.chart_panes import validate_layout
from terminal.display_indicators import parse_settings_document
from terminal.service import AppService


def indicator(kind,ident):
    return dict(id=ident,type=kind,params={'rsi':{'period':14},'stochastic':{'period':14,'smooth':3,'signal':3},'macd':{'fast':12,'slow':26,'signal':9},'atr':{'period':14},'stddev':{'period':14},'volume':{}}[kind],color='#123abc',visible=True)


def layout(ids):
    return dict(version=1,price_weight=400,recorded_weight=140,panes=[dict(id='osc',weight=240,instance_ids=ids)])


class IndependentPaneValidation(unittest.TestCase):
    def test_all_members_and_alias_isolation(self):
        rows=[indicator('rsi','r'),indicator('stochastic','s')]; rows[1]['visible']=False
        original=layout(['r','s']); actual=validate_layout(original,rows)
        actual['panes'][0]['instance_ids'].clear()
        self.assertEqual(original['panes'][0]['instance_ids'],['r','s'])
        for members in [['r'],['s'],['r','s','s'],['r','s','unknown']]:
            with self.subTest(members=members),self.assertRaises(ValueError):validate_layout(layout(members),rows)
    def test_weight_rejection_matrix(self):
        rows=[indicator('rsi','r')]
        for value in [True,False,None,'4',{},[],0,-1,float('nan'),float('inf'),float('-inf'),10000.0001,10**1000]:
            for field in ['price_weight','recorded_weight','nested']:
                doc=layout(['r'])
                if field=='nested':doc['panes'][0]['weight']=value
                else:doc[field]=value
                with self.subTest(value=str(value)[:30],field=field),self.assertRaises(ValueError):validate_layout(doc,rows)
        for value in [1,1.25,10000]:
            doc=layout(['r']);doc['price_weight']=value
            self.assertEqual(validate_layout(doc,rows)['price_weight'],value)
    def test_unit_and_overlay_boundaries(self):
        for kinds,valid in [(('rsi','stochastic'),True),(('atr','stddev'),True),(('rsi','macd'),False),(('atr','macd'),False)]:
            rows=[indicator(kind,str(chr(97+i))) for i,kind in enumerate(kinds)]
            if valid:self.assertEqual(validate_layout(layout(['a','b']),rows)['panes'][0]['instance_ids'],['a','b'])
            else:
                with self.assertRaises(ValueError):validate_layout(layout(['a','b']),rows)
        volume=indicator('volume','v')
        with self.assertRaises(ValueError):validate_layout(layout(['v']),[volume])
        volume['placement']='pane';validate_layout(layout(['v']),[volume])
    def test_legacy_and_unsupported_documents(self):
        doc=dict(version=1,revision=8,instances=[indicator('rsi','r')],origins={})
        self.assertNotIn('pane_layout',parse_settings_document(json.dumps(doc)))
        doc['pane_layout']=layout(['r']);self.assertEqual(parse_settings_document(json.dumps(doc)),doc)
        doc['pane_layout']['version']=2
        with self.assertRaises(ValueError):parse_settings_document(json.dumps(doc))
    def test_quantity_is_not_a_fixed_quota(self):
        rows=[indicator('rsi',f'r{i}') for i in range(513)]
        doc=layout([]);doc['panes']=[dict(id=f'p{i}',weight=2,instance_ids=[r['id']]) for i,r in enumerate(rows)]
        self.assertEqual(len(validate_layout(doc,rows)['panes']),513)


class IndependentPaneService(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.service=AppService(Path(self.tmp.name))
        self.rows=[indicator('rsi','r'),indicator('stochastic','s')]
    def tearDown(self):self.service.close();self.tmp.cleanup()
    def call(self,command,**params):return self.service.handle(dict(version=1,id='independent-pane',command=command,params=params))
    def save(self,revision,**extra):return self.call('chart_indicator_save',market='spot',symbol='BTCUSDT',instances=self.rows,revision=revision,**extra)
    def test_legacy_service_optional_source_and_layout_then_fail_closed(self):
        first=self.save(0);self.assertIn('result',first,first)
        second=self.save(1,pane_layout=layout(['r','s']));self.assertIn('result',second,second)
        old_client=self.save(2);self.assertNotIn('result',old_client,old_client)
        self.assertEqual(self.service.display_indicators.settings('spot','BTCUSDT'),second['result'])
        explicit_reset=self.save(2,pane_layout=None);self.assertIn('result',explicit_reset,explicit_reset)
        self.assertNotIn('pane_layout',explicit_reset['result'])
    def test_atomic_stale_invalid_and_source_isolation(self):
        first=self.save(0,pane_layout=layout(['r','s']))['result']
        bad=layout(['r','s']);bad['panes'][0]['instance_ids'].append('absent')
        for args in [dict(revision=0,pane_layout=layout(['r','s'])),dict(revision=1,pane_layout=bad)]:
            self.assertNotIn('result',self.save(**args))
            self.assertEqual(self.service.display_indicators.settings('spot','BTCUSDT'),first)
        other=self.save(0,source='okx',pane_layout=None)
        self.assertIn('result',other);self.assertNotIn('pane_layout',other['result'])
        self.assertEqual(self.service.display_indicators.settings('spot','BTCUSDT'),first)
    def test_preset_unknown_extension_survives_metadata_duplicate(self):
        self.save(0,pane_layout=layout(['r','s']))
        p=self.service.chart_presets;meta=p.save_current('With panes','bybit','spot','BTCUSDT',1)
        doc=p.get(meta['id'],1)['content'];doc['extensions']['future']={'schema':99,'opaque':[1,2,3]}
        with self.service.store.connect() as db:db.execute('UPDATE chart_presets_v1 SET content=? WHERE id=?',(json.dumps(doc),meta['id']))
        p.rename(meta['id'],1,'Renamed');dupe=p.duplicate(meta['id'],2,'Copy')
        self.assertEqual(p.get(dupe['id'],1)['content'],doc)
        p.trash(meta['id'],2);p.restore(meta['id'],3)
        self.assertEqual(p.get(meta['id'],4)['content'],doc)
    def test_invalid_saved_layout_does_not_destroy_stored_document(self):
        saved=self.save(0,pane_layout=layout(['r','s']))['result'];saved['pane_layout']['version']=99
        with self.service.store.connect() as db:db.execute('UPDATE chart_presentation_v1 SET document=?',(json.dumps(saved),))
        self.assertIn('warning',self.service.display_indicators.settings('spot','BTCUSDT'))
        with self.assertRaises(ValueError):self.service.chart_presets.save_current('Do not replace','bybit','spot','BTCUSDT',0)
        with self.service.store.connect() as db:self.assertEqual(json.loads(db.execute('SELECT document FROM chart_presentation_v1').fetchone()[0]),saved)

if __name__=='__main__':unittest.main(verbosity=2)
