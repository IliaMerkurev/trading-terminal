import {displayRecorder,observeChartDisplay} from './DisplayedEvidence';
import {useEffect,useId,useRef,useState} from 'react';
import {createChart,CandlestickSeries,HistogramSeries,ColorType,CrosshairMode,createSeriesMarkers,type MouseEventParams,type UTCTimestamp,type Logical} from 'lightweight-charts';
import type {LiveCandle} from './liveChartData';

type Props={candles:LiveCandle[];missing:number[];reference:any;seconds:number;record:ReturnType<typeof displayRecorder>};
type Direction='previous'|'next'|'first'|'last';
type Inspection={rows:LiveCandle[];time:number}|null;
type GapBands={rows:LiveCandle[];width:number;bottom:number;bands:{time:number;left:number;width:number}[]}|null;
const finite=(value:unknown):value is number=>typeof value==='number'&&Number.isFinite(value);
const valueText=(value:unknown)=>finite(value)?String(value):'N/A';
const utc=(time:number)=>new Date(time*1000).toISOString().replace('T',' ').replace('.000Z',' UTC');
const interval=(seconds:number)=>seconds%86400===0?`${seconds/86400}d`:seconds%3600===0?`${seconds/3600}h`:seconds%60===0?`${seconds/60}m`:`${seconds}s`;

// A new verified reference resets the complete presentation, including selection.
export default function ObservationChart(props:Props){
 return <ObservationChartPage key={JSON.stringify([props.reference,props.seconds])} {...props}/>;
}

