import {useEffect,useRef,useState} from 'react';
import {createChart,CandlestickSeries,LineSeries,createSeriesMarkers,ColorType} from 'lightweight-charts';
import {api} from './api';
import {poll} from './poll';
import {displayIndicator,displayIntervals,liveMarkers,type LiveCandle} from './liveChartData';
import {mergeChartWindow,prependShift} from './chartWindow';

export default function MarketChart({sessionId,market='spot',symbol='BTCUSDT',paper,price,mark,fresh}:{sessionId?:string;market?:string;symbol?:string;paper?:any;price?:string;mark?:string;fresh:boolean}){
 const host=useRef<HTMLDivElement>(null),chartRef=useRef<any>(null),candleRef=useRef<any>(null),lineRef=useRef<any>(null),markerRef=useRef<any>(null),priceLines=useRef<any[]>([]);
 const [minutes,setMinutes]=useState(1),[indicator,setIndicator]=useState(''),[error,setError]=useState(''),[loading,setLoading]=useState(false),[exhausted,setExhausted]=useState(false);
 const [overlay,setOverlay]=useState<any>({}),[rows,setRows]=useState<LiveCandle[]>([]),[reload,setReload]=useState(0);
 const current=useRef<LiveCandle[]>([]),generation=useRef(0),loadPrevious=useRef(()=>{}),paging=useRef<number|null>(null),historical=useRef(false),fitted=useRef(false);
 const userNavigation=useRef(false),applying=useRef(false),lastFrom=useRef<number|null>(null);
 const apply=(next:LiveCandle[])=>{
  const series=candleRef.current,chart=chartRef.current;if(!series||!chart)return;
  const previous=current.current,range=chart.timeScale().getVisibleLogicalRange?.();
  applying.current=true;
  const samePrefix=previous.length&&next.length>=previous.length&&next.length<=previous.length+1&&previous.slice(0,-1).every((c,i)=>JSON.stringify(c)===JSON.stringify(next[i]));
  const plotted=(c:LiveCandle)=>({...c,time:c.time+minutes*60});
  if(samePrefix&&series.update){for(const c of next.slice(previous.length-1))series.update(plotted(c));}
  else series.setData(next.map(plotted));
  current.current=next;setRows(next);
  if(!fitted.current&&next.length){chart.timeScale().fitContent();fitted.current=true;}
  else if(range&&!samePrefix){const shift=prependShift(previous,next);if(shift>=0)chart.timeScale().setVisibleLogicalRange?.({from:range.from+shift,to:range.to+shift});}
  applying.current=false;
 };
 useEffect(()=>{
  if(!host.current)return;
  const chart=createChart(host.current,{autoSize:true,layout:{background:{type:ColorType.Solid,color:'#111720'},textColor:'#a5b3c9',attributionLogo:true},grid:{vertLines:{color:'#1c2532'},horzLines:{color:'#1c2532'}},timeScale:{timeVisible:true},rightPriceScale:{borderColor:'#2b374b'}});
  const candles=chart.addSeries(CandlestickSeries,{upColor:'#42cda8',downColor:'#ed7e86',borderVisible:false,wickUpColor:'#42cda8',wickDownColor:'#ed7e86'});
  chartRef.current=chart;candleRef.current=candles;lineRef.current=chart.addSeries(LineSeries,{color:'#e0b95e',lineWidth:2,visible:false});markerRef.current=createSeriesMarkers(candles,[]);
  const rangeChanged=(r:any)=>{if(r&&userNavigation.current&&!applying.current&&r.from<30&&lastFrom.current!=null&&r.from<lastFrom.current)loadPrevious.current();if(r)lastFrom.current=r.from;};
  const navigation=()=>{userNavigation.current=true;};
  host.current.addEventListener('pointerdown',navigation);host.current.addEventListener('wheel',navigation);
  const element=host.current;
  chart.timeScale().subscribeVisibleLogicalRangeChange(rangeChanged);
  return()=>{element.removeEventListener('pointerdown',navigation);element.removeEventListener('wheel',navigation);chart.timeScale().unsubscribeVisibleLogicalRangeChange(rangeChanged);chart.remove();chartRef.current=null;candleRef.current=null;lineRef.current=null;priceLines.current=[];};
 },[]);
 useEffect(()=>{
  const version=++generation.current;current.current=[];setRows([]);paging.current=null;historical.current=false;fitted.current=false;setError('');setExhausted(false);
  candleRef.current?.setData([]);let ended=false;
  loadPrevious.current=()=>{if(paging.current==null&&current.current.length&&current.current[0].time>0)paging.current=current.current[0].time;};
  const cancel=poll(async()=>{const before=paging.current;return {page:await api<any>('market_chart',{market,symbol,minutes,before}),before};},({page,before})=>{
   if(ended||version!==generation.current)return;
   setLoading(!!page.loading);setError(page.error??'');
   if(before!=null){if(!page.loading){
    const incoming=(page.candles??[]).filter((c:LiveCandle)=>c.time<before);
    if(incoming.length){historical.current=true;apply(mergeChartWindow(current.current,incoming,true));}
    if(page.exhausted||!incoming.length){setExhausted(true);loadPrevious.current=()=>{};}
    paging.current=null;
   }}else{
    const recent=page.candles??[];
    if(!historical.current||!current.current.length)apply(mergeChartWindow(current.current,recent));
    else if(recent.length&&current.current.at(-1)!.time>=recent[0].time)apply(mergeChartWindow(current.current,recent,true));
   }
  },()=>setError('Market chart unavailable; retrying.'),1000);
  return()=>{ended=true;cancel();loadPrevious.current=()=>{};};
 },[market,symbol,minutes,reload]);
 useEffect(()=>{setOverlay({});if(!sessionId)return;return poll(()=>api<any>('live_chart',{session_id:sessionId}),setOverlay,()=>{},3000);},[sessionId]);
 useEffect(()=>{
  if(!lineRef.current)return;
  const start=rows[0]?.time??Infinity,end=(rows.at(-1)?.time??0)+minutes*60;
  lineRef.current.setData(displayIndicator(overlay.evaluations??[],indicator,minutes).filter(p=>p.time>start&&p.time<=end));
  lineRef.current.applyOptions({title:indicator||'Recorded IR',visible:!!indicator});lineRef.current.moveToPane(indicator?1:0);
  markerRef.current.setMarkers(liveMarkers(overlay,minutes).filter(m=>m.time>start&&m.time<=end));
 },[overlay,indicator,rows,minutes]);
 useEffect(()=>{
  const candles=candleRef.current;if(!candles)return;
  priceLines.current.forEach(line=>candles.removePriceLine(line));priceLines.current=[];
  for(const [title,value,color] of [['PAPER entry',paper?.position?.entry,'#7eabff'],['PAPER stop',paper?.position?.stop,'#ed7e86'],['PAPER take',paper?.position?.take,'#42cda8'],['Last',fresh?price:null,'#aaaaaa'],['Mark',fresh?mark:null,'#ba9bdb']])if(value&&Number.isFinite(Number(value)))priceLines.current.push(candles.createPriceLine({price:Number(value),color,lineWidth:1,lineStyle:2,axisLabelVisible:true,title}));
 },[paper,price,mark,fresh]);
 const keys=[...new Set<string>((overlay.evaluations??[]).flatMap((p:any)=>Object.keys(p.values??{}).filter(k=>typeof p.values[k]==='number')))];
 return <section className="live-chart" aria-label="Live candlestick chart"><div className="live-chart-toolbar"><strong>Market chart</strong><label>Chart display<select aria-label="Chart display timeframe" value={minutes} onChange={e=>setMinutes(Number(e.target.value))}>{displayIntervals.map(n=><option key={n} value={n}>{n<60?`${n}m`:n<1440?`${n/60}H`:'1D'}</option>)}</select></label><label>Recorded indicator<select aria-label="Live chart indicator" value={indicator} onChange={e=>setIndicator(e.target.value)}><option value="">None</option>{keys.map(k=><option key={k}>{k}</option>)}</select></label><button onClick={()=>chartRef.current?.timeScale().fitContent()}>Fit chart</button><button onClick={()=>setReload(v=>v+1)}>Latest market</button><button disabled={loading||exhausted||!rows.length} onClick={()=>loadPrevious.current()}>Older history</button></div>{error&&<small role="alert">{error}</small>}<div className="live-chart-canvas" ref={host}/><small>{loading?'Loading market history… ':''}{exhausted?'Available history boundary reached. ':''}Native market candles · UTC interval-end labels · bounded 1,800-bar viewport; older history stays cached. IR values are recorded, never recomputed. {fresh?'':'Market data is paused or stale.'}</small></section>;
}
