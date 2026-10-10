import {displayRecorder,observeDisplay} from './DisplayedEvidence';
import {useEffect,useId,useMemo,useRef,useState} from 'react';
import {createChart,CandlestickSeries,HistogramSeries,ColorType,CrosshairMode,createSeriesMarkers,type MouseEventParams,type UTCTimestamp,type Logical} from 'lightweight-charts';
import type {LiveCandle} from './liveChartData';
import {finite,observationInterval as interval,projectObservation,observationSourceRanges,renderedSlot,validPrice,type ObservationSlot} from './observationChartData';

type Props={candles:LiveCandle[];missing:number[];reference:any;seconds:number;displaySeconds:number;start:number;end:number;record:ReturnType<typeof displayRecorder>};
type Direction='previous'|'next'|'first'|'last';
type Inspection={rows:ObservationSlot[];time:number}|null;
type GapBands={rows:ObservationSlot[];width:number;bottom:number;bands:{time:number;left:number;width:number}[]}|null;
const valueText=(value:unknown)=>finite(value)?String(value):'N/A';
const utc=(time:number)=>new Date(time*1000).toISOString().replace('T',' ').replace('.000Z',' UTC');

// A new verified reference resets the complete presentation, including selection.
export default function ObservationChart(props:Props){
 return <ObservationChartPage key={JSON.stringify([props.reference,props.seconds,props.displaySeconds,props.start,props.end])} {...props}/>;
}

