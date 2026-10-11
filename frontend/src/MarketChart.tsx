import {useEffect,useLayoutEffect,useMemo,useRef,useState} from 'react';
import {createChart,CandlestickSeries,LineSeries,createSeriesMarkers,ColorType} from 'lightweight-charts';
import {api} from './api';
import {poll} from './poll';
import {displayIndicator,displayIntervals,liveMarkers,type LiveCandle} from './liveChartData';
import {mergeChartWindow,preserveChartRange,olderChartRange,latestChartRange,chartShowsLatest,indicatorWindow} from './chartWindow';
import ChartDrawings from './ChartDrawings';
import {isTypingTarget} from './chartDrawings';
import ChartIndicators,{indicatorName} from './ChartIndicators';
import {useChartIndicators} from './useChartIndicators';
import {installIndicatorSeries,updateIndicatorSeries,auxiliaryKinds} from './chartIndicatorSeries';

import {chartPriceData,type PriceStyle} from './chartPriceData';

export default function MarketChart({source='bybit',sessionId,market='spot',symbol='BTCUSDT',paper,price,mark,fresh,active=true,focusMode=false}:{focusMode?:boolean;source?:string;active?:boolean;sessionId?:string;market?:string;symbol?:string;paper?:any;price?:string;mark?:string;fresh:boolean}){
 const host=useRef<HTMLDivElement>(null),chartRef=useRef<any>(null),candleRef=useRef<any>(null),lineRef=useRef<any>(null),rawLineRef=useRef<any>(null),markerRef=useRef<any>(null),priceLines=useRef<any[]>([]);
 const [minutes,setMinutes]=useState(1),[indicator,setIndicator]=useState(''),[error,setError]=useState(''),[loading,setLoading]=useState(false),[exhausted,setExhausted]=useState(false);
 const [overlay,setOverlay]=useState<any>({}),[rows,setRows]=useState<LiveCandle[]>([]),[refresh,setRefresh]=useState(0);
 const [olderError,setOlderError]=useState(''),[returnError,setReturnError]=useState(''),[returning,setReturning]=useState(false),[following,setFollowing]=useState(true);
 const [logScale,setLogScale]=useState(false),[autoScale,setAutoScale]=useState(true),[windowEpoch,setWindowEpoch]=useState(0);
 const current=useRef<LiveCandle[]>([]),generation=useRef(0),navigationEpoch=useRef(0),loadPrevious=useRef(()=>{}),paging=useRef<number|null>(null),historical=useRef(false),fitted=useRef(false);
 const follows=useRef(true),pendingReturn=useRef(false),atBoundary=useRef(false);
 const [priceStyle,setPriceStyle]=useState<PriceStyle>('candles');
 const styleRef=useRef(priceStyle),projectedStyle=useRef(priceStyle);styleRef.current=priceStyle;
 const display=useChartIndicators(market,symbol,minutes,active,current,source,windowEpoch,priceStyle);
 const displayResult=useMemo(()=>indicatorWindow(display.result,rows,minutes),[display.result,rows,minutes]);
 const owned=useRef<ReturnType<typeof installIndicatorSeries>>([]),[hoverTime,setHoverTime]=useState<number|null>(null);
 const presentation=useRef({result:display.result,overlay,indicator});presentation.current={result:display.result,overlay,indicator};
 const userNavigation=useRef(false),applying=useRef(false),lastFrom=useRef<number|null>(null);
 // autoSize can emit a range callback after layout changes. A prior pan must
 // not turn focus-mode resizing into a fresh user gesture or older-page read.
 useLayoutEffect(()=>{userNavigation.current=false;},[focusMode]);
 const follow=(value:boolean)=>{follows.current=value;setFollowing(value);};
 const clearWindowOverlays=()=>{
  // All chart series share the logical time domain. Remove old timestamps
  // before installing a disjoint candle window or measuring its right edge.
  lineRef.current?.setData([]);rawLineRef.current?.setData([]);markerRef.current?.setMarkers([]);
  updateIndicatorSeries(owned.current,null);
  chartRef.current?.clearCrosshairPosition?.();setHoverTime(null);
 };
 const apply=(next:LiveCandle[],{replace=false,older=false}:{replace?:boolean;older?:boolean}={})=>{
  const series=candleRef.current,chart=chartRef.current;if(!series||!chart)return;
  const previous=current.current,range=chart.timeScale().getVisibleLogicalRange?.();
  applying.current=true;userNavigation.current=false;
  if(replace){clearWindowOverlays();setWindowEpoch(value=>value+1);}
  else {
   // Trim rolled-off display/IR timestamps synchronously; delayed indicator
   // reads must never leave a second, larger logical domain behind candles.
   const latest=presentation.current;
   updateIndicatorSeries(owned.current,indicatorWindow(latest.result,next,minutes));
   const times=new Set(next.map(c=>c.time+minutes*60));
   lineRef.current?.setData(displayIndicator(latest.overlay.evaluations??[],latest.indicator,minutes).filter(p=>times.has(p.time)));
   markerRef.current?.setMarkers(liveMarkers(latest.overlay,minutes).filter(m=>times.has(m.time)));
  }
  const style=styleRef.current;
  series.setData(chartPriceData(next,minutes,style,replace?null:presentation.current.result));
  rawLineRef.current?.setData(next.map(row=>({time:row.time+minutes*60,value:row.close})));
  current.current=next;setRows(next);
  if(!fitted.current&&next.length){chart.timeScale().fitContent();fitted.current=true;}
  else if(range){
   const nextRange=replace?latestChartRange(range,next.length)
    :follows.current?{from:range.from+next.length-previous.length,to:range.to+next.length-previous.length}
    :older?olderChartRange(previous,next,range)
    :preserveChartRange(previous,next,range);
   if(nextRange)chart.timeScale().setVisibleLogicalRange?.(nextRange);
  }
  applying.current=false;
 };
 const returnToLatest=()=>{
  if(!active||pendingReturn.current)return;
  ++navigationEpoch.current;paging.current=null;setOlderError('');setReturnError('');setError('');
  userNavigation.current=false;
  if(!historical.current&&current.current.length){
   setLoading(false);follow(true);
   const chart=chartRef.current,range=chart?.timeScale().getVisibleLogicalRange?.();
   if(range){applying.current=true;chart.timeScale().setVisibleLogicalRange?.(latestChartRange(range,current.current.length));applying.current=false;}
   return;
  }
  pendingReturn.current=true;setReturning(true);setLoading(true);follow(false);
  // Restart just the read subscription, preserving the mounted chart, zoom,
  // annotation history, persisted settings and any unsaved editor drafts.
  setRefresh(value=>value+1);
 };
 const fitChart=()=>{
  if(pendingReturn.current){++navigationEpoch.current;pendingReturn.current=false;setReturning(false);setLoading(false);}
  userNavigation.current=false;applying.current=true;
  chartRef.current?.timeScale().fitContent();applying.current=false;
  follow(!historical.current);
  chartRef.current?.priceScale('right',0).applyOptions({autoScale:true});setAutoScale(true);
 };
 useEffect(()=>{
  if(!active)return;
  const sync=setInterval(()=>{const options=chartRef.current?.priceScale?.('right',0).options();if(options){setAutoScale(options.autoScale);setLogScale(options.mode===1);}},500);
  return()=>clearInterval(sync);
 },[active]);
 useEffect(()=>{
  if(!host.current)return;
  const chart=createChart(host.current,{autoSize:true,layout:{background:{type:ColorType.Solid,color:'#111720'},textColor:'#a5b3c9',attributionLogo:true},grid:{vertLines:{color:'#1c2532'},horzLines:{color:'#1c2532'}},timeScale:{timeVisible:true,shiftVisibleRangeOnNewBar:false},rightPriceScale:{borderColor:'#2b374b'}});
  const candles=chart.addSeries(CandlestickSeries,{upColor:'#42cda8',downColor:'#ed7e86',borderVisible:false,wickUpColor:'#42cda8',wickDownColor:'#ed7e86'});
  chartRef.current=chart;candleRef.current=candles;rawLineRef.current=chart.addSeries(LineSeries,{color:'#7eabff',lineWidth:2,visible:true,lineVisible:false,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});lineRef.current=chart.addSeries(LineSeries,{color:'#e0b95e',lineWidth:2,visible:false});markerRef.current=createSeriesMarkers(candles,[]);
  const rangeChanged=(r:any)=>{
   if(r&&userNavigation.current&&!applying.current){
    if(pendingReturn.current){++navigationEpoch.current;pendingReturn.current=false;setReturning(false);setLoading(false);}
    if(!chartShowsLatest(r,current.current.length)||historical.current)follow(false);
    if(r.from<30&&lastFrom.current!=null&&r.from<lastFrom.current)loadPrevious.current();
   }
   if(r)lastFrom.current=r.from;
  };
  const crosshair=(event:any)=>setHoverTime(typeof event.time==='number'?event.time:null);
  chart.subscribeCrosshairMove?.(crosshair);
  const navigation=()=>{userNavigation.current=true;};
  const dragging=(event:PointerEvent)=>{if(event.buttons===1)navigation();};
  host.current.addEventListener('pointerdown',navigation);host.current.addEventListener('pointermove',dragging);host.current.addEventListener('wheel',navigation);
  const element=host.current;
  chart.timeScale().subscribeVisibleLogicalRangeChange(rangeChanged);
  return()=>{chart.unsubscribeCrosshairMove?.(crosshair);owned.current=[];element.removeEventListener('pointerdown',navigation);element.removeEventListener('pointermove',dragging);element.removeEventListener('wheel',navigation);chart.timeScale().unsubscribeVisibleLogicalRangeChange(rangeChanged);chart.remove();chartRef.current=null;candleRef.current=null;rawLineRef.current=null;lineRef.current=null;priceLines.current=[];};
 },[]);
 useEffect(()=>{
  ++generation.current;++navigationEpoch.current;current.current=[];setRows([]);paging.current=null;historical.current=false;fitted.current=false;pendingReturn.current=false;atBoundary.current=false;
  follow(true);setReturning(false);setLoading(false);setReturnError('');setError('');setOlderError('');setExhausted(false);
  userNavigation.current=false;lastFrom.current=null;clearWindowOverlays();setWindowEpoch(value=>value+1);
  candleRef.current?.setData([]);
 },[source,market,symbol,minutes]);
 useEffect(()=>{
  if(!active){
   ++navigationEpoch.current;paging.current=null;
   if(pendingReturn.current){pendingReturn.current=false;setReturning(false);}
   setLoading(false);return;
  }
  const version=generation.current;let ended=false;
  loadPrevious.current=()=>{if(!pendingReturn.current&&!atBoundary.current&&paging.current==null&&current.current.length&&current.current[0].time>0){++navigationEpoch.current;paging.current=current.current[0].time;follow(false);setReturnError('');setOlderError('');setLoading(true);}};
  const cancel=poll(async()=>{
   const before=paging.current,epoch=navigationEpoch.current;
   try{return {page:await api<any>('market_chart',{market,symbol,minutes,before,...(source==='bybit'?{}:{source})}),before,epoch};}
   catch{return {page:{loading:false,error:'Market chart unavailable; retrying.',page_status:'error'},before,epoch};}
  },({page,before,epoch})=>{
   if(ended||version!==generation.current||epoch!==navigationEpoch.current)return;
   setLoading(!!page.loading);
   if(pendingReturn.current){
    if(page.error||page.page_status==='error'||(!page.loading&&!(page.candles??[]).length)){
     pendingReturn.current=false;setReturning(false);setLoading(false);
     setReturnError(page.error||'Recent history is empty. Your current chart is preserved. Retry return to latest.');return;
    }
    if(page.loading)return;
    historical.current=false;pendingReturn.current=false;setReturning(false);setReturnError('');setError('');setExhausted(false);atBoundary.current=false;follow(true);
    apply(mergeChartWindow([],page.candles),{replace:true});return;
   }
   setError(page.error??'');
   if(before!=null){if(!page.loading){
    if(page.error||page.page_status==='error'){
     setOlderError(page.error||'Older history unavailable; retry.');paging.current=null;return;
    }
    // Empty cached data is not proof of completion while a page awaits fetching.
    if(page.page_status!=='ready'&&page.page_status!=='end')return;
    const incoming=(page.candles??[]).filter((c:LiveCandle)=>c.time<before);
    if(incoming.length){historical.current=true;follow(false);apply(mergeChartWindow(current.current,incoming,true),{older:true});}
    if(page.page_status==='end'&&page.exhausted){setExhausted(true);atBoundary.current=true;}
    paging.current=null;
   }}else{
    const recent=page.candles??[];
    if(!historical.current||!current.current.length)apply(mergeChartWindow(current.current,recent));
    else if(recent.length&&current.current.at(-1)!.time>=recent[0].time)apply(mergeChartWindow(current.current,recent,true));
   }
  },()=>{},1000);
  return()=>{ended=true;cancel();loadPrevious.current=()=>{};};
 },[source,market,symbol,minutes,refresh,active]);
 useEffect(()=>{if(!active)return;setOverlay({});if(!sessionId)return;return poll(()=>api<any>('live_chart',{session_id:sessionId}),setOverlay,()=>{},3000);},[sessionId,active]);
 useEffect(()=>{
  if(!lineRef.current)return;
  const times=new Set(rows.map(c=>c.time+minutes*60));
  lineRef.current.setData(displayIndicator(overlay.evaluations??[],indicator,minutes).filter(p=>times.has(p.time)));
  lineRef.current.applyOptions({title:indicator||'Recorded IR',visible:!!indicator});
  markerRef.current.setMarkers(liveMarkers(overlay,minutes).filter(m=>times.has(m.time)));
 },[overlay,indicator,rows,minutes]);
 useEffect(()=>{
  const chart=chartRef.current;if(!chart)return;
  // Move the recorded series out before deleting panes owned by displays.
  lineRef.current?.moveToPane(0);
  for(const item of owned.current)chart.removeSeries?.(item.series);
  owned.current=installIndicatorSeries(chart,lineRef.current,display.settings.instances,!!indicator);
  updateIndicatorSeries(owned.current,displayResult);
 },[display.settings.instances,indicator]);
 useEffect(()=>{updateIndicatorSeries(owned.current,displayResult);},[displayResult]);
 useEffect(()=>{
  const chart=chartRef.current,candles=candleRef.current;if(!chart||!candles)return;
  if(priceStyle!=='heikin_ashi'&&projectedStyle.current===priceStyle)return;
  if(projectedStyle.current!==priceStyle){
   markerRef.current?.detach?.();
   markerRef.current=createSeriesMarkers(priceStyle==='line'?rawLineRef.current:candles,[]);
   const times=new Set(rows.map(row=>row.time+minutes*60));
   markerRef.current.setMarkers(liveMarkers(overlay,minutes).filter(marker=>times.has(marker.time)));
  }
  projectedStyle.current=priceStyle;
  const range=chart.timeScale().getVisibleLogicalRange?.();
  applying.current=true;userNavigation.current=false;
  candles.applyOptions({lastValueVisible:priceStyle==='candles',priceLineVisible:priceStyle==='candles'});
  candles.setData(chartPriceData(rows,minutes,priceStyle,displayResult));
  rawLineRef.current?.applyOptions({visible:true,lineVisible:priceStyle==='line'});
  rawLineRef.current?.setData(rows.map(row=>({time:row.time+minutes*60,value:row.close})));
  if(range)chart.timeScale().setVisibleLogicalRange?.(range);
  applying.current=false;
 },[priceStyle,displayResult,rows,minutes]);
 useEffect(()=>{
  const candles=candleRef.current;if(!candles)return;
  priceLines.current.forEach(({owner,line})=>owner.removePriceLine(line));priceLines.current=[];
  // An invisible line stroke retains a real first value for coordinates and
  // actual-price levels even when every synthetic candle is whitespace.
  const levelSeries=rawLineRef.current;
  const levels=[['PAPER entry',paper?.position?.entry,'#7eabff'],['PAPER '+(paper?.position?.stop_reason??'stop'),paper?.position?.stop,'#ed7e86'],['PAPER take',paper?.position?.take,'#42cda8'],['Last',fresh?price:null,'#aaaaaa'],['Mark',fresh?mark:null,'#ba9bdb'],...(paper?.position?.take_levels??[]).map((level:any)=>['PAPER TP '+level.step,level.price,'#42cda8']),...(paper?.position?.dca_levels??[]).map((level:any)=>['PAPER DCA '+level.step,level.price,'#d5b367'])];
  for(const [title,value,color] of levels)if(value&&Number.isFinite(Number(value)))priceLines.current.push({owner:levelSeries,line:levelSeries.createPriceLine({price:Number(value),color,lineWidth:1,lineStyle:2,axisLabelVisible:true,title})});
 },[paper,price,mark,fresh,priceStyle]);
 const visibleDisplays=display.settings.instances.filter(i=>i.visible);
 const paneCount=new Set(visibleDisplays.filter(i=>(i.type!=='volume'&&auxiliaryKinds.includes(i.type))||(i.type==='volume'&&i.placement==='pane')).map(i=>i.type)).size+(indicator?1:0);
 const hoverCandle=hoverTime==null?rows.at(-1):rows.find(row=>row.time+minutes*60===hoverTime);
 const format=(value:unknown)=>typeof value==='number'&&Number.isFinite(value)?value.toLocaleString(undefined,{maximumSignificantDigits:9}):'N/A';
 const selectedTime=hoverTime??(rows.length?rows.at(-1)!.time+minutes*60:null);
 const selectedPoint=displayResult?.times?.indexOf(selectedTime)??-1;
 const unknown=rows.filter(c=>!['closed_rest','provider_confirmed','synthetic_closed'].includes(c.confirmation??'legacy_unknown')).length;
 const keys=[...new Set<string>((overlay.evaluations??[]).flatMap((p:any)=>Object.keys(p.values??{}).filter(k=>typeof p.values[k]==='number')))];
 return <section className="live-chart" aria-label="Live candlestick chart"><ChartIndicators focusMode={focusMode} settings={display.settings} onApply={display.apply} busy={display.saving||!display.loaded} error={display.error} volumeUnit={display.result?.volume_unit}
 toolbar={<><strong className="chart-instrument">{symbol}<small>{source.toUpperCase()} · {market}</small></strong><label className="chart-timeframe-select">Timeframe<select aria-label="Chart display timeframe" value={minutes} onChange={e=>setMinutes(Number(e.target.value))}>{displayIntervals.map(n=><option key={n} value={n}>{n<60?`${n}m`:n<1440?`${n/60}H`:'1D'}</option>)}</select></label><div className="chart-quick-timeframes" role="group" aria-label="Quick native timeframes">{displayIntervals.map(n=><button key={n} aria-pressed={minutes===n} onClick={()=>setMinutes(n)}>{n<60?`${n}m`:n<1440?`${n/60}H`:"1D"}</button>)}</div></>}
 toolbarActions={<><label>Style<select aria-label="Chart price style" value={priceStyle} onChange={event=>setPriceStyle(event.target.value as PriceStyle)}><option value="candles">Candles</option><option value="heikin_ashi">Heikin Ashi</option><option value="line">Line · raw close</option></select></label><button disabled={!active||returning} onClick={returnToLatest}>{returning?'Returning to latest…':returnError?'Retry return to latest':'Return to latest'}</button><details className="chart-options" onKeyDown={event=>{
  if(event.key==='Escape' && !event.isDefaultPrevented() && !event.nativeEvent.isComposing && !isTypingTarget(event.target) && event.currentTarget.open){event.preventDefault();event.stopPropagation();event.currentTarget.open=false;event.currentTarget.querySelector('summary')?.focus({preventScroll:true});}
 }}><summary>Chart options</summary><div><label>Recorded IR<select aria-label="Live chart indicator" value={indicator} onChange={e=>setIndicator(e.target.value)}><option value="">None</option>{keys.map(k=><option key={k}>{k}</option>)}</select></label><button onClick={fitChart}>Fit chart</button><button aria-pressed={autoScale} onClick={()=>{chartRef.current?.priceScale("right",0).applyOptions({autoScale:!autoScale});setAutoScale(v=>!v);}}>Auto scale</button><button aria-pressed={logScale} onClick={()=>{chartRef.current?.priceScale("right",0).applyOptions({mode:logScale?0:1});setLogScale(v=>!v);}}>Log scale</button></div></details></>}/>
<div className="chart-navigation" aria-label="Chart navigation"><strong>{returning?'Returning to latest…':following?'Following latest':'Browsing history'}</strong><span>{returning?'Keeping this window until recent history is ready.':following?'New candles stay in view at your zoom.':'Your history view stays in place. Return to latest to follow new candles.'}</span><button disabled={!active||returning||loading||exhausted||!rows.length} onClick={()=>loadPrevious.current()}>{olderError?'Retry older history':'Older history'}</button></div>{(returnError||olderError||error)&&<small role="alert">{returnError||olderError||error}</small>}{display.error&&<small role="alert">{display.error}</small>}{priceStyle==='heikin_ashi'&&<small role="status">Heikin Ashi · synthetic prices{displayResult?.status==='ready'?'':' · awaiting cached calculation'}. Raw OHLC, Last/Mark, PAPER levels and drawing snapping remain actual prices; drawings use the price axis. Missing synthetic bars are blank. Raw closes retain the price scale for actual levels and drawings.</small>}<div className="chart-ohlcv" aria-label="Chart OHLC and volume"><strong>Raw OHLC · {symbol} · {minutes<60?`${minutes}m`:minutes<1440?`${minutes/60}H`:"1D"}</strong><span>{hoverCandle?new Date((hoverCandle.time+minutes*60)*1000).toISOString().replace("T"," ").replace(".000Z"," UTC"):"No candle selected"}</span>{[ ["O",hoverCandle?.open],["H",hoverCandle?.high],["L",hoverCandle?.low],["C",hoverCandle?.close],["Vol",hoverCandle?.volume] ].map(([label,value])=><span key={String(label)}>{label} {format(value)}</span>)}</div><ChartDrawings focusMode={focusMode} chart={chartRef} series={rawLineRef} rows={rows} minutes={minutes} source={source} market={market} symbol={symbol} active={active}><div className="chart-plot" style={paneCount?{minHeight:320+paneCount*130}:undefined}><div className="live-chart-canvas" ref={host}/>{!rows.length&&<div className="chart-empty" role="status"><strong>{error?'Market history is unavailable':'Waiting for public market data'}</strong><p>{error?'The public source could not provide chart history. Check the connection or try Return to latest. No prices have been substituted.':`${symbol} candles will appear when the public source responds. No strategy or paper account is required.`}</p></div>}</div></ChartDrawings><div className="chart-indicator-readout" aria-label="Display indicator values">{visibleDisplays.map(item=><span key={item.id}>{indicatorName(item)} #{display.settings.instances.findIndex(i=>i.id===item.id)+1}: {Object.entries(displayResult?.columns?.[item.id]??{value:[]}).map(([port,values])=>`${port} ${typeof (values as any[])[selectedPoint]==='number'?(values as number[])[selectedPoint].toLocaleString(undefined,{maximumSignificantDigits:10}):'N/A (warmup or unconfirmed)'}`).join(' · ')}</span>)}</div>{(visibleDisplays.length>0||priceStyle==='heikin_ashi')&&<details className="chart-indicator-details"><summary>Price and indicator calculation details</summary><p>Native {minutes} minute timeframe · confirmed closes only · price and indicators both use UTC interval-end labels. No strategy, signals or orders are changed.</p><p>Origin: {display.result?.origin?new Date(display.result.origin.time*1000).toISOString():'Awaiting cached history'} · generation {display.result?.origin?.generation??'—'} · {display.result?.origin?.contract??'native-close-engine-seeds-v1'}. Replay cap: 10,000 cached bars. Warmup restarts at gaps or unknown candles.</p><p>{display.result?.confirmed??0} confirmed inputs · {display.result?.unknown??0} unconfirmed/unknown · {display.result?.gaps??0} origin-replay gaps. {display.result?.before_origin?'Before the saved origin, recursive indicators and Stochastic are unavailable. ':''}{display.result?.message??''}</p><p>EMA is first-close seeded. RSI uses zero-difference Wilder seed; flat input returns 100. MACD signal starts at the first ready MACD. Bollinger Bands use population deviation. Display ATR uses a mean true-range seed then Wilder smoothing (price units), unlike the graph engine seed; it is not recorded IR. Stochastic uses rolling high/low with SMA K/D (percent; flat window = 0). OBV starts at zero and accumulates signed source-native volume; missing volume resets only OBV. Volume/OBV units: {display.result?.volume_unit??'source-native units (unverified)'}. Red means down; selected color means up.</p><p>Heikin Ashi uses a segment midpoint seed then prior confirmed synthetic open/close; forming previews never advance that recurrence. Gaps and unknown history reset it. All display formulas still use raw native candles.</p>{visibleDisplays.map(item=><p key={item.id}>{indicatorName(item)}: {display.result?.formula_metadata?.[item.id]?.seed??''} {display.result?.formula_metadata?.[item.id]?.unit??''}</p>)}<button disabled={!display.loaded||display.saving} onClick={display.reanchor}>Recalculate with earlier cached history</button><small>This changes the shared origin/generation for Heikin Ashi and indicators; synthetic prices and recursive values may change. No history is fetched.</small></details>}<small>{unknown?`${unknown} visible candles are forming, legacy-unknown or conflicted. Price and available volume remain visible; calculated indicators need confirmed cached history. No age-based confirmation or automatic indicator backfill. `:''}{loading?'Loading market history… ':''}{exhausted?'Available history boundary reached. ':''}Native market candles · UTC interval-end labels · bounded 1,800-bar viewport; older history stays cached. IR values are recorded, never recomputed. {fresh?'':'Market data is paused or stale.'}</small></section>;
}
