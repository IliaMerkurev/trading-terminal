"""Independent, synthetic-only reconstruction checks for frozen alert core/storage."""
import copy,itertools,sqlite3,tempfile,unittest
from terminal import indicator_alerts as a
from terminal.indicator_alert_store import IndicatorAlertStore
from terminal.display_indicators import CONTRACT
from terminal.storage import RunStore


def settings(period=2,minutes=1,origin=0):
 return dict(version=1,revision=4,instances=[dict(id='average',type='sma',params={'period':period},color='#aabbcc',visible=True)],origins={str(minutes):dict(time=origin,generation=2,contract=CONTRACT)})
def cond(op='cross_above',level=10):
 return dict(predicate=op,left=dict(kind='series',instance_id='average',port='value'),right=dict(kind='level',unit='price',value=level))
def rule(op='cross_above',period=2,minutes=1,origin=0):
 return a.freeze_rule(settings(period,minutes,origin),'okx','spot','BTCUSDT',minutes,[cond(op)])
def tape(values,minutes=1,origin=0):
 return [dict(time=origin+i*minutes*60,open=v,high=v+1,low=v-1,close=v,volume=10,confirmation='synthetic_closed') for i,v in enumerate(values)]


class IndependentAlertPure(unittest.TestCase):
 def test_independent_sma_cross_arithmetic_and_five_minute_clock(self):
  values=[8,12,10,14,6,8,14,12,8]
  for minutes,origin in [(1,0),(5,600)]:
   result=a.replay(rule(minutes=minutes,origin=origin),tape(values,minutes,origin))
   means=[None]+[(values[i-1]+values[i])/2 for i in range(1,len(values))]
   wanted=[None if i<2 else means[i-1]<=10 and means[i]>10 for i in range(len(values))]
   self.assertEqual([r['truth'] for r in result['rows']],wanted)
   self.assertEqual([r['confirmed_at'] for r in result['events']],[origin+(i+1)*minutes*60 for i,v in enumerate(wanted) if v])
   for i,r in enumerate(result['rows']):self.assertEqual(r['conditions'][0]['left'],means[i])
 def test_all_three_input_truth_tables_independently(self):
  for values in itertools.product([False,None,True],repeat=3):
   wanted_all= False if any(v is False for v in values) else None if any(v is None for v in values) else True
   wanted_any= True if any(v is True for v in values) else None if any(v is None for v in values) else False
   self.assertIs(a.combine_truth(values,'ALL'),wanted_all);self.assertIs(a.combine_truth(values,'ANY'),wanted_any)
 def test_state_unknown_reset_and_mixed_pulse_do_not_accumulate(self):
  sequence=[None,True,True,False,True,None,True,False,True]
  prior=None;hits=[]
  for i,truth in enumerate(sequence):
   out=a.transition([dict(kind='state',truth=truth)],'ALL',prior,prior)
   if out['hit']:hits.append(i)
   prior=out['truth']
  self.assertEqual(hits,[4,8])
  prior=state_prior=None
  for pulse in [True,False,True,False]:
   out=a.transition([dict(kind='impulse',truth=pulse),dict(kind='state',truth=True)],'ANY',prior,state_prior)
   self.assertIs(out['hit'],pulse);prior,state_prior=out['truth'],out['state_truth']
 def test_future_and_appearance_cannot_rewrite_frozen_prefix(self):
  config=settings();frozen=a.freeze_rule(config,'okx','spot','BTCUSDT',1,[cond()]);before=copy.deepcopy(frozen)
  config['instances'][0].update(visible=False,color='#000000');config['pane_layout']={'unknown':'appearance'}
  self.assertEqual(a.changed_dependencies(frozen,config),[])
  config['instances'][0]['params']['period']=3;self.assertEqual(a.changed_dependencies(frozen,config),['average'])
  data=tape([8,12,10,14,5,20,50,30]);prefix=a.replay(frozen,data[:4])['rows'];changed=copy.deepcopy(data)
  for row in changed[4:]:
   for field in ['open','high','low','close']:row[field]+=10000
  self.assertEqual(a.replay(frozen,changed)['rows'][:4],prefix);self.assertEqual(frozen,before)
 def test_resource_malformed_finite_and_origin_boundaries(self):
  r=rule();good=tape([8,12,10])
  for data in [good[1:],good[:1]+good[2:],[],tape([10]*10001)]:
   with self.assertRaises(ValueError):a.replay(r,data)
  for value in [float('nan'),float('inf'),10**1000,True]:
   bad=copy.deepcopy(r);bad['conditions'][0]['right']['value']=value
   with self.subTest(value=str(value)[:30]),self.assertRaises(ValueError):a.validate_definition(bad)
  for raw in ['{"x":1,"x":2}','{"x":NaN}']:
   with self.assertRaises(ValueError):a.decode(raw)
  with self.assertRaises(ValueError):a.freeze_rule(settings(),'okx','spot','BTCUSDT',1,[cond()]*17)
  with self.assertRaises(ValueError):a.replay(a.freeze_rule(settings(),'okx','spot','BTCUSDT',1,[cond()]*16),tape([10]*5000))


