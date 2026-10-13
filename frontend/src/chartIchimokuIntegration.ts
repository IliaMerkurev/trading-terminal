import {ichimokuProjectionLines, type IchimokuLines} from './chartIchimokuPrimitive';
import type {ChartIndicator} from './ChartIndicators';
import type {LiveCandle} from './liveChartData';

export type ProjectionContext = {source:string; market:string; symbol:string; minutes:number; revision:number};
export function acceptedIchimoku(result:any, item:ChartIndicator, rows:LiveCandle[], context:ProjectionContext): IchimokuLines {
 const empty = {senkou_a:[],senkou_b:[],chikou:[]};
 const envelope=result?.projections, actual=envelope?.context;
 if(result?.status!=='ready'||!actual||!rows.length||!result.origin||!item.visible) return empty;
 const expected={source:context.source,market:context.market,symbol:context.symbol,minutes:context.minutes,
  start:rows[0].time,end:rows.at(-1)!.time,settings_revision:context.revision,
  generation:result.origin.generation,origin:result.origin.time};
 if(!Number.isInteger(expected.generation)||!Number.isFinite(expected.origin)||
  Object.entries(expected).some(([key,value])=>actual[key]!==value)||
  envelope.horizon!==expected.end+context.minutes*60||
  envelope.instances?.[item.id]?.displacement!==item.params.displacement) return empty;
 return ichimokuProjectionLines(envelope,item.id,rows.map(row=>row.time+context.minutes*60));
}

// LWC needs a populated raw bar in the viewport to resolve price coordinates.
// Keep only a half-bar margin at the last raw point; do not add fake timestamps.
export function retainIchimokuRawAnchor(range:{from:number;to:number}, count:number, enabled:boolean) {
 if(!enabled||count<1||!Number.isFinite(range.from)||!Number.isFinite(range.to)||range.from<=count-1) return range;
 const from=count-1-0.5; return {from,to:from+(range.to-range.from)};
}
