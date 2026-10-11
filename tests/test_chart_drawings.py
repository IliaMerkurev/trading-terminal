import copy
import tempfile
import unittest
from pathlib import Path
from terminal.chart_drawings import ChartDrawings, validate_drawings
from terminal.storage import RunStore


def drawing(kind='trend'):
    anchors=[dict(time=172800,price=100),dict(time=259200,price=120)]
    return dict(id='line1',kind=kind,anchors=anchors[:1] if kind in ('horizontal','vertical','text') else anchors,color='#abcdef',width=2,style='solid',text='Review <not HTML>',visible=True,locked=False)


class ChartDrawingTests(unittest.TestCase):
    def test_all_tools_and_strict_payloads(self):
        for kind in ('horizontal','vertical','trend','ray','rectangle','fib','text'):
            self.assertEqual(validate_drawings([drawing(kind)]),[drawing(kind)])
        for field,value in [('width',True),('width',5),('visible',1),('locked','yes'),('text','x'*201),('text','bad\x00text'),('kind','script'),('color','red'),('style','x')]:
            item=drawing();item[field]=value
            with self.subTest(field=field,value=value), self.assertRaises(ValueError):validate_drawings([item])
        for field,value in [('time',0),('time',float('inf')),('price',float('nan')),('price',True),('price',-1)]:
            item=drawing();item['anchors'][0][field]=value
            with self.assertRaises(ValueError):validate_drawings([item])
        with self.assertRaises(ValueError):validate_drawings([drawing(),drawing()])
        with self.assertRaises(ValueError):validate_drawings([drawing()]*101)
        item=drawing();item['unknown']='no'
        with self.assertRaises(ValueError):validate_drawings([item])

    def test_atomic_revision_source_market_instrument_and_reopen(self):
        with tempfile.TemporaryDirectory() as root:
            store=RunStore(Path(root));manager=ChartDrawings(store)
            self.assertEqual(manager.settings('spot','BTCUSDT')['drawings'],[])
            first=manager.save('spot','BTCUSDT',[drawing()],0)
            other=copy.deepcopy(drawing());other['anchors'][0]['price']=900
            okx=manager.save('spot','BTCUSDT',[other],0,source='okx')
            with self.assertRaises(ValueError):manager.save('spot','BTCUSDT',[],0)
            invalid=drawing();invalid['anchors'][0]['price']=float('nan')
            with self.assertRaises(ValueError):manager.save('spot','BTCUSDT',[invalid],1)
            reopened=ChartDrawings(store)
            self.assertEqual(reopened.settings('spot','BTCUSDT'),first)
            self.assertEqual(reopened.settings('spot','BTCUSDT',source='okx'),okx)
            self.assertEqual(reopened.settings('linear','BTCUSDT')['drawings'],[])
            self.assertEqual(reopened.settings('spot','ETHUSDT')['drawings'],[])
            self.assertEqual(reopened.save('spot','BTCUSDT',[],1)['revision'],2)
            with store.connect() as db:self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_invalid_saved_payload_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as root:
            store=RunStore(Path(root));manager=ChartDrawings(store)
            with store.connect() as db:db.execute('INSERT INTO chart_drawings_v1 VALUES(?,?,?)',('spot','BTCUSDT','{"version":99}'))
            with self.assertRaises(ValueError):manager.settings('spot','BTCUSDT')
            with self.assertRaises(ValueError):manager.save('spot','BTCUSDT',[],0)
