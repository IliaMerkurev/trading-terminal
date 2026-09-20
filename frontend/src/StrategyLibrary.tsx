import {useCallback,useEffect,useState} from 'react';
import {api} from './api';
import LibraryResearch,{canonical,formatLibraryMetric as metric} from './LibraryResearch';
import type {Profile} from './model';

type Entry={id:string;version:number;name:string;family:string;kind:string;source_url:string;license:string;
  markets:string[];directions:string[];source_default_minutes:number|null;author_recommended_minutes:number|null;
  author:string;availability:string;local_default_minutes:number;timeframes:number[];timeframe_evidence:string;adaptation:string;review:string;
  compatibility:string;verification:string;parameters:Record<string,{type:string;default:string|number;min:string|number;max:string|number}>};

function Card({entry,onCopy,onSelection,report,stale}:{entry:Entry;onCopy:(id:string)=>Promise<void>;onSelection?:(id:string,value:any)=>void;report:any;stale:boolean}){
  const [minutes,setMinutes]=useState(entry.local_default_minutes),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [included,setIncluded]=useState(false);
  const [parameters,setParameters]=useState<Record<string,string>>(Object.fromEntries(Object.entries(entry.parameters).map(([k,v])=>[k,String(v.default)])));
  const selection={entry_id:entry.id,version:entry.version,minutes,parameters:Object.fromEntries(Object.entries(parameters).map(([k,v])=>[k,entry.parameters[k].type==='decimal'?v:Number(v)]))};
  const selectionKey=canonical(selection);
  useEffect(()=>{onSelection?.(entry.id,included?selection:null);},[included,selectionKey,onSelection]);
  const saved=report?.rows.find((r:any)=>report.snapshot.rows[r.ordinal].selection?.entry_id===entry.id);
  const measured=saved?.metrics,baselines=report?.rows.filter((r:any)=>report.snapshot.rows[r.ordinal].kind==='benchmark')??[];
  const prior=stale||!!saved&&canonical(report.snapshot.rows[saved.ordinal].selection)!==selectionKey;
  async function copy(){setBusy(true);setError('');try{
    const values=Object.fromEntries(Object.entries(parameters).map(([k,v])=>[k,entry.parameters[k].type==='decimal'?v:Number(v)]));
    const result=await api<{strategy_id:string}>('library_copy',{entry_id:entry.id,version:entry.version,minutes,parameters:values});
    await onCopy(result.strategy_id);
  }catch(e){setError(String(e instanceof Error?e.message:e));}finally{setBusy(false);}}
  return <article className="panel" aria-label={entry.name}>
    <h3>{entry.name} <small>v{entry.version} · {entry.kind}</small></h3>
    {onSelection&&<label><input type="checkbox" aria-label={`Include ${entry.name}`} checked={included} onChange={e=>setIncluded(e.target.checked)}/>Include in batch</label>}
    <p>{entry.family} · {entry.markets.join(', ')} · {entry.directions.join('/')}</p>
    <p>{entry.author} · Review: {entry.availability}</p><p><a href={entry.source_url} target="_blank" rel="noreferrer">Pinned source</a> · {entry.license}</p>
    <p>Source default: {entry.source_default_minutes===null?'unspecified':`${entry.source_default_minutes}m`}. Author recommendation: {entry.author_recommended_minutes===null?'unknown':`${entry.author_recommended_minutes}m`}.</p>
    <p className="muted">{entry.timeframe_evidence}</p>
    <label>Strategy timeframe <select aria-label={`${entry.name} timeframe`} value={minutes} onChange={e=>setMinutes(Number(e.target.value))}>{entry.timeframes.map(m=><option key={m} value={m}>{m}m</option>)}</select></label>
    {Object.entries(entry.parameters).map(([name,field])=><label className="field" key={name}>{name}<input aria-label={`${entry.name} ${name}`} type="number" step={field.type==='integer'?1:'any'} min={field.min} max={field.max} value={parameters[name]} onChange={e=>setParameters(p=>({...p,[name]:e.target.value}))}/></label>)}
    <p>{entry.adaptation}</p><details><summary>Review and compatibility</summary><p>{entry.review}</p><p>{entry.compatibility}</p></details>
    <p role="status">{saved?.metrics?`${prior?'Prior run — changed inputs':'Saved result'} · Net PnL ${Number(saved.metrics.net_pnl).toFixed(4)} USDT · Return ${(Number(saved.metrics.period_return)*100).toFixed(2)}% · ${saved.metrics.completed_positions} completed positions`:`Preview · Performance: N/A.${saved?' '+saved.status:''}`} {entry.verification}</p>
    {measured&&<div aria-label={`${entry.name} saved metrics`}><p>Tested timeframe: {report.snapshot.rows[saved.ordinal].profile.primary_minutes}m · Final equity {metric(measured.final_equity)} USDT · Drawdown {metric(measured.max_drawdown,true)} · Win rate {metric(measured.win_rate,true)}</p><p>Fees {metric(measured.fees)} / funding {metric(measured.funding)} USDT · Annualized geometric return {metric(measured.annualized_geometric_return,true)} ({measured.annualized_unavailable_reason??measured.annualization_convention})</p>{baselines.map((b:any,i:number)=><p key={i}>vs {report.snapshot.rows[b.ordinal].name}: {b.metrics?`${metric(Number(measured.net_pnl)-Number(b.metrics.net_pnl))} USDT / ${metric(100*(Number(measured.period_return)-Number(b.metrics.period_return)))} pp`:'N/A'}</p>)}</div>}
    <button disabled={busy} onClick={copy}>{busy?'Creating copy…':'Create my copy'}</button>
    {error&&<p role="alert">{error}</p>}
  </article>;
}

export default function StrategyLibrary({onCopy,datasets=[],profile,onActive=()=>{},onOpenRun=()=>{}}:{onCopy:(id:string)=>Promise<void>;datasets?:any[];profile?:Profile;onActive?:(id:string|null)=>void;onOpenRun?:(id:string)=>void}){
  const [entries,setEntries]=useState<Entry[]|null>(null),[error,setError]=useState('');
  const [selections,setSelections]=useState<Record<string,any>>({}),[report,setReport]=useState<any>(null),[stale,setStale]=useState(false);
  const update=useCallback((id:string,value:any)=>setSelections(previous=>{if(canonical(previous[id]??null)===canonical(value))return previous;const next={...previous};if(value)next[id]=value;else delete next[id];return next;}),[]);
  const receive=useCallback((value:any,changed:boolean)=>{setReport(value);setStale(changed);},[]);
  useEffect(()=>{let current=true;api<Entry[]>('library_catalog').then(v=>{if(current)setEntries(Array.isArray(v)?v:[]);}).catch(e=>{if(current)setError(String(e));});return()=>{current=false;};},[]);
  return <section className="content"><h2>Strategy Library preview</h2><p>Reviewed immutable templates. Create a copy to edit independently. Native execution always requires explicit source-bound consent; unsupported batch combinations remain visible.</p>
    {error&&<p role="alert">{error}</p>}{!entries&&!error&&<p role="status">Loading library…</p>}
    {entries?.map(entry=><Card key={`${entry.id}:${entry.version}`} entry={entry} onCopy={onCopy} onSelection={profile?update:undefined} report={report} stale={stale}/>)}
    {profile&&<LibraryResearch catalog={entries??[]} selections={Object.values(selections)} datasets={datasets} profile={profile} onActive={onActive} onOpenRun={onOpenRun} onReport={receive}/>}
    </section>;
}
