import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen} from '@testing-library/react';
import MarketChart from './MarketChart';

const mock=vi.hoisted(()=>({api:vi.fn(),chart:null as any,series:[] as any[],range:null as any,rangeChanged:(_r:any)=>{},crosshair:(_r:any)=>{},fits:0,ranges:[] as any[],markers:vi.fn(),price:{mode:0,autoScale:true,scaleMargins:{top:.2,bottom:.1}},removed:0}));
vi.mock('./api',()=>({api:mock.api}));
vi.mock('lightweight-charts',()=>({CandlestickSeries:'candle',LineSeries:'line',HistogramSeries:'histogram',ColorType:{Solid:'solid'},createSeriesMarkers:()=>({setMarkers:mock.markers}),createChart:()=>{
 const domain=()=>[...new Set(mock.series.flatMap(s=>s.data.map((row:any)=>row.time)))].sort((a:any,b:any)=>a-b);
 const scale={options:()=>({...mock.price}),applyOptions:(options:any)=>Object.assign(mock.price,options)};
 const timeScale={getVisibleLogicalRange:()=>mock.range,setVisibleLogicalRange:(range:any)=>{mock.range={...range};mock.ranges.push({range:{...range},domain:domain()});mock.rangeChanged(range);},fitContent:()=>{mock.fits++;mock.range={from:0,to:domain().length-1};mock.rangeChanged(mock.range);},subscribeVisibleLogicalRangeChange:(listener:any)=>{mock.rangeChanged=listener;},unsubscribeVisibleLogicalRangeChange:vi.fn()};
 mock.chart={addSeries:(kind:string)=>{const series={kind,data:[] as any[],setData:vi.fn((data:any[])=>{series.data=data;}),update:vi.fn((row:any)=>{const index=series.data.findIndex(c=>c.time===row.time);if(index<0)series.data.push(row);else series.data[index]=row;}),applyOptions:vi.fn(),moveToPane:vi.fn(),createPriceLine:vi.fn(),removePriceLine:vi.fn(),priceScale:()=>scale};mock.series.push(series);return series;},removeSeries:(series:any)=>{mock.series=mock.series.filter(s=>s!==series);},priceScale:()=>scale,timeScale:()=>timeScale,applyOptions:vi.fn(),panes:()=>[],subscribeCrosshairMove:(listener:any)=>{mock.crosshair=listener;},unsubscribeCrosshairMove:vi.fn(),clearCrosshairPosition:vi.fn(()=>mock.crosshair({})),remove:()=>{mock.removed++;}};
 return mock.chart;
}}));
const candle=(index:number,close=100)=>({time:index*60,open:100,high:110,low:90,close,volume:1,confirmation:'provider_confirmed'});
const bars=(first:number,count:number)=>Array.from({length:count},(_,index)=>candle(first+index));
const candles=()=>mock.series.find(s=>s.kind==='candle').data;
const plotted=(first:number,count:number)=>bars(first,count).map(row=>({...row,time:row.time+60}));
const ready=(candles:any[])=>({candles,loading:false,page_status:'ready'});
const settings={version:1,revision:7,instances:[{id:'ema',type:'ema',params:{period:20},color:'#7eabff',visible:true}],origins:{}};
const drawing={id:'saved',kind:'horizontal',anchors:[{time:180000,price:101}],color:'#e0b95e',width:2,style:'solid',text:'',visible:true,locked:false,name:'Reference'};
const pending=()=>{let resolve:(value:any)=>void=()=>{},reject:(value:any)=>void=()=>{};const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};
let marketRead:(p:any)=>any,indicatorRead:(p:any)=>any,doc:any;
async function flush(){await act(async()=>{for(let i=0;i<8;i++)await Promise.resolve();});}
async function tick(ms=1000){await act(async()=>{await vi.advanceTimersByTimeAsync(ms);});}
function pan(from:number,to:number){fireEvent.wheel(document.querySelector('.live-chart-canvas')!);act(()=>{mock.range={from,to};mock.rangeChanged(mock.range);});}
function mode(){return screen.getByLabelText('Chart navigation').textContent;}
function goLatest(){fireEvent.click(screen.getByRole('button',{name:/^(Return to latest|Retry return to latest)$/}));}
async function older(){fireEvent.click(screen.getByRole('button',{name:'Older history'}));await tick();}
beforeEach(()=>{
 vi.useFakeTimers();mock.api.mockReset();mock.series=[];mock.range=null;mock.ranges=[];mock.fits=0;mock.removed=0;mock.markers.mockClear();mock.price={mode:0,autoScale:true,scaleMargins:{top:.2,bottom:.1}};
 doc={version:1,revision:4,drawings:[drawing]};marketRead=p=>ready(p.before==null?bars(3000,300):bars(p.before/60-300,300));
 indicatorRead=p=>({status:'ready',times:[p.start+60,p.end+60],columns:{ema:{value:[101,102]}},origin:{time:0,generation:3},directions:[1,1]});
 mock.api.mockImplementation(async(command:string,p:any)=>{
  if(command==='market_chart')return marketRead(p);
  if(command==='chart_indicator_settings')return settings;
  if(command==='chart_indicator_read')return indicatorRead(p);
  if(command==='chart_drawing_settings')return doc;
  if(command==='chart_drawing_save'){doc={...doc,revision:doc.revision+1,drawings:p.drawings};return doc;}
  if(command==='live_chart')return {evaluations:[{time:180060,values:{ema:111}}]};
  throw new Error('Unexpected command: '+command);
 });
});
afterEach(()=>{cleanup();vi.useRealTimers();});

