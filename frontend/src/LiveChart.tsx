import {useEffect,useRef,useState} from 'react';
import {createChart,CandlestickSeries,LineSeries,createSeriesMarkers,ColorType,type UTCTimestamp} from 'lightweight-charts';
import {api} from './api';
import {poll} from './poll';
import {displayCandles,displayIndicator,displayIntervals,liveMarkers,type LiveCandle} from './liveChartData';

export default function LiveChart({sessionId,forming,paper,price,mark,fresh,latestMinute}:{sessionId?:string;forming?:LiveCandle;paper?:any;price?:string;mark?:string;fresh:boolean;latestMinute?:number}){
 const host=useRef<HTMLDivElement>(null),chartRef=useRef<any>(null),candleRef=useRef<any>(null),lineRef=useRef<any>(null),markerRef=useRef<any>(null),priceLines=useRef<any[]>([]);
 const [data,setData]=useState<any>({candles:[],evaluations:[],signals:[],fills:[]}),[minutes,setMinutes]=useState(1),[indicator,setIndicator]=useState(''),[error,setError]=useState('');
 useEffect(()=>{setData({candles:[],evaluations:[],signals:[],fills:[]});setError('');if(!sessionId)return;return poll(()=>api<any>('live_chart',{session_id:sessionId}),setData,()=>setError('Recorded chart data is unavailable; retrying.'),3000);},[sessionId]);
 useEffect(()=>{
  if(!host.current)return;
  const chart=createChart(host.current,{autoSize:true,layout:{background:{type:ColorType.Solid,color:'#111720'},textColor:'#a5b3c9',attributionLogo:true},grid:{vertLines:{color:'#1c2532'},horzLines:{color:'#1c2532'}},timeScale:{timeVisible:true},rightPriceScale:{borderColor:'#2b374b'}});
  const candles=chart.addSeries(CandlestickSeries,{upColor:'#42cda8',downColor:'#ed7e86',borderVisible:false,wickUpColor:'#42cda8',wickDownColor:'#ed7e86'});
  const line=chart.addSeries(LineSeries,{color:'#e0b95e',lineWidth:2,visible:false});
  chartRef.current=chart;candleRef.current=candles;lineRef.current=line;markerRef.current=createSeriesMarkers(candles,[]);
  return()=>{chart.remove();chartRef.current=null;candleRef.current=null;lineRef.current=null;priceLines.current=[];};
 },[]);
 const fitted=useRef(''),ready=useRef('');
 useEffect(()=>{
  if(!candleRef.current)return;
  const candles=displayCandles(data.candles??[],forming,minutes);
  candleRef.current.setData(candles.map(c=>({...c,time:c.time as UTCTimestamp})));
  lineRef.current.setData(displayIndicator(data.evaluations??[],indicator,minutes).map(p=>({...p,time:p.time as UTCTimestamp})));
  lineRef.current.applyOptions({title:indicator||'Recorded IR',visible:!!indicator});
  lineRef.current.moveToPane(indicator?1:0);
  markerRef.current.setMarkers(liveMarkers(data,minutes).filter(m=>candles.length&&m.time>=candles[0].time&&m.time<=candles.at(-1)!.time));
  const key=`${sessionId}:${minutes}`;
  const caughtUp=latestMinute==null||(data.candles.at(-1)?.time??-1)>=latestMinute;
  if(candles.length&&(fitted.current!==key||(fresh&&caughtUp&&ready.current!==sessionId))){
   chartRef.current.timeScale().fitContent();fitted.current=key;if(fresh&&caughtUp)ready.current=sessionId??'';
  }
 },[data,forming,minutes,indicator,sessionId,fresh,latestMinute]);
 useEffect(()=>{
  const candles=candleRef.current;if(!candles)return;
  priceLines.current.forEach(line=>candles.removePriceLine(line));priceLines.current=[];
  for(const [title,value,color] of [['PAPER entry',paper?.position?.entry,'#7eabff'],['PAPER stop',paper?.position?.stop,'#ed7e86'],['PAPER take',paper?.position?.take,'#42cda8'],['Last',fresh?price:null,'#aaaaaa'],['Mark',fresh?mark:null,'#ba9bdb']]){
    if(value&&Number.isFinite(Number(value)))priceLines.current.push(candles.createPriceLine({price:Number(value),color,lineWidth:1,lineStyle:2,axisLabelVisible:true,title}));
  }
 },[paper,price,mark,fresh]);
 const keys=[...new Set<string>((data.evaluations??[]).flatMap((p:any)=>Object.keys(p.values??{}).filter(k=>typeof p.values[k]==='number')))];
 return <section className="live-chart" aria-label="Live candlestick chart"><div className="live-chart-toolbar"><strong>Market chart</strong><label>Chart display<select aria-label="Chart display timeframe" value={minutes} onChange={e=>setMinutes(Number(e.target.value))}>{displayIntervals.map(n=><option key={n} value={n}>{n<60?`${n}m`:n<1440?`${n/60}H`:'1D'}</option>)}</select></label><label>Recorded indicator<select aria-label="Live chart indicator" value={indicator} onChange={e=>setIndicator(e.target.value)}><option value="">None</option>{keys.map(k=><option key={k}>{k}</option>)}</select></label><button onClick={()=>chartRef.current?.timeScale().fitContent()}>Fit chart</button></div>{error&&<small role="alert">{error}</small>}<div className="live-chart-canvas" ref={host}/><small>Display only · UTC interval-end labels · up to 2,880 M1 records / 600 display bars. IR line uses the last recorded sample in each display interval, never recomputed. {fresh?'':'Market data is paused or stale.'}</small></section>;
}
