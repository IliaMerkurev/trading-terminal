import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import LiveChart from './LiveChart';
const mock=vi.hoisted(()=>({api:vi.fn(),setData:vi.fn(),candles:vi.fn(),remove:vi.fn(),fit:vi.fn(),pane:vi.fn(),range:vi.fn(),visible:vi.fn(()=>null)}));
vi.mock('./api',()=>({api:mock.api}));
vi.mock('lightweight-charts',()=>({CandlestickSeries:'candle',LineSeries:'line',ColorType:{Solid:'solid'},createSeriesMarkers:()=>({setMarkers:vi.fn()}),createChart:()=>({addSeries:(kind:string)=>({setData:(rows:any[])=>{mock.setData(rows);if(kind==='candle')mock.candles(rows);},applyOptions:vi.fn(),moveToPane:mock.pane,createPriceLine:vi.fn(),removePriceLine:vi.fn()}),remove:mock.remove,timeScale:()=>({fitContent:mock.fit,subscribeVisibleLogicalRangeChange:vi.fn(),unsubscribeVisibleLogicalRangeChange:vi.fn(),getVisibleLogicalRange:mock.visible,setVisibleLogicalRange:mock.range})})}));

it('chart interval updates only presentation, maintains recorded values and cleans up',async()=>{
 mock.api.mockResolvedValue({candles:[{time:0,open:100,high:110,low:90,close:105,volume:1}],evaluations:[{time:60,values:{ema:102.5}}],signals:[],fills:[]});
 const {unmount}=render(<LiveChart sessionId="s" fresh/>);
 await waitFor(()=>expect(mock.setData).toHaveBeenCalledWith(expect.arrayContaining([expect.objectContaining({close:105,time:60})])));
 fireEvent.change(screen.getByLabelText('Chart display timeframe'),{target:{value:'60'}});
 fireEvent.change(screen.getByLabelText('Live chart indicator'),{target:{value:'ema'}});
 await waitFor(()=>expect(mock.setData).toHaveBeenCalledWith([{time:3600,value:102.5,observed:60}]));
 expect(mock.api.mock.calls.every(call=>['live_chart','market_chart','chart_indicator_settings','chart_drawing_settings'].includes(call[0]))).toBe(true);
 expect(mock.api).toHaveBeenCalledWith('market_chart',{market:'spot',symbol:'BTCUSDT',minutes:60,before:null});
 unmount();expect(mock.remove).toHaveBeenCalledOnce();
});

it('does not refit on strategy readiness and allocates an indicator pane only when selected',async()=>{
 mock.fit.mockClear();mock.pane.mockClear();
 mock.api.mockResolvedValue({candles:[{time:0,open:100,high:110,low:90,close:105,volume:1}],evaluations:[{time:60,values:{ema:102.5}}]});
 const {rerender}=render(<LiveChart sessionId="recovery" fresh={false}/>);
 await waitFor(()=>expect(mock.fit).toHaveBeenCalledOnce());
 expect(mock.pane).toHaveBeenLastCalledWith(0);
 rerender(<LiveChart sessionId="recovery" fresh/>);
 await waitFor(()=>expect(mock.fit).toHaveBeenCalledTimes(1));
 rerender(<LiveChart sessionId="recovery" fresh price="106"/>);
 expect(mock.fit).toHaveBeenCalledTimes(1);
 fireEvent.change(screen.getByLabelText('Live chart indicator'),{target:{value:'ema'}});
 expect(mock.pane).toHaveBeenLastCalledWith(1);
 fireEvent.change(screen.getByLabelText('Live chart indicator'),{target:{value:''}});
 expect(mock.pane).toHaveBeenLastCalledWith(0);
});

