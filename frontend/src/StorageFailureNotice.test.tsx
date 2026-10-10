import {afterEach,it,expect,vi} from 'vitest';
import {cleanup,render,screen,waitFor} from '@testing-library/react';
import StorageFailureNotice from './StorageFailureNotice';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
afterEach(()=>{cleanup();vi.resetAllMocks();});

it('shows a non-durable failure without starting or retrying a calculation',async()=>{
  vi.mocked(api).mockResolvedValue({storage_failure:{id:'a'.repeat(32),kind:'library_batch',durable:false,message:'Calculations blocked by storage finalization failure. Check available storage and restart the application. No automatic retry.'}});
  render(<StorageFailureNotice connected={true}/>);
  expect(await screen.findByRole('alert',{name:'Storage finalization failure'})).toBeTruthy();
  expect(screen.getByText(/held in memory/).textContent).toContain('completed reports are unchanged');
  expect(api).toHaveBeenCalledWith('scheduler_status');
  expect(vi.mocked(api).mock.calls.every(([command])=>command==='scheduler_status')).toBe(true);
});

it('retains the storage warning if later status reads fail',async()=>{
  vi.mocked(api).mockResolvedValueOnce({storage_failure:{id:'r',kind:'run',durable:false,message:'Storage failure'}}).mockRejectedValue(new Error('offline'));
  render(<StorageFailureNotice connected={true}/>);
  await screen.findByRole('alert',{name:'Storage finalization failure'});
  await waitFor(()=>expect(screen.getByText(/currently unavailable/)).toBeTruthy(),{timeout:2000});
  expect(screen.getByText('Storage failure')).toBeTruthy();
});

it('does not poll a disconnected service',()=>{
  render(<StorageFailureNotice connected={false}/>);
  expect(api).not.toHaveBeenCalled();
  expect(screen.queryByRole('alert')).toBeNull();
});

it('reconciles stale calculation controls only after all scheduler ownership is released',async()=>{
 const onReleased=vi.fn();
 vi.mocked(api).mockResolvedValue({storage_failure:{id:'r',kind:'run',durable:false,message:'Storage failure'},active:null,reservation:null});
 render(<StorageFailureNotice connected={true} onReleased={onReleased}/>);
 await waitFor(()=>expect(onReleased).toHaveBeenCalledOnce());
});
