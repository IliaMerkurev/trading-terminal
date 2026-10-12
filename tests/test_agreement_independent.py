"""Independent agreement expectations; precomputed inputs test semantics, not formulas."""
import copy,json,pathlib,unittest
from terminal.indicator_agreement import evaluate_agreement,prepare_agreement,threshold_evidence
ROOT=pathlib.Path(__file__).resolve().parent
FIXTURES=json.loads((ROOT/'fixtures'/'indicator_agreement_v1.json').read_text())


def check(test,result,expected):
 if 'overall' in expected:
  if expected['overall'] is None:test.assertIsNone(result['overall'])
  else:test.assertEqual(result['overall']['exact'],{d:list(map(str,v)) for d,v in expected['overall'].items()})
 if 'trend' in expected:test.assertEqual(next(g for g in result['groups'] if g['group']=='trend')['distribution']['exact'],{d:list(map(str,v)) for d,v in expected['trend'].items()})
 if 'percentages' in expected:test.assertEqual(result['overall']['percentages'],expected['percentages'])
 for key,value in expected.get('member_direction',{}).items():test.assertEqual(next(m for m in result['members'] if m['id']==key)['status'],value)
 for key in expected.get('member_unavailable',[]):test.assertEqual(next(m for m in result['members'] if m['id']==key)['status'],'unavailable')
 for key,field in [('fully_available_types','fully_covered_types'),('total_supported_types','total_types'),('available_variants','available_variants'),('total_variants','total_variants')]:
  if key in expected:test.assertEqual(result['coverage'][field],expected[key])
 if 'group_conflict' in expected:test.assertIs(result['group_conflict'],expected['group_conflict'])
 for dist in [result['overall']]+[g['distribution'] for g in result['groups']]:
  if dist:test.assertEqual(sum(dist['percentages'].values()),100)


class IndependentAgreement(unittest.TestCase):
 def test_independent_48_expected_cases(self):
  results={}
  for case in FIXTURES['cases']:
   with self.subTest(case=case['name']):
    result=evaluate_agreement(case['input']);check(self,result,case['expected']);results[case['name']]=result
 def test_seven_independent_thresholds(self):
  cases={c['name']:c['input'] for c in FIXTURES['cases']}
  for c in FIXTURES['threshold_cases']:
   with self.subTest(case=c['name']):self.assertIs(threshold_evidence(evaluate_agreement(cases[c['result_case']]),c['direction'],c['threshold'],c['required_groups'])['truth'],c['expected'])
 def test_conflicts_invalid_geometry_no_fallback_and_neighbor_fail_closed(self):
  base=copy.deepcopy(FIXTURES['cases'][0]['input'])
  for patch in [{'conflict':True},{'low':1000},{'high':0},{'open':float('nan')},{'confirmation':'forming'}]:
   x=copy.deepcopy(base);x['candles'][-1].update(patch);r=evaluate_agreement(x)
   with self.subTest(patch=patch):self.assertIsNone(r['overall']);self.assertTrue(all(m['status']=='unavailable' for m in r['members']))
  x=copy.deepcopy(base);x['display']['times']=x['display']['times'][:-1]
  self.assertIsNone(evaluate_agreement(x)['overall'])
  x=copy.deepcopy(base);x['instances']=[dict(id='o',type='obv',params={},visible=True)];x['display']['columns']={'o':{'value':[10,20]}}
  self.assertEqual(evaluate_agreement(x)['members'][0]['status'],'up')
  x['candles'][-2]['conflict']=True;self.assertEqual(evaluate_agreement(x)['members'][0]['status'],'unavailable')
 def test_prepared_snapshot_is_detached_and_future_invariant(self):
  x=copy.deepcopy(FIXTURES['cases'][0]['input']);prepared=prepare_agreement(x);before=prepared.evaluate(x['close_time'])
  x['instances'][0]['params']['period']=999;x['display']['columns']['s']['value'][-1]=-99;x['candles'][-1]['close']=0
  self.assertEqual(prepared.evaluate(1920),before)
  y=copy.deepcopy(FIXTURES['cases'][0]['input']);y['candles'].append(dict(time=1920,open=500,close=500,high=501,low=499,confirmation='synthetic_closed'));y['display']['times'].append(1980)
  for ports in y['display']['columns'].values():
   for values in ports.values():values.append(-999)
  self.assertEqual(evaluate_agreement(y),before)

if __name__=='__main__':unittest.main(verbosity=2)
