"""Independent pre-implementation arithmetic and accepted-v1 compatibility oracles."""
import copy, hashlib, json, unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch
from terminal import indicator_alerts as core, indicator_agreement as agreement, display_indicators as display
from terminal import indicator_alert_history as history
from terminal.service import AppService
import test_history_independent as mechanics
ROOT=Path(__file__).resolve().parent/'fixtures'
ORACLE=json.loads((ROOT/'agreement_history_independent.json').read_text())
LEGACY=json.loads((ROOT/'agreement_legacy_v1_independent.json').read_text())
TAPE=[r['raw'] for r in ORACLE['rows']]
BASE=TAPE[0]['time']
def config(items=None):
 return dict(version=1,revision=7,origins={'1':dict(time=BASE,generation=1,contract=display.CONTRACT)},instances=copy.deepcopy(items or [{**m,'visible':True,'color':'#ffffff'} for m in ORACLE['instances']]))
def freeze(direction='up',threshold=.66,items=None):
 return core.freeze_rule(config(items),'bybit','spot','BTCUSDT',1,[dict(predicate='agreement',direction=direction,threshold=threshold,required_groups=['trend','momentum'])],'ALL')
def verify(test,rows,direction):
 test.assertEqual(len(rows),482)
 for i,(row,source) in enumerate(zip(rows,ORACLE['rows'])):
  expected=source['expected'];proof=row['conditions'][0]['agreement']
  test.assertEqual(row['confirmed_at'],expected['confirmed_at'],i)
  test.assertEqual(row['raw_open_time'],source['raw']['time'],i)
  test.assertIs(row['truth'],expected[direction+'_truth'],i)
  test.assertEqual(proof['group_conflict'],expected['conflict'],i)
  if expected['overall'] is None:test.assertIsNone(proof['overall'])
  else:
   for key,ratio in expected['overall'].items():
    pair=proof['overall']['exact'][key];test.assertEqual(Fraction(int(pair[0]),int(pair[1])),Fraction(ratio),(i,key))
class IndependentAgreementReplay(unittest.TestCase):
 def test_pre_extension_v1_four_hashes_and_entire_replay_bytes(self):
  for fixture in LEGACY['fixtures']:
   rule=fixture['definition'];self.assertEqual(core.definition_hash(rule),fixture['definition_hash'])
   result=core.replay(rule,TAPE)
   self.assertEqual(hashlib.sha256(core.encode(result,256*1024*1024)).hexdigest(),fixture['replay_bytes_sha256'],fixture['name'])
 def test_all_482_closes_match_preimplementation_fraction_oracle_both_directions(self):
  for direction in ('up','down'):
   result=core.replay(freeze(direction),TAPE,include_values=True);verify(self,result['rows'],direction)
   self.assertEqual([r['raw_open_time'] for r in result['events']],[TAPE[i]['time'] for i in ORACLE['expected_summary'][direction+'_hit_indices']])
   for row,source in zip(result['rows'],ORACLE['rows']):
    self.assertEqual(row['values']['trend']['value'],source['expected']['sma2'])
    self.assertEqual(row['values']['volume']['value'],-.5)
 def test_unknown_to_true_suppressed_and_sustained_true_not_repeated(self):
  items=config()['instances'];items[1]['params']['period']=2
  result=core.replay(freeze(items=items),TAPE)
  self.assertIsNone(result['rows'][1]['truth']);self.assertTrue(result['rows'][2]['truth']);self.assertFalse(result['rows'][2]['hit'])
  self.assertEqual(len(result['events']),59)
  tape=copy.deepcopy(TAPE[:5])
  for row,v in zip(tape,[10,10,14,18,22]):row.update(open=v,close=v,high=v+3,low=v-1)
  result=core.replay(freeze(),tape);self.assertEqual([r['truth'] for r in result['rows']],[None,False,True,True,True]);self.assertEqual(len(result['events']),1)
 def test_threshold_uses_unrounded_fraction_and_manifest_tamper_rejected(self):
  self.assertFalse(core.replay(freeze(threshold=.67),TAPE[:3])['rows'][2]['truth'])
  self.assertTrue(core.replay(freeze(threshold=2/3),TAPE[:3])['rows'][2]['truth'])
  rule=freeze();rule['agreement']['manifest_hash']='f'*64
  with self.assertRaises(ValueError):core.replay(rule,TAPE[:3])
 def test_duplicate_formula_once_prepared_once_expanded_budget_before_allocation(self):
  items=config()['instances'];items.append({**copy.deepcopy(items[0]),'id':'copy'})
  with patch.object(display,'calculate',wraps=display.calculate) as calc,patch.object(agreement,'prepare_agreement',wraps=agreement.prepare_agreement) as prep:
   result=core.replay(freeze(items=items),TAPE)
  self.assertEqual(calc.call_count,1);self.assertEqual(prep.call_count,1);self.assertEqual(len(calc.call_args.args[1]),3)
  self.assertEqual(result['rows'][2]['conditions'][0]['agreement']['coverage']['total_variants'],3)
  many=[{**copy.deepcopy(items[0]),'id':f'copy{i}'} for i in range(200)]+[items[1],items[2]]
  with patch.object(display,'calculate',side_effect=AssertionError('budget must precede formula')) as calc:
   with self.assertRaisesRegex(ValueError,'256 MiB'):core.replay(freeze(items=many),TAPE)
  calc.assert_not_called()
