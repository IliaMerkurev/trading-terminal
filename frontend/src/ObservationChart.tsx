import {useEffect,useRef} from 'react';
import {createChart,CandlestickSeries,ColorType,type UTCTimestamp} from 'lightweight-charts';

// Deliberately has no service access. Only the bounded, verified local page is drawn.
export default function ObservationChart({candles}:{candles:any[]}){
 const host=useRef<HTMLDivElement>(null);
 useEffect(()=>{
  if(!host.current)return;
  const chart=createChart(host.current,{height:350,autoSize:true,layout:{background:{type:ColorType.Solid,color:'#111722'},textColor:'#b8c5d9'},timeScale:{timeVisible:true,secondsVisible:false}});
  const series=chart.addSeries(CandlestickSeries);
  series.setData(candles.map(c=>({time:c.time as UTCTimestamp,open:c.open,high:c.high,low:c.low,close:c.close})));
  chart.timeScale().fitContent();
  return()=>chart.remove();
 },[candles]);
 return <div ref={host} role="img" aria-label="Prepared local trade candles, opening times in UTC"/>;
}
