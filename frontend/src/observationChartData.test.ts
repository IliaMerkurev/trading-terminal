import {describe,expect,it} from 'vitest';
import {displayUnavailable,projectObservation,observationSourceRanges} from './observationChartData';
import type {LiveCandle} from './liveChartData';
const h=3600;
const golden:LiveCandle[]=[
 {time:0,open:100,high:103,low:99,close:102,volume:1},
 {time:h,open:102,high:106,low:101,close:105,volume:2},
 {time:2*h,open:105,high:108,low:98,close:100,volume:3},
 {time:3*h,open:100,high:109,low:99,close:107,volume:4},
];
const row=(time:number,volume=10):LiveCandle=>({time,open:100,high:110,low:90,close:105,volume});
const input=(extra:any={})=>({start:0,end:4*h,seconds:h,width:4*h,candles:golden,missing:[],...extra});
const visible={from:0,to:24*h};

describe('bounded saved-history projection',()=>{
 it('preserves exact native values, opening/exclusive-close labels and input identity without mutation',()=>{
  const copy=structuredClone(golden),page=projectObservation(input({width:h}));
  expect(page.issue).toBeNull();expect(page.slots.map(s=>s.candle)).toEqual(copy);
  expect(page.slots.map(s=>[s.time,s.end,s.sourceTimes])).toEqual([[0,h,[0]],[h,2*h,[h]],[2*h,3*h,[2*h]],[3*h,4*h,[3*h]]]);
  expect(golden).toEqual(copy);expect(page.slots[0].candle).not.toBe(golden[0]);
 });
 it('matches an independently specified four-hour OHLCV golden and includes its final constituent in evidence',()=>{
  const p=projectObservation(input());expect(p.issue).toBeNull();
  expect(p.slots).toEqual([{time:0,end:4*h,expected:4,sourceTimes:[0,h,2*h,3*h],missing:0,outside:0,candle:{time:0,open:100,high:109,low:98,close:107,volume:10}}]);
  expect(observationSourceRanges(p.slots,h,{from:0,to:0})).toEqual([[0,3*h]]);
 });
 it('aggregates a full UTC day from six four-hour bars across a month boundary',()=>{
  const start=1706659200; // Jan 31, 2024 00:00 UTC.
  const candles=Array.from({length:6},(_,i)=>({time:start+i*4*h,open:100+i,high:110+i,low:90-i,close:101+i,volume:i+1}));
  const p=projectObservation(input({start,end:1706745600,seconds:4*h,width:24*h,candles}));
  expect(p.slots[0]).toMatchObject({time:1706659200,end:1706745600,expected:6,missing:0,outside:0,candle:{time:1706659200,open:100,high:115,low:85,close:106,volume:21}});
  expect(new Date(p.slots[0].end*1000).toISOString()).toBe('2024-02-01T00:00:00.000Z');
 });
 it('renders every wholly missing/internal/edge bucket as whitespace and keeps missing versus outside counts separate',()=>{
  const p=projectObservation(input({start:h,end:15*h,candles:[row(h),row(3*h),row(12*h),row(14*h)],missing:[2*h,4*h,5*h,6*h,7*h,8*h,9*h,10*h,11*h,13*h]}));
  expect(p.slots.map(({time,end,expected,sourceTimes,missing,outside,candle})=>[time,end,expected,sourceTimes,missing,outside,candle])).toEqual([
   [0,4*h,4,[h,3*h],1,1,undefined],[4*h,8*h,4,[],4,0,undefined],[8*h,12*h,4,[],4,0,undefined],[12*h,16*h,4,[12*h,14*h],1,1,undefined],
  ]);
  expect(observationSourceRanges(p.slots,h,visible)).toEqual([]);
 });
 it('suppresses an incomplete internal bucket without over-recording its retained rows or undercounting the last complete bucket',()=>{
  const candles=Array.from({length:12},(_,i)=>row(i*h)).filter(c=>c.time!==6*h);
  const p=projectObservation(input({end:12*h,candles,missing:[6*h]}));
  expect(p.slots.map(s=>s.candle?.volume)).toEqual([40,undefined,40]);
  expect(p.slots[1].sourceTimes).toEqual([4*h,5*h,7*h]);
  expect(observationSourceRanges(p.slots,h,visible)).toEqual([[0,3*h],[8*h,11*h]]);
  expect(observationSourceRanges(p.slots,h,{from:8*h,to:8*h})).toEqual([[8*h,11*h]]);
  expect(observationSourceRanges(p.slots,h,{from:4*h,to:7*h})).toEqual([]);
  expect(observationSourceRanges(p.slots,h,{from:1,to:3*h})).toEqual([]);
 });
 it('does not stitch a UTC day bisected by adjoining 500-hour source pages',()=>{
  const a=projectObservation(input({end:500*h,width:24*h,candles:Array.from({length:500},(_,i)=>row(i*h))}));
  const b=projectObservation(input({start:500*h,end:900*h,width:24*h,candles:Array.from({length:400},(_,i)=>row((500+i)*h))}));
  expect(a.slots.at(-1)).toMatchObject({time:480*h,missing:0,outside:4});expect(a.slots.at(-1)!.candle).toBeUndefined();
  expect(b.slots[0]).toMatchObject({time:480*h,missing:0,outside:20});expect(b.slots[0].candle).toBeUndefined();
 });
 it('keeps empty and all-missing pages explicit without relying on first or last retained rows',()=>{
  for(const missing of [[],[0,h,2*h,3*h]]){
   const p=projectObservation(input({candles:[],missing}));expect(p.slots).toEqual([{time:0,end:4*h,expected:4,sourceTimes:[],missing:4,outside:0}]);
  }
 });
 it.each([NaN,Infinity,undefined,null,-1])('makes an unavailable volume constituent %s N/A, never a partial sum',value=>{
  const candles=golden.map((c,i)=>({...c,volume:i===2?value:c.volume})) as LiveCandle[];
  const c=projectObservation(input({candles})).slots[0].candle!;
  expect(Number.isNaN(c.volume)).toBe(true);expect(c.close).toBe(107);
 });
 it('keeps zero volume zero and overflow unavailable independently of valid prices',()=>{
  expect(projectObservation(input({candles:golden.map(c=>({...c,volume:0}))})).slots[0].candle?.volume).toBe(0);
  const c=projectObservation(input({candles:golden.map(c=>({...c,volume:Number.MAX_VALUE}))})).slots[0].candle!;
  expect(Number.isNaN(c.volume)).toBe(true);expect(c.high).toBe(109);
 });
 it.each([NaN,Infinity,50])('never derives valid aggregate prices from an invalid high %s',high=>{
  const candles=golden.map((c,i)=>i===1?{...c,high}:c),c=projectObservation(input({candles})).slots[0].candle!;
  expect([c.open,c.high,c.low,c.close].every(Number.isNaN)).toBe(true);expect(c.volume).toBe(10);
 });
 it.each([
  {candles:[golden[0],golden[1],golden[1],golden[3]]},
  {candles:golden.map((c,i)=>i===2?{...c,time:2*h+1}:c)},
  {candles:[...golden,row(4*h)]},{missing:[0]},{missing:[h/2]},{missing:[4*h]},
  {candles:[golden[0]],missing:[h,h]},
 ])('fails closed on malformed timestamp or missing-slot metadata: %s',extra=>{
  const p=projectObservation(input(extra));expect(p.issue).toMatch(/Invalid/);expect(p.slots).toEqual([]);
 });
 it.each([
  [0,4*h,'Invalid'],[NaN,4*h,'Invalid'],[h,0,'Invalid'],[h,NaN,'Invalid'],[h,h/2,'Finer'],[3*h,4*h,'whole multiple'],[60,24*h,'1440 source slots'],[1,501,'501 source slots'],
 ] as const)('explains source %s and width %s incompatibility', (seconds,width,reason)=>{
  expect(displayUnavailable(seconds,width)).toContain(reason);expect(projectObservation(input({seconds,width})).slots).toEqual([]);
 });
 it('allows exactly 500 source slots, 5m daily and 3h daily but rejects over-budget coverage',()=>{
  const p=projectObservation(input({seconds:1,width:500,end:500,candles:Array.from({length:500},(_,i)=>row(i,1))}));
  expect(p.slots[0].candle?.volume).toBe(500);expect(p.slots[0].sourceTimes).toHaveLength(500);
  expect(displayUnavailable(300,86400)).toBeNull();expect(displayUnavailable(3*h,86400)).toBeNull();
  expect(projectObservation(input({seconds:1,width:500,end:501,candles:[]})).issue).toContain('500 source slots');
 });
 it('is causal per bucket: later values and appended buckets cannot change earlier aggregates or their mapping',()=>{
  const earlier=projectObservation(input()),later=projectObservation(input({end:8*h,candles:[...golden,...Array.from({length:4},(_,i)=>row((4+i)*h,999))]}));
  expect(later.slots[0]).toEqual(earlier.slots[0]);expect(observationSourceRanges(later.slots,h,{from:0,to:0})).toEqual([[0,3*h]]);
  const changed=projectObservation(input({end:8*h,candles:[...golden,...Array.from({length:4},(_,i)=>({...row((4+i)*h),close:NaN}))]}));
  expect(changed.slots[0]).toEqual(earlier.slots[0]);
 });
});