function ObservationChartPage({candles,missing,reference,seconds,displaySeconds,start,end,record}:Props){
 const projection=useMemo(()=>projectObservation({candles,missing,seconds,width:displaySeconds,start,end}),[candles,missing,seconds,displaySeconds,start,end]);
 const displaySlots=projection.slots,aggregate=displaySeconds!==seconds,rendered=displaySlots.filter(renderedSlot);
 const host=useRef<HTMLDivElement>(null),navigate=useRef<(direction:Direction)=>void>(()=>{}),fit=useRef(()=>{}),helpId=useId();
 const [inspection,setInspection]=useState<Inspection>(null),[gaps,setGaps]=useState<GapBands>(null);
 const selected=inspection?.rows===displaySlots?inspection.time:null;
 const selectedSlot=displaySlots.find(slot=>slot.time===selected),candle=selectedSlot?.candle;
 const gap=!!selectedSlot&&!candle;
 useEffect(()=>{
  if(!host.current)return;
  setInspection(null);setGaps(null);
  // Both panes share UTC opening labels and all incomplete bucket whitespace.
  const byTime=new Map(displaySlots.filter(slot=>slot.candle).map(slot=>[slot.time,slot.candle!])),missingTimes=new Set(displaySlots.filter(slot=>!slot.candle).map(slot=>slot.time));
  const slots=displaySlots.map(slot=>slot.time),navigable=displaySlots.filter(slot=>slot.candle&&validPrice(slot.candle)).map(slot=>slot.candle!);
  const chart=createChart(host.current,{height:360,autoSize:true,layout:{background:{type:ColorType.Solid,color:'#111722'},textColor:'#b8c5d9',panes:{separatorColor:'#344154'}},grid:{vertLines:{color:'#1c2532'},horzLines:{color:'#1c2532'}},crosshair:{mode:CrosshairMode.Normal},timeScale:{timeVisible:true,secondsVisible:displaySeconds<60,ignoreWhitespaceIndices:false},localization:{timeFormatter:(time:unknown)=>typeof time==='number'?utc(time):''}});
  const price=chart.addSeries(CandlestickSeries,{upColor:'#42cda8',downColor:'#ed7e86',borderVisible:false,wickUpColor:'#42cda8',wickDownColor:'#ed7e86',lastValueVisible:false,priceLineVisible:false});
  const volume=chart.addSeries(HistogramSeries,{title:'Recorded volume',priceFormat:{type:'volume'},lastValueVisible:false,priceLineVisible:false},1);
  price.setData(slots.map(t=>{const c=byTime.get(t),time=t as UTCTimestamp;return c&&validPrice(c)?{time,open:c.open,high:c.high,low:c.low,close:c.close}:{time};}));
  volume.setData(slots.map(t=>{const c=byTime.get(t),time=t as UTCTimestamp;return c&&finite(c.volume)?{time,value:c.volume,color:!validPrice(c)?'#a1aec299':c.close>=c.open?'#42cda899':'#ed7e8699'}:{time};}));
  chart.panes()[0].setStretchFactor(3);chart.panes()[1].setStretchFactor(1);
  const marker=createSeriesMarkers(price,[]),scale=chart.timeScale();
  let current:number|null=null,pending:number|null=null,frame=0,disposed=false,keyboardSelected=false;
  const inView=(time:number)=>{const range=scale.getVisibleRange();return !!range&&typeof range.from==='number'&&typeof range.to==='number'&&time>=range.from&&time<=range.to;};
  const select=(time:number|null,keyboard=false)=>{
   if(time===current&&keyboardSelected===(keyboard&&time!==null))return;
   keyboardSelected=keyboard&&time!==null;current=time;setInspection(time===null?null:{rows:displaySlots,time});
   const c=time===null?undefined:byTime.get(time);
   marker.setMarkers(c&&validPrice(c)?[{time:c.time as UTCTimestamp,position:'aboveBar',shape:'circle',color:'#e0b95e',size:1}]:[]);
  };
  const refresh=()=>{
   if(disposed)return;
   if(pending!==null&&inView(pending)){select(pending,true);pending=null;}
   if(current!==null&&!inView(current))select(null);
   const width=scale.width();
   const bands=slots.flatMap((time,index)=>{
    if(!missingTimes.has(time)||byTime.has(time))return [];
    // The pinned chart API accepts integer logical indices only. Derive slot
    // edges from adjacent centers; fractional indices collapse to coordinate 0.
    const center=scale.logicalToCoordinate(index as Logical),next=scale.logicalToCoordinate((index+1) as Logical);
    if(center===null||next===null)return [];
    const half=(next-center)/2,left=center-half,right=center+half;
    return right>0&&left<width?[{time,left:Math.max(0,left),width:Math.max(1,Math.min(width,right)-Math.max(0,left))}]:[];
   });
   setGaps({rows:displaySlots,width,bottom:scale.height(),bands});
  };
  const schedule=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(refresh);};
  const pointer=(event:MouseEventParams)=>{
   // Marker/viewport redraws can replay the old crosshair without a pointer event.
   if(disposed||(!event.sourceEvent&&(keyboardSelected||pending!==null)))return;
   pending=null;
   const time=event.point&&typeof event.time==='number'?event.time:null;
   select(time!==null&&(byTime.has(time)||missingTimes.has(time))&&inView(time)?time:null);
  };
  navigate.current=direction=>{
   if(!navigable.length)return;
   const visible=navigable.filter(c=>inView(c.time));
   let target:LiveCandle|undefined;
   if(direction==='first')target=navigable[0];
   else if(direction==='last')target=navigable.at(-1);
   else if(current===null)target=direction==='next'?(visible[0]??navigable[0]):(visible.at(-1)??navigable.at(-1));
   else target=direction==='next'?navigable.find(c=>c.time>current!):[...navigable].reverse().find(c=>c.time<current!);
   if(!target)return;
   pending=null;
   if(inView(target.time)){select(target.time,true);return;}
   // Reveal the actual displayed candle first. The ordinary viewport observer is
   // the only evidence path; an unseen inspector value is never recorded.
   const index=slots.indexOf(target.time),range=scale.getVisibleLogicalRange();
   const span=Math.min(slots.length,Math.max(2,range?range.to-range.from:50));
   const from=Math.max(-.5,Math.min(index-span/2,slots.length-.5-span));
   select(null);pending=target.time;
   scale.setVisibleLogicalRange({from,to:from+span});schedule();
  };
  fit.current=()=>{pending=null;scale.fitContent();schedule();};
  chart.subscribeCrosshairMove(pointer);chart.subscribeClick(pointer);
  scale.subscribeVisibleLogicalRangeChange(schedule);scale.subscribeSizeChange(schedule);
  scale.fitContent();schedule();
  // One actual-visibility observer for both panes. Every displayed aggregate
  // expands to its contributing source opens, excluding suppressed buckets.
  const observer=observeDisplay(host.current,()=>{
   const range=scale.getVisibleRange();if(!range||typeof range.from!=='number'||typeof range.to!=='number')return;
   observationSourceRanges(displaySlots,seconds,{from:range.from,to:range.to}).forEach(run=>record(reference,run));
  });
  scale.subscribeVisibleTimeRangeChange(observer.schedule);
  const stop=()=>{scale.unsubscribeVisibleTimeRangeChange(observer.schedule);observer.dispose();};
  return()=>{disposed=true;cancelAnimationFrame(frame);navigate.current=()=>{};fit.current=()=>{};stop();scale.unsubscribeVisibleLogicalRangeChange(schedule);scale.unsubscribeSizeChange(schedule);chart.unsubscribeCrosshairMove(pointer);chart.unsubscribeClick(pointer);marker.detach();chart.remove();};
 },[displaySlots,seconds,displaySeconds,record]);
 const canPrevious=rendered.some(s=>s.candle&&validPrice(s.candle)&&(selected===null||s.time<selected)),canNext=rendered.some(s=>s.candle&&validPrice(s.candle)&&(selected===null||s.time>selected));
 return <section className="observation-chart" aria-label="Saved-history candle analysis">
  <div className="observation-chart-toolbar"><strong>Price &amp; recorded volume</strong><span>{aggregate?`${interval(displaySeconds)} display · ${interval(seconds)} source`:`${interval(seconds)} source candles`}</span><button disabled={!canPrevious} onClick={()=>navigate.current('previous')}>Previous candle</button><button disabled={!canNext} onClick={()=>navigate.current('next')}>Next candle</button><button onClick={()=>fit.current()}>Fit page</button></div>
  {projection.issue&&<p role="alert" className="observation-chart-help">Display projection unavailable: {projection.issue} No values are fabricated.</p>}
  {!projection.issue&&aggregate&&!rendered.length&&<p className="observation-chart-help">No complete {interval(displaySeconds)} candle in this loaded page. Choose Source to inspect retained source candles, or navigate pages explicitly.</p>}
  <div className="observation-chart-plot"><div ref={host} role="img" tabIndex={0} aria-label="Prepared local price and volume chart, opening times in UTC" aria-describedby={helpId} aria-keyshortcuts="ArrowLeft ArrowRight Home End" onKeyDown={event=>{const direction=({ArrowLeft:'previous',ArrowRight:'next',Home:'first',End:'last'} as const)[event.key as 'ArrowLeft'];if(direction){event.preventDefault();navigate.current(direction);}}}/>
   {gaps?.rows===displaySlots&&<div className="observation-gap-overlay" aria-hidden="true" style={{width:gaps.width,bottom:gaps.bottom}}>{gaps.bands.map(band=><span key={band.time} style={{left:band.left,width:band.width}}/>)}</div>}
  </div>
  <div className="observation-inspector" role="status" aria-live="polite" aria-atomic="true">
   <div className="observation-inspector-heading"><strong>{selected===null?'No candle selected':utc(selected)}</strong><span>{aggregate?`${interval(displaySeconds)} display interval · ${interval(seconds)} source interval`:`${interval(seconds)} interval`} · opening time</span></div>
   {selectedSlot&&<p>Closes {utc(selectedSlot.end)} (exclusive). {selectedSlot.candle?'Complete source coverage':'Source coverage'}: {selectedSlot.sourceTimes.length}/{selectedSlot.expected}.</p>}
   {aggregate&&selectedSlot?.candle&&<p>Contributing source opens: {utc(selectedSlot.sourceTimes[0])} to {utc(selectedSlot.sourceTimes.at(-1)!)}.</p>}
   {gap?(aggregate?<p>Incomplete UTC bucket: {selectedSlot!.missing} missing source slots in the loaded page; {selectedSlot!.outside} source slots outside the loaded page. No partial price or volume is shown.</p>:<p>Missing source slot. No recorded candle, price or volume.</p>):<dl>{(['open','high','low','close','volume'] as const).map(key=><div key={key}><dt>{key==='volume'?'Recorded volume':key[0].toUpperCase()+key.slice(1)}</dt><dd>{valueText(candle?.[key])}</dd></div>)}</dl>}
  </div>
  <p id={helpId} className="observation-chart-help">Hover or click either pane to inspect. Focus the chart and use ← / → for previous / next recorded candle, Home / End for page boundaries. Selection stays within the visible chart; navigation skips incomplete or unavailable candles.</p>
  <p className="observation-chart-help">Volume is in recorded source units; unit unspecified. 0 is recorded zero; N/A is unavailable. {aggregate?'Recorded volumes are summed. Complete UTC buckets only; incomplete buckets are blank in both panes with striped bands. Page-edge buckets are not joined across pages. No additional history is read.':`${displaySlots.reduce((count,slot)=>count+slot.missing,0)} missing source slots are blank in both panes and marked with striped bands. No resampling.`}</p>
 </section>;
}
