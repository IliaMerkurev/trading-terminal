import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import threading
import unittest

from terminal.data import (BybitClient,DataError,DatasetStore,canonical,coverage,prepare_dataset,run_manifest)
from terminal.graph import example_graph
from terminal.profile import Profile
from terminal.series import Candle


class DataTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_paginated_reverse_candles_deduplicate_and_cache_offline(self):
        calls=[]
        def transport(path,params):
            calls.append(params)
            rows=[[str(t*1000),"10","12","9","11","100","1100"] for t in (120,60,0) if t*1000<=params["end"]][:2]
            return {"retCode":0,"result":{"list":rows},"time":300000}
        client=BybitClient(self.root/"cache",transport=transport)
        candles=client.candles("spot","BTCUSDT",0,180)
        self.assertEqual([c.time for c in candles],[0,60,120])
        self.assertEqual(len(calls),2)
        offline=BybitClient(self.root/"cache",offline=True,transport=lambda *_:self.fail("Offline must not connect"))
        self.assertEqual(offline.candles("spot","BTCUSDT",0,180),candles)

    def test_missing_history_reports_leading_internal_and_trailing_gaps(self):
        bars=[Candle(60,10,10,10,10,1),Candle(180,10,10,10,10,1)]
        result=coverage(bars,0,300)
        self.assertFalse(result["complete"])
        self.assertEqual(result["gaps"],[[0,60],[120,180],[240,300]])
        self.assertEqual(result["expected_count"],5)

    def test_error_response_is_not_cached_or_interpreted_as_empty_history(self):
        client=BybitClient(self.root,transport=lambda *_:{"retCode":10001,"result":{"list":[]}})
        with self.assertRaisesRegex(DataError,"10001"): client.candles("spot","BTCUSDT",0,180)
        self.assertEqual(list(self.root.glob("*.json")),[])

    def test_nonadvancing_page_is_bounded(self):
        client=BybitClient(self.root,transport=lambda *_:{"retCode":0,"result":{"list":[["60000","10","10","10","10","1"]]}})
        with self.assertRaisesRegex(DataError,"did not advance"): client.candles("spot","BTCUSDT",0,180)

    def test_open_provider_minute_is_excluded(self):
        def transport(path,params):
            rows=[["120000","10","10","10","10","1"]] if params["end"]>=120000 else []
            return {"retCode":0,"result":{"list":rows},"time":150000}
        client=BybitClient(self.root,transport=transport)
        self.assertEqual(client.candles("spot","BTCUSDT",0,180),[])

    def test_funding_pagination_preserves_event_rates_and_timing(self):
        def transport(path,params):
            rows=[{"symbol":"BTCUSDT","fundingRateTimestamp":str(t*1000),"fundingRate":rate}
                  for t,rate in [(120,"-0.01"),(0,"0.02")] if t*1000<=params["endTime"]][:1]
            return {"retCode":0,"result":{"list":rows}}
        client=BybitClient(self.root,transport=transport)
        self.assertEqual(client.funding("BTCUSDT",0,180),{0:"0.02",120:"-0.01"})

    def save_fixture(self,market="linear",funding=None):
        store=DatasetStore(self.root/"datasets")
        bars=[Candle(i*60,100,101,99,100,10) for i in range(3)]
        manifest=store.save(market,"BTCUSDT",0,180,bars,bars if market=="linear" else [],funding or {},
            metadata={"instrument":{"fundingInterval":1}},provenance=[{"source":"synthetic test"}])
        return store,manifest,bars

    def test_immutable_parquet_snapshot_roundtrips_and_detects_corruption(self):
        store,manifest,bars=self.save_fixture(funding={0:"0",60:"0.01",120:"0"})
        loaded,trade,mark,funding=store.load(manifest["id"])
        self.assertEqual(manifest,loaded)
        self.assertEqual(trade,bars)
        self.assertEqual(mark[60],bars[1])
        self.assertEqual(funding[60],"0.01")
        file=store.root/manifest["id"]/"trade.parquet"
        file.write_bytes(file.read_bytes()+b"corruption")
        with self.assertRaisesRegex(DataError,"file checksum"): store.load(manifest["id"])

    def test_funding_gaps_require_explicit_assumption(self):
        store,manifest,_=self.save_fixture(funding={0:"0"})
        self.assertEqual(manifest["coverage"]["funding"]["missing_expected"],[60,120])
        profile=Profile(market="linear")
        with self.assertRaisesRegex(DataError,"Funding coverage"): store.for_run(manifest["id"],profile)
        self.assertEqual(store.for_run(manifest["id"],replace(profile,funding_mode="assumed_zero"))[0],manifest)

    def test_manifest_snapshots_strategy_settings_runtime_and_dataset(self):
        store,dataset,_=self.save_fixture("spot")
        ir=example_graph(); profile=Profile()
        manifest=run_manifest(ir,profile,dataset)
        old=copy.deepcopy(manifest)
        ir["nodes"][0]["params"]["field"]="high"
        self.assertEqual(manifest,old)
        self.assertNotEqual(manifest["snapshot_sha256"],run_manifest(ir,profile,dataset)["snapshot_sha256"])
        self.assertEqual(manifest["runtime"]["packages"]["nautilus_trader"],"1.231.0")

    def test_endpoint_boundary_offline_missing_and_cancel(self):
        client=BybitClient(self.root,offline=True)
        with self.assertRaisesRegex(DataError,"Unsupported public endpoint"): client.get("/v5/order/create")
        with self.assertRaisesRegex(DataError,"offline cache"): client.candles("spot","BTCUSDT",0,180)
        event=threading.Event();event.set()
        with self.assertRaisesRegex(DataError,"cancelled"):
            BybitClient(self.root,cancel=event).get("/v5/market/time")

    def test_snapshot_identifiers_cannot_escape_storage_root(self):
        with self.assertRaises(DataError): DatasetStore(self.root).load("../../outside")
