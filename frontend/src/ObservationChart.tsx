import {displayRecorder,observeChartDisplay} from './DisplayedEvidence';
import {useEffect,useRef} from 'react';
import {createChart,CandlestickSeries,ColorType,type UTCTimestamp} from 'lightweight-charts';

// Only the bounded, verified local page is drawn; evidence follows visible candles.
export default function ObservationChart({candles,reference,seconds,record}:{candles:any[];reference:any;seconds:number;record:ReturnType<typeof displayRecorder>}){
 const host=useRef<HTMLDivElement>(null);
 useEffect(()=>{
  if(!host.current)return;
  const chart=createChart(host.current,{height:350,autoSize:true,layout:{background:{type:ColorType.Solid,color:'#111722'},textColor:'#b8c5d9'},timeScale:{timeVisible:true,secondsVisible:false}});
  const series=chart.addSeries(CandlestickSeries);
  series.setData(candles.map(c=>({time:c.time as UTCTimestamp,open:c.open,high:c.high,low:c.low,close:c.close})));
  chart.timeScale().fitContent();
  const stop=observeChartDisplay(host.current,chart,candles,seconds,false,range=>record(reference,range));
  return()=>{stop();chart.remove();};
 },[candles,JSON.stringify(reference),seconds]);
 return <div ref={host} role="img" aria-label="Prepared local trade candles, opening times in UTC"/>;
}