it('returns within the recent buffer at the same 80-bar zoom without reload, fit or scale changes; freshness is separate',async()=>{
 const view=render(<MarketChart fresh/>);await flush();
 expect(mock.fits).toBe(1);pan(100,180);expect(mode()).toContain('Browsing history');
 fireEvent.click(screen.getByText('Chart options'));
 fireEvent.click(screen.getByRole('button',{name:'Log scale'}));fireEvent.click(screen.getByRole('button',{name:'Auto scale'}));
 const reads=mock.api.mock.calls.filter(c=>c[0]==='market_chart').length;
 goLatest();expect(mock.range).toEqual({from:221,to:301});expect(mock.fits).toBe(1);
 expect(mock.price).toMatchObject({mode:1,autoScale:false});expect(mode()).toContain('Following latest');
 expect(mock.api.mock.calls.filter(c=>c[0]==='market_chart')).toHaveLength(reads);
 view.rerender(<MarketChart fresh={false}/>);expect(mode()).toContain('Following latest');expect(screen.getByText(/Market data is paused or stale/)).toBeTruthy();
});

it('follows forming/new candles and the 1800-bar rollover without refitting or changing zoom',async()=>{
 let recent=bars(3000,1800);marketRead=()=>ready(recent);render(<MarketChart fresh/>);await flush();
 pan(1719,1799);goLatest();expect(mock.range).toEqual({from:1721,to:1801});
 recent=[...recent.slice(0,-1),candle(4799,108)];await tick();
 expect(candles().at(-1).close).toBe(108);expect(mock.range).toEqual({from:1721,to:1801});
 recent=[...recent,candle(4800)];await tick();
 expect(candles()).toHaveLength(1800);expect(candles()[0].time).toBe(3002*60);expect(candles().at(-1).time).toBe(4801*60);
 expect(mock.range).toEqual({from:1721,to:1801});expect(mock.fits).toBe(1);expect(mode()).toContain('Following latest');
});

it('moves an 80-bar following range by one for an appended bar and preserves a browsing time anchor at rollover',async()=>{
 let recent=bars(3000,300);marketRead=()=>ready(recent);render(<MarketChart fresh/>);await flush();
 pan(100,180);goLatest();recent=bars(3000,301);await tick();expect(mock.range).toEqual({from:222,to:302});
 pan(100,180);recent=bars(3000,1800);await tick();expect(mode()).toContain('Browsing history');expect(mock.range).toEqual({from:100,to:180});
 recent=bars(3001,1800);await tick();expect(mock.range).toEqual({from:99,to:179});expect(mock.fits).toBe(1);
});

it('keeps oldest history capped, never follows its right edge, then replaces it atomically with a disjoint recent page',async()=>{
 let recent=bars(3000,300);marketRead=p=>ready(p.before==null?recent:bars(p.before/60-600,600));
 render(<MarketChart fresh/>);await flush();
 await older();await older();await older();expect(candles()).toHaveLength(1800);expect(candles()[0].time).toBe(1201*60);expect(candles().at(-1).time).toBe(3000*60);
 pan(1719,1799);expect(mode()).toContain('Browsing history');const old=candles();recent=bars(5000,300);await tick();expect(candles()).toEqual(old);expect(mock.range).toEqual({from:1719,to:1799});
 const returnPage=pending();marketRead=()=>returnPage.promise;goLatest();await flush();
 expect(candles()).toEqual(old);expect(mode()).toContain('Returning to latest');expect(mock.fits).toBe(1);
 returnPage.resolve(ready(recent));await flush();expect(candles()).toEqual(plotted(5000,300));expect(mock.range).toEqual({from:221,to:301});expect(mode()).toContain('Following latest');expect(mock.fits).toBe(1);
 expect(mock.ranges.at(-1).domain[0]).toBe(5001*60);expect(mock.ranges.at(-1).domain.at(-1)).toBe(5300*60);
});

