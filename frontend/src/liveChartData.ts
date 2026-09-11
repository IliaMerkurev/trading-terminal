export type LiveCandle={time:number;open:number;high:number;low:number;close:number;volume:number};
export const displayIntervals=[1,5,15,60,240,1440] as const;
export function displayCandles(recorded:LiveCandle[],forming:LiveCandle|undefined,minutes:number){
  const rows=new Map(recorded.map(c=>[c.time,c]));
  const last=recorded.at(-1)?.time??-1;
  if(forming&&forming.time>last)rows.set(forming.time,forming);
  const buckets=new Map<number,LiveCandle>();const width=minutes*60;
  for(const c of [...rows.values()].sort((a,b)=>a.time-b.time)){
    const end=Math.floor(c.time/width)*width+width,old=buckets.get(end);
    buckets.set(end,old?{...old,high:Math.max(old.high,c.high),low:Math.min(old.low,c.low),close:c.close,volume:old.volume+c.volume}:{...c,time:end});
  }
  return [...buckets.values()].slice(-600);
}
export function displayIndicator(evaluations:any[],key:string,minutes:number){
  const values=new Map<number,{time:number;value:number;observed:number}>();
  for(const point of evaluations){const value=point.values?.[key];if(typeof value==='number'&&Number.isFinite(value)){
    const time=Math.ceil(point.time/(minutes*60))*minutes*60;values.set(time,{time,value,observed:point.time});
  }}
  return [...values.values()].sort((a,b)=>a.time-b.time).slice(-600);
}
export function liveMarkers(data:any,minutes:number){
  const at=(time:number)=>Math.ceil(time/(minutes*60))*minutes*60;
  return [...(data.signals??[]).slice(0,200).map((s:any)=>({time:at(s.time),position:'aboveBar',color:'#d5b367',shape:'circle',text:s.type.replaceAll('_',' ')})),
    ...(data.fills??[]).slice(-200).map((f:any)=>({time:at(f.time_ns/1e9),position:f.side==='buy'?'belowBar':'aboveBar',color:f.side==='buy'?'#42cda8':'#ed7e86',shape:f.side==='buy'?'arrowUp':'arrowDown',text:'PAPER '+f.reason}))].sort((a,b)=>a.time-b.time);
}
