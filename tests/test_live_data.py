import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from terminal.graph import example_graph
from terminal.live_data import PublicStream, LiveHistory, LiveProtocolError, reconnect_delay
from terminal.live_store import LiveStore, LiveSession
from terminal.profile import Profile
from terminal.storage import RunStore


class PublicStreamTests(unittest.TestCase):
    def test_subscription_is_public_bounded_and_not_duplicated(self):
        socket=Mock();connector=Mock(return_value=socket)
        stream=PublicStream('linear','BTCUSDT',connector)
        stream.open()
        self.assertEqual(connector.call_args.args[0],'wss://stream.bybit.com/v5/public/linear')
        self.assertEqual(connector.call_args.kwargs['max_queue'],32)
        self.assertEqual(json.loads(socket.send.call_args.args[0])['args'],['tickers.BTCUSDT','kline.1.BTCUSDT'])
        with self.assertRaises(LiveProtocolError):stream.open()
        stream.close();socket.close.assert_called_once()
        stream.open();self.assertEqual(connector.call_count,2)
        self.assertEqual([reconnect_delay(n) for n in range(8)],[1,2,4,8,16,30,30,30])

    def test_delta_duplicate_out_of_order_and_stale(self):
        stream=PublicStream('linear','BTCUSDT')
        def msg(time,data,kind='delta'):
            return json.dumps({'topic':'tickers.BTCUSDT','type':kind,'ts':time,'data':{'symbol':'BTCUSDT',**data}})
        first=stream.parse(msg(100000,{'lastPrice':'100','markPrice':'101'},'snapshot'),100100)[0]
        self.assertEqual(first['mark'],'101')
        second=stream.parse(msg(100001,{'lastPrice':'102'}),100100)[0]
        self.assertEqual((second['price'],second['mark']),('102','101'))
        self.assertEqual(stream.parse(msg(100000,{'lastPrice':'1'}),100100),[])
        self.assertEqual(stream.parse(msg(100001,{'lastPrice':'2'}),100100),[])
        with self.assertRaises(LiveProtocolError):stream.parse(msg(100010,{'lastPrice':'3'}),200011)
        with self.assertRaisesRegex(LiveProtocolError,'ticker is stale'):stream.parse(msg(100010,{'lastPrice':'3'}),120011)

    def test_forming_not_confirmed_and_clock_bounds(self):
        stream=PublicStream('spot','BTCUSDT')
        row={'start':60000,'end':119999,'interval':'1','confirm':False,'open':'100','high':'110','low':'90','close':'105','volume':'1'}
        def msg(ts):return json.dumps({'topic':'kline.1.BTCUSDT','ts':ts,'data':[row]})
        self.assertEqual(stream.parse(msg(100000),100100)[0]['kind'],'forming')
        row['confirm']=True
        with self.assertRaises(LiveProtocolError):stream.parse(msg(100000),100100)
        self.assertEqual(stream.parse(msg(120000),120100)[0]['kind'],'candle')

    def test_recovery_reconstructs_gap_without_notifying(self):
        with tempfile.TemporaryDirectory() as directory:
            store=LiveStore(RunStore(Path(directory)))
            sid=store.create(example_graph(),Profile(primary_minutes=1),'fixture','Fixture')
            session=LiveSession(store,sid)
            def transport(path,p):
                start=p['start']//1000;end=(p['end']+1)//1000
                return {'retCode':0,'time':999999999,'result':{'list':[[t*1000,str(100+t//60),str(100+t//60),str(100+t//60),str(100+t//60),'1','1'] for t in reversed(range(start,end,60))]}}
            history=LiveHistory(Path(directory)/'cache',transport=transport)
            self.assertEqual(history.recover(session,120,warmup_start=0),2)
            self.assertEqual(store.events(sid),[])
            self.assertEqual(history.recover(session,300),3)
            self.assertEqual(session.last,240)
            self.assertTrue(session.verify_replay()['match'])
            self.assertEqual(store.get(sid)['status'],'RECOVERING DATA')
