import {act,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import ObservationChart from './ObservationChart';
import Observations from './Observations';
import {displayRecorder,finishDisplayWrites,DisplayTrackingNotice} from './DisplayedEvidence';
import {api} from './api';

const charts=vi.hoisted(()=>[] as any[]);
vi.mock('./api',()=>({api:vi.fn()}));
vi.mock('lightweight-charts',()=>({
 CandlestickSeries:'Candlestick',HistogramSeries:'Histogram',ColorType:{Solid:'solid'},CrosshairMode:{Normal:0},
 createSeriesMarkers:(series:any)=>series.marker,
 createChart:vi.fn((host:HTMLElement,options:any)=>{
  const state:any={host,options,times:[],range:null,logical:null,series:[],rangeCallbacks:new Set(),logicalCallbacks:new Set(),sizeCallbacks:new Set(),moveCallbacks:new Set(),clickCallbacks:new Set()};
  const emit=()=>{state.logicalCallbacks.forEach((fn:any)=>fn(state.logical));state.rangeCallbacks.forEach((fn:any)=>fn(state.range));};
  state.show=(from:number,to:number)=>{state.range={from,to};state.logical={from:state.times.indexOf(from),to:state.times.indexOf(to)};emit();};
  state.scale={
   fitContent:vi.fn(()=>{if(state.times.length)state.show(state.times[0],state.times.at(-1));}),
   getVisibleRange:()=>state.range,getVisibleLogicalRange:()=>state.logical,
   setVisibleLogicalRange:vi.fn((range:any)=>{state.logical=range;state.range={from:state.times[Math.max(0,Math.ceil(range.from))],to:state.times[Math.min(state.times.length-1,Math.floor(range.to))]};emit();}),
   logicalToCoordinate:vi.fn((index:number)=>!Number.isInteger(index)?0:state.logical?400*(index-state.logical.from+.5)/(state.logical.to-state.logical.from+1):null),
   width:()=>400,height:()=>24,
   subscribeVisibleTimeRangeChange:vi.fn((fn:any)=>state.rangeCallbacks.add(fn)),unsubscribeVisibleTimeRangeChange:vi.fn((fn:any)=>state.rangeCallbacks.delete(fn)),
   subscribeVisibleLogicalRangeChange:vi.fn((fn:any)=>state.logicalCallbacks.add(fn)),unsubscribeVisibleLogicalRangeChange:vi.fn((fn:any)=>state.logicalCallbacks.delete(fn)),
   subscribeSizeChange:vi.fn((fn:any)=>state.sizeCallbacks.add(fn)),unsubscribeSizeChange:vi.fn((fn:any)=>state.sizeCallbacks.delete(fn)),
  };
  state.paneApis=[{setStretchFactor:vi.fn()},{setStretchFactor:vi.fn()}];
  state.chart={
   timeScale:()=>state.scale,panes:()=>state.paneApis,
   addSeries:vi.fn((kind:string,settings:any,pane=0)=>{
    const s:any={kind,settings,pane,marker:{setMarkers:vi.fn(),detach:vi.fn()}};
    s.setData=vi.fn((rows:any[])=>{s.data=rows;if(kind==='Candlestick')state.times=rows.map(r=>r.time);});state.series.push(s);return s;
   }),
   subscribeCrosshairMove:vi.fn((fn:any)=>state.moveCallbacks.add(fn)),unsubscribeCrosshairMove:vi.fn((fn:any)=>state.moveCallbacks.delete(fn)),
   subscribeClick:vi.fn((fn:any)=>state.clickCallbacks.add(fn)),unsubscribeClick:vi.fn((fn:any)=>state.clickCallbacks.delete(fn)),remove:vi.fn(),
  };
  state.pointer=(time?:number,paneIndex=0,click=false)=>(click?state.clickCallbacks:state.moveCallbacks).forEach((fn:any)=>fn({time,point:time===undefined?undefined:{x:100,y:50},paneIndex,sourceEvent:time===undefined?undefined:{},seriesData:new Map()}));
  charts.push(state);return state.chart;
 }),
}));

let observers:{callback:(entries:any[])=>void;target:HTMLElement|null;disconnect:ReturnType<typeof vi.fn>}[]=[];
let frames=new Map<number,()=>void>(),frameId=0;
const flush=()=>{const work=[...frames.values()];frames.clear();work.forEach(fn=>fn());};
const intersect=(target:HTMLElement,visible=true)=>observers.forEach(o=>{if(o.target===target)o.callback([{target,isIntersecting:visible,intersectionRect:{width:visible?400:0,height:visible?360:0}}]);});
const rows=[
 {time:1704070800,open:101.25,high:104.5,low:100.75,close:102,volume:0},
 {time:1704078000,open:104,high:105.5,low:101,close:102.5,volume:11.75},
 {time:1704081600,open:102.5,high:107,low:101.5,close:106,volume:8.125},
];
const missing=[1704067200,1704074400,1704085200];
const reference={surface:'observation_chart',page_id:'verified-page'};
const props=()=>({candles:rows,missing,reference,seconds:3600,displaySeconds:3600,start:1704067200,end:1704088800,record:vi.fn()});
const chart=()=>charts.at(-1);
const surface=()=>screen.getByRole('img',{name:'Prepared local price and volume chart, opening times in UTC'});
const field=(name:string)=>within(screen.getByRole('status')).getByText(name,{selector:'dt'}).nextElementSibling?.textContent;

beforeEach(()=>{
 charts.length=0;observers=[];frames=new Map();frameId=0;vi.mocked(api).mockReset().mockResolvedValue({recorded:1});
 vi.stubGlobal('IntersectionObserver',class {entry:any;constructor(callback:any){this.entry={callback,target:null,disconnect:vi.fn()};observers.push(this.entry);}observe(target:HTMLElement){this.entry.target=target;}disconnect(){this.entry.disconnect();this.entry.target=null;}});
 vi.stubGlobal('requestAnimationFrame',(fn:()=>void)=>{frames.set(++frameId,fn);return frameId;});vi.stubGlobal('cancelAnimationFrame',(id:number)=>frames.delete(id));
 vi.spyOn(HTMLElement.prototype,'getClientRects').mockReturnValue([{width:400,height:360}] as any);
 vi.spyOn(document,'visibilityState','get').mockReturnValue('visible');
});
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});

