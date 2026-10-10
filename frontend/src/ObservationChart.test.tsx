import {act,fireEvent,render,screen,within} from '@testing-library/react';
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import ObservationChart from './ObservationChart';
import {displayRecorder,finishDisplayWrites} from './DisplayedEvidence';
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
   logicalToCoordinate:(index:number)=>state.logical?400*(index-state.logical.from+.5)/(state.logical.to-state.logical.from+1):null,
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
const props=()=>({candles:rows,missing,reference,seconds:3600,record:vi.fn()});
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

 it('inspects either pane in UTC, distinguishes zero and clears stale OHLCV on a gap or pointer exit',()=>{
  render(<ObservationChart {...props()}/>);
  act(()=>chart().pointer(1704070800));
  expect(screen.getByText('2024-01-01 01:00:00 UTC')).toBeTruthy();
  expect(field('Open')).toBe('101.25');expect(field('High')).toBe('104.5');expect(field('Low')).toBe('100.75');expect(field('Close')).toBe('102');expect(field('Recorded volume')).toBe('0');
  act(()=>chart().pointer(1704078000,1,true));
  expect(screen.getByText('2024-01-01 03:00:00 UTC')).toBeTruthy();expect(field('Recorded volume')).toBe('11.75');
  act(()=>chart().pointer(1704074400,1));
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
  render(<ObservationChart {...props()} candles={candles} missing={[]} seconds={60}/>);
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
  act(()=>chart().pointer(1704074400));fireEvent.click(screen.getByRole('button',{name:'Next candle'}));expect(field('Open')).toBe('104');
 });

 it('preserves keyboard selection and pending reveal across synthetic redraw callbacks but honors real pointer/gap changes',()=>{
  render(<ObservationChart {...props()}/>);const c=chart();
  act(()=>c.pointer(1704078000));fireEvent.keyDown(surface(),{key:'Home'});expect(field('Open')).toBe('101.25');
  const redraw=()=>c.moveCallbacks.forEach((fn:any)=>fn({time:1704078000,point:{x:200,y:50},seriesData:new Map()}));
  act(redraw);expect(field('Open')).toBe('101.25');
  act(()=>c.pointer(1704074400,1,true));expect(screen.getByText('Missing source slot. No recorded candle, price or volume.')).toBeTruthy();
  act(()=>{c.show(1704078000,1704081600);flush();c.pointer(1704078000);});
  fireEvent.keyDown(surface(),{key:'Home'});expect(screen.getByText('No candle selected')).toBeTruthy();
  act(()=>{redraw();flush();});expect(field('Open')).toBe('101.25');
  act(()=>c.pointer(1704074400));expect(screen.getByText('Missing source slot. No recorded candle, price or volume.')).toBeTruthy();
 });

 it('moves gap bands on fractional logical scrolling even when visible timestamp boundaries do not change',()=>{
  render(<ObservationChart {...props()}/>);act(flush);
  const band=()=>document.querySelectorAll<HTMLElement>('.observation-gap-overlay>span')[1];
  const before=band().style.left;
  act(()=>{chart().logical={from:.25,to:5.25};chart().logicalCallbacks.forEach((fn:any)=>fn(chart().logical));flush();});
  expect(band().style.left).not.toBe(before);
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
  view.rerender(<ObservationChart {...p} candles={[]} missing={[1704067200,1704070800]}/>);
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
  expect(vi.mocked(api).mock.calls).toHaveLength(1);
  expect(api).toHaveBeenLastCalledWith('research_displayed',expect.objectContaining({reference,viewport:[1704070800,1704081600]}));
  act(()=>{chart().pointer(1704070800,0);chart().pointer(1704078000,1);flush();});await finishDisplayWrites();expect(api).toHaveBeenCalledTimes(1);
  act(()=>{chart().show(1704074400,1704074400);flush();});await finishDisplayWrites();expect(api).toHaveBeenCalledTimes(1);
  act(()=>{chart().show(1704074400,1704078000);flush();});await finishDisplayWrites();
  expect(api).toHaveBeenLastCalledWith('research_displayed',expect.objectContaining({viewport:[1704078000,1704078000]}));
  expect(api).toHaveBeenCalledTimes(2);
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
