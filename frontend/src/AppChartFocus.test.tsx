import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen} from '@testing-library/react';
import App from './App';
import {defaultProfile} from './model';
const {readFileSync}=await vi.importActual<{readFileSync(path:string,encoding:'utf8'):string}>('node:fs');
const styles=readFileSync('frontend/src/styles.css','utf8')+readFileSync('frontend/src/market-workspace.css','utf8');
vi.mock('./GraphEditor',()=>({default:()=> <div>Graph workspace</div>}));
vi.mock('./StrategyLibrary',()=>({default:()=> <div>Strategy library content</div>}));
vi.mock('./Experiments',()=>({default:()=> <div>Experiment content</div>}));
vi.mock('./Observations',()=>({default:()=> <div>Saved observation content</div>}));
const mock=vi.hoisted(()=>({api:vi.fn(),chart:null as any,series:[] as any[],range:null as any,rangeChanged:(_r:any)=>{},crosshair:(_r:any)=>{},fits:0,ranges:[] as any[],markers:vi.fn(),price:{mode:0,autoScale:true,scaleMargins:{top:.2,bottom:.1}},removed:0,created:0}));
vi.mock('./api',()=>({api:mock.api,transportCapabilities:()=>({mode:'browser',localService:true,nativeWindow:false,stopService:true}),productVersion:async()=>'0.6.0-dev',stopLocalService:vi.fn(),downloadArchive:vi.fn()}));
vi.mock('lightweight-charts',()=>({CandlestickSeries:'candle',LineSeries:'line',HistogramSeries:'histogram',ColorType:{Solid:'solid'},createSeriesMarkers:()=>({setMarkers:mock.markers}),createChart:()=>{
 mock.created++;
 const domain=()=>[...new Set(mock.series.flatMap(s=>s.data.map((row:any)=>row.time)))].sort((a:any,b:any)=>a-b);
 const scale={options:()=>({...mock.price}),applyOptions:(options:any)=>Object.assign(mock.price,options)};
 const timeScale={logicalToCoordinate:(n:number)=>n*2,coordinateToLogical:(n:number)=>n/2,getVisibleLogicalRange:()=>mock.range,setVisibleLogicalRange:(range:any)=>{mock.range={...range};mock.ranges.push({range:{...range},domain:domain()});mock.rangeChanged(range);},fitContent:()=>{mock.fits++;mock.range={from:0,to:domain().length-1};mock.rangeChanged(mock.range);},subscribeVisibleLogicalRangeChange:(listener:any)=>{mock.rangeChanged=listener;},unsubscribeVisibleLogicalRangeChange:vi.fn()};
 mock.chart={addSeries:(kind:string)=>{const series={kind,data:[] as any[],setData:vi.fn((data:any[])=>{series.data=data;}),update:vi.fn((row:any)=>{const index=series.data.findIndex(c=>c.time===row.time);if(index<0)series.data.push(row);else series.data[index]=row;}),applyOptions:vi.fn(),moveToPane:vi.fn(),createPriceLine:vi.fn(),removePriceLine:vi.fn(),priceToCoordinate:(n:number)=>390-n,coordinateToPrice:(n:number)=>390-n,priceScale:()=>scale};mock.series.push(series);return series;},removeSeries:(series:any)=>{mock.series=mock.series.filter(s=>s!==series);},priceScale:()=>scale,timeScale:()=>timeScale,applyOptions:vi.fn(),paneSize:()=>({width:600,height:390}),panes:()=>[],subscribeCrosshairMove:(listener:any)=>{mock.crosshair=listener;},unsubscribeCrosshairMove:vi.fn(),clearCrosshairPosition:vi.fn(()=>mock.crosshair({})),remove:()=>{mock.removed++;}};
 return mock.chart;
}}));

