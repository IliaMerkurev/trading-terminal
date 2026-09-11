import copy
import json
from pathlib import Path
import tempfile
import time
import unittest

from terminal.data import DatasetStore
from terminal.graph import example_graph
from terminal.jobs import JobManager
from terminal.profile import Profile
from terminal.series import Candle
from terminal.service import AppService


class JobTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        bars=[Candle(i*60,100+i%20,101+i%20,99+i%20,100+i%20,100) for i in range(120)]
        self.dataset=DatasetStore(self.root/"datasets").save("spot","BTCUSDT",0,7200,bars,[],{},metadata={},provenance=[])
        self.manager=JobManager(self.root)
        self.addCleanup(self.manager.close)

    def wait(self,run_id):
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            result=self.manager.status(run_id)
            if result["status"] in ("completed","failed","cancelled"): return result
            time.sleep(0.03)
        self.fail("Worker did not finish within bounded test deadline")

    def test_snapshot_worker_persistence_paging_and_repeated_results(self):
        graph=example_graph()
        profile=Profile(primary_minutes=1)
        run_id=self.manager.start(graph,profile,self.dataset["id"])
        graph["nodes"][0]["params"]["field"]="high"
        status=self.wait(run_id)
        self.assertEqual(status["status"],"completed",status)
        saved=self.manager.store.get(run_id)
        self.assertEqual(saved["manifest"]["strategy"]["nodes"][0]["params"]["field"],"close")
        result=self.manager.store.result(run_id)
        self.assertTrue(result["engine_orders"])
        self.assertEqual(result["engine_orders"][0]["status"],"FILLED")
        page=self.manager.store.page(run_id,"candles",0,30)
        self.assertEqual(len(page["rows"]),30)
        self.assertEqual(page["next"],30)
        self.assertEqual(page["total"],120)
        again=self.manager.start(example_graph(),profile,self.dataset["id"])
        again_status=self.wait(again)
        self.assertEqual(again_status["status"],"completed",again_status)
        second=self.manager.store.result(again)
        self.assertEqual(result,second)
        self.assertEqual(len(self.manager.store.recent()),2)
        with self.assertRaises(ValueError): self.manager.store.status(run_id,"running")

    def test_cancel_is_never_successful_and_second_run_is_blocked(self):
        run_id=self.manager.start(example_graph(),Profile(primary_minutes=1),self.dataset["id"])
        with self.assertRaisesRegex(ValueError,"already active"):
            self.manager.start(example_graph(),Profile(),self.dataset["id"])
        self.manager.cancel(run_id)
        self.assertEqual(self.wait(run_id)["status"],"cancelled")
        with self.assertRaisesRegex(ValueError,"not completed"): self.manager.store.result(run_id)
        self.assertIsNone(self.manager.active)

    def test_worker_failure_has_explicit_error_without_success_artifact(self):
        # Corrupt the snapshot after job creation through a direct store fixture;
        # completed output is rejected unless tied to its manifest.
        from terminal.data import run_manifest
        run_id=self.manager.store.create(run_manifest(example_graph(),Profile(),self.dataset))
        self.manager.store.status(run_id,"running")
        with self.assertRaisesRegex(ValueError,"does not match"):
            self.manager.store.complete(run_id,{"status":"completed","manifest_sha256":"wrong"})
        self.manager.store.status(run_id,"failed","Invalid worker output")
        self.assertEqual(self.manager.status(run_id)["status"],"failed")

    def test_service_commands_are_bounded_and_do_not_execute_arbitrary_actions(self):
        service=AppService(self.root/"other")
        self.addCleanup(service.close)
        def call(command,params):
            return service.handle({"version":1,"id":"test","command":command,"params":params})
        self.assertEqual(call("eval",{"code":"raise Exception()"})["type"],"error")
        self.assertEqual(call("list_runs",{"path":"outside"})["type"],"error")
        response=call("save_graph",{"name":"Example","graph":example_graph(),"layout":{"close":{"x":1,"y":2}},"strategy_id":None})
        self.assertEqual(response["type"],"result",response)
        saved=call("get_strategy",{"strategy_id":response["result"]["strategy_id"]})
        self.assertEqual(saved["result"]["document"]["graph"],example_graph())
        self.assertEqual(call("result_page",{"run_id":"bad","kind":"candles","offset":0,"limit":100000})["type"],"error")

    def test_second_application_cannot_recover_a_live_workspaces_jobs(self):
        with self.assertRaisesRegex(ValueError,"Another application instance"):
            JobManager(self.root)

    def test_cancel_after_engine_reports_progress_and_partial_output_is_not_final(self):
        bars=[Candle(i*60,100,101,99,100,100) for i in range(10080)]
        dataset=self.manager.datasets.save("spot","BTCUSDT",0,10080*60,bars,[],{},metadata={},provenance=[])
        run_id=self.manager.start(example_graph(),Profile(primary_minutes=1,evaluation="intrabar"),dataset["id"])
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            status=self.manager.status(run_id)
            if status["progress"]:
                break
            if status["status"] in ("failed","completed"):
                self.fail(f"Worker exited before cancellation checkpoint: {status['status']}")
            time.sleep(0.01)
        else: self.fail("No worker progress within deadline")
        self.manager.cancel(run_id)
        self.assertEqual(self.wait(run_id)["status"],"cancelled")
        self.assertFalse((self.manager.store.directory(run_id)/"result.json").exists())
