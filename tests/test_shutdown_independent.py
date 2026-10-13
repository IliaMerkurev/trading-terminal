"""Independent failure-injection checks for recovered background owners."""
import sqlite3,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from terminal.service import AppService

def flatten(error):
 if isinstance(error,BaseExceptionGroup):return [e for child in error.exceptions for e in flatten(child)]
 return [error]
class IndependentShutdown(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.denied=[];self.patches=[]
  def forbidden(*a,**kw):self.denied.append(True);raise AssertionError('No external action allowed')
  for name in ['terminal.data.BybitClient.get','terminal.okx_market.OKXHistory.candles','terminal.live_data.PublicStream.open','terminal.live.LiveManager.start','terminal.live.LiveManager.start_manual','terminal.live.LiveManager.manual','terminal.live.LiveManager._notify']:
   p=patch(name,side_effect=forbidden);p.start();self.patches.append(p)
  self.s=AppService(Path(self.temp.name))
 def tearDown(self):
  self.s.close()
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup();self.assertEqual(self.denied,[])
 def test_shared_storage_failure_stops_every_owner_and_preserves_original_error(self):
  fault=sqlite3.OperationalError('independent forced read-only storage')
  with patch.object(self.s.store,'connect',side_effect=fault),patch.object(self.s.live,'close',wraps=self.s.live.close) as live,patch.object(self.s.downloads,'close',wraps=self.s.downloads.close) as downloads:
   with self.assertRaises(ExceptionGroup) as caught:self.s.close()
  self.assertIn(fault,flatten(caught.exception));live.assert_called_once();downloads.assert_called_once()
  for thread in (self.s.indicator_history.thread,self.s.indicator_alerts.thread,self.s.display_indicators.thread,self.s.live.delivery_thread,self.s.live.chart_history.thread):self.assertFalse(thread.is_alive())
  self.assertTrue(self.s.jobs.instance_file.closed)
  self.s.close();self.s.close()
 def test_first_cursor_failure_does_not_skip_later_runtime_cancel_and_observer_close(self):
  runtime=self.s.indicator_alerts
  states=[dict(phase='ARMED',cancel=threading.Event(),observer=Mock()) for _ in range(2)]
  with runtime.lock:runtime.states.update({'a'*32:states[0],'b'*32:states[1]})
  fault=sqlite3.OperationalError('independent cursor persistence failure')
  with patch.object(runtime.store,'invalidate_cursor',side_effect=fault):
   try:runtime.close()
   except Exception as error:self.assertIn(fault,flatten(error))
   else:self.fail('Persistence failure must be reported')
  self.assertFalse(runtime.thread.is_alive())
  for state in states:
   self.assertTrue(state['cancel'].is_set());state['observer'].close.assert_called_once();self.assertEqual(state['phase'],'PAUSED')
 def test_successful_second_close_does_not_reopen_removed_workspace(self):
  self.s.close();self.temp.cleanup()
  self.s.close();self.s.close()
  self.assertTrue(self.s.jobs.instance_file.closed)
  self.assertFalse(self.s.indicator_history.thread.is_alive());self.assertFalse(self.s.indicator_alerts.thread.is_alive())
import test_history_independent as history_mechanics
from terminal import indicator_alerts as core
class IndependentBlockedShutdown(unittest.TestCase):
 setUp=history_mechanics.IndependentHistoricalResearch.setUp
 tearDown=history_mechanics.IndependentHistoricalResearch.tearDown
 seed=history_mechanics.IndependentHistoricalResearch.seed
 raw=history_mechanics.IndependentHistoricalResearch.raw
 call=history_mechanics.IndependentHistoricalResearch.call
 args=history_mechanics.IndependentHistoricalResearch.args
 start=history_mechanics.IndependentHistoricalResearch.start
 def test_blocked_history_plus_storage_error_cancels_both_workers_and_retains_dependencies(self):
  entered=threading.Event();release=threading.Event();real=core.replay
  def delayed(*a,**kw):entered.set();release.wait(8);return real(*a,**kw)
  with patch.object(core,'replay',side_effect=delayed):
   self.start();self.assertTrue(entered.wait(2))
   try:
    with patch.object(self.s.store,'connect',side_effect=sqlite3.OperationalError('independent failed status write')),patch.object(self.s.live,'close',wraps=self.s.live.close) as live:
     with self.assertRaises(ExceptionGroup) as caught:self.s.close()
     self.assertTrue(any(isinstance(e,sqlite3.OperationalError) for e in flatten(caught.exception)))
     self.assertTrue(any(isinstance(e,RuntimeError) and 'shutdown' in str(e).lower() for e in flatten(caught.exception)))
     live.assert_not_called();self.assertFalse(self.s.jobs.instance_file.closed)
     self.assertTrue(self.s.indicator_history.thread.is_alive());self.assertFalse(self.s.indicator_alerts.thread.is_alive())
   finally:release.set();self.s.indicator_history.thread.join(3)
  self.s.close();self.assertTrue(self.s.jobs.instance_file.closed)
if __name__=='__main__':unittest.main()