const settings={version:1,revision:7,instances:[{id:'ema',type:'ema',params:{period:20},color:'#7eabff',visible:true}],origins:{}};
const drawing={id:'saved',kind:'fib',anchors:[{time:60,price:101},{time:180,price:110}],color:'#e0b95e',width:2,style:'solid',text:'',visible:true,locked:false,name:'Reference',levels:[0,.5,1]};
let doc:any,live:any,styleElement:HTMLStyleElement;
async function flush(){await act(async()=>{for(let i=0;i<12;i++)await Promise.resolve();});}
async function tick(ms=1000){await act(async()=>{await vi.advanceTimersByTimeAsync(ms);});}
async function market(){render(<App/>);await flush();fireEvent.click(screen.getByRole('button',{name:'Market'}));await flush();}
const focus=()=>fireEvent.click(screen.getByRole('button',{name:'Focus chart'}));
const exit=()=>fireEvent.click(screen.getByRole('button',{name:'Exit chart focus'}));
const focused=()=>!!document.querySelector('.app.market-chart-focused');
const writes=()=>mock.api.mock.calls.filter(([command])=>/(_save$|_start$|_set$|^start_)/.test(command));
const display=(selector:string)=>getComputedStyle(document.querySelector(selector)!).display;
beforeEach(()=>{
 vi.useFakeTimers();vi.stubGlobal('PointerEvent',MouseEvent);mock.api.mockReset();mock.series=[];mock.range=null;mock.ranges=[];mock.fits=0;mock.created=0;mock.removed=0;mock.price={mode:0,autoScale:true,scaleMargins:{top:.2,bottom:.1}};
 doc={version:1,revision:4,drawings:[structuredClone(drawing)]};
 live={active:false,terminal_state:'RECONNECTING',market:{source:'bybit',symbol:'BTCUSDT',market:'spot',active:true,fresh:false,detail:'Synthetic offline fixture; source waiting',ticker:{lastPrice:'110'}}};
 mock.api.mockImplementation(async(command:string,p:any)=>{
  if(command==='run_history'||command==='library_batch_history')return {rows:[],next:null};
  if(command.startsWith('list_')||command==='library_batches')return [];
  if(command==='platform_capabilities')return {platform:'linux',native_execution:{available:false}};
  if(command==='download_status')return {status:'idle'};
  if(command==='market_preferences')return {source:'bybit'};
  if(command==='live_status')return live;
  if(command==='market_chart')return {candles:Array.from({length:300},(_,i)=>({time:(3000+i)*60,open:100,high:110,low:90,close:100,volume:1,confirmation:'synthetic_closed'})),loading:false,page_status:'ready'};
  if(command==='chart_indicator_settings')return settings;
  if(command==='chart_indicator_read')return {status:'ready',times:[],columns:{},volume_unit:'BTC'};
  if(command==='chart_drawing_settings')return structuredClone(doc);
  if(command==='chart_drawing_save'){doc={...doc,revision:doc.revision+1,drawings:p.drawings};return structuredClone(doc);}
  return {};
 });
 styleElement=document.createElement('style');styleElement.textContent=styles;document.head.append(styleElement);
});
afterEach(()=>{cleanup();styleElement.remove();vi.useRealTimers();});

