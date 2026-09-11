import { useEffect,useRef,useState } from 'react';
import { createChart,CandlestickSeries,LineSeries,createSeriesMarkers,ColorType,type UTCTimestamp } from 'lightweight-charts';
import { api } from './api';

export function chartPoints(data:any,indicator:string){
  return {
    candles:data.series.candles.map((c:any)=>({time:(c.time+60) as UTCTimestamp,open:c.open,high:c.high,low:c.low,close:c.close})),
    indicator:data.series.indicators.filter((p:any)=>typeof p.values[indicator]==='number').map((p:any)=>({time:p.time as UTCTimestamp,value:p.values[indicator]})),
    // Multiple engine observations in one minute use the last recorded equity.
    equity:[...new Map(data.series.equity.map((p:any)=>[Math.ceil(p.time_ns/1e9/60)*60,{time:(Math.ceil(p.time_ns/1e9/60)*60) as UTCTimestamp,value:Number(p.equity)}])).values()] as any[],
  };
}
export default function RunChart({runId,focus}:{runId:string;focus:{time:number;request:number}|null}){
  const container=useRef<HTMLDivElement>(null),[data,setData]=useState<any>(null),[start,setStart]=useState<number|null>(null),[minutes,setMinutes]=useState(240),[indicator,setIndicator]=useState(''),[error,setError]=useState('');
  useEffect(()=>{setStart(null);setData(null);setIndicator('');},[runId]);
  useEffect(()=>{if(focus!==null)setStart(Math.floor(focus.time/60)*60-60*30);},[focus]);
  useEffect(()=>{let live=true;setError('');api<any>('chart_window',{run_id:runId,start,minutes}).then(d=>{if(live)setData(d);}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[runId,start,minutes]);
  const available:string[]=data?[...new Set<string>(data.series.indicators.flatMap((p:any)=>Object.keys(p.values).filter(k=>typeof p.values[k]==='number')))]:[];
  useEffect(()=>{
    if(!container.current||!data)return;
    const chart=createChart(container.current,{autoSize:true,height:430,handleScale:{mouseWheel:false},handleScroll:{mouseWheel:false},layout:{background:{type:ColorType.Solid,color:'#111720'},textColor:'#a5b3c9',attributionLogo:true},grid:{vertLines:{color:'#1c2532'},horzLines:{color:'#1c2532'}},timeScale:{timeVisible:true,secondsVisible:false},rightPriceScale:{borderColor:'#2b374b'}});
    const points=chartPoints(data,indicator);
    const candles=chart.addSeries(CandlestickSeries,{upColor:'#42cda8',downColor:'#ed7e86',borderVisible:false,wickUpColor:'#42cda8',wickDownColor:'#ed7e86'});
    candles.setData(points.candles);
    if(indicator){const line=chart.addSeries(LineSeries,{color:'#e0b95e',lineWidth:2,title:indicator},1);line.setData(points.indicator);}
    const equity=chart.addSeries(LineSeries,{color:'#7eabff',lineWidth:2,title:'Equity (USDT)'},indicator?2:1);equity.setData(points.equity);
    const markers=data.series.fills.map((f:any)=>({time:Math.ceil(f.time_ns/1e9/60)*60 as UTCTimestamp,position:f.side==='buy'?'belowBar' as const:'aboveBar' as const,color:f.side==='buy'?'#42cda8':'#ed7e86',shape:f.side==='buy'?'arrowUp' as const:'arrowDown' as const,text:`${f.side} · ${f.reason}`}));
    if(points.candles.length)createSeriesMarkers(candles,markers);
    chart.timeScale().fitContent();
    return()=>chart.remove();
  },[data,indicator]);
  return <div className="run-chart"><div className="chart-toolbar"><strong>Recorded candles & indicators</strong><select aria-label="Chart indicator" value={indicator} onChange={e=>setIndicator(e.target.value)}><option value="">Select recorded indicator</option>{available.map(k=><option key={k}>{k}</option>)}</select><select aria-label="Chart window" value={minutes} onChange={e=>setMinutes(Number(e.target.value))}>{[60,240,480].map(n=><option key={n} value={n}>{n/60}h window</option>)}</select></div>{error&&<p role="alert">{error}</p>}{data&&!data.series.candles.length&&<p className="assumption">Raw candle history is absent from this saved report. Available derived series remain viewable; rerunning requires the original dataset.</p>}<div ref={container} style={{height:430}}/><div className="pagination"><button disabled={!data||data.start<=data.range[0]} onClick={()=>setStart(data.start-minutes*60)}>Earlier</button><span>{data?`${new Date(data.start*1000).toISOString().slice(0,16)} — ${new Date(data.end*1000).toISOString().slice(11,16)} UTC`: 'Loading saved series'}</span><button disabled={!data||data.end>=data.range[1]} onClick={()=>setStart(data.end)}>Later</button></div><small>M1 candles labeled at close; indicators use their recorded availability times. Arrows identify fills within the minute. No indicator is recalculated by the UI. Charts by <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">TradingView</a>.</small></div>;
}
