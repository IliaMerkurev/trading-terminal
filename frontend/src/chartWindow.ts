import type {LiveCandle} from './liveChartData';
export const CHART_WINDOW_LIMIT=1800;
export function mergeChartWindow(previous:LiveCandle[],incoming:LiveCandle[],older=false){
 const rows=new Map(previous.map(c=>[c.time,c])); incoming.forEach(c=>rows.set(c.time,c));
 const ordered=[...rows.values()].sort((a,b)=>a.time-b.time);
 return older?ordered.slice(0,CHART_WINDOW_LIMIT):ordered.slice(-CHART_WINDOW_LIMIT);
}
export function prependShift(previous:LiveCandle[],next:LiveCandle[]){
 return previous.length?next.findIndex(c=>c.time===previous[0].time):0;
}

export type ChartRange={from:number;to:number};
export function chartShowsLatest(range:ChartRange,count:number){
 return count>0&&range.from<=count-1&&range.to>=count-1;
}
// Return uses a small right gutter, retaining the exact zoom width.
export function latestChartRange(range:ChartRange,count:number):ChartRange{
 const width=range.to-range.from;
 const to=Math.max(0,count-1)+Math.min(2,Math.max(0,width/4));
 return {from:to-width,to};
}
export function preserveChartRange(previous:LiveCandle[],next:LiveCandle[],range:ChartRange):ChartRange{
 const indexes=new Map(next.map((row,index)=>[row.time,index]));
 for(let index=0;index<previous.length;index++){
  const nextIndex=indexes.get(previous[index].time);
  if(nextIndex!==undefined){const shift=nextIndex-index;return {from:range.from+shift,to:range.to+shift};}
 }
 return range;
}
// The chart's shared logical domain must contain only the current candles,
// including when an asynchronous display result still describes an older page.
export function indicatorWindow(result:any,rows:LiveCandle[],minutes:number){
 if(!result)return null;
 const allowed=new Set(rows.map(row=>row.time+minutes*60));
 const indexes:number[]=[];
 (result.times??[]).forEach((time:number,index:number)=>{if(allowed.has(time))indexes.push(index);});
 return {...result,times:indexes.map(index=>result.times[index]),
  directions:indexes.map(index=>result.directions?.[index]),
  columns:Object.fromEntries(Object.entries(result.columns??{}).map(([id,ports])=>[id,
   Object.fromEntries(Object.entries(ports as Record<string,any[]>).map(([port,values])=>[port,indexes.map(index=>values[index])]))]))};
}
