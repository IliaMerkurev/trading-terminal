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