describe('bounded saved-history OHLCV chart',()=>{
 it('uses one shared opening-time scale, exact independent values and leading/internal/trailing whitespace',()=>{
  render(<ObservationChart {...props()}/>);const c=chart();
  expect(c.series.map((s:any)=>[s.kind,s.pane])).toEqual([['Candlestick',0],['Histogram',1]]);
  expect(c.series[0].data).toEqual([
   {time:1704067200},{time:1704070800,open:101.25,high:104.5,low:100.75,close:102},
   {time:1704074400},{time:1704078000,open:104,high:105.5,low:101,close:102.5},
   {time:1704081600,open:102.5,high:107,low:101.5,close:106},{time:1704085200},
  ]);
  expect(c.series[1].data).toEqual([
   {time:1704067200},{time:1704070800,value:0,color:'#42cda899'},
   {time:1704074400},{time:1704078000,value:11.75,color:'#ed7e8699'},
   {time:1704081600,value:8.125,color:'#42cda899'},{time:1704085200},
  ]);
  expect(c.paneApis[0].setStretchFactor).toHaveBeenCalledWith(3);expect(c.paneApis[1].setStretchFactor).toHaveBeenCalledWith(1);
  expect(c.options.crosshair.mode).toBe(0);expect(c.options.timeScale.ignoreWhitespaceIndices).toBe(false);
  expect(c.options.localization.timeFormatter(1704070800)).toBe('2024-01-01 01:00:00 UTC');
  expect(screen.getByText(/recorded source units; unit unspecified/)).toBeTruthy();
  expect(screen.getByText(/3 missing source slots/)).toBeTruthy();
  act(flush);expect(document.querySelectorAll('.observation-gap-overlay>span')).toHaveLength(3);
  expect(screen.getByText('No candle selected')).toBeTruthy();
 });

 it('inspects either pane in UTC, distinguishes zero and clears a clicked gap or unpinned pointer exit',()=>{
  render(<ObservationChart {...props()}/>);
  act(()=>chart().pointer(1704070800));
  expect(screen.getByText('2024-01-01 01:00:00 UTC')).toBeTruthy();
  expect(field('Open')).toBe('101.25');expect(field('High')).toBe('104.5');expect(field('Low')).toBe('100.75');expect(field('Close')).toBe('102');expect(field('Recorded volume')).toBe('0');
  act(()=>chart().pointer(1704078000,1,true));
  expect(screen.getByText('2024-01-01 03:00:00 UTC')).toBeTruthy();expect(field('Recorded volume')).toBe('11.75');
  act(()=>chart().pointer(1704074400,1,true));
  expect(screen.getByText('2024-01-01 02:00:00 UTC')).toBeTruthy();expect(screen.getByText('Missing source slot. No recorded candle, price or volume.')).toBeTruthy();
  expect(within(screen.getByRole('status')).queryByText('11.75')).toBeNull();
  expect(chart().series[0].marker.setMarkers).toHaveBeenLastCalledWith([]);
  act(()=>chart().pointer());expect(screen.getByText('No candle selected')).toBeTruthy();expect(field('Recorded volume')).toBe('N/A');
 });

 it('shows unavailable and non-finite values as N/A without zero-filled histogram bars',()=>{
  const candles=[
   {time:60,open:1,high:2,low:.5,close:1.5,volume:NaN},
   {time:120,open:1.5,high:2,low:1,close:1.75,volume:undefined},
   {time:180,open:Infinity,high:NaN,low:null,close:undefined,volume:Infinity},
  ] as any;
  render(<ObservationChart {...props()} candles={candles} missing={[]} seconds={60} displaySeconds={60} start={60} end={240}/>);
  expect(chart().series[1].data).toEqual([{time:60},{time:120},{time:180}]);
  expect(chart().series[0].data[2]).toEqual({time:180});
  act(()=>chart().pointer(60));expect(field('Recorded volume')).toBe('N/A');expect(field('Close')).toBe('1.5');
  act(()=>chart().pointer(120));expect(field('Recorded volume')).toBe('N/A');
  act(()=>chart().pointer(180));['Open','High','Low','Close','Recorded volume'].forEach(name=>expect(field(name)).toBe('N/A'));
 });

 it('offers focusable keyboard navigation through actual candles, skips gaps and stops at boundaries',()=>{
  render(<ObservationChart {...props()}/>);const host=surface();host.focus();expect(document.activeElement).toBe(host);
  expect(host.getAttribute('aria-keyshortcuts')).toBe('ArrowLeft ArrowRight Home End');
  fireEvent.keyDown(host,{key:'ArrowRight'});expect(field('Open')).toBe('101.25');
  expect((screen.getByRole('button',{name:'Previous candle'}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.keyDown(host,{key:'ArrowRight'});expect(field('Open')).toBe('104');
  fireEvent.keyDown(host,{key:'ArrowRight'});expect(field('Close')).toBe('106');
  expect((screen.getByRole('button',{name:'Next candle'}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.keyDown(host,{key:'ArrowRight'});expect(field('Close')).toBe('106');
  fireEvent.keyDown(host,{key:'Home'});expect(field('Open')).toBe('101.25');
  fireEvent.keyDown(host,{key:'End'});expect(field('Close')).toBe('106');
  fireEvent.keyDown(host,{key:'ArrowLeft'});expect(field('Open')).toBe('104');
  fireEvent.mouseMove(document.body);act(()=>chart().pointer());expect(field('Open')).toBe('104');
  expect(chart().scale.setVisibleLogicalRange).not.toHaveBeenCalled();
 });

 it('starts navigation in the actual visible window and reveals an offscreen candle before exposing its inspector',()=>{
  render(<ObservationChart {...props()}/>);act(()=>{chart().show(1704078000,1704081600);flush();});
  fireEvent.click(screen.getByRole('button',{name:'Next candle'}));expect(field('Open')).toBe('104');
  fireEvent.click(screen.getByRole('button',{name:'Previous candle'}));
  expect(chart().scale.setVisibleLogicalRange).toHaveBeenCalledOnce();expect(screen.getByText('No candle selected')).toBeTruthy();
  expect(chart().range).toEqual({from:1704067200,to:1704074400});
  act(flush);expect(field('Open')).toBe('101.25');
  expect(chart().series[0].marker.setMarkers).toHaveBeenLastCalledWith([{time:1704070800,position:'aboveBar',shape:'circle',color:'#e0b95e',size:1}]);
 });

 it('clears an offscreen selection on panning and starts Previous from the last visible candle',()=>{
  render(<ObservationChart {...props()}/>);act(()=>chart().pointer(1704070800));
  act(()=>{chart().show(1704078000,1704081600);flush();});expect(screen.getByText('No candle selected')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Previous candle'}));expect(field('Close')).toBe('106');
  fireEvent.click(screen.getByRole('button',{name:'Fit page'}));expect(chart().scale.fitContent).toHaveBeenCalledTimes(2);
 });

 it('steps from a missing slot to adjacent actual candles without inventing a record',()=>{
  render(<ObservationChart {...props()}/>);act(()=>chart().pointer(1704074400));
  fireEvent.click(screen.getByRole('button',{name:'Previous candle'}));expect(field('Open')).toBe('101.25');
  act(()=>chart().pointer(1704074400,0,true));fireEvent.click(screen.getByRole('button',{name:'Next candle'}));expect(field('Open')).toBe('104');
 });

 it('preserves pinned keyboard selection and pending reveal across hover/redraw but honors explicit gap clicks',()=>{
  render(<ObservationChart {...props()}/>);const c=chart();
  act(()=>c.pointer(1704078000));fireEvent.keyDown(surface(),{key:'Home'});expect(field('Open')).toBe('101.25');
  const redraw=()=>c.moveCallbacks.forEach((fn:any)=>fn({time:1704078000,point:{x:200,y:50},seriesData:new Map()}));
  act(redraw);expect(field('Open')).toBe('101.25');
  act(()=>c.pointer(1704074400,1,true));expect(screen.getByText('Missing source slot. No recorded candle, price or volume.')).toBeTruthy();
  act(()=>{c.show(1704078000,1704081600);flush();c.pointer(1704078000);});
  fireEvent.keyDown(surface(),{key:'Home'});expect(screen.getByText('No candle selected')).toBeTruthy();
  act(()=>{redraw();flush();});expect(field('Open')).toBe('101.25');
  act(()=>c.pointer(1704074400,0,true));expect(screen.getByText('Missing source slot. No recorded candle, price or volume.')).toBeTruthy();
 });

 it('uses integer coordinate centers for gap bands while following fractional scrolling with unchanged timestamp boundaries',()=>{
  render(<ObservationChart {...props()}/>);act(flush);
  const band=()=>document.querySelectorAll<HTMLElement>('.observation-gap-overlay>span')[1];
  const before=band().style.left;
  act(()=>{chart().logical={from:.25,to:5.25};chart().logicalCallbacks.forEach((fn:any)=>fn(chart().logical));flush();});
  expect(band().style.left).not.toBe(before);
  expect(Number.parseFloat(band().style.width)).toBeGreaterThan(0);
  expect(chart().scale.logicalToCoordinate.mock.calls.every(([index]:number[])=>Number.isInteger(index))).toBe(true);
  expect(chart().range).toEqual({from:1704067200,to:1704085200});
 });

 it('resets selection and releases all listeners, observer and markers on source/page replacement and unmount',()=>{
  const p=props(),view=render(<ObservationChart {...p}/>);const first=chart(),stalePointer=[...first.moveCallbacks][0] as any,observer=observers[0];
  act(()=>first.pointer(1704070800));expect(field('Open')).toBe('101.25');
  view.rerender(<ObservationChart {...p} reference={{surface:'observation_chart',page_id:'other-source-page'}}/>);
  expect(charts).toHaveLength(2);expect(screen.getByText('No candle selected')).toBeTruthy();
  expect(first.chart.remove).toHaveBeenCalledOnce();expect(first.series[0].marker.detach).toHaveBeenCalledOnce();expect(observer.disconnect).toHaveBeenCalledOnce();
  expect(first.rangeCallbacks.size).toBe(0);expect(first.logicalCallbacks.size).toBe(0);expect(first.sizeCallbacks.size).toBe(0);expect(first.moveCallbacks.size).toBe(0);expect(first.clickCallbacks.size).toBe(0);
  act(()=>stalePointer({time:1704070800,point:{x:1,y:1}}));expect(screen.getByText('No candle selected')).toBeTruthy();
  const second=chart();view.unmount();expect(second.chart.remove).toHaveBeenCalledOnce();expect(frames.size).toBe(0);
 });

 it('also clears selection when the same page replaces its candle payload',()=>{
  const p=props(),view=render(<ObservationChart {...p}/>);act(()=>chart().pointer(1704070800));
  view.rerender(<ObservationChart {...p} candles={[{time:1704070800,open:501,high:503,low:500,close:502,volume:20}]}/>);
  expect(screen.getByText('No candle selected')).toBeTruthy();expect(field('Open')).toBe('N/A');
  act(()=>chart().pointer(1704070800));expect(field('Open')).toBe('501');
 });

 it('keeps empty and all-missing pages readable with no selectable or fabricated candles',()=>{
  const p=props(),view=render(<ObservationChart {...p} candles={[]} missing={[]}/>);
  expect((screen.getByRole('button',{name:'Next candle'}) as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByRole('button',{name:'Previous candle'}) as HTMLButtonElement).disabled).toBe(true);
  view.rerender(<ObservationChart {...p} candles={[]} missing={[1704067200,1704070800]} end={1704074400}/>);
  expect(chart().series[0].data).toEqual([{time:1704067200},{time:1704070800}]);expect(chart().series[1].data).toEqual([{time:1704067200},{time:1704070800}]);
  act(()=>{chart().pointer(1704067200);intersect(surface());flush();});
  expect(screen.getByText('Missing source slot. No recorded candle, price or volume.')).toBeTruthy();expect(p.record).not.toHaveBeenCalled();
 });
});

describe('original-candle display evidence integration',()=>{
 it('uses one observer and recorder for both panes, excludes leading/trailing and gap-only whitespace, and deduplicates hover',async()=>{
  const record=displayRecorder();render(<ObservationChart {...props()} record={record}/>);
  expect(observers).toHaveLength(1);expect(api).not.toHaveBeenCalled();
  act(()=>{intersect(surface());flush();});await finishDisplayWrites();
  expect(vi.mocked(api).mock.calls.map(([,payload]:any)=>payload.viewport)).toEqual([[1704070800,1704070800],[1704078000,1704081600]]);
  expect(api).toHaveBeenLastCalledWith('research_displayed',expect.objectContaining({reference,viewport:[1704078000,1704081600]}));
  act(()=>{chart().pointer(1704070800,0);chart().pointer(1704078000,1);flush();});await finishDisplayWrites();expect(api).toHaveBeenCalledTimes(2);
  act(()=>{chart().show(1704074400,1704074400);flush();});await finishDisplayWrites();expect(api).toHaveBeenCalledTimes(2);
  act(()=>{chart().show(1704074400,1704078000);flush();});await finishDisplayWrites();
  expect(api).toHaveBeenLastCalledWith('research_displayed',expect.objectContaining({viewport:[1704078000,1704078000]}));
  expect(api).toHaveBeenCalledTimes(3);
 });

 it('records keyboard navigation only through the newly visible actual candle window',async()=>{
  render(<ObservationChart {...props()} record={displayRecorder()}/>);
  act(()=>{chart().show(1704078000,1704081600);intersect(surface());flush();});await finishDisplayWrites();
  expect(api).toHaveBeenLastCalledWith('research_displayed',expect.objectContaining({viewport:[1704078000,1704081600]}));
  fireEvent.keyDown(surface(),{key:'Home'});
  expect(api).toHaveBeenCalledTimes(1);expect(screen.getByText('No candle selected')).toBeTruthy();
  expect(chart().range.from).toBeLessThanOrEqual(1704070800);expect(chart().range.to).toBeGreaterThanOrEqual(1704070800);
  act(flush);await finishDisplayWrites();expect(field('Open')).toBe('101.25');
  expect(api).toHaveBeenLastCalledWith('research_displayed',expect.objectContaining({viewport:[1704070800,1704070800]}));expect(api).toHaveBeenCalledTimes(2);
 });

 it('preserves hidden, background-tab and modal suppression after chart navigation',async()=>{
  const p={...props(),record:displayRecorder()},view=render(<div hidden><ObservationChart {...p}/></div>);
  act(()=>{intersect(chart().host);flush();});expect(api).not.toHaveBeenCalled();
  view.rerender(<div><ObservationChart {...p}/></div>);
  vi.spyOn(document,'visibilityState','get').mockReturnValue('hidden');act(()=>{chart().show(1704070800,1704078000);flush();});expect(api).not.toHaveBeenCalled();
  vi.spyOn(document,'visibilityState','get').mockReturnValue('visible');
  const dialog=document.createElement('dialog');dialog.setAttribute('open','');document.body.append(dialog);
  act(()=>{chart().show(1704078000,1704081600);flush();});expect(api).not.toHaveBeenCalled();
  dialog.remove();act(()=>{chart().show(1704078000,1704081600);flush();});await finishDisplayWrites();expect(api).toHaveBeenCalledTimes(1);
  expect(api).toHaveBeenLastCalledWith('research_displayed',expect.objectContaining({viewport:[1704078000,1704081600]}));
 });
});

const h=3600;
const aggregateRows=Array.from({length:12},(_,i)=>({time:i*h,open:100+i,high:110+i,low:90+i,close:105+i,volume:i+1})).filter(c=>c.time!==6*h);
const aggregateProps=()=>({...props(),candles:aggregateRows,missing:[6*h],start:0,end:12*h,displaySeconds:4*h});

describe('complete UTC display aggregates',()=>{
 it('plots complete price and summed volume on shared openings, explains incomplete coverage and skips it by keyboard',()=>{
  render(<ObservationChart {...aggregateProps()}/>);const c=chart();
  expect(c.series[0].data).toEqual([{time:0,open:100,high:113,low:90,close:108},{time:4*h},{time:8*h,open:108,high:121,low:98,close:116}]);
  expect(c.series[1].data).toEqual([{time:0,value:10,color:'#42cda899'},{time:4*h},{time:8*h,value:42,color:'#42cda899'}]);
  act(()=>c.pointer(0,1));expect(field('Recorded volume')).toBe('10');
  expect(screen.getByText('4h display interval · 1h source interval · opening time')).toBeTruthy();
  expect(screen.getByText('Closes 1970-01-01 04:00:00 UTC (exclusive). Complete source coverage: 4/4.')).toBeTruthy();
  expect(screen.getByText('Contributing source opens: 1970-01-01 00:00:00 UTC to 1970-01-01 03:00:00 UTC.')).toBeTruthy();
  act(()=>{c.pointer(4*h);flush();});
  expect(screen.getByText(/Incomplete UTC bucket: 1 missing source slots in the loaded page; 0 source slots outside/)).toBeTruthy();
  expect(within(screen.getByRole('status')).queryByText('10',{selector:'dd'})).toBeNull();
  expect(document.querySelectorAll('.observation-gap-overlay>span')).toHaveLength(1);
  fireEvent.keyDown(surface(),{key:'ArrowRight'});expect(field('Recorded volume')).toBe('42');
  fireEvent.keyDown(surface(),{key:'ArrowLeft'});expect(field('Recorded volume')).toBe('10');
 });
 it('records exact constituent runs with one observer, final source opens included and hidden partial rows excluded',async()=>{
  render(<ObservationChart {...aggregateProps()} record={displayRecorder()}/>);
  expect(observers).toHaveLength(1);expect(api).not.toHaveBeenCalled();
  act(()=>{intersect(surface());flush();});await finishDisplayWrites();
  expect(vi.mocked(api).mock.calls.map(([,p]:any)=>p.viewport)).toEqual([[0,3*h],[8*h,11*h]]);
  expect(vi.mocked(api).mock.calls.every(([,p]:any)=>p.reference===reference)).toBe(true);
  act(()=>{chart().pointer(0);chart().pointer(8*h,1);chart().show(0,8*h);flush();});await finishDisplayWrites();expect(api).toHaveBeenCalledTimes(2);
  act(()=>{chart().show(4*h,4*h);flush();});await finishDisplayWrites();expect(api).toHaveBeenCalledTimes(2);
  act(()=>{chart().show(8*h,8*h);flush();});await finishDisplayWrites();expect(api).toHaveBeenCalledTimes(2);
 });
 it('reveals the last complete aggregate before inspection and only then records all its underlying source bars',async()=>{
  render(<ObservationChart {...aggregateProps()} record={displayRecorder()}/>);
  act(()=>{chart().show(0,0);intersect(surface());flush();});await finishDisplayWrites();
  expect(api).toHaveBeenCalledTimes(1);expect(api).toHaveBeenLastCalledWith('research_displayed',expect.objectContaining({viewport:[0,3*h]}));
  fireEvent.keyDown(surface(),{key:'End'});expect(screen.getByText('No candle selected')).toBeTruthy();expect(api).toHaveBeenCalledTimes(1);
  act(flush);await finishDisplayWrites();expect(field('Recorded volume')).toBe('42');
  expect(api).toHaveBeenLastCalledWith('research_displayed',expect.objectContaining({viewport:[8*h,11*h]}));
  act(()=>{chart().show(0,0);flush();});expect(screen.getByText('No candle selected')).toBeTruthy();
 });
 it('keeps a compatible incomplete-only page selected, explains outside slots and records nothing',async()=>{
  render(<ObservationChart {...aggregateProps()} start={h} end={3*h} candles={aggregateRows.slice(1,3)} missing={[]} record={displayRecorder()}/>);
  expect(screen.getByText(/No complete 4h candle in this loaded page/)).toBeTruthy();
  expect(chart().series[0].data).toEqual([{time:0}]);expect(chart().series[1].data).toEqual([{time:0}]);
  act(()=>{chart().pointer(0);intersect(surface());flush();});await finishDisplayWrites();expect(api).not.toHaveBeenCalled();
  expect(screen.getByText(/0 missing source slots in the loaded page; 2 source slots outside/)).toBeTruthy();
  const bands=document.querySelectorAll<HTMLElement>('.observation-gap-overlay>span');expect(bands).toHaveLength(1);expect(bands[0].style.width).toBe('400px');
  expect((screen.getByRole('button',{name:'Next candle'}) as HTMLButtonElement).disabled).toBe(true);
 });
 it('disposes projection callbacks and selection on interval switches, restoring exact native values on return',()=>{
  const p=aggregateProps(),view=render(<ObservationChart {...p}/>),first=chart(),stale=[...first.moveCallbacks][0] as any;
  act(()=>first.pointer(0));expect(field('Recorded volume')).toBe('10');
  view.rerender(<ObservationChart {...p} displaySeconds={h}/>);expect(screen.getByText('No candle selected')).toBeTruthy();
  expect(first.chart.remove).toHaveBeenCalledOnce();expect(first.rangeCallbacks.size).toBe(0);expect(first.moveCallbacks.size).toBe(0);
  act(()=>{stale({time:0,point:{x:1,y:1},sourceEvent:{}});chart().pointer(0);});expect(field('Recorded volume')).toBe('1');
  view.rerender(<ObservationChart {...p} displaySeconds={24*h}/>);expect(screen.getByText(/No complete 1d candle/)).toBeTruthy();expect(screen.getByText('No candle selected')).toBeTruthy();
  view.rerender(<ObservationChart {...p}/>);act(()=>chart().pointer(0));expect(field('Recorded volume')).toBe('10');
 });
 it('retains offscreen, hidden ancestor, background document and modal evidence suppression for aggregates',async()=>{
  const p={...aggregateProps(),record:displayRecorder()},view=render(<div hidden><ObservationChart {...p}/></div>);
  act(()=>{intersect(chart().host);flush();});expect(api).not.toHaveBeenCalled();view.rerender(<div><ObservationChart {...p}/></div>);
  act(()=>{intersect(chart().host,false);chart().show(0,8*h);flush();});expect(api).not.toHaveBeenCalled();
  vi.spyOn(document,'visibilityState','get').mockReturnValue('hidden');act(()=>{intersect(chart().host);flush();});expect(api).not.toHaveBeenCalled();
  vi.spyOn(document,'visibilityState','get').mockReturnValue('visible');const modal=document.createElement('dialog');modal.setAttribute('open','');document.body.append(modal);
  act(()=>{chart().show(0,8*h);flush();});expect(api).not.toHaveBeenCalled();modal.remove();
  act(()=>{chart().show(0,8*h);flush();});await finishDisplayWrites();expect(api).toHaveBeenCalledTimes(2);
 });
 it('fails closed visibly on duplicate timestamps without fabricating either pane or recording exposure',()=>{
  render(<ObservationChart {...aggregateProps()} candles={[aggregateRows[0],aggregateRows[0]]}/>);
  expect(screen.getByRole('alert').textContent).toContain('duplicate source opening timestamp');
  expect(chart().series[0].data).toEqual([]);expect(chart().series[1].data).toEqual([]);
  act(()=>{intersect(surface());flush();});expect(api).not.toHaveBeenCalled();
 });
});
it('keeps the existing explicit incomplete-tracking warning when mapped runs reach an already-full pending budget',async()=>{
 const resolves:((v:any)=>void)[]=[];vi.mocked(api).mockImplementation(()=>new Promise(resolve=>resolves.push(resolve)));
 const record=displayRecorder();for(let i=0;i<256;i++)record({surface:'run_metrics',run_id:String(i)},null);
 render(<><ObservationChart {...aggregateProps()} record={record}/><DisplayTrackingNotice/></>);
 act(()=>{intersect(surface());flush();});expect(api).toHaveBeenCalledTimes(256);
 expect(screen.getByRole('alert').textContent).toContain('bounded recording budget was reached');
 expect(screen.getByRole('region',{name:'Saved-history candle analysis'})).toBeTruthy();
 await act(async()=>{resolves.forEach(resolve=>resolve({recorded:1}));await finishDisplayWrites();});
});


it('records only the genuinely visible replacement page after exact navigation and explicit failure recovery',async()=>{
 const hour=3600,source={id:'navigation-evidence',source:'Synthetic',symbol:'BTCUSDT',market:'spot',range:[0,1200*hour],interval_seconds:hour,classification:'synthetic'};
 let reads=0,reject!:(error:Error)=>void;
 const makePage=(p:any)=>({source,start:p.start,end:p.end,candles:Array.from({length:(p.end-p.start)/hour},(_,i)=>p.start+i*hour).filter(t=>t!==4*hour).map(time=>({time,open:100,high:102,low:99,close:101,volume:2})),missing:p.start<=4*hour&&p.end>4*hour?[4*hour]:[],display_reference:{surface:'observation_chart',page_id:String(p.start)}});
 vi.mocked(api).mockImplementation(async(c,p:any)=>{
  if(c==='observation_history')return {rows:[],next:null};
  if(c==='local_history_window'){if(++reads===2)return new Promise((_resolve,no)=>{reject=no;});return makePage(p);}
  if(c==='research_displayed')return {recorded:1};throw Error(`Unexpected command ${c}`);
 });
 const view=render(<Observations datasets={[source]} request={{dataset:source.id,request:1}} onTest={vi.fn()} onBatch={vi.fn()}/>);
 await waitFor(()=>expect(charts).toHaveLength(1));const first=chart();
 act(()=>{first.pointer(0);intersect(surface());});expect(screen.getByText('1970-01-01 00:00:00 UTC')).toBeTruthy();
 fireEvent.change(screen.getByLabelText('Go to UTC date'),{target:{value:'1970-01-01T01:00'}});
 fireEvent.submit(screen.getByLabelText('Go to UTC date').closest('form')!);
 expect(screen.queryByRole('img')).toBeNull();expect(first.chart.remove).toHaveBeenCalledOnce();act(flush);
 expect(vi.mocked(api).mock.calls.filter(([c])=>c==='research_displayed')).toHaveLength(0);
 await act(async()=>reject(Error('Controlled local read failure')));expect(screen.queryByRole('img')).toBeNull();
 fireEvent.change(screen.getByLabelText('Go to UTC date'),{target:{value:'invalid pending text'}});fireEvent.click(screen.getByRole('button',{name:'Retry reading'}));
 await waitFor(()=>expect(charts).toHaveLength(2));expect(screen.getByText('No candle selected')).toBeTruthy();
 fireEvent.change(screen.getByLabelText('Saved-history display interval'),{target:{value:'14400'}});
 act(()=>{intersect(surface());flush();});await finishDisplayWrites();
 const writes=vi.mocked(api).mock.calls.filter(([c])=>c==='research_displayed');
 expect(writes.map(([,p]:any)=>p.viewport)).toEqual([[8*hour,499*hour]]);
 expect(writes[0][1]).toMatchObject({reference:{surface:'observation_chart',page_id:String(hour)}});
 expect((screen.getByLabelText('Go to UTC date') as HTMLInputElement).value).toBe('invalid pending text');
 act(()=>chart().pointer(0));expect(screen.getByText(/0 missing source slots in the loaded page; 1 source slots outside/)).toBeTruthy();
 view.unmount();act(flush);await finishDisplayWrites();expect(vi.mocked(api).mock.calls.filter(([c])=>c==='research_displayed')).toHaveLength(1);
});


describe('explicit chart-to-observation boundaries',()=>{
 const button=(name:string)=>screen.getByRole('button',{name}) as HTMLButtonElement;
 const actions=()=>({boundaryIdentity:'exact-page-source-display',onUseBoundary:vi.fn()});
 it('requires explicit selection, pins both-pane clicks through hover and pointer exit, and applies exact half-open boundaries only on a button',()=>{
  const a=actions();render(<ObservationChart {...props()} {...a}/>);
  act(()=>chart().pointer(1704070800));expect(button('Set observation start').disabled).toBe(true);expect(a.onUseBoundary).not.toHaveBeenCalled();
  act(()=>chart().pointer(1704070800,1,true));
  act(()=>{chart().pointer(1704081600);chart().pointer();});expect(field('Open')).toBe('101.25');
  expect(button('Set observation start').disabled).toBe(false);expect(a.onUseBoundary).not.toHaveBeenCalled();
  fireEvent.click(button('Set observation start'));fireEvent.click(button('Set observation end'));
  expect(a.onUseBoundary.mock.calls.map(([value])=>value)).toEqual([
   {edge:'start',opening:1704070800,closing:1704074400,identity:a.boundaryIdentity},
   {edge:'end',opening:1704070800,closing:1704074400,identity:a.boundaryIdentity},
  ]);
  fireEvent.click(button('Clear candle selection'));expect(button('Set observation start').disabled).toBe(true);
  act(()=>chart().pointer(1704081600));expect(field('Close')).toBe('106');act(()=>chart().pointer());expect(screen.getByText('No candle selected')).toBeTruthy();
 });
 it('supports keyboard selection and button focus without auto-applying, and invalidates pinned actions immediately when panned out of range',()=>{
  const a=actions();render(<ObservationChart {...props()} {...a}/>);
  surface().focus();fireEvent.keyDown(surface(),{key:'ArrowRight'});expect(a.onUseBoundary).not.toHaveBeenCalled();
  const apply=button('Set observation end');apply.focus();expect(document.activeElement).toBe(apply);fireEvent.click(apply);
  expect(a.onUseBoundary).toHaveBeenLastCalledWith({edge:'end',opening:1704070800,closing:1704074400,identity:a.boundaryIdentity});
  act(()=>chart().show(1704078000,1704081600));fireEvent.click(apply);expect(a.onUseBoundary).toHaveBeenCalledOnce();
  act(flush);expect(button('Set observation end').disabled).toBe(true);
 });
 it('uses a complete aggregate exclusive end and rejects clicked gaps and outside-page buckets',()=>{
  const a=actions(),p=aggregateProps(),view=render(<ObservationChart {...p} {...a}/>);
  act(()=>chart().pointer(0,1,true));fireEvent.click(button('Set observation end'));
  expect(a.onUseBoundary).toHaveBeenLastCalledWith({edge:'end',opening:0,closing:4*h,identity:a.boundaryIdentity});
  act(()=>chart().pointer(4*h,0,true));expect(button('Set observation end').disabled).toBe(true);expect(screen.getByText(/Incomplete UTC bucket: 1 missing/)).toBeTruthy();
  view.rerender(<ObservationChart {...p} {...a} start={h} end={3*h} candles={aggregateRows.slice(1,3)} missing={[]}/>);
  act(()=>chart().pointer(0,0,true));expect(button('Set observation start').disabled).toBe(true);expect(a.onUseBoundary).toHaveBeenCalledOnce();
 });
 it('allows valid price with unavailable volume but never pins invalid price',()=>{
  const a=actions(),p=props();render(<ObservationChart {...p} {...a} candles={[{...rows[0],volume:NaN},{...rows[1],open:NaN}]} missing={[]}/>);
  act(()=>chart().pointer(rows[0].time,1,true));expect(button('Set observation start').disabled).toBe(false);expect(field('Recorded volume')).toBe('N/A');
  fireEvent.click(button('Set observation start'));expect(a.onUseBoundary).toHaveBeenCalledOnce();
  act(()=>chart().pointer(rows[1].time,1,true));expect(button('Set observation start').disabled).toBe(true);
 });
 it('resets action selection on display/source/payload replacement and ignores disposed click callbacks',()=>{
  const a=actions(),p=aggregateProps(),view=render(<ObservationChart {...p} {...a}/>);
  act(()=>chart().pointer(0,0,true));const stale=[...chart().clickCallbacks][0] as any;
  view.rerender(<ObservationChart {...p} {...a} displaySeconds={h}/>);
  act(()=>stale({time:0,point:{x:1,y:1},sourceEvent:{}}));expect(button('Set observation start').disabled).toBe(true);
  act(()=>chart().pointer(0,0,true));view.rerender(<ObservationChart {...p} {...a} displaySeconds={h} boundaryIdentity="new-source"/>);
  expect(button('Set observation start').disabled).toBe(true);expect(a.onUseBoundary).not.toHaveBeenCalled();
  act(()=>chart().pointer(0,0,true));view.rerender(<ObservationChart {...p} {...a} displaySeconds={h} boundaryIdentity="new-source" candles={[...aggregateRows]}/>);
  expect(button('Set observation start').disabled).toBe(true);
 });
 it('disables use for saved notes and during actions without recreating the chart or losing inspection',()=>{
  const a=actions(),p=props(),view=render(<ObservationChart {...p} {...a}/>);const first=chart();act(()=>first.pointer(rows[0].time,0,true));
  view.rerender(<ObservationChart {...p} {...a} boundaryDisabledReason="Saved dates are fixed"/>);
  expect(chart()).toBe(first);expect(button('Set observation start').disabled).toBe(true);expect(screen.getByText('Saved dates are fixed')).toBeTruthy();
  fireEvent.click(button('Set observation start'));expect(a.onUseBoundary).not.toHaveBeenCalled();
  view.rerender(<ObservationChart {...p} {...a}/>);expect(button('Set observation start').disabled).toBe(false);
 });
 it('does not create display evidence merely from pinning, setting either endpoint or clearing',async()=>{
  const a=actions();render(<ObservationChart {...props()} {...a} record={displayRecorder()}/>);
  act(()=>{intersect(surface());flush();});await finishDisplayWrites();expect(api).toHaveBeenCalledTimes(2);
  act(()=>chart().pointer(rows[0].time,0,true));fireEvent.click(button('Set observation start'));fireEvent.click(button('Set observation end'));fireEvent.click(button('Clear candle selection'));
  act(flush);await finishDisplayWrites();expect(api).toHaveBeenCalledTimes(2);expect(a.onUseBoundary).toHaveBeenCalledTimes(2);
 });
});
