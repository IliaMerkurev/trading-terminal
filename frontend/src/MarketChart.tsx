import {useEffect,useRef,useState} from 'react';
import {createChart,CandlestickSeries,LineSeries,createSeriesMarkers,ColorType} from 'lightweight-charts';
import {api} from './api';
import {poll} from './poll';
import {displayIndicator,displayIntervals,liveMarkers,type LiveCandle} from './liveChartData';
import {mergeChartWindow,prependShift} from './chartWindow';
import ChartDrawings from './ChartDrawings';
import ChartIndicators,{indicatorName} from './ChartIndicators';
import {useChartIndicators} from './useChartIndicators';
import {installIndicatorSeries,updateIndicatorSeries} from './chartIndicatorSeries';

export default function MarketChart({source='bybit',sessionId,market='spot',symbol='BTCUSDT',paper,price,mark,fresh,active=true}:{source?:string;active?:boolean;sessionId?:string;market?:string;symbol?:string;paper?:any;price?:string;mark?:string;fresh:boolean}){
 const host=useRef<HTMLDivElement>(null),chartRef=useRef<any>(null),candleRef=useRef<any>(null),lineRef=useRef<any>(null),markerRef=useRef<any>(null),priceLines=useRef<any[]>([]);
 const [minutes,setMinutes]=useState(1),[indicator,setIndicator]=useState(''),[error,setError]=useState(''),[loading,setLoading]=useState(false),[exhausted,setExhausted]=useState(false);
 const [overlay,setOverlay]=useState<any>({}),[rows,setRows]=useState<LiveCandle[]>([]),[reload,setReload]=useState(0);
 const [olderError,setOlderError]=useState('');
 const [logScale,setLogScale]=useState(false),[autoScale,setAutoScale]=useState(true);
 const current=useRef<LiveCandle[]>([]),generation=useRef(0),loadPrevious=useRef(()=>{}),paging=useRef<number|null>(null),historical=useRef(false),fitted=useRef(false);
 const display=useChartIndicators(market,symbol,minutes,active,current,source);
 const owned=useRef<ReturnType<typeof installIndicatorSeries>>([]),[hoverTime,setHoverTime]=useState<number|null>(null);
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
  if(!active)return;
  const sync=setInterval(()=>{const options=chartRef.current?.priceScale?.('right',0).options();if(options){setAutoScale(options.autoScale);setLogScale(options.mode===1);}},500);
  return()=>clearInterval(sync);
 },[active]);
 useEffect(()=>{
  if(!host.current)return;
  const chart=createChart(host.current,{autoSize:true,layout:{background:{type:ColorType.Solid,color:'#111720'},textColor:'#a5b3c9',attributionLogo:true},grid:{vertLines:{color:'#1c2532'},horzLines:{color:'#1c2532'}},timeScale:{timeVisible:true},rightPriceScale:{borderColor:'#2b374b'}});
  const candles=chart.addSeries(CandlestickSeries,{upColor:'#42cda8',downColor:'#ed7e86',borderVisible:false,wickUpColor:'#42cda8',wickDownColor:'#ed7e86'});
  chartRef.current=chart;candleRef.current=candles;lineRef.current=chart.addSeries(LineSeries,{color:'#e0b95e',lineWidth:2,visible:false});markerRef.current=createSeriesMarkers(candles,[]);
  const rangeChanged=(r:any)=>{if(r&&userNavigation.current&&!applying.current&&r.from<30&&lastFrom.current!=null&&r.from<lastFrom.current)loadPrevious.current();if(r)lastFrom.current=r.from;};
  const crosshair=(event:any)=>setHoverTime(typeof event.time==='number'?event.time:null);
  chart.subscribeCrosshairMove?.(crosshair);
  const navigation=()=>{userNavigation.current=true;};
  host.current.addEventListener('pointerdown',navigation);host.current.addEventListener('wheel',navigation);
  const element=host.current;
  chart.timeScale().subscribeVisibleLogicalRangeChange(rangeChanged);
  return()=>{chart.unsubscribeCrosshairMove?.(crosshair);owned.current=[];element.removeEventListener('pointerdown',navigation);element.removeEventListener('wheel',navigation);chart.timeScale().unsubscribeVisibleLogicalRangeChange(rangeChanged);chart.remove();chartRef.current=null;candleRef.current=null;lineRef.current=null;priceLines.current=[];};
 },[]);
 useEffect(()=>{
  const version=++generation.current;current.current=[];setRows([]);paging.current=null;historical.current=false;fitted.current=false;setError('');setOlderError('');setExhausted(false);setHoverTime(null);
  candleRef.current?.setData([]);
 },[source,market,symbol,minutes,reload]);
 useEffect(()=>{
  if(!active)return;
  const version=generation.current;let ended=false;
  loadPrevious.current=()=>{if(paging.current==null&&current.current.length&&current.current[0].time>0){paging.current=current.current[0].time;setOlderError('');setLoading(true);}};
  const cancel=poll(async()=>{const before=paging.current;return {page:await api<any>('market_chart',{market,symbol,minutes,before,...(source==='bybit'?{}:{source})}),before};},({page,before})=>{
   if(ended||version!==generation.current)return;
   setLoading(!!page.loading);setError(page.error??'');
   if(before!=null){if(!page.loading){
    if(page.error||page.page_status==='error'){
     setOlderError(page.error||'Older history unavailable; retry.');paging.current=null;return;
    }
    // Empty cached data is not proof of completion while a page awaits fetching.
    if(page.page_status!=='ready'&&page.page_status!=='end')return;
    const incoming=(page.candles??[]).filter((c:LiveCandle)=>c.time<before);
    if(incoming.length){historical.current=true;apply(mergeChartWindow(current.current,incoming,true));}
    if(page.page_status==='end'&&page.exhausted){setExhausted(true);loadPrevious.current=()=>{};}
    paging.current=null;
   }}else{
    const recent=page.candles??[];
    if(!historical.current||!current.current.length)apply(mergeChartWindow(current.current,recent));
    else if(recent.length&&current.current.at(-1)!.time>=recent[0].time)apply(mergeChartWindow(current.current,recent,true));
   }
  },()=>{setLoading(false);if(paging.current!=null){paging.current=null;setOlderError('Older history unavailable; retry.');}else setError('Market chart unavailable; retrying.');},1000);
  return()=>{ended=true;cancel();loadPrevious.current=()=>{};};
 },[source,market,symbol,minutes,reload,active]);
 useEffect(()=>{if(!active)return;setOverlay({});if(!sessionId)return;return poll(()=>api<any>('live_chart',{session_id:sessionId}),setOverlay,()=>{},3000);},[sessionId,active]);
 useEffect(()=>{
  if(!lineRef.current)return;
  const start=rows[0]?.time??Infinity,end=(rows.at(-1)?.time??0)+minutes*60;
  lineRef.current.setData(displayIndicator(overlay.evaluations??[],indicator,minutes).filter(p=>p.time>start&&p.time<=end));
  lineRef.current.applyOptions({title:indicator||'Recorded IR',visible:!!indicator});
  markerRef.current.setMarkers(liveMarkers(overlay,minutes).filter(m=>m.time>start&&m.time<=end));
 },[overlay,indicator,rows,minutes]);
 useEffect(()=>{
  const chart=chartRef.current;if(!chart)return;
  // Move the recorded series out before deleting panes owned by displays.
  lineRef.current?.moveToPane(0);
  for(const item of owned.current)chart.removeSeries?.(item.series);
  owned.current=installIndicatorSeries(chart,lineRef.current,display.settings.instances,!!indicator);
  updateIndicatorSeries(owned.current,display.result);
 },[display.settings.instances,indicator]);
 useEffect(()=>{updateIndicatorSeries(owned.current,display.result);},[display.result]);
 useEffect(()=>{
  const candles=candleRef.current;if(!candles)return;
  priceLines.current.forEach(line=>candles.removePriceLine(line));priceLines.current=[];
  const levels=[['PAPER entry',paper?.position?.entry,'#7eabff'],['PAPER '+(paper?.position?.stop_reason??'stop'),paper?.position?.stop,'#ed7e86'],['PAPER take',paper?.position?.take,'#42cda8'],['Last',fresh?price:null,'#aaaaaa'],['Mark',fresh?mark:null,'#ba9bdb'],...(paper?.position?.take_levels??[]).map((level:any)=>['PAPER TP '+level.step,level.price,'#42cda8']),...(paper?.position?.dca_levels??[]).map((level:any)=>['PAPER DCA '+level.step,level.price,'#d5b367'])];
  for(const [title,value,color] of levels)if(value&&Number.isFinite(Number(value)))priceLines.current.push(candles.createPriceLine({price:Number(value),color,lineWidth:1,lineStyle:2,axisLabelVisible:true,title}));
 },[paper,price,mark,fresh]);
 const visibleDisplays=display.settings.instances.filter(i=>i.visible);
 const paneCount=new Set(visibleDisplays.filter(i=>['rsi','macd'].includes(i.type)||(i.type==='volume'&&i.placement==='pane')).map(i=>i.type)).size+(indicator?1:0);
 const hoverCandle=hoverTime==null?rows.at(-1):rows.find(row=>row.time+minutes*60===hoverTime);
 const format=(value:unknown)=>typeof value==='number'&&Number.isFinite(value)?value.toLocaleString(undefined,{maximumSignificantDigits:9}):'N/A';
 const selectedPoint=hoverTime==null?(display.result?.times?.length??0)-1:display.result?.times?.indexOf(hoverTime)??-1;
 const unknown=rows.filter(c=>!['closed_rest','provider_confirmed','synthetic_closed'].includes(c.confirmation??'legacy_unknown')).length;
 const keys=[...new Set<string>((overlay.evaluations??[]).flatMap((p:any)=>Object.keys(p.values??{}).filter(k=>typeof p.values[k]==='number')))];
 return <section className="live-chart" aria-label="Live candlestick chart"><div className="live-chart-toolbar"><strong>{source.toUpperCase()} market chart</strong><label>Chart display<select aria-label="Chart display timeframe" value={minutes} onChange={e=>setMinutes(Number(e.target.value))}>{displayIntervals.map(n=><option key={n} value={n}>{n<60?`${n}m`:n<1440?`${n/60}H`:'1D'}</option>)}</select></label><div className="chart-quick-timeframes" role="group" aria-label="Quick native timeframes">{displayIntervals.map(n=><button key={n} aria-pressed={minutes===n} onClick={()=>setMinutes(n)}>{n<60?`${n}m`:n<1440?`${n/60}H`:"1D"}</button>)}</div><ChartIndicators settings={display.settings} onApply={display.apply} busy={display.saving||!display.loaded} error={display.error}/><label>Recorded IR<select aria-label="Live chart indicator" value={indicator} onChange={e=>setIndicator(e.target.value)}><option value="">None</option>{keys.map(k=><option key={k}>{k}</option>)}</select></label><button onClick={()=>{chartRef.current?.timeScale().fitContent();chartRef.current?.priceScale("right",0).applyOptions({autoScale:true});setAutoScale(true);}}>Fit chart</button><button aria-pressed={autoScale} onClick={()=>{chartRef.current?.priceScale("right",0).applyOptions({autoScale:!autoScale});setAutoScale(v=>!v);}}>Auto scale</button><button aria-pressed={logScale} onClick={()=>{chartRef.current?.priceScale("right",0).applyOptions({mode:logScale?0:1});setLogScale(v=>!v);}}>Log scale</button><button onClick={()=>setReload(v=>v+1)}>Latest market</button><button disabled={loading||exhausted||!rows.length} onClick={()=>loadPrevious.current()}>{olderError?'Retry older history':'Older history'}</button></div>{(olderError||error)&&<small role="alert">{olderError||error}</small>}{display.error&&<small role="alert">{display.error}</small>}<div className="chart-ohlcv" aria-label="Chart OHLC and volume"><strong>{symbol} · {minutes<60?`${minutes}m`:minutes<1440?`${minutes/60}H`:"1D"}</strong><span>{hoverCandle?new Date((hoverCandle.time+minutes*60)*1000).toISOString().replace("T"," ").replace(".000Z"," UTC"):"No candle selected"}</span>{[ ["O",hoverCandle?.open],["H",hoverCandle?.high],["L",hoverCandle?.low],["C",hoverCandle?.close],["Vol",hoverCandle?.volume] ].map(([label,value])=><span key={String(label)}>{label} {format(value)}</span>)}</div><ChartDrawings chart={chartRef} series={candleRef} rows={rows} minutes={minutes} source={source} market={market} symbol={symbol} active={active}><div className="chart-plot" style={paneCount?{minHeight:320+paneCount*130}:undefined}><div className="live-chart-canvas" ref={host}/>{!rows.length&&<div className="chart-empty" role="status"><strong>{error?'Market history is unavailable':'Waiting for public market data'}</strong><p>{error?'The public source could not provide chart history. Check the connection or try Latest market. No prices have been substituted.':`${symbol} candles will appear when the public source responds. No strategy or paper account is required.`}</p></div>}</div></ChartDrawings><div className="chart-indicator-readout" aria-label="Display indicator values">{visibleDisplays.map(item=><span key={item.id}>{indicatorName(item)} #{display.settings.instances.findIndex(i=>i.id===item.id)+1}: {Object.entries(display.result?.columns?.[item.id]??{value:[]}).map(([port,values])=>`${port} ${typeof (values as any[])[selectedPoint]==='number'?(values as number[])[selectedPoint].toLocaleString(undefined,{maximumSignificantDigits:10}):'N/A (warmup or unconfirmed)'}`).join(' · ')}</span>)}</div>{visibleDisplays.length>0&&<details className="chart-indicator-details"><summary>Indicator calculation details</summary><p>Native {minutes} minute timeframe · confirmed closes only · price and indicators both use UTC interval-end labels. No strategy, signals or orders are changed.</p><p>Origin: {display.result?.origin?new Date(display.result.origin.time*1000).toISOString():'Awaiting cached history'} · generation {display.result?.origin?.generation??'—'} · {display.result?.origin?.contract??'native-close-engine-seeds-v1'}. Replay cap: 10,000 cached bars. Warmup restarts at gaps or unknown candles.</p><p>{display.result?.confirmed??0} confirmed inputs · {display.result?.unknown??0} unconfirmed/unknown · {display.result?.gaps??0} origin-replay gaps. {display.result?.before_origin?'Before the saved origin, recursive indicators are unavailable. ':''}{display.result?.message??''}</p><p>EMA is first-close seeded. RSI uses zero-difference Wilder seed; flat input returns 100. MACD signal starts at the first ready MACD. Bollinger Bands use population deviation. Volume: {display.result?.volume_unit??'source-native units (unverified)'}. Red means down; selected color means up.</p><button disabled={!display.loaded||display.saving} onClick={display.reanchor}>Recalculate with earlier cached history</button><small>This explicitly changes the origin/generation; recursive values may change. No history is fetched.</small></details>}<small>{unknown?`${unknown} visible candles are forming, legacy-unknown or conflicted. Price and available volume remain visible; calculated indicators need confirmed cached history. No age-based confirmation or automatic indicator backfill. `:''}{loading?'Loading market history… ':''}{exhausted?'Available history boundary reached. ':''}Native market candles · UTC interval-end labels · bounded 1,800-bar viewport; older history stays cached. IR values are recorded, never recomputed. {fresh?'':'Market data is paused or stale.'}</small></section>;
}
