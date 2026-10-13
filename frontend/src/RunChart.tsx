import {displayRecorder,observeChartDisplay,DisplayTrackingNotice} from './DisplayedEvidence';
import { useEffect,useRef,useState } from 'react';
import { createChart,CandlestickSeries,LineSeries,createSeriesMarkers,ColorType,type UTCTimestamp,type LogicalRange } from 'lightweight-charts';
import { api } from './api';
import type {TradeFocus} from './TradeReview';

export function chartPoints(data:any,indicator:string){
  const seconds=data.interval_seconds??60;
  return {
    candles:data.series.candles.map((c:any)=>({time:(c.time+seconds) as UTCTimestamp,open:c.open,high:c.high,low:c.low,close:c.close})),
    indicator:data.series.indicators.filter((p:any)=>typeof p.values[indicator]==='number').map((p:any)=>({time:p.time as UTCTimestamp,value:p.values[indicator]})),
    // Multiple engine observations in one source candle use the last recorded equity.
    equity:[...new Map(data.series.equity.map((p:any)=>[Math.ceil(p.time_ns/1e9/seconds)*seconds,{time:(Math.ceil(p.time_ns/1e9/seconds)*seconds) as UTCTimestamp,value:Number(p.equity)}])).values()] as any[],
  };
}
export function fillGroups(fills:any[]){
  const groups=new Map<string,{time:UTCTimestamp;side:string;fills:any[]}>();
  for(const fill of fills){const time=(fill.chart_time??Math.ceil(fill.time_ns/1e9/60)*60) as UTCTimestamp,key=`${time}:${fill.side}`;if(!groups.has(key))groups.set(key,{time,side:fill.side,fills:[]});groups.get(key)!.fills.push(fill);}
  return [...groups.values()].sort((a,b)=>a.time-b.time);
}
export default function RunChart({runId,focus}:{runId:string;focus:TradeFocus|null}){
  const container=useRef<HTMLDivElement>(null),[data,setData]=useState<any>(null),[start,setStart]=useState<number|null>(null),[minutes,setMinutes]=useState(240),[indicator,setIndicator]=useState(''),[error,setError]=useState('');
  const record=useRef<ReturnType<typeof displayRecorder>|null>(null);
  if(!record.current)record.current=displayRecorder();
  const reader=useRef({viewId:crypto.randomUUID().replaceAll('-',''),generation:0});
  const [phase,setPhase]=useState(''),[readNotice,setReadNotice]=useState(''),[retry,setRetry]=useState(0);
  const readControl=useRef<{requestId:string|null;cancelRequested:boolean;settled:boolean;finish:(value:any)=>void}|null>(null);
  const viewport=useRef<{key:string;range:LogicalRange|null}|null>(null);
  const appliedFocus=useRef<number|null>(null);
  useEffect(()=>{setStart(null);setData(null);setIndicator('');},[runId]);
  useEffect(()=>{if(focus!==null){const seconds=focus.clock?.interval_seconds??data?.interval_seconds??60;setStart(Math.floor(focus.time/seconds)*seconds-seconds*30);if(data===null&&!phase)setRetry(value=>value+1);}},[focus]);
  useEffect(()=>{let live=true;const controller=new AbortController();const generation=++reader.current.generation;
    const owns=()=>live&&generation===reader.current.generation;
    const control={requestId:null as string|null,cancelRequested:false,settled:false,finish:(value:any)=>{
      if(!owns()||control.settled)return;
      if(['cancelled','ready','failed','superseded'].includes(value.status)){
        control.settled=true;setPhase('');setError('');
        if(value.status==='failed')setError(value.error??'Could not read saved series.');
        else setReadNotice(value.status==='ready'?'Read completed before cancellation. Retry reading to display it.':'Reading cancelled. No partial page is displayed.');
      }
    }};readControl.current=control;
    setError('');setData(null);setReadNotice('');setPhase('queued');
    api<any>('chart_window',{run_id:runId,start,minutes},{signal:controller.signal,viewId:reader.current.viewId,generation,
      onRequest:id=>{control.requestId=id;},cancelRequested:()=>control.cancelRequested,onPhase:p=>{if(owns()&&!control.settled)setPhase(control.cancelRequested?'cancellation requested':p);}})
      .then(d=>{if(!owns()||control.settled)return;if(control.cancelRequested)control.finish({status:'ready'});else{control.settled=true;setData(d);setPhase('');}})
      .catch(e=>{if(!owns()||control.settled)return;if(e.saveOutcome==='cancelled')control.finish({status:'cancelled'});else if(control.cancelRequested&&e.saveOutcome==='unknown'){setPhase('cancellation requested; outcome unavailable');setError('Could not confirm the read outcome. Inspect this request before retrying.');}else{control.settled=true;setError(e.message);setPhase('');}});
    return()=>{live=false;controller.abort();};},[runId,start,minutes,retry]);
  async function cancelReading(inspect=false){
    const control=readControl.current;if(!control?.requestId||control.settled||!inspect&&control.cancelRequested)return;
    if(!inspect)control.cancelRequested=true;
    setPhase(control.cancelRequested?'cancellation requested':'checking request');
    try{
      let result:any=await api(inspect?'chart_read_status':'chart_read_cancel',{request_id:control.requestId});
      if(readControl.current!==control||control.settled)return;
      if(inspect&&control.cancelRequested&&!['ready','cancelled','failed','superseded'].includes(result.status))result=await api('chart_read_cancel',{request_id:control.requestId});
      control.finish(result);
    }
    catch{if(readControl.current===control&&!control.settled)setError('Cancellation is not confirmed yet; checking the current request.');}
  }

  const available:string[]=data?[...new Set<string>(data.series.indicators.flatMap((p:any)=>Object.keys(p.values).filter(k=>typeof p.values[k]==='number')))]:[];
  useEffect(()=>{
    if(!container.current||!data)return;
    const chart=createChart(container.current,{autoSize:true,height:430,handleScale:{mouseWheel:false},handleScroll:{mouseWheel:false},layout:{background:{type:ColorType.Solid,color:'#111720'},textColor:'#a5b3c9',attributionLogo:true},grid:{vertLines:{color:'#1c2532'},horzLines:{color:'#1c2532'}},timeScale:{timeVisible:true,secondsVisible:false},rightPriceScale:{borderColor:'#2b374b'}});
    const points=chartPoints(data,indicator);
    const candles=chart.addSeries(CandlestickSeries,{upColor:'#42cda8',downColor:'#ed7e86',borderVisible:false,wickUpColor:'#42cda8',wickDownColor:'#ed7e86'});
    candles.setData(points.candles);
    if(indicator){const line=chart.addSeries(LineSeries,{color:'#e0b95e',lineWidth:2,title:indicator},1);line.setData(points.indicator);}
    const equity=chart.addSeries(LineSeries,{color:'#7eabff',lineWidth:2,title:'Equity (USDT)'},indicator?2:1);equity.setData(points.equity);
    const markers=fillGroups(data.series.fills).map(g=>({time:g.time,position:g.side==='buy'?'belowBar' as const:'aboveBar' as const,color:g.side==='buy'?'#42cda8':'#ed7e86',shape:g.side==='buy'?'arrowUp' as const:'arrowDown' as const,text:`${g.fills.length>1?String(g.fills.length):''}${focus?.clock?.source_close===g.time?' · selected candle':''}`}));
    if(points.candles.length)createSeriesMarkers(candles,markers);
    const key=`${runId}:${data.start}:${data.end}`;
    const explicitFocus=focus!==null&&appliedFocus.current!==focus.request;
    if(!explicitFocus&&viewport.current?.key===key&&viewport.current.range)chart.timeScale().setVisibleLogicalRange(viewport.current.range);else chart.timeScale().fitContent();
    if(focus)appliedFocus.current=focus.request;
    const stop=observeChartDisplay(chart.panes()[0].getHTMLElement()??container.current,chart,data.series.candles,data.interval_seconds??60,true,range=>record.current!(data.display_reference,range));
    return()=>{stop();viewport.current={key,range:chart.timeScale().getVisibleLogicalRange()};chart.remove();};
  },[data,indicator,focus]);
  const target=focus?.clock;
  const targetInWindow=!!(target&&data&&data.start<=target.source_open&&target.source_open<data.end);
  const targetCandle=targetInWindow&&data.series.candles.some((c:any)=>c.time===target!.source_open);
  // Context only: never use a later availability time or claim this row caused a fill.
  const recorded=targetInWindow?data.series.indicators.filter((row:any)=>Number.isSafeInteger(row.time)&&row.time<=target!.available_through).at(-1):null;
  return <div className="run-chart"><DisplayTrackingNotice/><div className="chart-toolbar"><strong>Recorded candles & indicators</strong><select aria-label="Chart indicator" value={indicator} onChange={e=>setIndicator(e.target.value)}><option value="">Select recorded indicator</option>{available.map(k=><option key={k}>{k}</option>)}</select><select aria-label="Chart window" value={minutes} onChange={e=>setMinutes(Number(e.target.value))}>{[60,240,480].map(n=><option key={n} value={n}>{n} candles</option>)}</select></div>{phase&&<div><p role="status">Reading verified saved series · {phase}</p><button disabled={!readControl.current?.requestId||readControl.current.cancelRequested} onClick={()=>cancelReading()}>{readControl.current?.cancelRequested?'Cancellation requested':'Cancel reading'}</button>{readControl.current?.cancelRequested&&<button onClick={()=>cancelReading(true)}>Inspect reading</button>}</div>}{readNotice&&<p role="status">{readNotice}</p>}{!phase&&(error||readNotice)&&<button onClick={()=>setRetry(value=>value+1)}>Retry reading</button>}{error&&<p role="alert">{error}</p>}{data?.missing?.length>0&&<p role="alert">Missing local history: {data.missing.length} candle slots. No candles are fabricated.</p>}{data?.history_note&&<p>{data.history_note}</p>}{data&&!data.series.candles.length&&<p className="assumption">Raw candle history is absent from this saved report. Available derived series remain viewable; rerunning requires the original dataset.</p>}{target&&<p className="trade-target">{focus.label} · actual fill: {target.utc}<br/>Source candle: {new Date(target.source_open*1000).toISOString()} → {new Date(target.source_close*1000).toISOString()} (close label). Fill and candle clocks are distinct.{data&&!targetInWindow?' Selected fill is outside this chart window.':data&&!targetCandle?' Exact source candle is unavailable; no nearby candle is substituted.':''}</p>}<div ref={container} style={{height:430}}/>{target&&data&&<details className="recorded-fill-context"><summary>Recorded evaluation context for the selected fill</summary><p>This is the last recorded evaluation in this window available no later than the fill. It is context only, not a causal explanation for entries, stops, DCA, reductions or exits. Nothing is recalculated.</p>{recorded?<><p>Recorded availability: {new Date(recorded.time*1000).toISOString()} · actual fill: {target.utc}</p><p>False, unknown (null) and unavailable are distinct. Native results may contain values without signal outputs.</p><pre>{JSON.stringify({signals:recorded.signals??'Unavailable: no signal outputs were archived',values:recorded.values??'Unavailable: no node values were archived'},null,2)}</pre></>:<p>No recorded evaluation available by this fill in the loaded window. Missing per-fill/leaf-condition evidence is not reconstructed.</p>}</details>}<div className="pagination"><button disabled={!data||data.start<=data.range[0]} onClick={()=>setStart(data.start-minutes*(data.interval_seconds??60))}>Earlier</button><span>{data?`${new Date(data.start*1000).toISOString().slice(0,16)} — ${new Date(data.end*1000).toISOString().slice(0,16)} UTC`: 'Loading saved series'}</span><button disabled={!data||data.end>=data.range[1]} onClick={()=>setStart(data.end)}>Later</button></div><details><summary>Fill details in this window ({data?.series.fills.length??0})</summary>{data&&fillGroups(data.series.fills).map(g=><div key={`${g.time}:${g.side}`}><strong>{new Date(g.time*1000).toISOString()} · {g.side} · {g.fills.length} fill(s)</strong>{g.fills.map((f:any,i:number)=><p key={i}>{f.review_clock?.utc??'Exact fill time unavailable'} · {f.reason} · price {f.price} · quantity {f.quantity} · fee {f.fee} USDT</p>)}</div>)}</details><small>Source candles labeled at their actual interval close; indicators use their recorded availability times. Arrows identify fills within the recorded source candle. No indicator is recalculated by the UI. Charts by <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">TradingView</a>.</small></div>;
}