it('keeps a fully evicted older-page viewport populated at the same zoom without following, fitting or resetting price scales',async()=>{
 marketRead=p=>ready(p.before==null?bars(3000,1800):bars(2700,300));
 render(<MarketChart fresh/>);await flush();pan(1699,1799);
 fireEvent.click(screen.getByText('Chart options'));
 fireEvent.click(screen.getByRole('button',{name:'Log scale'}));fireEvent.click(screen.getByRole('button',{name:'Auto scale'}));
 await older();expect(candles()).toEqual(plotted(2700,1800));expect(mock.range).toEqual({from:1699,to:1799});
 expect(mock.ranges.at(-1).domain).toEqual(Array.from({length:1800},(_,i)=>(2701+i)*60));
 expect(mock.api).toHaveBeenCalledWith('market_chart',{market:'spot',symbol:'BTCUSDT',minutes:1,before:3000*60});
 expect(mode()).toContain('Browsing history');expect(mock.fits).toBe(1);expect(mock.price).toMatchObject({mode:1,autoScale:false});
 await tick();expect(mock.range).toEqual({from:1699,to:1799});expect(candles()).toEqual(plotted(2700,1800));
 // An ordinary overlapping recent poll must not apply the older-page fallback.
 pan(1900,2000);await tick();expect(mock.range).toEqual({from:1900,to:2000});
 goLatest();await flush();expect(candles()).toEqual(plotted(3000,1800));expect(mock.range).toEqual({from:1701,to:1801});
 expect(mode()).toContain('Following latest');expect(mock.fits).toBe(1);expect(mock.price).toMatchObject({mode:1,autoScale:false});
});

it.each([[20,100,320,400],[-100,-20,200,280]])('keeps left-edge automatic paging anchored from %s to %s',async(from,to,expectedFrom,expectedTo)=>{
 marketRead=p=>ready(p.before==null?bars(3000,1800):bars(2700,300));
 render(<MarketChart fresh/>);await flush();pan(40,140);pan(from,to);await tick();
 expect(mock.range).toEqual({from:expectedFrom,to:expectedTo});expect(candles()).toEqual(plotted(2700,1800));
 expect(mode()).toContain('Browsing history');expect(mock.fits).toBe(1);
 const reads=mock.api.mock.calls.filter(c=>c[0]==='market_chart'&&c[1].before!=null);
 expect(reads).toHaveLength(1);expect(reads[0][1].before).toBe(3000*60);
 await tick();expect(mock.range).toEqual({from:expectedFrom,to:expectedTo});
 expect(mock.api.mock.calls.filter(c=>c[0]==='market_chart'&&c[1].before!=null)).toHaveLength(1);
});

it('leaves the current range alone for loading, failed and empty older pages',async()=>{
 let page:any={...ready(bars(2700,300)),loading:true,page_status:'loading'};
 marketRead=p=>p.before==null?ready(bars(3000,1800)):page;
 render(<MarketChart fresh/>);await flush();pan(1900,2000);const old=candles(),ranges=mock.ranges.length;
 await older();expect(candles()).toEqual(old);expect(mock.ranges).toHaveLength(ranges);
 page={candles:[],loading:false,page_status:'error',error:'Temporary older failure'};await tick();
 expect(candles()).toEqual(old);expect(mock.range).toEqual({from:1900,to:2000});expect(mock.ranges).toHaveLength(ranges);
 page=ready([]);fireEvent.click(screen.getByRole('button',{name:'Retry older history'}));await tick();
 expect(candles()).toEqual(old);expect(mock.range).toEqual({from:1900,to:2000});expect(mock.ranges).toHaveLength(ranges);
 expect(screen.queryByText(/Available history boundary reached/)).toBeNull();expect(mock.fits).toBe(1);
});

