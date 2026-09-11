from pathlib import Path
from decimal import Decimal
import tempfile
import time
import unittest

from terminal.data import DatasetStore
from terminal.native import preview,trust_identity
from terminal.profile import Profile
from terminal.series import Candle
from terminal.service import AppService


def native_document(source=None):
    return {"version":1,"engine":"nautilus_trader","engine_version":"1.231.0",
        "source":source or "from nautilus_trader.examples.strategies.ema_cross import EMACross, EMACrossConfig\n",
        "class_name":"EMACross","config_class":"EMACrossConfig",
        "config":{"instrument_id":"$instrument","bar_type":"$bar:1","trade_size":"1",
                  "fast_ema_period":2,"slow_ema_period":3,"request_bars":False,"subscribe_trade_ticks":False,"close_positions_on_stop":True},
        "bar_minutes":[1],"dependencies":{"nautilus_trader":"1.231.0"},
        "provenance":"Installed official NautilusTrader EMACross example, LGPLv3; source imported, not copied"}


class NativeImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.service=AppService(self.root)
        self.addCleanup(self.service.close)
        bars=[Candle(i*60,p-1,p+1,p-2,p,100) for i,p in enumerate([100,102,104,106,108])]
        self.dataset=DatasetStore(self.root/"datasets").save("spot","BTCUSDT",0,300,bars,[],{},metadata={},provenance=[])

    def call(self,command,params):
        return self.service.handle({"version":1,"id":"native-test","command":command,"params":params})

    def trust(self,doc):
        response=self.call("trust_native",{"document":doc,"expected_sha256":trust_identity(doc),"acknowledge_user_permissions":True})
        self.assertEqual(response["type"],"result",response)

    def run_native(self,doc,dataset=None):
        run_id=self.service.jobs.start(doc,Profile(primary_minutes=1,fee_rate="0"),dataset or self.dataset["id"])
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            state=self.service.jobs.status(run_id)
            if state["status"] in ("completed","failed"): return run_id,state
            time.sleep(0.03)
        self.fail("Native worker timed out")

    def test_preview_save_reopen_do_not_execute_then_trusted_example_runs_unchanged(self):
        sentinel=self.root/"import-side-effect.txt"
        source=f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('import happened')\nprint('this is not IPC JSON')\n"+native_document()["source"]
        doc=native_document(source)
        report=self.call("preview_native",{"document":doc})
        self.assertFalse(report["result"]["trusted"])
        saved=self.call("save_native",{"name":"Vetted fixture","document":doc,"strategy_id":None,"profile":Profile().snapshot()})
        self.assertEqual(saved["type"],"result",saved)
        reopened=self.call("get_strategy",{"strategy_id":saved["result"]["strategy_id"]})
        self.assertEqual(reopened["result"]["document"],doc)
        self.assertFalse(sentinel.exists())
        with self.assertRaisesRegex(ValueError,"Explicit trust"):
            self.run_native(doc)
        self.assertFalse(sentinel.exists())
        self.trust(doc)
        self.assertFalse(sentinel.exists(),"Consent alone does not execute source")
        run_id,status=self.run_native(doc)
        self.assertEqual(status["status"],"completed",status)
        self.assertTrue(sentinel.exists())
        result=self.service.store.result(run_id)
        self.assertEqual(Decimal(result["metrics"]["net_pnl"]),4)
        self.assertEqual(len(result["trades"]),1)
        self.assertTrue(result["indicators"])
        self.assertIn("this is not IPC JSON",(self.service.store.directory(run_id)/"worker.log").read_text())
        self.assertEqual(self.call("list_runs",{})["type"],"result")
        doc["source"]+="\n# Source changed\n"
        with self.assertRaisesRegex(ValueError,"Explicit trust"): self.run_native(doc)

    def test_missing_dependency_and_wrong_confirmation_do_not_install_or_load(self):
        doc=native_document()
        doc["dependencies"]["trading_terminal_missing_test_dependency"]="0.0.0"
        self.assertTrue(preview(doc)["dependency_problems"])
        bad=self.call("trust_native",{"document":doc,"expected_sha256":"0"*64,"acknowledge_user_permissions":True})
        self.assertEqual(bad["type"],"error")
        self.trust(doc)
        with self.assertRaisesRegex(ValueError,"dependencies are missing"): self.run_native(doc)

    def test_unsupported_historical_request_fails_visibly(self):
        doc=native_document();doc["config"]["request_bars"]=True
        self.trust(doc)
        _,status=self.run_native(doc)
        self.assertEqual(status["status"],"failed",status)
        self.assertIn("historical requests",status["error"])

    def test_native_multiple_declared_timeframes_keep_engine_callbacks(self):
        source='''from nautilus_trader.config import StrategyConfig
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.objects import Quantity

class MultiConfig(StrategyConfig, frozen=True):
    instrument_id: str
    one: str
    three: str

class Multi(Strategy):
    def on_start(self):
        from nautilus_trader.model.identifiers import InstrumentId
        self.asset = InstrumentId.from_str(self.config.instrument_id)
        self.n1 = self.n3 = 0
        self.subscribe_bars(BarType.from_str(self.config.one))
        self.subscribe_bars(BarType.from_str(self.config.three))
    def on_bar(self, bar):
        if str(bar.bar_type) == self.config.one:
            self.n1 += 1
        else:
            self.n3 += 1
            if self.n3 == 1:
                self.submit_order(self.order_factory.market(self.asset, OrderSide.BUY, Quantity.from_str("1.000")))
    def on_stop(self):
        if self.n1 != 6 or self.n3 != 2:
            raise ValueError("Native multi-timeframe callbacks did not match actual completed bars")
        self.close_all_positions(self.asset)
'''
        doc=native_document(source)
        doc.update(class_name="Multi",config_class="MultiConfig",bar_minutes=[1,3],
                   config={"instrument_id":"$instrument","one":"$bar:1","three":"$bar:3"},provenance="Independently authored synthetic native callback fixture")
        bars=[Candle(i*60,p,p+1,p-1,p,100) for i,p in enumerate([100,102,104,106,108,110])]
        dataset=DatasetStore(self.root/"datasets").save("spot","BTCUSDT",0,360,bars,[],{},metadata={},provenance=[])
        self.trust(doc)
        run_id,status=self.run_native(doc,dataset["id"])
        self.assertEqual(status["status"],"completed",status)
        self.assertEqual(Decimal(self.service.store.result(run_id)["metrics"]["net_pnl"]),6)

    def test_partial_exit_fails_instead_of_being_silently_reinterpreted(self):
        source='''from nautilus_trader.config import StrategyConfig
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.objects import Quantity

class Partial(Strategy):
    def on_start(self):
        self.asset=InstrumentId.from_str("BTCUSDT.RESEARCH")
        self.seen=0
        self.subscribe_bars(BarType.from_str("BTCUSDT.RESEARCH-1-MINUTE-LAST-EXTERNAL"))
    def on_bar(self, bar):
        self.seen+=1
        if self.seen==1:
            self.submit_order(self.order_factory.market(self.asset,OrderSide.BUY,Quantity.from_str("1.000")))
        elif self.seen==2:
            self.submit_order(self.order_factory.market(self.asset,OrderSide.SELL,Quantity.from_str("0.500")))
    def on_stop(self):
        self.close_all_positions(self.asset)
'''
        doc=native_document(source)
        doc.update(class_name="Partial",config_class="StrategyConfig",config={},provenance="Independently authored unsupported-order fixture")
        self.trust(doc)
        run_id,status=self.run_native(doc)
        self.assertEqual(status["status"],"failed",status)
        self.assertIn("partial exits",status["error"])
        with self.assertRaises(ValueError): self.service.store.result(run_id)

    def test_unavailable_native_feed_does_not_succeed_with_silent_missing_data(self):
        doc=native_document();doc["config"]["subscribe_trade_ticks"]=True
        self.trust(doc)
        _,status=self.run_native(doc)
        self.assertEqual(status["status"],"failed",status)
        self.assertIn("Unsupported native data subscription",status["error"])
