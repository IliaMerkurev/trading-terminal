"""Independent real-Hub/Service challenges on synthetic local receipts only."""
import copy,queue,tempfile,threading,time,unittest,uuid
from pathlib import Path
from unittest.mock import patch
from terminal.service import AppService
from terminal.data import canonical,digest
from terminal.display_indicators import CONTRACT
import terminal.indicator_alert_runtime as runtime_module


def uid():return uuid.uuid4().hex
def bar(t,c):return dict(time=t,open=c,high=c+1,low=c-1,close=c,volume=1)
def eventually(fn,timeout=5):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  value=fn()
  if value:return value
  time.sleep(.01)
 raise AssertionError('Synthetic condition did not become true')

class LocalStream:
 def __init__(self,*_):self.inputs=queue.Queue();self.subscribed=False;self.seq=0
 def open(self):self.subscribed=True;self.state.connected()
 def read(self):
  self.seq+=1;now=int(time.time()*1000)
  self.state.ticker_update({'lastPrice':'10'},now)
  self.state.book_update('snapshot',{'u':self.seq,'seq':self.seq,'b':[['9','1']],'a':[['11','1']]},now)
  try:return [self.inputs.get(timeout=.01)]
  except queue.Empty:return []
 def close(self):pass

class IndependentRuntime(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.now=1_800_000_000;self.patches=[];self.forbidden=[]
  self.patches.append(patch('time.time',side_effect=lambda:self.now))
  def no_external(*args,**kwargs):self.forbidden.append(True);raise AssertionError('Forbidden provider/trading path')
  for name in ['terminal.data.BybitClient.get','terminal.okx_market.OKXHistory.candles','terminal.live_data.PublicStream.open','terminal.live.LiveManager.start','terminal.live.LiveManager.start_manual','terminal.live.LiveManager.manual','terminal.live.LiveManager._notify']:
   self.patches.append(patch(name,side_effect=no_external))
  for p in self.patches:p.start()
  self.service=AppService(Path(self.temp.name));self.streams=[]
  def factory(*args):s=LocalStream();self.streams.append(s);return s
  self.service.live.hub.stream_factory=factory
  self.call('market_open',source='bybit',market='spot',symbol='BTCUSDT')
  eventually(lambda:self.service.live.hub.snapshot()['status']=='CONNECTED')
  self.session=uid();self.context_revision=1;self.call('alert_session_init',session_id=self.session)
  self.minutes=1;self.seed(1)
 def tearDown(self):
  self.service.close()
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup();self.assertEqual(self.forbidden,[])
 def raw_call(self,command,**params):return self.service.handle(dict(version=1,id=uid(),command=command,params=params))
 def call(self,command,**params):
  response=self.raw_call(command,**params)
  self.assertEqual(response['type'],'result',response)
  return response['result']
 def context(self,visible=True):
  return self.call('alert_context',session_id=self.session,context_revision=self.context_revision,source='bybit',market='spot',symbol='BTCUSDT',minutes=self.minutes,visible=visible)
 def seed(self,minutes):
  self.minutes=minutes;self.width=minutes*60;self.boundary=self.now//self.width*self.width;self.origin=self.boundary-2*self.width
  doc=self.service.display_indicators.settings('spot','BTCUSDT')
  doc=self.call('chart_indicator_save',market='spot',symbol='BTCUSDT',instances=[dict(id='i',type='sma',params={'period':1},color='#123abc',visible=True)],revision=doc['revision'])
  doc['origins'][str(minutes)]=dict(time=self.origin,generation=1,contract=CONTRACT)
  self.service.display_indicators._write('spot','BTCUSDT',doc)
  with self.service.store.connect() as db:
   for t in [self.origin,self.origin+self.width]:
    value=bar(t,9);db.execute('INSERT OR REPLACE INTO chart_candles_v1 VALUES(?,?,?,?,?)',('spot','BTCUSDT',minutes,t,canonical(value).decode()))
    db.execute('INSERT OR REPLACE INTO chart_confirmation_v1 VALUES(?,?,?,?,?,?,0)',('spot','BTCUSDT',minutes,t,digest(value),'synthetic_closed'))
  self.context()
  self.push(self.boundary-self.width,9)
  eventually(lambda:self.service.live.hub.confirmations.get(str(minutes),{}).get('candle',{}).get('time')==self.boundary-self.width)
  preview=self.call('alert_preview',source='bybit',market='spot',symbol='BTCUSDT',minutes=minutes,settings_revision=doc['revision'],conditions=[dict(predicate='cross_above',left=dict(kind='series',instance_id='i',port='value'),right=dict(kind='level',unit='price',value=10))])
  self.create_request=uid();self.create_args=dict(request_id=self.create_request,name='Independent crossing',definition=preview['definition'],definition_hash=preview['definition_hash'],settings_revision=doc['revision'])
  self.rule=self.call('alert_create',**self.create_args)
 def push(self,t,value):self.streams[-1].inputs.put(dict(kind='candle',interval=str(self.minutes),candle=bar(t,value),provider_ms=int(self.now*1000)))
 def arm(self):
  return self.call('alert_arm',request_id=uid(),rule_id=self.rule['id'],revision=self.rule['revision'],definition_hash=self.rule['definition_hash'],session_id=self.session,context_revision=self.context_revision,reviewed=True)
 def phase(self):return self.call('alert_status',rule_id=self.rule['id'])['phase']
 def ready(self):self.arm();eventually(lambda:self.phase()=='ARMED')
 def events(self):return self.call('alert_events')['events']
 def test_observed_cross_duplicate_no_backfill_and_detached_receipt(self):
  self.ready();self.assertEqual(self.events(),[]);self.now+=self.width;self.push(self.boundary,11)
  eventually(lambda:len(self.events())==1);event=self.events()[0]
  self.assertEqual(event['evidence']['confirmed_at'],self.boundary+self.width)
  self.assertEqual(event['evidence']['raw_open_time'],self.boundary)
  self.assertEqual(event['evidence']['conditions'][0]['left'],11)
  self.push(self.boundary,11)
  eventually(lambda:self.streams[-1].inputs.empty());time.sleep(.05)
  self.assertEqual(self.phase(),'ARMED')
  self.assertEqual(len(self.events()),1)
  self.call('alert_pause');self.now+=self.width;self.push(self.boundary+self.width,8);time.sleep(.05)
  self.assertEqual(len(self.events()),1);self.assertEqual(self.phase(),'PAUSED')
 def test_healthy_five_minute_arm_not_limited_to_first_fifteen_seconds(self):
  self.context_revision+=1;self.seed(5);self.now=self.boundary+120
  self.ready();self.assertEqual(self.events(),[])
 def test_async_arm_context_fence_and_pause_prevent_late_reactivation(self):
  entered=threading.Event();release=threading.Event();real=runtime_module.replay
  def delayed(*args,**kwargs):entered.set();release.wait(4);return real(*args,**kwargs)
  with patch.object(runtime_module,'replay',side_effect=delayed):
   self.arm();self.assertTrue(entered.wait(2));self.context_revision+=1;self.context(False)
   self.assertEqual(self.phase(),'PAUSED');release.set()
   eventually(lambda:not self.service.indicator_alerts.thread.is_alive() or self.phase()=='PAUSED');time.sleep(.05)
  self.assertEqual(self.phase(),'PAUSED');self.assertEqual(self.events(),[])
 def test_four_pending_receipts_fail_closed_in_three_capacity_observer(self):
  entered=threading.Event();release=threading.Event();real=runtime_module.replay
  def delayed(*args,**kwargs):entered.set();release.wait(4);return real(*args,**kwargs)
  with patch.object(runtime_module,'replay',side_effect=delayed):
   self.arm();self.assertTrue(entered.wait(2));observer=self.service.indicator_alerts.states[self.rule['id']]['observer']
   self.assertEqual(observer.events.maxsize,3)
   for i in range(4):
    self.now=self.boundary+(i+1)*self.width;self.push(self.boundary+i*self.width,11 if i%2 else 9)
   eventually(lambda:observer.failed);release.set();eventually(lambda:self.phase()=='PAUSED')
  self.assertEqual(self.events(),[])
 def test_missing_close_or_changed_prefix_never_fabricates_event(self):
  self.ready()
  with self.service.store.connect() as db:db.execute('DELETE FROM chart_candles_v1 WHERE market=? AND symbol=? AND minutes=? AND time=?',('spot','BTCUSDT',1,self.origin))
  eventually(lambda:self.phase()=='PAUSED');self.assertEqual(self.events(),[])
 def test_session_reload_and_parameter_revert_cannot_resume(self):
  self.ready();self.call('alert_session_init',session_id=uid());self.assertEqual(self.phase(),'PAUSED')
  self.assertIsNone(self.call('alert_status')['context']);self.assertEqual(self.events(),[])
  doc=self.service.display_indicators.settings('spot','BTCUSDT');changed=copy.deepcopy(doc['instances']);changed[0]['params']['period']=2
  self.call('chart_indicator_save',market='spot',symbol='BTCUSDT',instances=changed,revision=doc['revision'])
  self.call('chart_indicator_save',market='spot',symbol='BTCUSDT',instances=doc['instances'],revision=doc['revision']+1)
  self.assertEqual(self.phase(),'PAUSED')
 def test_active_parameter_change_and_reversal_persist_rebind_requirement(self):
  self.ready();doc=self.service.display_indicators.settings('spot','BTCUSDT');changed=copy.deepcopy(doc['instances']);changed[0]['params']['period']=2
  self.call('chart_indicator_save',market='spot',symbol='BTCUSDT',instances=changed,revision=doc['revision'])
  self.assertEqual(self.phase(),'PAUSED');self.assertTrue(self.call('alert_get',rule_id=self.rule['id'])['rebind_required'])
  self.call('chart_indicator_save',market='spot',symbol='BTCUSDT',instances=doc['instances'],revision=doc['revision']+1)
  self.assertTrue(self.call('alert_get',rule_id=self.rule['id'])['rebind_required'])
  self.service.close();self.service=AppService(Path(self.temp.name))
  self.assertTrue(self.call('alert_get',rule_id=self.rule['id'])['rebind_required']);self.assertEqual(self.phase(),'PAUSED')
 def test_uncertain_create_same_id_reconciles_without_second_rule_after_context_change(self):
  self.context_revision+=1;self.context(False)
  readback=self.call('alert_request',request_id=self.create_request);self.assertEqual(readback['rule_id'],self.rule['id'])
  duplicate=self.call('alert_create',**self.create_args);self.assertEqual(duplicate['id'],self.rule['id'])
  self.assertEqual(len(self.call('alert_list')['rules']),1)
  bad=dict(self.create_args,name='Different');self.assertEqual(self.raw_call('alert_create',**bad)['type'],'error')
 def test_premature_baseline_observation_remains_rejected_after_wall_clock_passes(self):
  self.now=self.boundary+10;self.push(self.boundary,11)
  eventually(lambda:self.service.live.hub.confirmations['1']['candle']['time']==self.boundary)
  self.now=self.boundary+61
  result=self.raw_call('alert_arm',request_id=uid(),rule_id=self.rule['id'],revision=self.rule['revision'],definition_hash=self.rule['definition_hash'],session_id=self.session,context_revision=self.context_revision,reviewed=True)
  self.assertEqual(result['type'],'error',result);self.assertEqual(self.events(),[])
 def test_shutdown_timeout_preserves_dependencies_until_worker_has_joined(self):
  entered=threading.Event();release=threading.Event();real=runtime_module.replay
  def delayed(*args,**kwargs):entered.set();release.wait(6);return real(*args,**kwargs)
  with patch.object(runtime_module,'replay',side_effect=delayed):
   self.arm();self.assertTrue(entered.wait(2))
   with patch.object(self.service.live,'close',wraps=self.service.live.close) as close_live:
    with self.assertRaises(RuntimeError):self.service.close()
    self.assertEqual(close_live.call_count,0);self.assertTrue(self.service.live.chart_history.thread.is_alive())
   release.set();eventually(lambda:not self.service.indicator_alerts.thread.is_alive())
  self.assertEqual(self.events(),[])

if __name__=='__main__':unittest.main(verbosity=2)
