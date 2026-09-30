export const timeframe=(minutes:number)=>minutes>=1440?`${minutes/1440}d`:minutes>=60?`${minutes/60}h`:`${minutes}m`;
export const dateTime=(seconds:number)=>new Date(seconds*1000).toISOString().slice(0,16);
export const dateOnly=(seconds:number)=>new Date(seconds*1000).toISOString().slice(0,10);
export const familyName=(family:string)=>({trend:'Trend following',momentum:'Momentum',mean_reversion:'Mean reversion',breakout:'Breakout'}[family]??family.replaceAll('_',' '));
