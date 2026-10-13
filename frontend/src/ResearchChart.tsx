import {useEffect,useRef} from 'react';
import {createChart,CandlestickSeries,LineSeries,createSeriesMarkers,ColorType,type UTCTimestamp} from 'lightweight-charts';
import {alertTime} from './AlertSession';
import {type RawCandle,type HistoryRow,type HistoryMarker} from './alertResearch';
const colors=['#f3c66f','#76b7ff','#bd94ed','#67d4ad','#ee8ba4'];
// Rendering only: raw snapshot candles and saved calculator values are the inputs.
export default function ResearchChart({candles,rows=[],markers=[],target,onSelect}:{candles:RawCandle[];rows?:HistoryRow[];markers?:HistoryMarker[];target?:number|null;onSelect?:(row:HistoryRow)=>void}){
 const host=useRef<HTMLDivElement>(null),select=useRef(onSelect);select.current=onSelect;
 const instanceIds=[...new Set(rows.flatMap(row=>Object.keys(row.evaluation.values)))];
 const height=300+instanceIds.length*140;
 useEffect(()=>{
  if(!host.current||!candles.length)return;
  const chart=createChart(host.current,{autoSize:true,height,layout:{background:{type:ColorType.Solid,color:'#111720'},textColor:'#c9d4e6',attributionLogo:true},grid:{vertLines:{color:'#1c2532'},horzLines:{color:'#1c2532'}},timeScale:{timeVisible:true,secondsVisible:false},localization:{timeFormatter:(time:number)=>alertTime(time)},handleScale:{mouseWheel:false},handleScroll:{mouseWheel:false}});
  const price=chart.addSeries(CandlestickSeries,{upColor:'#42cda8',downColor:'#ed7e86',borderVisible:false});
  price.setData(candles.map(c=>({time:c.time as UTCTimestamp,open:c.open,high:c.high,low:c.low,close:c.close})));
  const marks=markers.map(marker=>({time:marker.raw_open_time as UTCTimestamp,position:'belowBar' as const,color:'#67d4ad',shape:'arrowUp' as const,text:marker.raw_open_time===target?'Selected match':'Match'}));
  if(target!=null&&candles.some(c=>c.time===target)&&!marks.some(m=>m.time===target))marks.push({time:target as UTCTimestamp,position:'belowBar',color:'#f3c66f',shape:'arrowUp',text:'Selected confirmation'});
  createSeriesMarkers(price,marks.sort((a,b)=>a.time-b.time));
  instanceIds.forEach((id,index)=>{
   const ports=[...new Set(rows.flatMap(row=>Object.keys(row.evaluation.values[id]??{})))];
   ports.forEach((port,j)=>{
    const series=chart.addSeries(LineSeries,{title:`${id} · ${port} (saved)`,color:colors[(index+j)%colors.length],lineWidth:2},index+1);
    series.setData(rows.map(row=>{const value=row.evaluation.values[id]?.[port];return typeof value==='number'&&Number.isFinite(value)?{time:row.candle.time as UTCTimestamp,value}:{time:row.candle.time as UTCTimestamp};}));
   });
  });
  const click=(event:any)=>{const row=rows.find(row=>row.candle.time===event.time);if(row)select.current?.(row);};
  chart.subscribeClick(click);chart.timeScale().fitContent();
  return()=>{chart.unsubscribeClick(click);chart.remove();};
 },[candles,rows,markers,target,height]);
 return <div className="research-chart"><div ref={host} style={{height}} aria-label="Read-only research price and saved indicator chart"/><small>Candle axis labels are raw OPEN times in UTC. Conditions and saved indicator values are available at the corresponding confirmed CLOSE. {rows.length>0?'Lower line panes show saved calculated values only.':''} Charts by <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">TradingView</a>.</small></div>;
}
