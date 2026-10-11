import {beforeEach,it,expect,vi} from 'vitest';
import {render,screen,act,waitFor} from '@testing-library/react';
import RunChart from './RunChart';
import {api} from './api';
import {observeChartDisplay} from './DisplayedEvidence';
vi.mock('./api',()=>({api:vi.fn()}));
vi.mock('./DisplayedEvidence',()=>({displayRecorder:()=>vi.fn(),DisplayTrackingNotice:()=>null,observeChartDisplay:vi.fn(()=>vi.fn())}));
vi.mock('lightweight-charts',()=>({ColorType:{Solid:'solid'},CandlestickSeries:{},LineSeries:{},createSeriesMarkers:vi.fn(),createChart:()=>({addSeries:()=>({setData:vi.fn()}),panes:()=>[{getHTMLElement:()=>document.createElement('div')}],timeScale:()=>({fitContent:vi.fn(),getVisibleLogicalRange:()=>null,setVisibleLogicalRange:vi.fn()}),remove:vi.fn()})}));
const page=(time:number)=>({start:time,end:time+60,range:[0,3600],interval_seconds:60,series:{candles:[{time,open:100,high:102,low:99,close:101}],indicators:[],fills:[],equity:[]},display_reference:{surface:'run_chart',page_id:String(time)}});
beforeEach(()=>vi.clearAllMocks());
it('cancels obsolete report generations and never presents their late success or error',async()=>{
 const pending:any[]=[];vi.mocked(api).mockImplementation((_command,params,options)=>new Promise((resolve,reject)=>pending.push({params,options,resolve,reject})));
 const view=render(<RunChart runId="first" focus={null}/>);await waitFor(()=>expect(pending).toHaveLength(1));
 view.rerender(<RunChart runId="second" focus={null}/>);await waitFor(()=>expect(pending).toHaveLength(2));
 expect(pending[0].options.signal.aborted).toBe(true);expect(pending[1].options.generation).toBeGreaterThan(pending[0].options.generation);
 await act(async()=>pending[0].resolve(page(60)));expect(observeChartDisplay).not.toHaveBeenCalled();
 await act(async()=>pending[1].resolve(page(120)));expect(observeChartDisplay).toHaveBeenCalledTimes(1);
 expect(vi.mocked(observeChartDisplay).mock.calls[0][2]).toEqual(page(120).series.candles);
 view.rerender(<RunChart runId="third" focus={null}/>);await waitFor(()=>expect(pending).toHaveLength(3));
 view.rerender(<RunChart runId="fourth" focus={null}/>);await waitFor(()=>expect(pending).toHaveLength(4));
 await act(async()=>pending[2].reject(new Error('Obsolete checksum failure')));expect(screen.queryByText('Obsolete checksum failure')).toBeNull();
 expect(screen.queryByText(/1970-01-01T00:02/)).toBeNull();
 await act(async()=>pending[3].resolve(page(180)));expect(observeChartDisplay).toHaveBeenCalledTimes(2);
});
it('shows a current integrity failure without treating it as absent history',async()=>{
 vi.mocked(api).mockRejectedValue(new Error('Local trade history checksum mismatch'));
 render(<RunChart runId="run" focus={null}/>);
 expect((await screen.findByRole('alert')).textContent).toContain('checksum mismatch');
 expect(screen.queryByText(/Raw candle history is absent/)).toBeNull();expect(observeChartDisplay).not.toHaveBeenCalled();
});
it('cancels the exact report request, retries with a newer generation and withholds late results',async()=>{
 const pending:any[]=[];
 vi.mocked(api).mockImplementation((command,params:any,options:any)=>{
  if(command==='chart_read_cancel')return Promise.resolve({request_id:params.request_id,status:'cancelled'});
  options.onRequest(String(pending.length+1).repeat(32));
  return new Promise((resolve,reject)=>pending.push({params,options,resolve,reject}));
 });
 const {fireEvent}=await import('@testing-library/react');
 render(<RunChart runId="run" focus={null}/>);
 fireEvent.click(await screen.findByRole('button',{name:'Cancel reading'}));
 expect(await screen.findByText('Reading cancelled. No partial page is displayed.')).toBeTruthy();
 expect(api).toHaveBeenCalledWith('chart_read_cancel',{request_id:'1'.repeat(32)});
 fireEvent.click(screen.getByRole('button',{name:'Retry reading'}));await waitFor(()=>expect(pending).toHaveLength(2));
 expect(pending[1].options.generation).toBeGreaterThan(pending[0].options.generation);
 await act(async()=>pending[0].resolve(page(60)));expect(observeChartDisplay).not.toHaveBeenCalled();
 await act(async()=>pending[1].resolve(page(120)));expect(observeChartDisplay).toHaveBeenCalledTimes(1);
 expect(vi.mocked(observeChartDisplay).mock.calls[0][2]).toEqual(page(120).series.candles);
});
