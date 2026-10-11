import {render,screen} from '@testing-library/react';
import {describe,it,expect} from 'vitest';
import {RunProgress} from './RunProgress';
import {hasActiveWork} from './BrowserServiceControls';
describe('local result finalization',()=>{
 it('shows rows and bytes independently of computed percentage',()=>{
  render(<RunProgress status={{status:'finalizing',worker_active:true,progress:{fraction:1},finalization:{phase:'staging',staged_rows:128,total_rows:500,staged_bytes:65536}}}/>);
  expect(screen.getByRole('status').textContent).toContain('128/500 rows · 65536 bytes');
  expect(screen.queryByText(/100%/)).toBeNull();
 });
 it('keeps cancellation pending and considers cleanup active',()=>{
  render(<RunProgress status={{status:'cancel_requested',worker_active:true,finalization:{phase:'verifying',staged_rows:500,total_rows:500,staged_bytes:50000}}}/>);
  expect(screen.getByRole('status').textContent).toContain('Cancellation requested; waiting for cleanup');
  expect(hasActiveWork({status:'finalizing'})).toBe(true);
  expect(hasActiveWork({status:'completed',worker_active:true})).toBe(true);
  expect(hasActiveWork({status:'completed',worker_active:false})).toBe(false);
 });
});

it.each([
 ['cancelled','Cancelled. No completed result was published.'],
 ['failed','Calculation failed. No completed result was published.'],
 ['interrupted','Work was interrupted. No automatic retry.'],
 ['completed','Result saved.'],
])('describes terminal %s without preparation or stale engine percentage',(status,copy)=>{
 render(<RunProgress status={{status,worker_active:false,progress:{fraction:1},finalization:{phase:status}}}/>);
 expect(screen.getByText(copy)).toBeTruthy();
 expect(screen.queryByText(/Worker preparation|100%|Waiting for durable/)).toBeNull();
});
it('keeps committed-but-owned cleanup distinct from fully saved completion',()=>{
 render(<RunProgress status={{status:'completed',worker_active:true,finalization:{phase:'completed',staged_rows:2,total_rows:2,staged_bytes:50}}}/>);
 expect(screen.getByRole('status').textContent).toContain('Result saved; waiting for worker cleanup.');
 expect(screen.queryByText('Result saved.')).toBeNull();
});
it('describes cancellation before finalization without preparation',()=>{
 render(<RunProgress status={{status:'cancel_requested',worker_active:true,progress:{fraction:1}}}/>);
 expect(screen.getByText('Cancellation requested; waiting for worker cleanup.')).toBeTruthy();
 expect(screen.queryByText(/Worker preparation|100%/)).toBeNull();
});

it('shows a loading state when finalizing history has no detailed poll yet',()=>{
 render(<RunProgress status={{status:'finalizing',progress:{fraction:1}}}/>);
 expect(screen.getByRole('status').textContent).toBe('Loading finalization status…');
 expect(screen.queryByText(/Worker preparation|100%/)).toBeNull();
});