function ObservationChartPage({candles,missing,reference,seconds,record}:Props){
 const host=useRef<HTMLDivElement>(null),navigate=useRef<(direction:Direction)=>void>(()=>{}),fit=useRef(()=>{}),helpId=useId();
 const [inspection,setInspection]=useState<Inspection>(null),[gaps,setGaps]=useState<GapBands>(null);
 const selected=inspection?.rows===candles?inspection.time:null;
 const candle=selected===null?undefined:candles.find(c=>c.time===selected);
 const gap=selected!==null&&!candle&&missing.includes(selected);
 useEffect(()=>{
  if(!host.current)return;
  setInspection(null);setGaps(null);
  // Both panes use the original opening timestamps. Whitespace is a source slot,
  // never a synthetic OHLC candle or a zero-volume observation.
  const byTime=new Map(candles.map(c=>[c.time,c])),missingTimes=new Set(missing);
  const slots=[...new Set([...byTime.keys(),...missing])].sort((a,b)=>a-b);
  const chart=createChart(host.current,{height:360,autoSize:true,layout:{background:{type:ColorType.Solid,color:'#111722'},textColor:'#b8c5d9',panes:{separatorColor:'#344154'}},grid:{vertLines:{color:'#1c2532'},horzLines:{color:'#1c2532'}},crosshair:{mode:CrosshairMode.Normal},timeScale:{timeVisible:true,secondsVisible:seconds<60,ignoreWhitespaceIndices:false},localization:{timeFormatter:(time:unknown)=>typeof time==='number'?utc(time):''}});
  const price=chart.addSeries(CandlestickSeries,{upColor:'#42cda8',downColor:'#ed7e86',borderVisible:false,wickUpColor:'#42cda8',wickDownColor:'#ed7e86',lastValueVisible:false,priceLineVisible:false});
  const volume=chart.addSeries(HistogramSeries,{title:'Recorded volume',priceFormat:{type:'volume'},lastValueVisible:false,priceLineVisible:false},1);
  price.setData(slots.map(t=>{const c=byTime.get(t),time=t as UTCTimestamp;return c&&[c.open,c.high,c.low,c.close].every(finite)?{time,open:c.open,high:c.high,low:c.low,close:c.close}:{time};}));
  volume.setData(slots.map(t=>{const c=byTime.get(t),time=t as UTCTimestamp;return c&&finite(c.volume)?{time,value:c.volume,color:c.close>=c.open?'#42cda899':'#ed7e8699'}:{time};}));
  chart.panes()[0].setStretchFactor(3);chart.panes()[1].setStretchFactor(1);
  const marker=createSeriesMarkers(price,[]),scale=chart.timeScale();
  let current:number|null=null,pending:number|null=null,frame=0,disposed=false,keyboardSelected=false;
  const inView=(time:number)=>{const range=scale.getVisibleRange();return !!range&&typeof range.from==='number'&&typeof range.to==='number'&&time>=range.from&&time<=range.to;};
  const select=(time:number|null,keyboard=false)=>{
   if(time===current&&keyboardSelected===(keyboard&&time!==null))return;
   keyboardSelected=keyboard&&time!==null;current=time;setInspection(time===null?null:{rows:candles,time});
   const c=time===null?undefined:byTime.get(time);
   marker.setMarkers(c&&[c.open,c.high,c.low,c.close].every(finite)?[{time:c.time as UTCTimestamp,position:'aboveBar',shape:'circle',color:'#e0b95e',size:1}]:[]);
  };
  const refresh=()=>{
   if(disposed)return;
   if(pending!==null&&inView(pending)){select(pending,true);pending=null;}
   if(current!==null&&!inView(current))select(null);
   const width=scale.width();
   const bands=slots.flatMap((time,index)=>{
    if(!missingTimes.has(time)||byTime.has(time))return [];
    const left=scale.logicalToCoordinate((index-.5) as Logical),right=scale.logicalToCoordinate((index+.5) as Logical);
    return left!==null&&right!==null&&right>0&&left<width?[{time,left:Math.max(0,left),width:Math.max(1,Math.min(width,right)-Math.max(0,left))}]:[];
   });
   setGaps({rows:candles,width,bottom:scale.height(),bands});
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
   if(!candles.length)return;
   const visible=candles.filter(c=>inView(c.time));
   let target:LiveCandle|undefined;
   if(direction==='first')target=candles[0];
   else if(direction==='last')target=candles.at(-1);
   else if(current===null)target=direction==='next'?(visible[0]??candles[0]):(visible.at(-1)??candles.at(-1));
   else target=direction==='next'?candles.find(c=>c.time>current!):[...candles].reverse().find(c=>c.time<current!);
   if(!target)return;
   pending=null;
   if(inView(target.time)){select(target.time,true);return;}
   // Reveal the actual source candle first. The ordinary viewport observer is
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
  // Only original candles are evidence inputs: no whitespace or second volume record.
  const stop=observeChartDisplay(host.current,chart,candles,seconds,false,range=>record(reference,range));
  return()=>{disposed=true;cancelAnimationFrame(frame);navigate.current=()=>{};fit.current=()=>{};stop();scale.unsubscribeVisibleLogicalRangeChange(schedule);scale.unsubscribeSizeChange(schedule);chart.unsubscribeCrosshairMove(pointer);chart.unsubscribeClick(pointer);marker.detach();chart.remove();};
 },[candles,missing,seconds,record]);
 const canPrevious=candles.some(c=>selected===null||c.time<selected),canNext=candles.some(c=>selected===null||c.time>selected);
 return <section className="observation-chart" aria-label="Saved-history candle analysis">
  <div className="observation-chart-toolbar"><strong>Price &amp; recorded volume</strong><span>{interval(seconds)} source candles</span><button disabled={!canPrevious} onClick={()=>navigate.current('previous')}>Previous candle</button><button disabled={!canNext} onClick={()=>navigate.current('next')}>Next candle</button><button onClick={()=>fit.current()}>Fit page</button></div>
  <div className="observation-chart-plot"><div ref={host} role="img" tabIndex={0} aria-label="Prepared local price and volume chart, opening times in UTC" aria-describedby={helpId} aria-keyshortcuts="ArrowLeft ArrowRight Home End" onKeyDown={event=>{const direction=({ArrowLeft:'previous',ArrowRight:'next',Home:'first',End:'last'} as const)[event.key as 'ArrowLeft'];if(direction){event.preventDefault();navigate.current(direction);}}}/>
   {gaps?.rows===candles&&<div className="observation-gap-overlay" aria-hidden="true" style={{width:gaps.width,bottom:gaps.bottom}}>{gaps.bands.map(band=><span key={band.time} style={{left:band.left,width:band.width}}/>)}</div>}
  </div>
  <div className="observation-inspector" role="status" aria-live="polite" aria-atomic="true">
   <div className="observation-inspector-heading"><strong>{selected===null?'No candle selected':utc(selected)}</strong><span>{interval(seconds)} interval · opening time</span></div>
   {gap?<p>Missing source slot. No recorded candle, price or volume.</p>:<dl>{(['open','high','low','close','volume'] as const).map(key=><div key={key}><dt>{key==='volume'?'Recorded volume':key[0].toUpperCase()+key.slice(1)}</dt><dd>{valueText(candle?.[key])}</dd></div>)}</dl>}
  </div>
  <p id={helpId} className="observation-chart-help">Hover or click either pane to inspect. Focus the chart and use ← / → for previous / next recorded candle, Home / End for page boundaries. Selection stays within the visible chart; navigation skips missing slots.</p>
  <p className="observation-chart-help">Volume is in recorded source units; unit unspecified. 0 is recorded zero; N/A is unavailable. {missing.length>0?`${missing.length} missing source slots are blank in both panes and marked with striped bands.`:'No missing source slots in this page.'} No resampling.</p>
 </section>;
}