class IndependentAlertStore(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=RunStore(self.tmp.name);self.store=IndicatorAlertStore(self.db)
  self.rule=self.store.create('Original',rule(period=1));self.rows=a.replay(self.rule['definition'],tape([9,11,9,11]*40))['rows']
 def tearDown(self):self.tmp.cleanup()
 def arm(self):return self.store.begin_cursor(self.rule['id'],1,self.rows[0])['token']
 def commit(self,token,i):return self.store.commit_evaluation(self.rule['id'],1,token,self.rows[i-1]['confirmed_at'],self.rows[i],observed_at=self.rows[i]['confirmed_at']+2)
 def test_every_journal_page_no_lost_tail_and_no_false_events(self):
  token=self.arm();ids=[]
  for i in range(1,len(self.rows)):
   result=self.commit(token,i)
   if result['event_id']:ids.append(result['event_id'])
  self.assertEqual(len(ids),80)
  found=[];cursor=0
  while True:
   page=self.store.events(after=cursor,limit=7);found.extend(r['id'] for r in page['events'])
   if page['next_cursor'] is None:break
   self.assertGreater(page['next_cursor'],cursor);cursor=page['next_cursor']
  self.assertEqual(found,ids);self.assertEqual(len(set(found)),80)
 def test_atomic_write_failure_and_restart_fence(self):
  token=self.arm()
  with self.db.connect() as db:db.execute("CREATE TRIGGER independent_fail BEFORE UPDATE OF confirmed_at ON indicator_alert_cursors_v1 BEGIN SELECT RAISE(ABORT,'independent fault'); END")
  with self.assertRaises(sqlite3.IntegrityError):self.commit(token,1)
  self.assertEqual(self.store.events()['events'],[]);self.assertEqual(self.store.cursor(self.rule['id'])['confirmed_at'],60)
  with self.db.connect() as db:db.execute('DROP TRIGGER independent_fail')
  self.commit(token,1);IndicatorAlertStore(self.db)
  with self.assertRaises(ValueError):self.commit(token,2)
  self.assertEqual(len(self.store.events()['events']),1)
 def test_rearm_dedup_preserves_read_and_claim_and_old_evidence_after_rename(self):
  first=self.commit(self.arm(),1);eid=first['event_id'];original=self.store.event(eid)['evidence']
  self.assertTrue(self.store.claim_banner(eid));self.store.mark_read(eid)
  duplicate=self.commit(self.arm(),1);self.assertEqual(duplicate['event_id'],eid)
  self.assertTrue(duplicate['duplicate']);self.assertFalse(self.store.claim_banner(eid));self.assertTrue(self.store.event(eid)['is_read'])
  self.store.rename(self.rule['id'],1,'Current name');self.assertEqual(self.store.event(eid)['current_name'],'Current name')
  self.assertEqual(self.store.event(eid)['evidence'],original)
 def test_pause_rebind_and_conflicting_duplicate_never_advance_cursor(self):
  token=self.arm();self.commit(token,1);bad=copy.deepcopy(self.rows[1]);bad['conditions'][0]['left']=999
  with self.assertRaises(ValueError):self.store.commit_evaluation(self.rule['id'],1,token,60,bad,observed_at=122)
  self.assertEqual(self.store.cursor(self.rule['id'])['confirmed_at'],120)
  self.store.invalidate_cursor(self.rule['id'])
  with self.assertRaises(ValueError):self.commit(token,2)
  self.store.rebind(self.rule['id'],1,rule('cross_below',period=1))
  self.assertIsNone(self.store.cursor(self.rule['id'])['token']);self.assertEqual(len(self.store.events()['events']),1)

if __name__=='__main__':unittest.main(verbosity=2)
