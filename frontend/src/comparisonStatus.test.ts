import {expect,it} from 'vitest';
import {comparisonStatusLabel,comparisonStatusSummary} from './comparisonStatus';

const summary=(status:string,states:string[],extra={})=>comparisonStatusSummary({status,rows:states.map(status=>({status})),snapshot:{rows:states},...extra});

it('separates unavailable rows from real failures without changing saved statuses',()=>{
 expect(summary('completed_with_errors',[...Array(14).fill('completed'),'incompatible','incompatible']))
  .toBe('Completed · 14 completed · 2 unavailable · 0 failed');
 expect(summary('completed',['completed'])).toBe('Completed · 1 completed · 0 unavailable · 0 failed');
 expect(summary('completed_with_errors',['completed','incompatible','failed','error']))
  .toBe('Completed with failures · 1 completed · 1 unavailable · 2 failed');
 expect(summary('failed',['completed','pending'],{error:'Preparation failed'}))
  .toBe('Failed · 1 completed · 0 unavailable · 0 failed · 1 pending');
 expect(summary('completed_with_errors',['completed'],{error:'Finalization failed'}))
  .toBe('Finished with an error · 1 completed · 0 unavailable · 0 failed');
});

it.each(['running','preparing','pending','cancelled','interrupted','frozen'])('keeps %s distinct from completion',status=>{
 const value=summary(status,['completed','incompatible','pending']);
 expect(value).toBe(`${comparisonStatusLabel(status)} · 1 completed · 1 unavailable · 0 failed · 1 pending`);
 expect(value.startsWith('Completed')).toBe(false);
});

it('never treats partial, running, unknown or missing row details as complete',()=>{
 for(const state of ['pending','running','cancelled','interrupted','frozen','future_state']) {
  expect(summary('completed_with_errors',['completed',state]).startsWith('Incomplete results ·')).toBe(true);
 }
 expect(summary('completed',[])).toBe('Incomplete results · 0 completed · 0 unavailable · 0 failed');
 expect(summary('completed',['completed'],{snapshot:{rows:[{},{}]}}))
  .toBe('Incomplete results · 1 completed · 0 unavailable · 0 failed · Row details incomplete');
 expect(summary('new_state',['completed'])).toBe('Unknown status (new_state) · 1 completed · 0 unavailable · 0 failed');
});

it('uses conservative history labels without claiming unavailable-only outcomes',()=>{
 expect(comparisonStatusLabel('completed_with_errors')).toBe('Finished with unavailable or failed rows');
 expect(comparisonStatusLabel('incompatible')).toBe('Unavailable');
 expect(comparisonStatusLabel('frozen')).toBe('Frozen · not started');
 expect(comparisonStatusLabel('new_state')).toBe('Unknown status (new_state)');
 expect(comparisonStatusLabel('')).toBe('Unknown status (missing)');
 expect(comparisonStatusLabel('toString')).toBe('Unknown status (toString)');
});
