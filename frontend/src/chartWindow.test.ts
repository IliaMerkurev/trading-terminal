import {expect,it} from 'vitest';
import {mergeChartWindow,prependShift,CHART_WINDOW_LIMIT} from './chartWindow';
const candle=(time:number,close=100)=>({time,open:100,high:110,low:90,close,volume:1});
it('prepends chronological overlap once and preserves the visible logical anchor',()=>{
 const old=[candle(600),candle(900),candle(1200)];
 const next=mergeChartWindow(old,[candle(0),candle(300),candle(600)],true);
 expect(next.map(c=>c.time)).toEqual([0,300,600,900,1200]);
 const from=1,shift=prependShift(old,next);
 expect(shift).toBe(2);expect(next[from+shift].time).toBe(old[from].time);
});
it('keeps one updated forming candle without changing earlier candles',()=>{
 const old=[candle(0),candle(300)];const next=mergeChartWindow(old,[candle(300,105),candle(600)]);
 expect(next.map(c=>[c.time,c.close])).toEqual([[0,100],[300,105],[600,100]]);
 expect(old[1].close).toBe(100);
});
it('bounds distant history and recent windows separately without changing source candles',()=>{
 const all=Array.from({length:2400},(_,i)=>candle(i*60));
 const older=mergeChartWindow(all.slice(300),all.slice(0,300),true);
 expect(older.length).toBe(CHART_WINDOW_LIMIT);expect(older[0].time).toBe(0);
 const recent=mergeChartWindow([],all);expect(recent.length).toBe(CHART_WINDOW_LIMIT);expect(recent.at(-1)?.time).toBe(2399*60);
 expect(all.length).toBe(2400);
});
