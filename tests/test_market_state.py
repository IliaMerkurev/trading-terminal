import json
import unittest
from unittest.mock import patch
from terminal.market_state import OrderBook, MarketState
from terminal.live_data import PublicStream, LiveProtocolError


def book(u=10,seq=100,b=None,a=None):
    return {'s':'BTCUSDT','u':u,'seq':seq,'b':b if b is not None else [['99','2'],['98','3']],
            'a':a if a is not None else [['101','4'],['102','5']]}


class BookTests(unittest.TestCase):
    def test_snapshot_delta_zero_and_reset_independent_levels(self):
        b=OrderBook();b.apply('snapshot',book(),1000)
        b.apply('delta',book(15,105,[['99','0'],['98','7'],['97','9']],[['101','6']]),1001)
        self.assertEqual(b.snapshot()['bids'],[['98','7'],['97','9']])
        self.assertEqual(b.snapshot()['asks'],[['101','6'],['102','5']])
        b.apply('snapshot',book(1,1,[['90','1']],[['91','2']]),1002)
        self.assertEqual(b.snapshot()['bids'],[['90','1']])

    def test_reconnect_requires_snapshot_and_stale_does_not_change_book(self):
        b=OrderBook();b.apply('snapshot',book(),1000);expected=b.snapshot()
        self.assertFalse(b.apply('delta',book(9,99),1001))
        self.assertFalse(b.apply('snapshot',book(1,1),999))
        self.assertEqual(b.snapshot(),expected)
        b.reset()
        with self.assertRaisesRegex(ValueError,'snapshot'):b.apply('delta',book(),1001)
        self.assertFalse(b.valid)
        b.apply('snapshot',book(),1002);self.assertTrue(b.valid)

    def test_invalid_update_is_atomic_and_crossed_book_invalidates(self):
        b=OrderBook();b.apply('snapshot',book(),1000);before=b.snapshot()
        with self.assertRaises(ValueError):b.apply('delta',book(11,101,[['99','8']],[['101','NaN']]),1001)
        self.assertEqual(b.snapshot(),before)
        with self.assertRaises(ValueError):b.apply('delta',book(11,101,[['105','1']],[]),1001)
        self.assertFalse(b.valid)

    def test_depth_and_display_are_bounded(self):
        b=OrderBook();b.apply('snapshot',book(b=[[str(100-i),'1'] for i in range(60)],a=[[str(101+i),'1'] for i in range(60)]),1000)
        self.assertEqual(len(b.bids),50);self.assertEqual(len(b.snapshot()['bids']),15)


class MarketTests(unittest.TestCase):
    def test_tape_dedup_order_bounds_and_reset(self):
        m=MarketState()
        def row(i):return {'i':str(i),'T':1000+i,'s':'BTCUSDT','S':'Buy','p':'100','v':'2'}
        rows=[row(i) for i in range(500)]
        m.trade_update(rows,'BTCUSDT',2000);m.trade_update(rows,'BTCUSDT',2000)
        self.assertEqual(m.counts['trades'],500);self.assertEqual(len(m.trades),100)
        self.assertEqual(m.snapshot()['trades'][0]['time'],1499)
        m.connected();self.assertEqual(m.snapshot()['trades'],[]);self.assertFalse(m.snapshot()['fresh'])

    def test_ticker_delta_snapshot_and_freshness(self):
        stream=PublicStream('linear','BTCUSDT')
        def message(ts,kind,data):return json.dumps({'topic':'tickers.BTCUSDT','ts':ts,'type':kind,'data':{'symbol':'BTCUSDT',**data}})
        stream.parse(message(1000,'snapshot',{'lastPrice':'100','markPrice':'101','highPrice24h':'110'}),1000)
        stream.parse(message(1001,'delta',{'lastPrice':'102'}),1001)
        self.assertEqual(stream.state.snapshot()['ticker']['highPrice24h'],'110')
        stream.parse(message(1002,'snapshot',{'lastPrice':'103'}),1002)
        self.assertIsNone(stream.state.snapshot()['ticker']['markPrice'])
        self.assertFalse(stream.state.snapshot()['fresh'])

    def test_public_book_and_trade_topics_and_stale_rejection(self):
        stream=PublicStream('spot','BTCUSDT')
        raw=json.dumps({'topic':'orderbook.50.BTCUSDT','type':'snapshot','ts':1000,'data':book()})
        self.assertEqual(stream.parse(raw,1000),[]);self.assertTrue(stream.state.snapshot()['book']['valid'])
        with self.assertRaises(LiveProtocolError):stream.parse(raw,20000)
        with self.assertRaises(LiveProtocolError):stream.parse(json.dumps({'topic':'order','ts':1000,'data':{}}),1000)