it('loads the market without a strategy and does not reset candles when one is selected',async()=>{
 mock.api.mockClear();mock.fit.mockClear();
 mock.api.mockResolvedValue({candles:[{time:0,open:100,high:110,low:90,close:105,volume:1}],evaluations:[],signals:[],fills:[]});
 const {rerender}=render(<LiveChart fresh market="linear" symbol="BTCUSDT"/>);
 await waitFor(()=>expect(mock.fit).toHaveBeenCalledOnce());
 expect(mock.api).toHaveBeenCalledWith('market_chart',{market:'linear',symbol:'BTCUSDT',minutes:1,before:null});
 expect(mock.api.mock.calls.some(c=>c[0]==='live_chart')).toBe(false);
 rerender(<LiveChart fresh market="linear" symbol="BTCUSDT" sessionId="selected"/>);
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('live_chart',{session_id:'selected'}));
 expect(mock.fit).toHaveBeenCalledOnce();
 expect(mock.api.mock.calls.some(c=>c[0]==='live_start_terminal')).toBe(false);
});

it('requests older history only on demand with the oldest exclusive cursor',async()=>{
 mock.api.mockClear();mock.fit.mockClear();
 mock.api.mockImplementation(async(command:string,params:any)=>({candles:[{time:600,open:100,high:110,low:90,close:105,volume:1}],loading:false,evaluations:[],signals:[],fills:[]}));
 render(<LiveChart fresh/>);
 await waitFor(()=>expect((screen.getByRole('button',{name:'Older history'}) as HTMLButtonElement).disabled).toBe(false));
 expect(mock.api.mock.calls.some(c=>c[1]?.before!=null)).toBe(false);
 fireEvent.click(screen.getByRole('button',{name:'Older history'}));
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('market_chart',{market:'spot',symbol:'BTCUSDT',minutes:1,before:600}),{timeout:2500});
});


it('keeps a failed older page retryable and prepends only a successful page without losing live candles',async()=>{
 mock.api.mockClear();mock.setData.mockClear();mock.candles.mockClear();mock.range.mockClear();mock.fit.mockClear();
 mock.visible.mockReturnValue({from:0,to:1} as any);
 const candle=(time:number)=>({time,open:100,high:110,low:90,close:105,volume:1});
 let olderAttempts=0;
 mock.api.mockImplementation(async(command:string,p:any)=>{
  if(p.before!=null){
   olderAttempts++;
   if(olderAttempts===1)return {candles:[],loading:false,error:'Temporary page failure',page_status:'error',exhausted:false};
   return {candles:[candle(540)],loading:false,page_status:'ready',exhausted:false};
  }
  return {candles:[candle(600),candle(660)],loading:false};
 });
 const {unmount}=render(<LiveChart fresh/>);
 await waitFor(()=>expect(mock.fit).toHaveBeenCalledOnce());
 fireEvent.click(screen.getByRole('button',{name:'Older history'}));
 await waitFor(()=>expect((screen.getByRole('button',{name:'Retry older history'}) as HTMLButtonElement).disabled).toBe(false),{timeout:2500});
 expect(screen.queryByText(/Available history boundary reached/)).toBeNull();
 expect(mock.candles).toHaveBeenLastCalledWith([candle(660),candle(720)]);
 fireEvent.click(screen.getByRole('button',{name:'Retry older history'}));
 await waitFor(()=>expect(mock.candles).toHaveBeenLastCalledWith([candle(600),candle(660),candle(720)]),{timeout:2500});
 expect(mock.range).toHaveBeenLastCalledWith({from:1,to:2});
 expect(mock.fit).toHaveBeenCalledOnce();
 expect((screen.getByRole('button',{name:'Older history'}) as HTMLButtonElement).disabled).toBe(false);
 unmount();mock.visible.mockReturnValue(null);
});

