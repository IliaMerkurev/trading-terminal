import {expect,it} from 'vitest';
import {mergeChartWindow,prependShift,olderChartRange,CHART_WINDOW_LIMIT} from './chartWindow';
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

it.each([
 ['evicted newest window',1699,1799,1699,1799],
 ['retained fractional anchor',100.25,180.25,400.25,480.25],
 ['partly blank left edge',-20,80,280,380],
 ['left whitespace that becomes populated',-100,-20,200,280],
 ['partly evicted right edge',1450,1550,1750,1850],
 ['wide evicted window',1900,4900,-1201,1799],
 ['wide overlapping window',-500,2500,-200,2800],
 ['wholly blank left edge',-1000,-900,0,100],
 ['touching the last retained candle',1499,1599,1799,1899],
 ['touching the first retained candle',-400,-300,-100,0],
] as const)('preserves older-page zoom for %s',(_label,from,to,expectedFrom,expectedTo)=>{
 const previous=Array.from({length:1800},(_,i)=>candle((i+300)*60));
 const next=mergeChartWindow(previous,Array.from({length:300},(_,i)=>candle(i*60)),true);
 expect(olderChartRange(previous,next,{from,to})).toEqual({from:expectedFrom,to:expectedTo});
 expect(next).toHaveLength(1800);expect(next[0].time).toBe(0);expect(next.at(-1)?.time).toBe(1799*60);
});

it('anchors older pages by retained timestamps across gaps and falls back at the right edge for disjoint data',()=>{
 const previous=[1000,2000,10000,30000].map(time=>candle(time));
 const next=mergeChartWindow(previous,[candle(1),candle(5)],true);
 expect(olderChartRange(previous,next,{from:1.25,to:2.25})).toEqual({from:3.25,to:4.25});
 const disjoint=Array.from({length:300},(_,i)=>candle(i));
 expect(olderChartRange(previous,disjoint,{from:50,to:130})).toEqual({from:219,to:299});
});

it('handles empty and single-candle older windows without inventing a zoom',()=>{
 const range={from:50,to:130};
 expect(olderChartRange([candle(1000)],[],range)).toBe(range);
 expect(olderChartRange([],[],range)).toBe(range);
 expect(olderChartRange([], [candle(0)],range)).toEqual({from:-80,to:0});
 expect(olderChartRange([candle(1000)],[candle(0)],{from:5,to:5})).toEqual({from:0,to:0});
 expect(olderChartRange([candle(0)],[candle(0)],{from:0,to:0})).toEqual({from:0,to:0});
 const reversed={from:80,to:50},invalid={from:0,to:Infinity};
 expect(olderChartRange([], [candle(0)],reversed)).toBe(reversed);
 expect(olderChartRange([], [candle(0)],invalid)).toBe(invalid);
});

it('keeps an independent 80-bar return width and maps trimmed browsing anchors backwards',async()=>{
 const {latestChartRange,preserveChartRange,chartShowsLatest}=await import('./chartWindow');
 expect(latestChartRange({from:100,to:180},300)).toEqual({from:221,to:301});
 expect(latestChartRange({from:100,to:101},300)).toEqual({from:298.25,to:299.25});
 expect(preserveChartRange([candle(0),candle(60),candle(120)],[candle(60),candle(120),candle(180)],{from:.25,to:1.75})).toEqual({from:-.75,to:.75});
 expect(chartShowsLatest({from:220,to:299},300)).toBe(true);
 expect(chartShowsLatest({from:220,to:298.9},300)).toBe(false);
 expect(chartShowsLatest({from:301,to:380},300)).toBe(false);
});
it('clips indicator values, direction and whitespace to candle timestamps without changing origin metadata',async()=>{
 const {indicatorWindow}=await import('./chartWindow');
 const result={times:[60,120,180,240],directions:[-1,1,-1,1],origin:{time:0,generation:4},columns:{ema:{value:[10,20,null,40]}}};
 expect(indicatorWindow(result,[candle(60),candle(180)],1)).toEqual({times:[120,240],directions:[1,1],origin:{time:0,generation:4},columns:{ema:{value:[20,40]}}});
 expect(result.times).toEqual([60,120,180,240]);
});