it('focuses the actual App/Market layout while preserving the mounted chart, range, scale, drafts, selection and undo',async()=>{
 await market();const canvas=document.querySelector('.live-chart-canvas'),chart=mock.chart;
 fireEvent.wheel(canvas!);act(()=>{mock.range={from:100,to:180};mock.rangeChanged(mock.range);});
 fireEvent.click(screen.getByText('Chart options'));
 fireEvent.click(screen.getByRole('button',{name:'Log scale'}));fireEvent.click(screen.getByRole('button',{name:'Auto scale'}));
 fireEvent.click(screen.getByRole('button',{name:'Settings for 1 EMA'}));
 fireEvent.change(screen.getByLabelText('1 EMA period'),{target:{value:'37'}});
 fireEvent.change(screen.getByLabelText('Select saved drawing'),{target:{value:'saved'}});
 fireEvent.change(screen.getByLabelText('Drawing color'),{target:{value:'#123456'}});await flush();
 fireEvent.change(screen.getByLabelText('Drawing name'),{target:{value:'Unsaved name'}});
 fireEvent.change(screen.getByLabelText('Fibonacci levels'),{target:{value:'0, .382, .618, 1'}});
 const beforeDoc=structuredClone(doc),beforeWrites=writes().length,reads=mock.api.mock.calls.length;
 const host=screen.getByLabelText('Live Terminal');let scroll=172;
 // Browser layout can clamp normal scroll as soon as focus chrome disappears.
 Object.defineProperty(host,'scrollTop',{configurable:true,get:()=>focused()?Math.min(scroll,50):scroll,set:(value:number)=>{scroll=value;}});
 focus();expect(focused()).toBe(true);expect(host.scrollTop).toBe(0);
 expect(display('.app>header')).toBe('none');expect(display('nav[aria-label=Workspace]')).toBe('none');expect(display('.market-source-nav')).toBe('none');expect(display('.market-side')).toBe('none');expect(display('.market-advanced')).toBe('none');
 expect(display('.chart-focus-status')).not.toBe('none');expect(screen.getByText(/BTCUSDT · BYBIT · spot · RECONNECTING · stale/)).toBeTruthy();
 expect(screen.getByText(/Synthetic offline fixture; source waiting/)).toBeTruthy();
 expect(document.querySelector('.live-chart-canvas')).toBe(canvas);expect(mock.chart).toBe(chart);expect(mock.created).toBe(1);expect(mock.removed).toBe(0);expect(mock.fits).toBe(1);expect(mock.range).toEqual({from:100,to:180});
 expect(mock.price).toMatchObject({mode:1,autoScale:false});expect(screen.getByLabelText('Chart navigation').textContent).toContain('Browsing history');
 expect((screen.getByRole('button',{name:'Undo drawing'}) as HTMLButtonElement).disabled).toBe(false);
 expect(mock.api.mock.calls).toHaveLength(reads);exit();
 expect(focused()).toBe(false);expect(host.scrollTop).toBe(172);expect(document.activeElement).toBe(screen.getByRole('button',{name:'Focus chart'}));
 expect(display('.app>header')).not.toBe('none');expect(display('.market-side')).not.toBe('none');
 expect((screen.getByLabelText('1 EMA period') as HTMLInputElement).value).toBe('37');
 expect((screen.getByLabelText('Select saved drawing') as HTMLSelectElement).value).toBe('saved');
 expect((screen.getByLabelText('Drawing name') as HTMLInputElement).value).toBe('Unsaved name');expect((screen.getByLabelText('Fibonacci levels') as HTMLInputElement).value).toBe('0, .382, .618, 1');
 expect(doc).toEqual(beforeDoc);expect(writes()).toHaveLength(beforeWrites);expect(mock.created).toBe(1);
 fireEvent.click(screen.getByRole('button',{name:'Undo drawing'}));await flush();expect(doc.drawings[0].color).toBe('#e0b95e');
});

it('gives drawing tool/gesture and properties first Escape while a neutral Escape exits without losing selection drafts',async()=>{
 await market();focus();
 fireEvent.click(screen.getByRole('button',{name:'Trend line'}));const canvas=screen.getByLabelText('Price chart drawing canvas');await tick(20);
 fireEvent.pointerDown(canvas,{clientX:50,clientY:100,button:0,pointerId:1});fireEvent.pointerMove(canvas,{clientX:100,clientY:150,pointerId:1});
 fireEvent.keyDown(canvas,{key:'Escape'});expect(focused()).toBe(true);expect(screen.getByRole('button',{name:'Select / pan'}).getAttribute('aria-pressed')).toBe('true');
 fireEvent.keyDown(canvas,{key:'Escape'});expect(focused()).toBe(true);expect(screen.getByRole('button',{name:'Drawing properties'}).getAttribute('aria-expanded')).toBe('false');
 fireEvent.keyDown(canvas,{key:'Escape'});expect(focused()).toBe(false);expect(writes()).toHaveLength(0);
 focus();fireEvent.change(screen.getByLabelText('Select saved drawing'),{target:{value:'saved'}});fireEvent.change(screen.getByLabelText('Drawing name'),{target:{value:'Retained draft'}});
 fireEvent.keyDown(screen.getByLabelText('Drawing name'),{key:'Escape'});expect(focused()).toBe(true);
 fireEvent.keyDown(canvas,{key:'Escape'});expect(focused()).toBe(true);
 fireEvent.keyDown(canvas,{key:'Escape'});expect(focused()).toBe(false);
 expect((screen.getByLabelText('Select saved drawing') as HTMLSelectElement).value).toBe('saved');
 fireEvent.click(screen.getByRole('button',{name:'Drawing properties'}));expect((screen.getByLabelText('Drawing name') as HTMLInputElement).value).toBe('Retained draft');
});