it('retains display interval, candles and viewport across hidden navigation without polling',async()=>{
 mock.api.mockClear();mock.fit.mockClear();mock.candles.mockClear();
 mock.api.mockResolvedValue({candles:[{time:0,open:100,high:110,low:90,close:105,volume:1}],loading:false});
 const {rerender}=render(<LiveChart fresh active/>);
 fireEvent.change(screen.getByLabelText('Chart display timeframe'),{target:{value:'240'}});
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('market_chart',{market:'spot',symbol:'BTCUSDT',minutes:240,before:null}));
 await waitFor(()=>expect(mock.candles).toHaveBeenLastCalledWith([expect.objectContaining({time:14400,close:105})]));
 const fits=mock.fit.mock.calls.length;
 rerender(<LiveChart fresh={false} active={false}/>);
 const count=mock.api.mock.calls.length;
 await new Promise(resolve=>setTimeout(resolve,1100));
 expect(mock.api.mock.calls).toHaveLength(count);
 expect((screen.getByLabelText('Chart display timeframe') as HTMLSelectElement).value).toBe('240');
 expect(mock.candles).toHaveBeenLastCalledWith([expect.objectContaining({time:14400,close:105})]);
 rerender(<LiveChart fresh active/>);
 await waitFor(()=>expect(mock.api.mock.calls.length).toBeGreaterThan(count));
 expect(mock.fit).toHaveBeenCalledTimes(fits);
 expect(mock.api.mock.calls.every(c=>['market_chart','chart_indicator_settings','chart_drawing_settings'].includes(c[0]))).toBe(true);
});

it('drops old-source chart replies and requests separate settings after a source switch',async()=>{
 mock.api.mockClear();mock.candles.mockClear();let finishOld:(v:any)=>void=()=>{};
 const old=new Promise(resolve=>{finishOld=resolve;});
 const candle=(close:number)=>({time:0,open:close,high:close+1,low:close-1,close,volume:1});
 mock.api.mockImplementation((command:string,p:any)=>{
  if(command==='chart_indicator_settings')return Promise.resolve({version:1,revision:0,instances:[],origins:{}});
  if(command==='market_chart')return p.source==='okx'?Promise.resolve({candles:[candle(200)],source:'okx'}):old;
  return Promise.resolve({});
 });
 const {rerender}=render(<LiveChart fresh source="bybit"/>);
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('market_chart',expect.objectContaining({symbol:'BTCUSDT'})));
 rerender(<LiveChart fresh source="okx"/>);
 await waitFor(()=>expect(mock.candles).toHaveBeenLastCalledWith([{...candle(200),time:60}]));
 finishOld({candles:[candle(10)],source:'bybit'});
 await waitFor(()=>expect(mock.candles).toHaveBeenLastCalledWith([{...candle(200),time:60}]));
 expect(mock.api).toHaveBeenCalledWith('chart_indicator_settings',{market:'spot',symbol:'BTCUSDT',source:'okx'});
});

it('integrates indicator management and drawing context before the plot in the production chart',async()=>{
 mock.api.mockImplementation(async(command:string,p:any)=>{
  if(command==='chart_indicator_settings')return {version:1,revision:1,instances:[{id:'ema',type:'ema',params:{period:20},color:'#7eabff',visible:true}],origins:{}};
  if(command==='chart_drawing_settings')return {version:1,revision:1,drawings:[]};
  if(command==='chart_indicator_read')return {status:'ready',times:[],columns:{},volume_unit:'source-native units (unverified)'};
  return {candles:[{time:0,open:100,high:110,low:90,close:105,volume:1}],evaluations:[]};
 });
 const {container}=render(<LiveChart fresh/>);
 const legend=await screen.findByRole('list',{name:'Chart indicator legend'});
 const chart=container.querySelector('.chart-plot')!;
 expect(legend.compareDocumentPosition(chart) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
 expect(legend.closest('.live-chart-toolbar')).toBeNull();
 expect(container.querySelector('.drawing-context')!.compareDocumentPosition(chart) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Settings for 1 EMA'}));
 expect(screen.getByLabelText('1 EMA period')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Cancel edits'}));
 expect(screen.queryByLabelText('1 EMA period')).toBeNull();
});
