import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen} from '@testing-library/react';
import MarketChart from './MarketChart';

const mock=vi.hoisted(()=>({api:vi.fn(),chart:null as any,series:[] as any[],range:null as any,rangeChanged:(_r:any)=>{},crosshair:(_r:any)=>{},fits:0,ranges:[] as any[],markers:vi.fn(),markerTargets:[] as any[],price:{mode:0,autoScale:true,scaleMargins:{top:.2,bottom:.1}},removed:0}));
vi.mock('./api',()=>({api:mock.api}));
vi.mock('lightweight-charts',()=>({CandlestickSeries:'candle',LineSeries:'line',HistogramSeries:'histogram',ColorType:{Solid:'solid'},createSeriesMarkers:(series:any)=>{mock.markerTargets.push(series);return {setMarkers:mock.markers,detach:vi.fn()};},createChart:()=>{
 const domain=()=>[...new Set(mock.series.flatMap(s=>s.data.map((row:any)=>row.time)))].sort((a:any,b:any)=>a-b);
 const scale={options:()=>({...mock.price}),applyOptions:(options:any)=>Object.assign(mock.price,options)};
 const timeScale={getVisibleLogicalRange:()=>mock.range,setVisibleLogicalRange:(range:any)=>{mock.range={...range};mock.ranges.push({range:{...range},domain:domain()});mock.rangeChanged(range);},fitContent:()=>{mock.fits++;mock.range={from:0,to:domain().length-1};mock.rangeChanged(mock.range);},subscribeVisibleLogicalRangeChange:(listener:any)=>{mock.rangeChanged=listener;},unsubscribeVisibleLogicalRangeChange:vi.fn()};
 mock.chart={addSeries:(kind:string,options:any)=>{const series:any={kind,options:{...options},data:[] as any[],setData:vi.fn((data:any[])=>{series.data=data;}),update:vi.fn((row:any)=>{const index=series.data.findIndex((c:any)=>c.time===row.time);if(index<0)series.data.push(row);else series.data[index]=row;}),applyOptions:vi.fn((change:any)=>Object.assign(series.options,change)),moveToPane:vi.fn(),priceToCoordinate:(price:number)=>series.data.some((row:any)=>Number.isFinite(row.value??row.close))?320-price:null,coordinateToPrice:(coordinate:number)=>series.data.some((row:any)=>Number.isFinite(row.value??row.close))?320-coordinate:null,createPriceLine:vi.fn((level:any)=>({coordinate:()=>series.options.visible===false?null:series.priceToCoordinate(level.price)})),removePriceLine:vi.fn(),priceScale:()=>scale,attachPrimitive:vi.fn(),detachPrimitive:vi.fn()};mock.series.push(series);return series;},removeSeries:(series:any)=>{mock.series=mock.series.filter(s=>s!==series);},priceScale:()=>scale,timeScale:()=>timeScale,applyOptions:vi.fn(),panes:()=>[],subscribeCrosshairMove:(listener:any)=>{mock.crosshair=listener;},unsubscribeCrosshairMove:vi.fn(),clearCrosshairPosition:vi.fn(()=>mock.crosshair({})),remove:()=>{mock.removed++;}};
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
 vi.useFakeTimers();mock.api.mockReset();mock.series=[];mock.range=null;mock.ranges=[];mock.fits=0;mock.removed=0;mock.markers.mockClear();mock.markerTargets=[];mock.price={mode:0,autoScale:true,scaleMargins:{top:.2,bottom:.1}};
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
 expect(mock.series.filter(s=>s.kind==='line'&&s.options.crosshairMarkerVisible!==false).flatMap(s=>s.data)).toEqual([{time:180180,value:105,observed:180180}]);
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

it('switches mounted price styles without changing raw readouts, zoom, scales, drawings or recorded IR',async()=>{
 indicatorRead=p=>({status:'ready',price_style:p.price_style??'candles',times:[p.end+60],columns:{ema:{value:[102]}},origin:{time:0,generation:3},price_candles:p.price_style==='heikin_ashi'?[{time:p.end+60,open:500,high:510,low:490,close:505}]:[]});
 render(<MarketChart fresh price="108" mark="107" sessionId="session"/>);await flush();
 pan(100,180);const range={...mock.range};
 fireEvent.click(screen.getByText('Chart options'));fireEvent.click(screen.getByRole('button',{name:'Log scale'}));fireEvent.click(screen.getByRole('button',{name:'Auto scale'}));
 fireEvent.change(screen.getByLabelText('Live chart indicator'),{target:{value:'ema'}});
 const recorded=mock.series.find(series=>series.data.some((row:any)=>row.observed===180060));
 expect(recorded).toBeTruthy();
 const candleSeries=mock.series.find(series=>series.kind==='candle');
 candleSeries.setData.mockClear();
 fireEvent.change(screen.getByLabelText('Chart price style'),{target:{value:'heikin_ashi'}});
 expect(candles().every((row:any)=>row.close===undefined)).toBe(true);
 await flush();
 expect(candles().at(-1)).toMatchObject({open:500,close:505});
 expect(candleSeries.setData.mock.calls.flatMap((call:any[])=>call[0]).some((row:any)=>row.close===100)).toBe(false);
 expect(screen.getByLabelText('Chart OHLC and volume').textContent).toContain('C 100');
 expect(screen.getByText(/Heikin Ashi · synthetic prices/)).toBeTruthy();
 expect(candleSeries.applyOptions).toHaveBeenLastCalledWith({lastValueVisible:false,priceLineVisible:false});
 expect(mock.series.some(series=>series.createPriceLine.mock.calls.some((call:any[])=>call[0].title==='Last'&&call[0].price===108))).toBe(true);
 expect(mock.range).toEqual(range);expect(mock.price).toMatchObject({mode:1,autoScale:false});
 expect(recorded.data).toEqual([{time:180060,value:111,observed:180060}]);
 fireEvent.change(screen.getByLabelText('Chart price style'),{target:{value:'line'}});await flush();
 expect(candles().every((row:any)=>row.close===undefined)).toBe(true);
 const line=mock.series.find(series=>series!==recorded&&series.data.some((row:any)=>row.value===100));
 expect(line.data.at(-1)).toEqual({time:3300*60,value:100});expect(mock.markerTargets.at(-1)).toBe(line);
 expect(line.createPriceLine).toHaveBeenCalledWith(expect.objectContaining({title:'Last',price:108}));
 expect(line.createPriceLine).toHaveBeenCalledWith(expect.objectContaining({title:'Mark',price:107}));
 fireEvent.change(screen.getByLabelText('Chart price style'),{target:{value:'candles'}});await flush();
 expect(candles()).toEqual(plotted(3000,300));expect(line.data).toHaveLength(300);expect(line.applyOptions).toHaveBeenLastCalledWith({visible:true,lineVisible:false});expect(mock.markerTargets.at(-1)).toBe(candleSeries);
 expect(mock.range).toEqual(range);expect(mock.fits).toBe(1);expect(mock.removed).toBe(0);
 expect(mock.api.mock.calls.filter(call=>call[0]==='chart_drawing_settings')).toHaveLength(1);
 expect(mock.api.mock.calls.some(call=>call[0]==='chart_drawing_save')).toBe(false);
});

it('keeps HA on the raw timestamp domain during disjoint Return, timeframe changes and failed calculations',async()=>{
 let recent=bars(3000,300);marketRead=p=>ready(p.before==null?recent:bars(p.before/60-600,600));
 indicatorRead=p=>({status:'ready',price_style:'heikin_ashi',times:[p.end+p.minutes*60],columns:{},price_candles:[{time:p.end+p.minutes*60,open:200,high:220,low:180,close:210},{time:9999999,open:1,high:1,low:1,close:1}]});
 render(<MarketChart fresh/>);await flush();
 fireEvent.change(screen.getByLabelText('Chart price style'),{target:{value:'heikin_ashi'}});await flush();
 await older();await older();await older();pan(1719,1799);
 const obsolete=pending();indicatorRead=()=>obsolete.promise;
 await tick();recent=bars(5000,300);goLatest();await flush();
 expect(candles().every((row:any)=>row.time>=5001*60&&row.time<=5300*60)).toBe(true);
 expect(candles().every((row:any)=>row.close===undefined)).toBe(true);
 obsolete.resolve({price_style:'heikin_ashi',price_candles:[{time:60,open:999,high:999,low:999,close:999}]});await flush();
 expect(candles().every((row:any)=>row.close===undefined)).toBe(true);
 expect(mock.ranges.at(-1).domain).not.toContain(60);expect(mock.ranges.at(-1).domain).not.toContain(9999999);
 indicatorRead=()=>{throw new Error('Saved calculation origin is missing');};
 fireEvent.change(screen.getByLabelText('Chart display timeframe'),{target:{value:'60'}});await flush();await tick();
 expect(screen.getAllByRole('alert').some(alert=>alert.textContent?.includes('Saved calculation origin is missing'))).toBe(true);
 expect(candles().every((row:any)=>row.close===undefined)).toBe(true);
 expect(mock.api.mock.calls.filter(call=>call[0]==='chart_indicator_read').at(-1)![1]).toMatchObject({minutes:60,price_style:'heikin_ashi'});
});

it('offers the shared origin action with zero indicators and sends reanchor through the same HA poll',async()=>{
 const original=mock.api.getMockImplementation()!;
 mock.api.mockImplementation((command:string,p:any)=>command==='chart_indicator_settings'?Promise.resolve({...settings,instances:[]}):original(command,p));
 indicatorRead=p=>({status:'ready',price_style:'heikin_ashi',times:[],columns:{},origin:{time:0,generation:p.reanchor?4:3},price_candles:[]});
 render(<MarketChart fresh/>);await flush();
 expect(mock.api.mock.calls.filter(call=>call[0]==='chart_indicator_read')).toHaveLength(0);
 fireEvent.change(screen.getByLabelText('Chart price style'),{target:{value:'heikin_ashi'}});await flush();
 expect(mock.api.mock.calls.filter(call=>call[0]==='chart_indicator_read')).toHaveLength(1);
 fireEvent.click(screen.getByText('Price and indicator calculation details'));
 expect(screen.getByText(/This changes the shared origin/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Recalculate with earlier cached history'}));await tick();
 expect(mock.api.mock.calls.filter(call=>call[0]==='chart_indicator_read').at(-1)![1]).toMatchObject({price_style:'heikin_ashi',reanchor:true});
 expect(screen.getByText(/Origin:/).textContent).toContain('generation 4');
 expect(mock.api.mock.calls.some(call=>call[0]==='chart_indicator_save')).toBe(false);
});

it('discloses new formula seed and units from the actual backend formula_metadata response',async()=>{
 const original=mock.api.getMockImplementation()!;
 mock.api.mockImplementation((command:string,p:any)=>command==='chart_indicator_settings'?Promise.resolve({...settings,instances:[{id:'channel',type:'keltner',params:{period:20,atr_period:10,multiplier:2},color:'#7eabff',visible:true}]}):original(command,p));
 indicatorRead=p=>({status:'ready',times:[p.end+60],columns:{channel:{upper:[105],middle:[100],lower:[95]}},formula_metadata:{channel:{seed:'First-close-seeded EMA; display SMA-seeded Wilder ATR (not graph ATR)',unit:'price',warmup_bars:20}}});
 render(<MarketChart fresh/>);await flush();
 fireEvent.click(screen.getByText('Price and indicator calculation details'));
 expect(screen.getByText(/KELTNER \(20, 10, 2\): First-close-seeded EMA/).textContent).toContain('price');
 expect(screen.getByLabelText('Display indicator values').textContent).toContain('upper 105 · middle 100 · lower 95');
});

it('retains actual-level coordinates and drawable geometry when HA has no first value',async()=>{
 vi.stubGlobal('PointerEvent',MouseEvent);
 const calculation=pending();indicatorRead=()=>calculation.promise;
 render(<MarketChart fresh price="108" mark="107" paper={{position:{entry:103,stop:95,take:115}}}/>);await flush();
 mock.chart.paneSize=()=>({width:600,height:320});
 mock.chart.timeScale().logicalToCoordinate=(n:number)=>n*2;
 mock.chart.timeScale().coordinateToLogical=(n:number)=>n/2;
 await tick(32);
 const raw=mock.series.find(series=>series.kind==='line'&&series.options.crosshairMarkerVisible===false);
 const native=mock.series.find(series=>series.kind==='candle');
 const canvas=screen.getByLabelText('Price chart drawing canvas');
 expect(canvas.querySelector('.drawing-hit-target line')?.getAttribute('y1')).toBe('219');
 const levels=raw.createPriceLine.mock.results.map((result:any)=>result.value);
 expect(levels.map((level:any)=>level.coordinate())).toEqual([217,225,205,212,213]);
 fireEvent.change(screen.getByLabelText('Chart price style'),{target:{value:'heikin_ashi'}});await flush();await tick(32);
 expect(native.priceToCoordinate(101)).toBeNull(); // LWC firstValue requirement.
 expect(native.coordinateToPrice(219)).toBeNull();
 expect(raw.options).toMatchObject({visible:true,lineVisible:false,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});
 expect(raw.data).toHaveLength(300);expect(candles().every((row:any)=>row.close===undefined)).toBe(true);
 expect(canvas.querySelector('.drawing-hit-target line')?.getAttribute('y1')).toBe('219');
 expect(levels.map((level:any)=>level.coordinate())).toEqual([217,225,205,212,213]);
 calculation.reject(new Error('Synthetic calculation failed'));await flush();await tick(32);
 expect(screen.getAllByRole('alert').some(alert=>alert.textContent?.includes('Synthetic calculation failed'))).toBe(true);
 expect(canvas.querySelector('.drawing-hit-target line')?.getAttribute('y1')).toBe('219');
 indicatorRead=()=>({status:'ready',price_style:'heikin_ashi',price_candles:[],times:[],columns:{}});await tick();
 expect(candles().every((row:any)=>row.close===undefined)).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Horizontal line'}));
 fireEvent.pointerDown(canvas,{clientX:50,clientY:200,button:0,pointerId:1});
 fireEvent.pointerUp(canvas,{clientX:50,clientY:200,pointerId:1});await flush();
 expect(doc.drawings.at(-1).anchors[0].price).toBe(120);
 expect(doc.drawings).toHaveLength(2);
 vi.unstubAllGlobals();
});

it('shows UTC VWAP coverage diagnostics and Supertrend direction as a readout only',async()=>{
 const original=mock.api.getMockImplementation()!;
 mock.api.mockImplementation((command:string,p:any)=>command==='chart_indicator_settings'?Promise.resolve({...settings,instances:[{id:'vwap',type:'vwap',params:{mode:0,anchor:0},color:'#7eabff',visible:true},{id:'super',type:'supertrend',params:{period:10,multiplier:3},color:'#7eabff',visible:true}]}):original(command,p));
 indicatorRead=p=>({status:'ready',times:[p.end+60],columns:{vwap:{value:[null]},super:{up:[105],down:[null],direction:[1]}},formula_status:{vwap:{status:'unavailable',reason:'missing_session_start'}}});
 render(<MarketChart fresh/>);await flush();
 expect(screen.getByLabelText('Display indicator values').textContent).toContain('direction Up (+1)');
 fireEvent.click(screen.getByText('Price and indicator calculation details'));
 expect(screen.getByText(/Latest evaluated candle:/).textContent).toContain('exact session-start candle is missing');
 expect(screen.getByText(/readout only; not plotted/)).toBeTruthy();
 expect(screen.getAllByText(/UTC day · midnight reset/).length).toBeGreaterThan(0);
});

it('mounts Ichimoku on raw coordinates, Fits cloud without adding times, Returns raw and clears obsolete windows',async()=>{
 const original=mock.api.getMockImplementation()!;
 mock.api.mockImplementation((command:string,p:any)=>command==='chart_indicator_settings'?Promise.resolve({...settings,instances:[{id:'cloud',type:'ichimoku',params:{conversion:1,base:1,span_b:1,displacement:2},color:'#7eabff',visible:true}]}):original(command,p));
 indicatorRead=p=>{
  const times=bars(p.start/60,(p.end-p.start)/60+1).map(row=>row.time+60),last=times.length-1;
  return {status:'ready',origin:{time:0,generation:3},times,columns:{cloud:{tenkan:times.map(()=>101),kijun:times.map(()=>102)}},projections:{version:1,contract:'ichimoku-raw-ordinal-v1',raw_times:times,horizon:p.end+60,context:{source:p.source??'bybit',market:p.market,symbol:p.symbol,minutes:p.minutes,start:p.start,end:p.end,generation:3,origin:0,settings_revision:p.revision},instances:{cloud:{displacement:2,source_logical:[last-1,last],computed_at:times.slice(-2),segment:[0,0],senkou_a:[104,105],senkou_b:[102,103],chikou:[108,109],senkou_plotted_at:[times.at(-1)!+60,times.at(-1)!+120],chikou_plotted_at:[times[last-3],times[last-2]],senkou_estimated:[true,true]}}}};
 };
 const view=render(<MarketChart fresh/>);await flush();
 const carrier=mock.series.find(series=>series.options.crosshairMarkerVisible===false);
 expect(carrier.attachPrimitive).toHaveBeenCalled();
 const cloud=carrier.attachPrimitive.mock.calls.at(-1)[0];expect(cloud.extent()).toEqual({from:296,to:301});
 const domain=[...new Set(mock.series.flatMap(series=>series.data.map((row:any)=>row.time)))];expect(domain).toHaveLength(300);expect(Math.max(...domain)).toBe(3300*60);
 act(()=>mock.crosshair({logical:301,point:{x:100,y:100}}));
 expect(screen.getByLabelText('Ichimoku projected values').textContent).toContain('estimated date');
 fireEvent.click(screen.getByText('Chart options'));fireEvent.click(screen.getByRole('button',{name:'Fit chart'}));expect(mock.range).toEqual({from:0,to:301});
 pan(310,350);expect(mock.range).toEqual({from:298.5,to:338.5});
 goLatest();expect(mock.range).toEqual({from:261,to:301});
 const pendingRead=pending();indicatorRead=()=>pendingRead.promise;
 marketRead=()=>ready(bars(3001,300));await tick();expect(cloud.extent()).toBeNull();
 view.unmount();expect(carrier.detachPrimitive).toHaveBeenCalled();
});