it('collapses indicator settings on Escape without discarding a draft and protects typing, selects and dialogs',async()=>{
 await market();focus();fireEvent.click(screen.getByRole('button',{name:'Settings for 1 EMA'}));
 fireEvent.change(screen.getByLabelText('1 EMA period'),{target:{value:'29'}});
 fireEvent.keyDown(screen.getByLabelText('1 EMA period'),{key:'Escape'});expect(focused()).toBe(true);expect(screen.getByLabelText('1 EMA period')).toBeTruthy();
 fireEvent.keyDown(screen.getByLabelText('Chart display timeframe'),{key:'Escape'});expect(focused()).toBe(true);
 fireEvent.keyDown(screen.getByLabelText('Chart indicator settings'),{key:'Escape'});expect(focused()).toBe(true);expect(screen.queryByLabelText('1 EMA period')).toBeNull();expect(screen.getByText(/Unapplied edits retained/)).toBeTruthy();
 fireEvent.keyDown(document.activeElement!,{key:'Escape'});expect(focused()).toBe(false);
 fireEvent.click(screen.getByRole('button',{name:'Indicators (1)'}));expect((screen.getByLabelText('1 EMA period') as HTMLInputElement).value).toBe('29');
 focus();const modal=document.createElement('div');modal.setAttribute('role','dialog');document.body.append(modal);fireEvent.keyDown(window,{key:'Escape'});expect(focused()).toBe(true);modal.remove();
 const prevented=new KeyboardEvent('keydown',{key:'Escape',cancelable:true,bubbles:true});prevented.preventDefault();act(()=>{window.dispatchEvent(prevented);});expect(focused()).toBe(true);
 fireEvent.keyDown(window,{key:'Escape',isComposing:true});expect(focused()).toBe(true);
 exit();expect(writes()).toHaveLength(0);
});

