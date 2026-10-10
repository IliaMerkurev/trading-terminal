import type {LiveCandle} from './liveChartData';

export const observationDisplayWidths=[3600,14400,86400] as const;
export const observationInterval=(seconds:number)=>seconds%86400===0?`${seconds/86400}d`:seconds%3600===0?`${seconds/3600}h`:seconds%60===0?`${seconds/60}m`:`${seconds}s`;
export const finite=(value:unknown):value is number=>typeof value==='number'&&Number.isFinite(value);
export const validPrice=(c:LiveCandle)=>[c.open,c.high,c.low,c.close].every(finite)&&c.low>0&&c.low<=Math.min(c.open,c.close)&&c.high>=Math.max(c.open,c.close);
const validVolume=(value:unknown):value is number=>finite(value)&&value>=0;
const positiveInteger=(value:number)=>Number.isSafeInteger(value)&&value>0;

export function displayUnavailable(seconds:number,width:number):string|null{
 if(!positiveInteger(seconds)||!positiveInteger(width))return 'Invalid source or display interval.';
 if(width<seconds)return `Finer than the ${observationInterval(seconds)} source; no interpolation.`;
 if(width%seconds)return `Not a whole multiple of the ${observationInterval(seconds)} source.`;
 if(width/seconds>500)return `Needs ${width/seconds} source slots; this page is limited to 500.`;
 return null;
}

export type ObservationSlot={time:number;end:number;expected:number;sourceTimes:number[];missing:number;outside:number;candle?:LiveCandle};
export type ObservationProjection={slots:ObservationSlot[];issue:string|null};
type Page={start:number;end:number;candles:LiveCandle[];missing:number[];seconds:number;width:number};

// A chart-only projection of one verified page. Page bounds, not retained rows,
// determine completeness; missing slots consume the original 500-slot budget.
export function projectObservation({start,end,candles,missing,seconds,width}:Page):ObservationProjection{
 const fail=(issue:string):ObservationProjection=>({slots:[],issue});
 const unavailable=displayUnavailable(seconds,width);if(unavailable)return fail(unavailable);
 if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||end<=start||start%seconds||end%seconds||(end-start)/seconds>500)return fail('Invalid page boundaries or more than 500 source slots.');
 if(candles.length>500||missing.length>500)return fail('Invalid source payload exceeds 500 slots.');
 const inPage=(time:number)=>Number.isSafeInteger(time)&&time>=start&&time<end&&time%seconds===0;
 const byTime=new Map<number,LiveCandle>();
 for(const candle of candles){
  if(!inPage(candle.time)||byTime.has(candle.time))return fail('Invalid or duplicate source opening timestamp.');
  byTime.set(candle.time,candle);
 }
 const absent=new Set<number>();
 for(const time of missing){
  if(!inPage(time)||absent.has(time)||byTime.has(time))return fail('Invalid, duplicate or contradictory missing source slot.');
  absent.add(time);
 }
 const slots:ObservationSlot[]=[];
 for(let time=Math.floor(start/width)*width;time<end;time+=width){
  const source:LiveCandle[]=[],slot:ObservationSlot={time,end:time+width,expected:width/seconds,sourceTimes:[],missing:0,outside:0};
  for(let t=time;t<time+width;t+=seconds){
   if(t<start||t>=end){slot.outside++;continue;}
   const c=byTime.get(t);if(c){source.push(c);slot.sourceTimes.push(t);}else slot.missing++;
  }
  if(!slot.missing&&!slot.outside){
   if(width===seconds)slot.candle={...source[0]};
   else {
    const priceAvailable=source.every(validPrice),sum=source.every(c=>validVolume(c.volume))?source.reduce((v,c)=>v+c.volume,0):NaN;
    slot.candle={time,open:priceAvailable?source[0].open:NaN,high:priceAvailable?Math.max(...source.map(c=>c.high)):NaN,low:priceAvailable?Math.min(...source.map(c=>c.low)):NaN,close:priceAvailable?source.at(-1)!.close:NaN,volume:finite(sum)?sum:NaN};
   }
   // Invalid prices and volume stay independently unavailable, never partial sums.
   if(!validPrice(slot.candle))slot.candle={...slot.candle,open:NaN,high:NaN,low:NaN,close:NaN};
   if(!validVolume(slot.candle.volume))slot.candle={...slot.candle,volume:NaN};
  }
  slots.push(slot);
 }
 return {slots,issue:null};
}

export const renderedSlot=(slot:ObservationSlot)=>!!slot.candle&&(validPrice(slot.candle)||finite(slot.candle.volume));

// Existing recorder viewports are inclusive original source-opening endpoints.
// Splitting here excludes retained rows in an aggregate suppressed by a gap.
export function observationSourceRanges(slots:ObservationSlot[],seconds:number,range:{from:number;to:number}):number[][]{
 if(!finite(range.from)||!finite(range.to)||range.from>range.to||!positiveInteger(seconds))return [];
 const times=slots.filter(s=>s.time>=range.from&&s.time<=range.to&&renderedSlot(s)).flatMap(s=>s.sourceTimes);
 const runs:number[][]=[];
 for(const time of times){const last=runs.at(-1);if(last&&last[1]+seconds===time)last[1]=time;else runs.push([time,time]);}
 return runs;
}