class IndependentAgreementHistory(unittest.TestCase):
 setUp=mechanics.IndependentHistoricalResearch.setUp;tearDown=mechanics.IndependentHistoricalResearch.tearDown;seed=mechanics.IndependentHistoricalResearch.seed;raw=mechanics.IndependentHistoricalResearch.raw;call=mechanics.IndependentHistoricalResearch.call;finish=mechanics.IndependentHistoricalResearch.finish
 def prepare(self):
  self.rule=self.s.indicator_alerts.store.create('Independent agreement',freeze());self.seed(TAPE)
  args=dict(request_id='ab'*16,rule_id=self.rule['id'],revision=1,definition_hash=self.rule['definition_hash'],start=BASE+60,end=BASE+482*60)
  return self.finish(self.call('alert_history_start',**args))
 def test_full_evidence_pages_exact_cursor_and_restart_immutability(self):
  run=self.prepare();self.assertEqual((run['summary']['known_rows'],run['summary']['unknown_rows'],run['summary']['match_count']),(481,1,60))
  rows=[];start=0
  with patch.object(history,'MAX_RESPONSE_BYTES',100000):
   while True:
    page=self.call('alert_history_chart',run_id=run['id'],start_index=start,limit=200);rows.extend(page['rows'])
    if page['next_index'] is None:break
    self.assertEqual(page['next_index'],page['rows'][-1]['row_index']+1);start=page['next_index']
  verify(self,[r['evaluation'] for r in rows],'up')
  before=self.call('alert_history_row',run_id=run['id'],confirmed_at=BASE+180)
  self.seed([{**r,'open':99,'close':99,'high':100,'low':98} for r in TAPE]);self.s.close();self.s=AppService(Path(self.temp.name))
  self.assertEqual(self.call('alert_history_row',run_id=run['id'],confirmed_at=BASE+180),before)
 def test_three_hit_pages_and_frozen_graph_cannot_follow_current_composition(self):
  run=self.prepare();hits=[];cursor=0
  for count in range(3):
   page=self.call('alert_history_matches',run_id=run['id'],after=cursor);self.assertEqual(len(page['matches']),20);hits.extend(page['matches']);cursor=page['next_cursor']
  self.assertIsNone(cursor);self.assertEqual([h['confirmed_at'] for h in hits],[BASE+(i+1)*60 for i in range(2,482,8)])
  rule=self.rule['definition'];current=config()['instances'];current[2]['visible']=False
  currentrule=freeze(items=current)
  self.assertEqual(core.replay(currentrule,TAPE[:3])['rows'][2]['conditions'][0]['agreement']['overall']['exact']['up'],['1','1'])
  frozen=self.call('alert_history_row',run_id=run['id'],confirmed_at=BASE+180)['evaluation']['conditions'][0]['agreement']
  self.assertEqual(frozen['overall']['exact']['up'],['2','3']);self.assertTrue(frozen['group_conflict'])
 def test_history_never_mutates_live_rule_cursor_journal_or_claims(self):
  before=(self.call('alert_events'),self.call('alert_status'))
  run=self.prepare();self.call('alert_history_chart',run_id=run['id']);self.call('alert_history_matches',run_id=run['id'])
  self.assertEqual((self.call('alert_events'),self.call('alert_status')),before)
  self.assertIsNone(self.s.indicator_alerts.store.cursor(self.rule['id']))
if __name__=='__main__':unittest.main()
