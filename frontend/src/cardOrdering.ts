import {cohortKey,librarySortValue} from './LibraryResearch';

export type CardOrderMetric='name'|'period_return'|'max_drawdown'|'completed_positions';
export type CardOrderDirection='asc'|'desc';
type CatalogIdentity={id:string;version:number;name:string};
export type CardRank={value:number|null;reason:string;ordinal?:number};
export const cardMetricLabels:Record<CardOrderMetric,string>={name:'Name',period_return:'Saved period return',max_drawdown:'Saved max drawdown',completed_positions:'Saved completed positions'};

// Reject empty/invalid values without conflating losses or recorded zero with N/A.
export function finiteCardMetric(value:unknown):number|null{
 if(typeof value!=='number'&&typeof value!=='string'||typeof value==='string'&&!value.trim())return null;
 const number=Number(value);return Number.isFinite(number)?number:null;
}
export function isSelectionComparison(report:any){return !!report?.id&&!!report?.snapshot&&report.snapshot.phase!=='out_of_sample';}
const strategySpecs=(report:any):any[]=>isSelectionComparison(report)?(report.snapshot.rows??[]).map((spec:any,ordinal:number)=>({spec,ordinal})).filter(({spec}:any)=>spec.kind!=='benchmark'&&spec.selection):[];

export function cardOrderChoices(report:any){
 const specs=strategySpecs(report).filter(({spec})=>spec.profile&&spec.dataset?.id&&Number.isSafeInteger(spec.selection.minutes)&&spec.selection.minutes>0);
 // Include every saved cohort in numbering, exactly as the Saved tests table does.
 const allKeys=isSelectionComparison(report)?[...new Set<string>(report.snapshot.rows.map(cohortKey))].sort():[];
 const timeframes=[...new Set<number>(specs.map(({spec})=>spec.selection.minutes))].sort((a,b)=>a-b);
 const groups=allKeys.flatMap((key,index)=>{const matching=specs.filter(({spec})=>cohortKey(spec)===key);return matching.length?[{key,number:index+1,profile:matching[0].spec.profile,minutes:[...new Set<number>(matching.map(({spec})=>spec.selection.minutes))]}]:[];});
 return {timeframes,groups};
}

export function rankCard(entry:CatalogIdentity,report:any,minutes:number|null,group:string,metric:CardOrderMetric):CardRank{
 const unavailable=(reason:string):CardRank=>({value:null,reason});
 if(!isSelectionComparison(report))return unavailable('choose a saved selection comparison');
 if(metric==='name'||!minutes||!group)return unavailable('choose a saved timeframe and compatible group');
 const identities=strategySpecs(report).filter(({spec})=>spec.selection.entry_id===entry.id);
 if(!identities.length)return unavailable('not in selected comparison');
 const versions=identities.filter(({spec})=>spec.selection.version===entry.version);
 if(!versions.length)return unavailable('saved catalog version differs');
 const frames=versions.filter(({spec})=>spec.selection.minutes===minutes);
 if(!frames.length)return unavailable('not tested at this timeframe');
 const matches=frames.filter(({spec})=>spec.profile&&spec.dataset?.id&&cohortKey(spec)===group);
 if(!matches.length)return unavailable('outside selected group');
 // Count frozen variants, including pending/failed ones, before looking at metrics.
 if(matches.length!==1)return unavailable('multiple saved variants');
 const ordinal=matches[0].ordinal,rows=report.rows.filter((row:any)=>row.ordinal===ordinal);
 if(rows.length!==1)return unavailable('saved result unavailable');
 const row=rows[0];
 if(row.status!=='completed')return unavailable(`${row.status??'unavailable'}${row.error?` · ${row.error}`:''}`);
 const value=finiteCardMetric(librarySortValue(report,row,metric));
 return value===null?unavailable('metric unavailable'):{value,reason:'',ordinal};
}

export function orderCards<T extends CatalogIdentity>(entries:readonly T[],report:any,minutes:number|null,group:string,metric:CardOrderMetric,direction:CardOrderDirection){
 const byName=(a:T,b:T)=>a.name.localeCompare(b.name)||a.id.localeCompare(b.id)||a.version-b.version;
 return entries.map(entry=>({entry,rank:rankCard(entry,report,minutes,group,metric)})).sort((a,b)=>{
  if(metric==='name')return (direction==='asc'?1:-1)*byName(a.entry,b.entry);
  if(a.rank.value===null)return b.rank.value===null?byName(a.entry,b.entry):1;
  if(b.rank.value===null)return -1;
  return (direction==='asc'?a.rank.value-b.rank.value:b.rank.value-a.rank.value)||byName(a.entry,b.entry);
 });
}