it('keeps source/timeframe controls and truthful stale state, then clears focus on hidden Market and Saved history',async()=>{
 await market();focus();fireEvent.change(screen.getByLabelText('Chart display timeframe'),{target:{value:'60'}});await flush();
 expect(focused()).toBe(true);expect(mock.created).toBe(1);
 fireEvent.change(screen.getByLabelText('Market data source'),{target:{value:'okx'}});await flush();
 expect(focused()).toBe(true);expect(mock.created).toBe(2);expect(mock.removed).toBe(1);expect(screen.getByText(/BTCUSDT · OKX · spot · CONNECTING · stale/)).toBeTruthy();
 expect(mock.api).toHaveBeenCalledWith('market_open',{market:'spot',symbol:'BTCUSDT',source:'okx'});
 // Programmatic navigation can happen while focus hides ordinary route chrome.
 fireEvent.click(screen.getByRole('button',{name:'Lab',hidden:true}));await flush();expect(focused()).toBe(false);
 fireEvent.keyDown(window,{key:'Escape'});expect(document.querySelector('.market-host')?.hasAttribute('hidden')).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Market'}));await flush();expect(focused()).toBe(false);expect(mock.created).toBe(2);
 focus();fireEvent.click(screen.getByRole('button',{name:'Saved history · local',hidden:true}));await flush();expect(focused()).toBe(false);expect(screen.queryByRole('button',{name:'Focus chart'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Live market'}));await flush();expect(focused()).toBe(false);expect(mock.created).toBe(2);
});

it('does not treat a focus autoSize callback as another pan, stop following or fetch older history',async()=>{
 await market();const canvas=document.querySelector('.live-chart-canvas')!;
 fireEvent.wheel(canvas);act(()=>{mock.range={from:219,to:301};mock.rangeChanged(mock.range);});
 expect(screen.getByLabelText('Chart navigation').textContent).toContain('Following latest');
 focus();act(()=>{mock.range={from:10,to:301};mock.rangeChanged(mock.range);});await tick();
 expect(screen.getByLabelText('Chart navigation').textContent).toContain('Following latest');
 expect(mock.api.mock.calls.filter(([command,p])=>command==='market_chart'&&p.before!=null)).toHaveLength(0);
 fireEvent.wheel(canvas);act(()=>{mock.range={from:100,to:180};mock.rangeChanged(mock.range);});expect(screen.getByLabelText('Chart navigation').textContent).toContain('Browsing history');
 exit();act(()=>{mock.range={from:0,to:80};mock.rangeChanged(mock.range);});await tick();
 expect(mock.api.mock.calls.filter(([command,p])=>command==='market_chart'&&p.before!=null)).toHaveLength(0);expect(screen.getByLabelText('Chart navigation').textContent).toContain('Browsing history');
});

it('keeps sticky-exit, wrapping and single-scroll CSS contracts in the actual App ancestry',async()=>{
 await market();focus();fireEvent.click(screen.getByRole('button',{name:'Settings for 1 EMA'}));fireEvent.click(screen.getByRole('button',{name:'Drawing properties'}));
 expect(getComputedStyle(screen.getByLabelText('Live Terminal')).overflowY).toBe('auto');
 expect(getComputedStyle(document.querySelector('.market-workspace-heading')!).position).toBe('sticky');
 expect(getComputedStyle(document.querySelector('.market-workspace-heading')!).top).toBe('0px');
 for(const selector of ['.chart-indicator-controls','.drawing-properties']){expect(getComputedStyle(document.querySelector(selector)!).maxHeight).toBe('none');expect(getComputedStyle(document.querySelector(selector)!).overflow).toBe('visible');}
 expect(display('.terminal-market')).toBe('flex');expect(getComputedStyle(document.querySelector('.market-workspace-heading')!).flexWrap).toBe('wrap');
 expect(styles).toContain('.app.market-chart-focused{height:100dvh}');expect(styles).toContain('@media(max-width:480px)');
 expect(document.querySelector('.market-workspace-heading')!.contains(screen.getByRole('button',{name:'Exit chart focus'}))).toBe(true);
});

it('preserves a pending Return across repeated focus changes and applies its successful response only once',async()=>{
 await market();const original=mock.api.getMockImplementation()!;
 mock.api.mockImplementation(async(command:string,p:any)=>command==='market_chart'&&p.before!=null?{candles:Array.from({length:300},(_,i)=>({time:(2700+i)*60,open:100,high:110,low:90,close:100,volume:1,confirmation:'synthetic_closed'})),page_status:'ready',loading:false}:original(command,p));
 fireEvent.click(screen.getByRole('button',{name:'Older history'}));await tick();expect(screen.getByLabelText('Chart navigation').textContent).toContain('Browsing history');
 const before=structuredClone(mock.series.find(s=>s.kind==='candle').data);let resolve:(value:any)=>void=()=>{};
 const pending=new Promise(yes=>{resolve=yes;});mock.api.mockImplementation((command:string,p:any)=>command==='market_chart'?pending:original(command,p));
 fireEvent.click(screen.getByRole('button',{name:'Return to latest'}));await flush();expect(screen.getByRole('button',{name:'Returning to latest…'})).toBeTruthy();
 focus();exit();focus();expect(mock.created).toBe(1);expect(mock.series.find(s=>s.kind==='candle').data).toEqual(before);expect(mock.fits).toBe(1);
 await act(async()=>resolve({candles:Array.from({length:300},(_,i)=>({time:(6000+i)*60,open:100,high:110,low:90,close:100,volume:1,confirmation:'synthetic_closed'})),page_status:'ready',loading:false}));await flush();
 expect(focused()).toBe(true);expect(screen.getByLabelText('Chart navigation').textContent).toContain('Following latest');expect(mock.series.find(s=>s.kind==='candle').data[0].time).toBe(6001*60);expect(mock.created).toBe(1);expect(mock.fits).toBe(1);exit();
});

it('keeps focused transport errors visible and marks retained prices DEGRADED and stale',async()=>{
 await market();live={...live,terminal_state:'CONNECTED',market:{...live.market,fresh:true}};await tick(500);focus();
 expect(screen.getByText(/BTCUSDT · BYBIT · spot · CONNECTED · Live/)).toBeTruthy();
 const original=mock.api.getMockImplementation()!;mock.api.mockImplementation((command:string,p:any)=>{if(command==='live_status')return Promise.reject(new Error('offline'));return original(command,p);});await tick(500);
 expect(focused()).toBe(true);expect(screen.getByText(/BTCUSDT · BYBIT · spot · DEGRADED · stale/)).toBeTruthy();
 const alert=screen.getByText('Live service is unavailable; displayed values are stale.');expect(alert.getAttribute('role')).toBe('alert');expect(display('.terminal-message')).not.toBe('none');
 expect(screen.getByRole('button',{name:'Exit chart focus'})).toBeTruthy();
});

it('keeps focus while an active session freezes a different instrument and labels the new namespace',async()=>{
 await market();focus();live={active:true,terminal_state:'CONNECTED',session:{id:'frozen-session',snapshot:{profile:{...defaultProfile,symbol:'ETHUSDT',market:'linear'},strategy_name:'Fixture strategy'}},options:{paper:false,channels:[],execution_source:'strategy'},market:{source:'bybit',symbol:'ETHUSDT',market:'linear',active:true,fresh:true,ticker:{lastPrice:'123'},detail:'Synthetic session'}};
 await tick(500);expect(focused()).toBe(true);expect(mock.created).toBe(2);expect(mock.removed).toBe(1);
 expect(screen.getByText(/ETHUSDT · BYBIT · linear · CONNECTED · Live/)).toBeTruthy();expect((screen.getByLabelText('Market data source') as HTMLSelectElement).disabled).toBe(true);
 expect(mock.api).toHaveBeenCalledWith('market_open',{market:'linear',symbol:'ETHUSDT'});expect(mock.api).toHaveBeenCalledWith('chart_drawing_settings',{source:'bybit',market:'linear',symbol:'ETHUSDT'});
 exit();expect(focused()).toBe(false);expect(screen.getByText('Explore ETHUSDT · public market data')).toBeTruthy();expect(mock.created).toBe(2);
});

it('keeps toolbar options and the catalog in flow with layered Escape and no price-navigation gesture',async()=>{
 await market();focus();
 const toolbar=screen.getByLabelText('Market chart toolbar');
 expect(toolbar.textContent).toContain('BTCUSDT');expect(toolbar.textContent).toContain('BYBIT · spot');
 expect(toolbar.contains(screen.getByRole('button',{name:'Indicators (1)'}))).toBe(true);
 expect(screen.queryByRole('button',{name:'Fit chart'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Indicators (1)'}));
 expect(document.activeElement).toBe(screen.getByLabelText('Search indicators'));
 fireEvent.change(screen.getByLabelText('1 EMA period'),{target:{value:'33'}});
 const range={...mock.range},fits=mock.fits;
 fireEvent.pointerDown(screen.getByRole('button',{name:'Favorite EMA'}),{button:0,pointerId:1});
 fireEvent.click(screen.getByRole('button',{name:'Favorite EMA'}));
 fireEvent.click(screen.getByText('Chart options'));
 fireEvent.keyDown(screen.getByRole('button',{name:'Fit chart'}),{key:'Escape'});
 expect(screen.queryByRole('button',{name:'Fit chart'})).toBeNull();expect(focused()).toBe(true);
 expect((screen.getByLabelText('1 EMA period') as HTMLInputElement).value).toBe('33');
 fireEvent.keyDown(screen.getByRole('button',{name:'Close indicator settings'}),{key:'Escape'});
 expect(screen.queryByLabelText('1 EMA period')).toBeNull();expect(focused()).toBe(true);
 expect(mock.range).toEqual(range);expect(mock.fits).toBe(fits);expect(writes()).toHaveLength(0);
 expect(document.querySelector('.chart-plot')!.contains(toolbar)).toBe(false);
 fireEvent.keyDown(document.activeElement!,{key:'Escape'});expect(focused()).toBe(false);
});