it('preserves history through loading, errors and empty return pages; repeated clicks do not restart a request',async()=>{
 render(<MarketChart fresh/>);await flush();await older();pan(100,180);const old=candles();
 let recent:any={...ready(bars(5000,300)),loading:true,page_status:'loading'};marketRead=()=>recent;
 goLatest();await flush();expect(candles()).toEqual(old);expect(mode()).toContain('Returning to latest');
 const reads=mock.api.mock.calls.length;fireEvent.click(screen.getByRole('button',{name:'Returning to latest…'}));await flush();expect(mock.api.mock.calls.length).toBe(reads);
 recent={candles:[],loading:false,error:'Temporary recent failure',page_status:'error'};await tick();expect(candles()).toEqual(old);expect(screen.getByRole('button',{name:'Retry return to latest'})).toBeTruthy();
 recent=ready([]);goLatest();await flush();expect(candles()).toEqual(old);expect(screen.getByText(/Recent history is empty/)).toBeTruthy();
 recent=ready(bars(5000,300));goLatest();await flush();expect(candles()).toEqual(plotted(5000,300));expect(mock.range).toEqual({from:221,to:301});
 expect(mock.fits).toBe(1);
});

it('ignores a late older page and a late recent return after newer manual navigation',async()=>{
 render(<MarketChart fresh/>);await flush();await older();
 const lateOlder=pending();marketRead=p=>p.before==null?ready(bars(5000,300)):lateOlder.promise;
 fireEvent.click(screen.getByRole('button',{name:'Older history'}));await tick();
 goLatest();await flush();expect(candles()).toEqual(plotted(5000,300));
 lateOlder.resolve(ready(bars(1,300)));await flush();expect(candles()).toEqual(plotted(5000,300));
 marketRead=p=>ready(p.before==null?bars(5000,300):bars(4700,300));await older();const old=candles();
 const lateRecent=pending();marketRead=()=>lateRecent.promise;goLatest();await flush();pan(100,180);
 expect(mode()).toContain('Browsing history');lateRecent.resolve(ready(bars(9000,300)));await flush();expect(candles()).toEqual(old);expect(mock.range).toEqual({from:100,to:180});
});

it.each(['source','market','symbol','timeframe','active'])('cancels a pending return after changing %s',async(change)=>{
 const view=render(<MarketChart fresh/>);await flush();await older();const old=candles();
 const delayed=pending();marketRead=()=>delayed.promise;goLatest();await flush();
 marketRead=()=>ready(bars(9000,300));
 if(change==='timeframe')fireEvent.change(screen.getByLabelText('Chart display timeframe'),{target:{value:'5'}});
 else view.rerender(<MarketChart fresh source={change==='source'?'okx':'bybit'} market={change==='market'?'linear':'spot'} symbol={change==='symbol'?'ETHUSDT':'BTCUSDT'} active={change!=='active'}/>);
 await flush();const expected=change==='active'?old:bars(9000,300).map(row=>({...row,time:row.time+(change==='timeframe'?300:60)}));
 expect(candles()).toEqual(expected);delayed.resolve(ready(bars(1,300)));await flush();expect(candles()).toEqual(expected);expect(mode()).not.toContain('Returning to latest');
 if(change==='active'){const calls=mock.api.mock.calls.length;await tick(2000);expect(mock.api.mock.calls.length).toBe(calls);view.rerender(<MarketChart fresh/>);await flush();expect(candles()).toEqual(old);expect(mode()).toContain('Browsing history');}
});

