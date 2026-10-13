import {beforeEach,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,act} from '@testing-library/react';
import Observations from './Observations';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
vi.mock('./ObservationChart',()=>({default:({candles}:any)=><div>Rendered candle {candles[0]?.time}</div>}));
const source={id:'source',source:'Synthetic pending read',market:'spot',symbol:'BTCUSDT',range:[0,3600],interval_seconds:60,classification:'synthetic'};
const value=(t:number)=>({source,start:0,end:3600,candles:[{time:t,open:100,high:102,low:99,close:101}],missing:[]});
let pending:any[],cancelStatus:string;
beforeEach(()=>{
 vi.clearAllMocks();pending=[];cancelStatus='cancelled';
 vi.mocked(api).mockImplementation((c,p:any,o:any)=>{
  if(c==='observation_history')return Promise.resolve({rows:[],next:null});
  if(c==='observation_save_history')return Promise.resolve([]);
  if(c==='chart_read_cancel')return Promise.resolve({request_id:p.request_id,status:cancelStatus,result:cancelStatus==='ready'?value(60):null});
  if(c==='local_history_window'){o.onRequest(String(pending.length+1).repeat(32));return new Promise((resolve,reject)=>pending.push({p,o,resolve,reject}));}
  return Promise.resolve({});
 });
});
const props={datasets:[source],request:{dataset:'source',request:1},onTest:vi.fn(),onBatch:vi.fn()};
it('cancels and retries only the current chart read and ignores its late error',async()=>{
 render(<Observations {...props}/>);const cancel=await screen.findByRole('button',{name:'Cancel reading'});
 await waitFor(()=>expect((cancel as HTMLButtonElement).disabled).toBe(false));fireEvent.click(cancel);
 expect(await screen.findByText('Reading cancelled. No partial page is displayed.')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Retry reading'}));await waitFor(()=>expect(pending).toHaveLength(2));
 expect(pending[1].o.generation).toBeGreaterThan(pending[0].o.generation);
 await act(async()=>pending[0].reject(new Error('Stale error')));expect(screen.queryByText(/Stale error/)).toBeNull();
 await act(async()=>pending[1].resolve(value(120)));expect(screen.getByText('Rendered candle 120')).toBeTruthy();
 expect(api).toHaveBeenCalledWith('chart_read_cancel',{request_id:'1'.repeat(32)});
 expect(vi.mocked(api).mock.calls.filter(([c])=>c==='chart_read_cancel')).toHaveLength(1);
 expect(vi.mocked(api).mock.calls.some(([c])=>c==='observation_save')).toBe(false);
});
it('keeps cancellation requested until terminal acknowledgement and labels completion-winning truthfully',async()=>{
 cancelStatus='cancel_requested';render(<Observations {...props}/>);
 const cancel=await screen.findByRole('button',{name:'Cancel reading'});await waitFor(()=>expect((cancel as HTMLButtonElement).disabled).toBe(false));fireEvent.click(cancel);
 expect(await screen.findByText(/Cancellation requested; waiting for reader cleanup/)).toBeTruthy();
 expect(screen.queryByRole('button',{name:'Retry reading'})).toBeNull();
 await act(async()=>pending[0].resolve(value(60)));
 expect(await screen.findByText('Read completed before cancellation. Retry reading to display it.')).toBeTruthy();
 expect(screen.queryByText('Rendered candle 60')).toBeNull();
});
it('keeps a lost cancellation outcome inspectable until the same request is terminal',async()=>{
 cancelStatus='cancel_requested';const previous=vi.mocked(api).getMockImplementation()!;
 vi.mocked(api).mockImplementation((c,p,o)=>c==='chart_read_status'?Promise.resolve({request_id:'1'.repeat(32),status:'cancelled'}):previous(c,p,o));
 render(<Observations {...props}/>);const cancel=await screen.findByRole('button',{name:'Cancel reading'});await waitFor(()=>expect((cancel as HTMLButtonElement).disabled).toBe(false));fireEvent.click(cancel);
 await act(async()=>pending[0].reject(Object.assign(new Error('Lost status response'),{saveOutcome:'unknown'})));
 expect(screen.queryByRole('button',{name:'Retry reading'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Inspect reading'}));
 expect(await screen.findByText('Reading cancelled. No partial page is displayed.')).toBeTruthy();
 expect(api).toHaveBeenCalledWith('chart_read_status',{request_id:'1'.repeat(32)});
 expect(screen.getByRole('button',{name:'Retry reading'})).toBeTruthy();
});
