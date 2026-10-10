import {useEffect,useLayoutEffect,useRef,useState} from 'react';
import {api} from './api';
import {timeframe} from './research';

export type EquityTarget={batchId:string;ordinal:number;runId:string;comparisonName:string;group:number;spec:any;start:number;end:number;trigger:HTMLElement;request:number};
const utc=(value:number)=>Number.isFinite(value)?new Date(value*1000).toISOString().slice(0,16):'Unavailable';

function Equity({data}:{data:any}){
 const colors=['#7eabff','#42cda8','#e0b95e'],values=data.curves.flatMap((c:any)=>c.points.map((p:any)=>Number(p.equity)));
 const low=Math.min(Number(data.capital),...values),high=Math.max(Number(data.capital),...values),span=high-low||1;
 return <figure><figcaption>Equity · USDT · {utc(data.start)} — {utc(data.end)} UTC (end exclusive)</figcaption>
 <svg viewBox="0 0 800 240" role="img" aria-label="Strategy, Buy and Hold, and DCA equity comparison" style={{width:'100%',maxHeight:260}}>
 <text x="0" y="16" fill="currentColor">{high.toFixed(2)}</text><text x="0" y="232" fill="currentColor">{low.toFixed(2)}</text>
 {data.curves.map((c:any,i:number)=><polyline key={i} fill="none" stroke={colors[i]} strokeWidth="2" points={c.points.map((p:any)=>`${70+720*(p.time_ns/1e9-data.start)/(data.end-data.start)},${220-200*(Number(p.equity)-low)/span}`).join(' ')}/>)}</svg>
 <p>{data.curves.map((c:any,i:number)=><span key={i} style={{color:colors[i],marginRight:16}}>{c.name}: {c.status}{!c.points.length?' · N/A':''}</span>)}</p><small>{data.note}</small></figure>;
}

export default function EquityComparison({target,onClose}:{target:EquityTarget;onClose:()=>void}){
 const heading=useRef<HTMLHeadingElement>(null),epoch=useRef(0);
 const [attempt,setAttempt]=useState(0),[result,setResult]=useState<any>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true);
 useLayoutEffect(()=>{
  const node=heading.current;
  if(node&&!node.closest('[hidden]')&&!document.querySelector('dialog[open]')){node.focus({preventScroll:true});node.scrollIntoView?.({block:'start'});}
 },[]);
 useEffect(()=>{
  const current=++epoch.current;setLoading(true);setError('');setResult(null);
  api<any>('library_batch_equity',{batch_id:target.batchId,ordinal:target.ordinal}).then(value=>{
   if(current!==epoch.current)return;
   if(!Array.isArray(value?.curves)||!value.curves.every((curve:any)=>Array.isArray(curve.points)))throw Error('Invalid equity comparison response');
   setResult(value);
  }).catch(reason=>{if(current===epoch.current)setError(String(reason instanceof Error?reason.message:reason));}).finally(()=>{if(current===epoch.current)setLoading(false);});
  return()=>{epoch.current++;};
 },[target.batchId,target.ordinal,attempt]);
 const spec=target.spec,profile=spec.profile,selection=spec.selection,minutes=selection?.minutes??profile?.primary_minutes;
 const resolved=spec.contract?.parameters,hasResolved=resolved!==null&&typeof resolved==='object'&&!Array.isArray(resolved),parameters=hasResolved?resolved:selection?.parameters??{};
 return <section className="equity-inspector" aria-labelledby="equity-comparison-heading">
  <div className="equity-inspector-heading"><h3 ref={heading} id="equity-comparison-heading" tabIndex={-1}>Equity comparison</h3><button onClick={()=>{epoch.current++;onClose();}}>Back to result</button></div>
  <p><strong>{spec.name}</strong> · {Number.isFinite(minutes)?timeframe(minutes):'Timeframe unavailable'} · Comparison group {target.group}<br/>{target.comparisonName} · {utc(target.start)} — {utc(target.end)} UTC (end exclusive)</p>
  <p>{profile?.symbol??'Instrument unavailable'} · {profile?.market??'Market unavailable'} · Saved capital {profile?.capital??'N/A'} USDT · Source / execution {profile?timeframe(Number(profile.execution_minutes??1)):'N/A'}</p>
  <details><summary>Saved variant and identifiers</summary><p>Catalog version {selection?.version??'N/A'} · {selection?.entry_id??'Catalog identity unavailable'}</p><p>{hasResolved?'Resolved parameters from the saved contract':'Saved selection overrides only; resolved parameters unavailable.'}</p><dl>{Object.entries(parameters).map(([name,value])=><div key={name}><dt>{name}</dt><dd>{String(value)}</dd></div>)}</dl>{!Object.keys(parameters).length&&<p>{hasResolved?'No parameters in this saved contract.':'No saved selection overrides.'}</p>}<p>Comparison ID: {target.batchId}<br/>Row: {target.ordinal+1}<br/>Run ID: {target.runId}</p></details>
  {loading&&<p role="status">Loading saved equity for this variant…</p>}
  {error&&<div><p role="alert">Could not read saved equity: {error}</p><button onClick={()=>{heading.current?.focus({preventScroll:true});setLoading(true);setError('');setAttempt(value=>value+1);}}>Retry equity read</button></div>}
  {result&&<Equity data={result}/>}
 </section>;
}