it('preserves settings drafts, saved drawings, revisions and undo through return; clears old hover and indicator timestamps',async()=>{
 render(<MarketChart fresh sessionId="session"/>);await flush();await older();await tick();
 expect(screen.getByLabelText('Display indicator values').textContent).toContain('102');
 fireEvent.click(screen.getByRole('button',{name:'Settings for 1 EMA'}));fireEvent.change(screen.getByLabelText('1 EMA period'),{target:{value:'30'}});
 fireEvent.change(screen.getByLabelText('Select saved drawing'),{target:{value:'saved'}});
 fireEvent.change(screen.getByLabelText('Drawing name'),{target:{value:'New reference'}});fireEvent.click(screen.getByRole('button',{name:'Rename drawing'}));await flush();
 expect(doc.revision).toBe(5);expect((screen.getByRole('button',{name:'Undo drawing'}) as HTMLButtonElement).disabled).toBe(false);
 fireEvent.change(screen.getByLabelText('Drawing name'),{target:{value:'Unapplied name'}});
 act(()=>mock.crosshair({time:180060}));expect(screen.getByLabelText('Chart OHLC and volume').textContent).toContain('1970-01-03');
 const staleRead=pending();indicatorRead=()=>staleRead.promise;await tick();
 const settingsLoads=mock.api.mock.calls.filter(c=>c[0]==='chart_indicator_settings'||c[0]==='chart_drawing_settings').length;
 marketRead=()=>ready(bars(9000,300));goLatest();await flush();
 expect((screen.getByLabelText('1 EMA period') as HTMLInputElement).value).toBe('30');expect((screen.getByLabelText('Drawing name') as HTMLInputElement).value).toBe('Unapplied name');
 expect(screen.getByLabelText('Display indicator values').textContent).not.toContain('102');expect(mock.chart.clearCrosshairPosition).toHaveBeenCalled();
 expect(screen.getByLabelText('Chart OHLC and volume').textContent).toContain(new Date(9300*60000).toISOString().replace('T',' ').replace('.000Z',' UTC'));
 expect(mock.ranges.at(-1).domain).toEqual(Array.from({length:300},(_,i)=>(9001+i)*60));
 staleRead.resolve({status:'ready',times:[180060],columns:{ema:{value:[999]}}});await flush();expect(screen.getByLabelText('Display indicator values').textContent).not.toContain('999');
 expect(mock.api.mock.calls.filter(c=>c[0]==='chart_indicator_settings'||c[0]==='chart_drawing_settings')).toHaveLength(settingsLoads);
 expect(mock.api.mock.calls.some(c=>c[0]==='chart_indicator_save')).toBe(false);
 fireEvent.click(screen.getByRole('button',{name:'Undo drawing'}));await flush();expect(doc.revision).toBe(6);expect(doc.drawings).toEqual([drawing]);
 expect(mock.api).toHaveBeenLastCalledWith('chart_drawing_save',expect.objectContaining({revision:5,drawings:[drawing]}));
});

it('does not clear accepted indicator values on every ordinary price poll',async()=>{
 render(<MarketChart fresh/>);await flush();await tick();expect(screen.getByLabelText('Display indicator values').textContent).toContain('102');
 const display=mock.series.find(s=>s.kind==='line'&&s.data.some((p:any)=>p.value===102));expect(display).toBeTruthy();display.setData.mockClear();
 indicatorRead=()=>pending().promise;await tick();expect(screen.getByLabelText('Display indicator values').textContent).toContain('102');
 expect(display.setData.mock.calls.length).toBeGreaterThan(0);expect(display.setData.mock.calls.every((c:any[])=>c[0].length>0)).toBe(true);
});


it('keeps recorded IR and marker gap timestamps out of the shared logical domain',async()=>{
 marketRead=()=>ready([candle(3000),candle(3002),candle(3003)]);
 mock.api.mockImplementation(async(command:string,p:any)=>{
  if(command==='market_chart')return marketRead(p);
  if(command==='chart_indicator_settings')return {...settings,instances:[]};
  if(command==='chart_drawing_settings')return doc;
  if(command==='live_chart')return {evaluations:[{time:180120,values:{ema:999}},{time:180180,values:{ema:105}}],signals:[{time:180120,type:'entry_long'}]};
  throw new Error('Unexpected command');
 });
 render(<MarketChart fresh sessionId="gap"/>);await flush();
 fireEvent.change(screen.getByLabelText('Live chart indicator'),{target:{value:'ema'}});
 expect(mock.series.filter(s=>s.kind==='line').flatMap(s=>s.data)).toEqual([{time:180180,value:105,observed:180180}]);
 pan(0,1);goLatest();expect(mock.range).toEqual({from:1.25,to:2.25});
 expect(mock.ranges.at(-1).domain).toEqual([180060,180180,180240]);expect(mock.markers).toHaveBeenLastCalledWith([]);
 await tick();expect(mock.ranges.at(-1).domain).toEqual([180060,180180,180240]);
});

it('treats an explicit Fit during pending Return as newer navigation and keeps the historical view',async()=>{
 render(<MarketChart fresh/>);await flush();await older();const old=candles();
 const delayed=pending();marketRead=()=>delayed.promise;goLatest();await flush();
 fireEvent.click(screen.getByText('Chart options'));
 fireEvent.click(screen.getByRole('button',{name:'Fit chart'}));expect(mock.fits).toBe(2);expect(mode()).toContain('Browsing history');
 delayed.resolve(ready(bars(9000,300)));await flush();expect(candles()).toEqual(old);expect(mock.range).toEqual({from:0,to:599});
});
