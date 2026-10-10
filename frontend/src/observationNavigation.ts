// Saved-history navigation always counts native source slots, including gaps.
export const HISTORY_PAGE_SLOTS=500;
export const SOURCE_NAVIGATION_UNAVAILABLE='Saved-history navigation is unavailable: invalid or unrepresentable source boundaries.';
export type NavigationBounds={start:number;end:number;step:number;slots:number;latest:number};

export function navigationUTC(value:number):string{
 if(!Number.isSafeInteger(value))return '';
 const date=new Date(value*1000);
 if(!Number.isFinite(date.getTime())||date.getUTCFullYear()<1||date.getUTCFullYear()>9999)return '';
 return date.toISOString().slice(0,value%60===0?16:19);
}

export function parseNavigationUTC(value:string):number|null{
 const match=/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(value);
 if(!match)return null;
 const [year,month,day,hour,minute,second]=match.slice(1).map(v=>Number(v??0));
 if(year<1||month<1||month>12||day<1||day>31||hour>23||minute>59||second>59)return null;
 const date=new Date(0);date.setUTCFullYear(year,month-1,day);date.setUTCHours(hour,minute,second,0);
 const exact=[date.getUTCFullYear(),date.getUTCMonth()+1,date.getUTCDate(),date.getUTCHours(),date.getUTCMinutes(),date.getUTCSeconds()];
 const timestamp=date.getTime()/1000;
 return exact.every((v,i)=>v===[year,month,day,hour,minute,second][i])&&Number.isSafeInteger(timestamp)?timestamp:null;
}

export function navigationBounds(source:any):NavigationBounds|null{
 const start=source?.range?.[0],end=source?.range?.[1],step=source?.interval_seconds??60;
 if(!Array.isArray(source?.range)||source.range.length!==2||![start,end,step].every(Number.isSafeInteger)||step<=0||end<=start||start%step||end%step||!navigationUTC(start)||!navigationUTC(end))return null;
 const span=end-start,slots=span/step,pageSpan=HISTORY_PAGE_SLOTS*step;
 if(!Number.isSafeInteger(span)||!Number.isSafeInteger(slots)||slots<1||!Number.isSafeInteger(pageSpan))return null;
 const latest=start+Math.floor((slots-1)/HISTORY_PAGE_SLOTS)*pageSpan;
 return Number.isSafeInteger(latest)&&latest>=start&&latest<end?{start,end,step,slots,latest}:null;
}

export function navigationWindow(bounds:NavigationBounds,start:number):{start:number;end:number}|null{
 if(!Number.isSafeInteger(start)||start<bounds.start||start>=bounds.end||start%bounds.step)return null;
 // Subtract first so a short final page does not overflow through start + 500*s.
 const count=Math.min(HISTORY_PAGE_SLOTS,(bounds.end-start)/bounds.step),end=start+count*bounds.step;
 return Number.isSafeInteger(end)&&Number.isSafeInteger(count)&&count>0&&end<=bounds.end&&end%bounds.step===0?{start,end}:null;
}

export function navigationDraft(value:string,bounds:NavigationBounds|null):{start:number|null;issue:string|null}{
 if(!bounds)return {start:null,issue:SOURCE_NAVIGATION_UNAVAILABLE};
 const start=parseNavigationUTC(value);
 if(start===null)return {start:null,issue:'Enter a complete valid UTC date: YYYY-MM-DDTHH:mm, optionally with :ss. Do not add a timezone or fractional seconds.'};
 if(start<bounds.start||start>=bounds.end)return {start:null,issue:'Choose an opening inside the saved range. The exclusive source end is not a candle opening.'};
 if(start%bounds.step)return {start:null,issue:`Use exact ${bounds.step}-second native UTC candle boundaries. The date is not rounded.`};
 if(!navigationWindow(bounds,start))return {start:null,issue:SOURCE_NAVIGATION_UNAVAILABLE};
 return {start,issue:null};
}
