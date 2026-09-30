import {useCallback,useEffect,useState} from 'react';
import {api} from './api';
import LibraryResearch,{canonical,formatLibraryMetric as metric} from './LibraryResearch';
import type {Profile} from './model';
import {familyName,timeframe} from './research';

type Entry={id:string;version:number;name:string;family:string;kind:string;source_url:string;license:string;
 markets:string[];directions:string[];source_default_minutes:number|null;author_recommended_minutes:number|null;
 author:string;availability:string;local_default_minutes:number;timeframes:number[];timeframe_evidence:string;adaptation:string;review:string;
 compatibility:string;verification:string;parameters:Record<string,{type:string;default:string|number;min:string|number;max:string|number}>};
const descriptions:Record<string,string>={
 'ema-trend':'Follow sustained trends with two moving averages. Stay in cash when the trend weakens.',
 'donchian-breakout':'Buy a breakout above prior highs. Exit when price breaks below the shorter channel.',
 'historical-return':'Follow price direction over a chosen lookback. A simple momentum reference.',
 'macd-tolerance':'Look for momentum strong enough to clear a threshold relative to the fast EMA.',
 'bb-rsi-reversion':'Combine a lower Bollinger band touch with oversold RSI; exit toward the mean.',
 'rsi-threshold':'Buy oversold conditions and exit after strength returns. Exposed in persistent downtrends.',
 'native-ema-cross':'Original Python trend strategy with long and short positions. Customize to review and explicitly trust Python before execution.'
};
function Card({entry,onCopy,onSelection,report,stale,market,hidden,onOpenRun,onTest,testRequest}:{entry:Entry;onTest:()=>void;testRequest?:{id:string;request:number};onCopy:(id:string)=>Promise<void>;onSelection?:(id:string,value:any)=>void;report:any;stale:boolean;market?:string;hidden:boolean;onOpenRun:(id:string)=>void}){
 const [minutes,setMinutes]=useState(entry.local_default_minutes),[compare,setCompare]=useState<number[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [included,setIncluded]=useState(false);
 useEffect(()=>{if(testRequest)setIncluded(testRequest.id===entry.id);},[testRequest]);
 const [parameters,setParameters]=useState<Record<string,string>>(Object.fromEntries(Object.entries(entry.parameters).map(([k,v])=>[k,String(v.default)])));
 const values=Object.fromEntries(Object.entries(parameters).map(([k,v])=>[k,entry.parameters[k].type==='decimal'?v:Number(v)]));
 const frames=[...new Set([minutes,...compare])].sort((a,b)=>a-b);
 const selections=frames.map(m=>({entry_id:entry.id,version:entry.version,minutes:m,parameters:values}));
 const selectionKey=canonical(selections);
 useEffect(()=>{onSelection?.(entry.id,included?selections:null);},[included,selectionKey,onSelection]);
 const savedRows=report?.rows.filter((r:any)=>report.snapshot.rows[r.ordinal].selection?.entry_id===entry.id)??[];
 async function copy(){setBusy(true);setError('');try{
  const result=await api<{strategy_id:string}>('library_copy',{entry_id:entry.id,version:entry.version,minutes,parameters:values});
  await onCopy(result.strategy_id);
 }catch(e){setError(String(e instanceof Error?e.message:e));}finally{setBusy(false);}}
 return <article hidden={hidden} className={`strategy-card ${included?'selected':''}`} aria-label={entry.name}>
  <div className="card-topline"><span className={`family-icon ${entry.family}`}>{entry.family==='mean_reversion'?'⇄':entry.family==='breakout'?'↗':'⌁'}</span><span className="family-label">{familyName(entry.family)}</span><span className="card-kind">{entry.kind==='Native'?'PYTHON':'VISUAL'}</span></div>
  <h3>{entry.name}</h3><p className="card-description">{descriptions[entry.id]??entry.adaptation}</p>
  <div className="card-tags"><span>{entry.directions.join(' / ')}</span><span>{entry.markets.join(' / ')}</span><span>{entry.availability==='verified'?'Implementation verified':'Research candidate'}</span></div>
  {market&&!entry.markets.includes(market)&&<p className="warning-text">Choose {entry.markets.join(' or ')} history to test this strategy.</p>}
  <div className="card-timeframe"><label>Strategy timeframe <select aria-label={`${entry.name} timeframe`} value={minutes} onChange={e=>setMinutes(Number(e.target.value))}>{entry.timeframes.map(m=><option key={m} value={m}>{timeframe(m)}</option>)}</select></label><span>Compare also</span><div className="timeframe-chips">{[60,240,1440].filter(m=>entry.timeframes.includes(m)&&m!==minutes).map(m=><button key={m} aria-label={`${entry.name} compare ${timeframe(m)}`} aria-pressed={compare.includes(m)} onClick={()=>setCompare(old=>old.includes(m)?old.filter(v=>v!==m):[...old,m])}>{timeframe(m)}</button>)}</div></div>
  <div className="card-results" role="status">{!savedRows.length?<><span className="untested-mark">—</span><strong>No saved result yet</strong><small>Performance: N/A · Measure return and risk on your history.</small></>:savedRows.map((r:any)=>{const s=report.snapshot.rows[r.ordinal].selection,prior=stale||!selections.some(v=>canonical(v)===canonical(s));return <div className="card-result-row" key={r.ordinal}><span>{timeframe(s.minutes)}<small>{prior?'Prior run — changed inputs':'Saved result'}</small></span><strong className={Number(r.metrics?.period_return)>=0?'positive':'negative'}>{metric(r.metrics?.period_return,true)}<small>return</small></strong><span>{metric(r.metrics?.max_drawdown,true)}<small>drawdown</small></span>{r.status==='completed'&&<button aria-label={`Open ${entry.name} ${timeframe(s.minutes)} report`} onClick={()=>onOpenRun(r.run_id)}>↗</button>}</div>;})}</div>
  {onSelection&&<button className="primary full-width test-strategy" onClick={onTest}>Test this strategy</button>}<div className="card-actions">{onSelection&&<label className={`select-strategy ${included?'checked':''}`}><input type="checkbox" aria-label={`Include ${entry.name}`} checked={included} onChange={e=>setIncluded(e.target.checked)}/>{included?`${frames.length} ${frames.length===1?'test':'tests'} selected`:'Add to comparison'}</label>}<button disabled={busy} title="Create an independent editable copy" onClick={copy}>{busy?'Creating…':'Customize strategy'}</button></div>
  <details className="card-details"><summary>Parameters & source review</summary><div className="two-columns">{Object.entries(entry.parameters).map(([name,field])=><label className="field" key={name}>{name.replaceAll('_',' ')}<input aria-label={`${entry.name} ${name}`} type="number" step={field.type==='integer'?1:'any'} min={field.min} max={field.max} value={parameters[name]} onChange={e=>setParameters(p=>({...p,[name]:e.target.value}))}/></label>)}</div>
   <p>{entry.adaptation}</p><p>{entry.author} · {entry.license} · v{entry.version}</p><a href={entry.source_url} target="_blank" rel="noreferrer">Inspect pinned source ↗</a><p>Source default: {entry.source_default_minutes===null?'unspecified':timeframe(entry.source_default_minutes)}. Author recommendation: {entry.author_recommended_minutes===null?'unknown':timeframe(entry.author_recommended_minutes)}.</p><p>{entry.timeframe_evidence}</p><p>{entry.review}</p><p>{entry.compatibility}</p><p>{entry.verification}</p>
   {savedRows.map((r:any)=>r.metrics&&<p key={r.ordinal}>{timeframe(report.snapshot.rows[r.ordinal].selection.minutes)} · Net PnL {metric(r.metrics.net_pnl)} USDT · Equity {metric(r.metrics.final_equity)} · {r.metrics.completed_positions} positions · Win rate {metric(r.metrics.win_rate,true)} · Fees {metric(r.metrics.fees)} / funding {metric(r.metrics.funding)} · Annualized {metric(r.metrics.annualized_geometric_return,true)}</p>)}
  </details>{error&&<p role="alert">{error}</p>}
 </article>;
}
export default function StrategyLibrary({onCopy,datasets=[],profile,onProfile,onActive=()=>{},onOpenRun=()=>{},onHistory=()=>{},preferredDataset,view='catalog',onSaved=()=>{},onCatalog=()=>{},onRunHistory=()=>{}}:{view?:'catalog'|'saved';onSaved?:()=>void;onCatalog?:()=>void;onRunHistory?:()=>void;onCopy:(id:string)=>Promise<void>;datasets?:any[];profile?:Profile;onProfile?:(p:Profile)=>void;onActive?:(id:string|null)=>void;onOpenRun?:(id:string)=>void;onHistory?:()=>void;preferredDataset?:{id:string;request:number}}){
 const [testRequest,setTestRequest]=useState<{id:string;request:number}>();
 function test(id:string){setTestRequest(v=>({id,request:(v?.request??0)+1}));const heading=document.getElementById('test-setup');heading?.focus({preventScroll:true});heading?.scrollIntoView?.({block:'nearest'});}
 const [entries,setEntries]=useState<Entry[]|null>(null),[error,setError]=useState(''),[search,setSearch]=useState(''),[family,setFamily]=useState('');
 const [selections,setSelections]=useState<Record<string,any[]>>({}),[report,setReport]=useState<any>(null),[stale,setStale]=useState(false);
 const update=useCallback((id:string,value:any)=>setSelections(previous=>{if(canonical(previous[id]??null)===canonical(value))return previous;const next={...previous};if(value)next[id]=value;else delete next[id];return next;}),[]);
 const receive=useCallback((value:any,changed:boolean)=>{setReport(value);setStale(changed);},[]);
 useEffect(()=>{let current=true;api<Entry[]>('library_catalog').then(v=>{if(current)setEntries(Array.isArray(v)?v:[]);}).catch(e=>{if(current)setError(String(e));});return()=>{current=false;};},[]);
 const selected=Object.values(selections).flat();
 const visible=(entry:Entry)=>(!family||entry.family===family)&&`${entry.name} ${familyName(entry.family)}`.toLowerCase().includes(search.toLowerCase());
 return <section className={`content research-studio ${view==='saved'?'saved-studio':''}`}><div className="studio-heading" hidden={view==='saved'}><div><h1>Test a strategy</h1><p>Choose an idea, use saved history, then compare the results.</p></div><div className="studio-stats"><strong>{entries?.length??'—'}</strong><span>reviewed templates<br/>your results, saved locally</span></div></div>
  <div className="studio-filterbar" hidden={view==='saved'}><label className="strategy-search"><span>⌕</span><input aria-label="Search strategies" placeholder="Search strategies…" value={search} onChange={e=>setSearch(e.target.value)}/></label><div className="family-filters"><button aria-pressed={!family} onClick={()=>setFamily('')}>All strategies</button>{[...new Set(entries?.map(e=>e.family)??[])].map(f=><button key={f} aria-pressed={family===f} onClick={()=>setFamily(f)}>{familyName(f)}</button>)}</div></div>
  {error&&<p role="alert">{error}</p>}{!entries&&!error&&<p role="status">Loading library…</p>}
  {view==='saved'&&<div className="studio-heading"><div><h1>Saved tests</h1><p>Reopen comparisons and reports without running them again.</p></div><div className="saved-actions"><button onClick={onRunHistory}>Individual run reports</button><button className="primary" onClick={onCatalog}>New test</button></div></div>}<div className="studio-body"><div className="strategy-grid" hidden={view==='saved'}>{entries?.map(entry=><Card key={`${entry.id}:${entry.version}`} entry={entry} onTest={()=>test(entry.id)} testRequest={testRequest} onCopy={onCopy} onSelection={profile?update:undefined} report={report} stale={stale} market={profile?.market} hidden={!visible(entry)} onOpenRun={onOpenRun}/>)}{entries&&!entries.some(visible)&&<p>No strategies match this search.</p>}</div>{profile&&<LibraryResearch view={view} onSaved={onSaved} catalog={entries??[]} selections={selected} datasets={datasets} profile={profile} onProfile={onProfile} onHistory={onHistory} preferredDataset={preferredDataset} onActive={onActive} onOpenRun={onOpenRun} onReport={receive}/>}</div><p className="research-footnote">Strategies are research hypotheses. Saved performance includes configured costs; past returns do not establish future returns.</p>
 </section>;
}
