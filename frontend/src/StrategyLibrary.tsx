import {useEffect,useState} from 'react';
import {api} from './api';

type Entry={id:string;version:number;name:string;family:string;kind:string;source_url:string;license:string;
  markets:string[];directions:string[];source_default_minutes:number|null;author_recommended_minutes:number|null;
  local_default_minutes:number;timeframes:number[];timeframe_evidence:string;adaptation:string;review:string;
  compatibility:string;verification:string;parameters:Record<string,{type:string;default:string|number;min:string|number;max:string|number}>};

function Card({entry,onCopy}:{entry:Entry;onCopy:(id:string)=>Promise<void>}){
  const [minutes,setMinutes]=useState(entry.local_default_minutes),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [parameters,setParameters]=useState<Record<string,string>>(Object.fromEntries(Object.entries(entry.parameters).map(([k,v])=>[k,String(v.default)])));
  async function copy(){setBusy(true);setError('');try{
    const values=Object.fromEntries(Object.entries(parameters).map(([k,v])=>[k,entry.parameters[k].type==='decimal'?v:Number(v)]));
    const result=await api<{strategy_id:string}>('library_copy',{entry_id:entry.id,version:entry.version,minutes,parameters:values});
    await onCopy(result.strategy_id);
  }catch(e){setError(String(e instanceof Error?e.message:e));}finally{setBusy(false);}}
  return <article className="panel" aria-label={entry.name}>
    <h3>{entry.name} <small>v{entry.version} · {entry.kind}</small></h3>
    <p>{entry.family} · {entry.markets.join(', ')} · {entry.directions.join('/')}</p>
    <p><a href={entry.source_url} target="_blank" rel="noreferrer">Pinned source</a> · {entry.license}</p>
    <p>Source default: {entry.source_default_minutes===null?'unspecified':`${entry.source_default_minutes}m`}. Author recommendation: {entry.author_recommended_minutes===null?'unknown':`${entry.author_recommended_minutes}m`}.</p>
    <p className="muted">{entry.timeframe_evidence}</p>
    <label>Strategy timeframe <select aria-label={`${entry.name} timeframe`} value={minutes} onChange={e=>setMinutes(Number(e.target.value))}>{entry.timeframes.map(m=><option key={m} value={m}>{m}m</option>)}</select></label>
    {Object.entries(entry.parameters).map(([name,field])=><label className="field" key={name}>{name}<input aria-label={`${entry.name} ${name}`} type="number" step={field.type==='integer'?1:'any'} min={field.min} max={field.max} value={parameters[name]} onChange={e=>setParameters(p=>({...p,[name]:e.target.value}))}/></label>)}
    <p>{entry.adaptation}</p><details><summary>Review and compatibility</summary><p>{entry.review}</p><p>{entry.compatibility}</p></details>
    <p role="status">Preview · Performance: N/A. {entry.verification}</p>
    <button disabled={busy} onClick={copy}>{busy?'Creating copy…':'Create my copy'}</button>
    {error&&<p role="alert">{error}</p>}
  </article>;
}

export default function StrategyLibrary({onCopy}:{onCopy:(id:string)=>Promise<void>}){
  const [entries,setEntries]=useState<Entry[]|null>(null),[error,setError]=useState('');
  useEffect(()=>{let current=true;api<Entry[]>('library_catalog').then(v=>{if(current)setEntries(v);}).catch(e=>{if(current)setError(String(e));});return()=>{current=false;};},[]);
  return <section className="content"><h2>Strategy Library preview</h2><p>Reviewed source templates. Copy into the existing editor, review native consent where required, and use Backtest to run. Batch research and benchmark rankings are not available in this checkpoint.</p>
    {error&&<p role="alert">{error}</p>}{!entries&&!error&&<p role="status">Loading library…</p>}
    {entries?.map(entry=><Card key={`${entry.id}:${entry.version}`} entry={entry} onCopy={onCopy}/>)}</section>;
}
