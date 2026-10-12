"""Independent arithmetic, durability and isolation challenges for cache-only research."""
import copy,json,tempfile,threading,time,unittest,uuid
from pathlib import Path
from unittest.mock import patch
from terminal.service import AppService
from terminal.data import canonical,digest
from terminal.display_indicators import CONTRACT
from terminal import indicator_alerts as core
from terminal import indicator_alert_history as history

def ident():return uuid.uuid4().hex
def wait(fn):
 end=time.monotonic()+5
 while time.monotonic()<end:
  value=fn()
  if value:return value
  time.sleep(.01)
 raise AssertionError('Historical job did not reach the expected state')

class IndependentHistoricalResearch(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.denied=[];self.patches=[]
  def forbidden(*a,**kw):self.denied.append(True);raise AssertionError('External/trading path is forbidden')
  for name in ['terminal.data.BybitClient.get','terminal.okx_market.OKXHistory.candles','terminal.live_data.PublicStream.open','terminal.live.LiveManager.start','terminal.live.LiveManager.start_manual','terminal.live.LiveManager.manual','terminal.live.LiveManager._notify']:
   p=patch(name,side_effect=forbidden);p.start();self.patches.append(p)
  self.s=AppService(Path(self.temp.name));self.origin=1800000000;self.width=60
  settings=dict(version=1,revision=1,origins={'1':dict(time=self.origin,generation=1,contract=CONTRACT)},instances=[dict(id='s',type='sma',params={'period':2},visible=True,color='#ffffff')])
  definition=core.freeze_rule(settings,'bybit','spot','BTCUSDT',1,[dict(predicate='cross_above',left=dict(kind='series',instance_id='s',port='value'),right=dict(kind='level',unit='price',value=10))],'ALL')
  self.rule=self.s.indicator_alerts.store.create('Independent original',definition)
  self.tape=[]
  for i in range(362):
   v=[9,9,15,15,9,9][i%6];self.tape.append(dict(time=self.origin+i*60,open=v,high=v+1,low=v-1,close=v,volume=1,confirmation='synthetic_closed'))
  self.seed(self.tape)
 def tearDown(self):
  self.s.close()
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup();self.assertEqual(self.denied,[])
 def seed(self,tape):
  with self.s.store.connect() as db:
   for row in tape:
    candle={k:v for k,v in row.items() if k!='confirmation'};t=candle['time']
    db.execute('INSERT OR REPLACE INTO chart_candles_v1 VALUES(?,?,?,?,?)',('spot','BTCUSDT',1,t,canonical(candle).decode()))
    db.execute('INSERT OR REPLACE INTO chart_confirmation_v1 VALUES(?,?,?,?,?,?,0)',('spot','BTCUSDT',1,t,digest(candle),'synthetic_closed'))
 def raw(self,command,**params):return self.s.handle(dict(version=1,id=ident(),command=command,params=params))
 def call(self,command,**params):
  result=self.raw(command,**params);self.assertEqual(result['type'],'result',result);return result['result']
 def args(self,**changes):return dict(request_id=ident(),rule_id=self.rule['id'],revision=1,definition_hash=self.rule['definition_hash'],start=self.origin+60,end=self.origin+362*60,**changes)
 def start(self,args=None):return self.call('alert_history_start',**(args or self.args()))
 def finish(self,run):
  def terminal():
   result=self.call('alert_history_get',run_id=run['id']);return result if result['status'] not in history.UNFINISHED else None
  result=wait(terminal);self.assertEqual(result['status'],'completed',result);return result
 def test_independent_60_cross_oracle_exact_clocks_and_three_pages(self):
  run=self.finish(self.start());summary=run['summary'];self.assertEqual((summary['input_rows'],summary['known_rows'],summary['unknown_rows'],summary['match_count']),(362,360,2,60))
  cursor=0;hits=[]
  while True:
   page=self.call('alert_history_matches',run_id=run['id'],after=cursor);self.assertEqual(len(page['matches']),20);hits+=page['matches']
   if page['next_cursor'] is None:break
   cursor=page['next_cursor'];self.assertEqual(cursor,hits[-1]['confirmed_at'])
  self.assertEqual([x['raw_open_time'] for x in hits],[self.origin+i*60 for i in range(2,362,6)])
  self.assertEqual([x['confirmed_at'] for x in hits],[self.origin+(i+1)*60 for i in range(2,362,6)])
  for x in hits:self.assertEqual((x['conditions'][0]['left'],x['conditions'][0]['previous_left']),(12,9))
  exact=self.call('alert_history_row',run_id=run['id'],confirmed_at=hits[-1]['confirmed_at']);self.assertEqual(exact['candle']['time'],hits[-1]['raw_open_time']);self.assertEqual(exact['evaluation']['values']['s']['value'],12)
 def test_frozen_raw_formula_and_rule_survive_mutation_and_service_restart(self):
  run=self.finish(self.start());before=self.call('alert_history_chart',run_id=run['id'],start_index=0,limit=20)
  self.seed([{**x,'open':100,'high':101,'low':99,'close':100} for x in self.tape]);self.s.indicator_alerts.rename(self.rule['id'],1,'Changed current name')
  self.assertEqual(self.call('alert_history_chart',run_id=run['id'],start_index=0,limit=20),before)
  self.s.close();self.s=AppService(Path(self.temp.name));self.assertEqual(self.call('alert_history_chart',run_id=run['id'],start_index=0,limit=20),before);self.assertEqual(self.call('alert_history_get',run_id=run['id'])['rule_name'],'Independent original')
 def test_request_replay_is_idempotent_and_changed_content_rejected(self):
  args=self.args();run=self.finish(self.start(args));again=self.start(args);self.assertEqual(run['id'],again['id']);self.assertEqual(self.call('alert_history_request',request_id=args['request_id'])['run']['id'],run['id'])
  bad={**args,'start':args['start']+60};self.assertEqual(self.raw('alert_history_start',**bad)['type'],'error');self.assertFalse(self.call('alert_history_request',request_id=ident())['found']);self.assertEqual(len(self.call('alert_history_list')['runs']),1)
 def test_later_start_does_not_reduce_full_origin_budget_or_hide_a_gap(self):
  args=self.args();args.update(start=self.origin+10000*60,end=self.origin+10001*60)
  self.assertIn('10,000',self.raw('alert_history_start',**args)['error']['message'])
  with self.s.store.connect() as db:db.execute('DELETE FROM chart_candles_v1 WHERE time=?',(self.origin+60,))
  args=self.args();args['start']=self.origin+300*60;self.assertIn('gap',self.raw('alert_history_start',**args)['error']['message'])
 def test_byte_shortened_target_window_reports_cursor_and_exact_fallback(self):
  run=self.finish(self.start());target=self.origin+350*60
  with patch.object(history,'MAX_RESPONSE_BYTES',6000):
   page=self.call('alert_history_chart',run_id=run['id'],target_confirmed_at=target)
   self.assertEqual(page['start_index'],309);self.assertTrue(page['byte_limited']);self.assertFalse(page['target']['included']);self.assertEqual(page['next_index'],page['rows'][-1]['row_index']+1)
   exact=self.call('alert_history_row',run_id=run['id'],confirmed_at=target);self.assertEqual(exact['candle']['time'],target-60)
   second=self.call('alert_history_chart',run_id=run['id'],start_index=page['next_index']);self.assertEqual(second['rows'][0]['row_index'],page['next_index'])
 def test_research_does_not_change_live_cursor_journal_unread_or_banner(self):
  store=self.s.indicator_alerts.store;rows=core.replay(self.rule['definition'],self.tape[:3])['rows'];token=store.begin_cursor(self.rule['id'],1,rows[1])['token'];eventid=store.commit_evaluation(self.rule['id'],1,token,rows[1]['confirmed_at'],rows[2],observed_at=rows[2]['confirmed_at']+1)['event_id']
  before=(copy.deepcopy(store.cursor(self.rule['id'])),copy.deepcopy(store.event(eventid)))
  run=self.finish(self.start());self.call('alert_history_matches',run_id=run['id']);self.call('alert_history_chart',run_id=run['id']);self.call('alert_event_evidence',event_id=eventid)
  self.assertEqual((store.cursor(self.rule['id']),store.event(eventid)),before)
  self.seed([{**self.tape[2],'open':77,'high':78,'low':76,'close':77}]);evidence=self.call('alert_event_evidence',event_id=eventid,before=0,after=0);self.assertEqual(evidence['target_raw_open_time'],self.origin+120);self.assertEqual(evidence['target_candle']['close'],77);self.assertEqual(evidence['event']['evidence']['conditions'][0]['left'],12);self.assertIn('CURRENT',evidence['warning'])
  with self.s.store.connect() as db:db.execute('DELETE FROM chart_candles_v1 WHERE time=?',(self.origin+120,))
  absent=self.call('alert_event_evidence',event_id=eventid,before=1,after=1);self.assertEqual(absent['target_status'],'missing');self.assertIsNone(absent['target_candle']);self.assertFalse(absent['target_in_window']);self.assertEqual(absent['event']['evidence'],before[1]['evidence'])
 def test_eight_unfinished_cancel_and_restart_do_not_resume(self):
  entered=threading.Event();release=threading.Event();real=core.replay
  def delayed(*a,**kw):entered.set();release.wait(5);return real(*a,**kw)
  with patch.object(core,'replay',side_effect=delayed):
   first=self.start();self.assertTrue(entered.wait(2));others=[self.start() for _ in range(7)];self.assertIn('eight',self.raw('alert_history_start',**self.args())['error']['message'])
   cancel=self.call('alert_history_cancel',run_id=first['id']);self.assertTrue(cancel['cancel_requested']);self.assertEqual(cancel['status'],'cancel_requested');queued=self.call('alert_history_cancel',run_id=others[0]['id']);self.assertEqual(queued['status'],'cancelled');self.assertFalse(queued['cancel_requested']);release.set()
  result=wait(lambda:(x if x['status']=='cancelled' else None) if (x:=self.call('alert_history_get',run_id=first['id'])) else None);self.assertFalse(result['cancel_requested']);self.assertEqual(self.raw('alert_history_chart',run_id=first['id'])['type'],'error')
  self.s.close();self.s=AppService(Path(self.temp.name));self.assertEqual(self.call('alert_history_get',run_id=first['id'])['status'],'cancelled')
 def test_shutdown_timeout_retains_dependencies_and_restart_keeps_interrupted(self):
  entered=threading.Event();release=threading.Event();real=core.replay
  def delayed(*a,**kw):entered.set();release.wait(5);return real(*a,**kw)
  with patch.object(core,'replay',side_effect=delayed):
   run=self.start();self.assertTrue(entered.wait(2))
   try:
    with patch.object(self.s.live,'close',wraps=self.s.live.close) as live_close:
     with self.assertRaisesRegex(RuntimeError,'shutdown'):self.s.close()
     live_close.assert_not_called();self.assertTrue(self.s.indicator_history.thread.is_alive())
     self.assertEqual(self.call('alert_history_get',run_id=run['id'])['status'],'interrupted')
   finally:release.set();self.s.indicator_history.thread.join(3)
  self.s.close();self.s=AppService(Path(self.temp.name));self.assertEqual(self.call('alert_history_get',run_id=run['id'])['status'],'interrupted');self.assertFalse(self.call('alert_history_get',run_id=run['id'])['cancel_requested']);self.assertEqual(self.raw('alert_history_chart',run_id=run['id'])['type'],'error')
