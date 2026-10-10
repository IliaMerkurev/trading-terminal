import type {HistoryRequest} from './Observations';
import {useCallback,useEffect,useLayoutEffect,useRef,useState} from 'react';
import {api} from './api';
import LibraryResearch,{canonical,formatLibraryMetric as metric} from './LibraryResearch';
import type {Profile} from './model';
import {familyName,timeframe} from './research';
import './lab.css';
import ProfileTransfer from './ProfileTransfer';
import {DisplayedMetrics,DisplayTrackingNotice} from './DisplayedEvidence';
import {cardMetricLabels,cardOrderChoices,finiteCardMetric,isSelectionComparison,orderCards,type CardOrderDirection,type CardOrderMetric,type CardRank} from './cardOrdering';

type TestRequest={id:string|null;request:number;frames?:number[]};
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
function SavedCardResult({row,spec,batchId,prior,entry,onOpenRun,rank,orderMetric,groupNumber}:{row:any;spec:any;batchId:string;prior:boolean;entry:Entry;onOpenRun:(id:string)=>void;rank:CardRank;orderMetric:CardOrderMetric;groupNumber?:number}){
 const returned=finiteCardMetric(row.metrics?.period_return),drawdown=finiteCardMetric(row.metrics?.max_drawdown),positions=finiteCardMetric(row.metrics?.completed_positions);
 const used=rank.ordinal===row.ordinal&&rank.value!==null;
 const availability=[returned,drawdown,positions].map(value=>value!==null).join(':');
 return <DisplayedMetrics observationKey={availability} reference={{surface:'comparison_metrics',batch_id:batchId,ordinal:row.ordinal}}><div className={`card-result-row ${used?'card-result-ordered':''}`}>
  <span>{timeframe(spec.selection.minutes)}<small>{prior?'Prior run — changed inputs':'Saved result'}</small>{spec.selection.version!==entry.version&&<small>Saved v{spec.selection.version}</small>}</span>
  <strong className={returned===null?'':returned>=0?'positive':'negative'}><span data-metric={returned!==null?true:undefined}>{metric(returned,true)}</span><small>return</small></strong>
  <span><span data-metric={drawdown!==null?true:undefined}>{metric(drawdown,true)}</span><small>drawdown</small></span>
  {row.status==='completed'&&<button aria-label={`Open ${entry.name} ${timeframe(spec.selection.minutes)} report`} onClick={()=>onOpenRun(row.run_id)}>↗</button>}
  <small className="card-result-state"><span data-metric={positions!==null?true:undefined}>{positions===null?'N/A':positions} completed positions</span>{row.status==='completed'&&positions===0?' · no trades':row.status!=='completed'?` · ${row.status}`:''}</small>
  <div className="card-order-value" hidden={!used}><strong>{([['period_return',returned],['max_drawdown',drawdown],['completed_positions',positions]] as const).map(([key,value])=><span key={key} hidden={orderMetric!==key} data-metric={value!==null?true:undefined}>{key==='completed_positions'?value:metric(value,true)}</span>)}</strong><span>{cardMetricLabels[orderMetric]} · used for card order<small>{timeframe(spec.selection.minutes)} · Group {groupNumber}</small></span></div>
 </div></DisplayedMetrics>;
}
function Card({entry,onCopy,onSelection,report,stale,market,hidden,onOpenRun,onTest,testRequest,profile,editorProfile,rank,orderMetric,groupNumber}:{profile?:Profile;editorProfile?:Profile;entry:Entry;onTest:()=>void;testRequest?:TestRequest;onCopy:(id:string)=>Promise<void>;onSelection?:(id:string,value:any)=>void;report:any;stale:boolean;market?:string;hidden:boolean;onOpenRun:(id:string)=>void;rank:CardRank;orderMetric:CardOrderMetric;groupNumber?:number}){
 const [minutes,setMinutes]=useState(entry.local_default_minutes),[compare,setCompare]=useState<number[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [included,setIncluded]=useState(false),[transfer,setTransfer]=useState(false);
 useEffect(()=>{if(!testRequest)return;
  if(testRequest.id===null){const frames=testRequest.frames??[];setIncluded(frames.length>0);if(frames.length){setMinutes(frames[0]);setCompare(frames.slice(1));}}
  else setIncluded(testRequest.id===entry.id);
 },[testRequest]);
 const [parameters,setParameters]=useState<Record<string,string>>(Object.fromEntries(Object.entries(entry.parameters).map(([k,v])=>[k,String(v.default)])));
 const values=Object.fromEntries(Object.entries(parameters).map(([k,v])=>[k,entry.parameters[k].type==='decimal'?v:Number(v)]));
 const frames=[...new Set([minutes,...compare])].sort((a,b)=>a-b);
 const selections=frames.map(m=>({entry_id:entry.id,version:entry.version,minutes:m,parameters:values}));
 const selectionKey=canonical(selections);
 useEffect(()=>{onSelection?.(entry.id,included?selections:null);},[included,selectionKey,onSelection]);
 const savedRows=report?.rows.filter((r:any)=>report.snapshot.rows[r.ordinal].selection?.entry_id===entry.id)??[];
 async function copy(chosen?:Profile){setTransfer(false);setBusy(true);setError('');try{
  const result=await api<{strategy_id:string}>('library_copy',{entry_id:entry.id,version:entry.version,minutes,parameters:values,...(chosen?{profile:chosen}:{})});
  await onCopy(result.strategy_id);
 }catch(e){setError(String(e instanceof Error?e.message:e));}finally{setBusy(false);}}
 return <article hidden={hidden} className={`strategy-card ${included?'selected':''}`} aria-label={entry.name}>
  <div className="card-topline"><span className={`family-icon ${entry.family}`}>{entry.family==='mean_reversion'?'⇄':entry.family==='breakout'?'↗':'⌁'}</span><span className="family-label">{familyName(entry.family)}</span><span className="card-kind">{entry.kind==='Native'?'PYTHON':'VISUAL'}</span></div>
  <h3>{entry.name}</h3><p className="card-description">{descriptions[entry.id]??entry.adaptation}</p>{onSelection&&<button className="primary full-width test-strategy" onClick={onTest}>Test this strategy</button>}
  <div className="card-tags"><span>{entry.directions.join(' / ')}</span><span>{entry.markets.join(' / ')}</span><span>{entry.availability==='verified'?'Implementation verified':'Research candidate'}</span></div>
  {market&&!entry.markets.includes(market)&&<p className="warning-text">Choose {entry.markets.join(' or ')} history to test this strategy.</p>}
  <div className="card-timeframe"><label>Strategy timeframe <select aria-label={`${entry.name} timeframe`} value={minutes} onChange={e=>setMinutes(Number(e.target.value))}>{entry.timeframes.map(m=><option key={m} value={m}>{timeframe(m)}</option>)}</select></label><span>Compare also</span><div className="timeframe-chips">{[60,240,1440].filter(m=>entry.timeframes.includes(m)&&m!==minutes).map(m=><button key={m} aria-label={`${entry.name} compare ${timeframe(m)}`} aria-pressed={compare.includes(m)} onClick={()=>setCompare(old=>old.includes(m)?old.filter(v=>v!==m):[...old,m])}>{timeframe(m)}</button>)}</div></div>
  <div className="card-results" role="status">{orderMetric!=='name'&&rank.value===null&&<p className="card-order-unavailable">Card order: N/A · {rank.reason}</p>}{!savedRows.length?<><span className="untested-mark">—</span><strong>{report?'Not in selected comparison':'No comparison selected'}</strong><small>Performance: N/A · Measure return and risk on your history.</small></>:savedRows.map((r:any)=>{const s=report.snapshot.rows[r.ordinal],prior=stale||!selections.some(v=>canonical(v)===canonical(s.selection));return <SavedCardResult key={`${report.id}:${r.ordinal}`} row={r} spec={s} batchId={report.id} prior={prior} entry={entry} onOpenRun={onOpenRun} rank={rank} orderMetric={orderMetric} groupNumber={groupNumber}/>;})}</div>
  <div className="card-actions">{onSelection&&<label className={`select-strategy ${included?'checked':''}`}><input type="checkbox" aria-label={`Include ${entry.name}`} checked={included} onChange={e=>setIncluded(e.target.checked)}/>{included?`${frames.length} ${frames.length===1?'test':'tests'} selected`:'Add to comparison'}</label>}<button disabled={busy} title="Create an independent editable copy" onClick={()=>profile&&editorProfile?setTransfer(true):copy()}>{busy?'Creating…':'Customize strategy'}</button></div>
  <details className="card-details"><summary>Parameters & source review</summary><div className="two-columns">{Object.entries(entry.parameters).map(([name,field])=><label className="field" key={name}>{name.replaceAll('_',' ')}<input aria-label={`${entry.name} ${name}`} type="number" step={field.type==='integer'?1:'any'} min={field.min} max={field.max} value={parameters[name]} onChange={e=>setParameters(p=>({...p,[name]:e.target.value}))}/></label>)}</div>
   <p>{entry.adaptation}</p><p>{entry.author} · {entry.license} · v{entry.version}</p><a href={entry.source_url} target="_blank" rel="noreferrer">Inspect pinned source ↗</a><p>Source default: {entry.source_default_minutes===null?'unspecified':timeframe(entry.source_default_minutes)}. Author recommendation: {entry.author_recommended_minutes===null?'unknown':timeframe(entry.author_recommended_minutes)}.</p><p>{entry.timeframe_evidence}</p><p>{entry.review}</p><p>{entry.compatibility}</p><p>{entry.verification}</p>
   {savedRows.map((r:any)=>r.metrics&&<p key={r.ordinal}>{timeframe(report.snapshot.rows[r.ordinal].selection.minutes)} · Net PnL {metric(r.metrics.net_pnl)} USDT · Equity {metric(r.metrics.final_equity)} · {r.metrics.completed_positions} positions · Win rate {metric(r.metrics.win_rate,true)} · Fees {metric(r.metrics.fees)} / funding {metric(r.metrics.funding)} · Annualized {metric(r.metrics.annualized_geometric_return,true)}</p>)}
  </details>{transfer&&profile&&editorProfile&&<ProfileTransfer native={entry.kind==='Native'} lab={profile} editor={editorProfile} minutes={minutes} onChoose={copy} onCancel={()=>setTransfer(false)}/>}{error&&<p role="alert">{error}</p>}
 </article>;
}
export default function StrategyLibrary({onCopy,datasets=[],profile,editorProfile,onProfile,onActive=()=>{},onOpenRun=()=>{},onHistory=()=>{},preferredDataset,view='catalog',onSaved=()=>{},onCatalog=()=>{},onRunHistory=()=>{},suspendSetup=false,onObservation,preferredBatch}:{onObservation?:(id:string,revision:number)=>void;preferredBatch?:{id:string;request:number};editorProfile?:Profile;suspendSetup?:boolean;view?:'catalog'|'saved';onSaved?:()=>void;onCatalog?:()=>void;onRunHistory?:()=>void;onCopy:(id:string)=>Promise<void>;datasets?:any[];profile?:Profile;onProfile?:(p:Profile)=>void;onActive?:(id:string|null)=>void;onOpenRun?:(id:string)=>void;onHistory?:(origin?:'later',profile?:Profile)=>void;preferredDataset?:HistoryRequest}){
 const scrollSurface=useRef<HTMLElement>(null),viewScroll=useRef({catalog:0,saved:0});
 // The mounted views share one scroll element; keep their offsets independent.
 useLayoutEffect(()=>{if(!suspendSetup&&scrollSurface.current)scrollSurface.current.scrollTop=viewScroll.current[view];},[view,suspendSetup]);
 const [testRequest,setTestRequest]=useState<TestRequest>();
 function test(id:string){setTestRequest(v=>({id,request:(v?.request??0)+1}));}
 const [entries,setEntries]=useState<Entry[]|null>(null),[error,setError]=useState(''),[search,setSearch]=useState(''),[family,setFamily]=useState('');
 const [selections,setSelections]=useState<Record<string,any[]>>({}),[report,setReport]=useState<any>(null),[stale,setStale]=useState(false);
 const [orderMetric,setOrderMetric]=useState<CardOrderMetric>('name'),[orderDirection,setOrderDirection]=useState<CardOrderDirection>('asc');
 const [orderContext,setOrderContext]=useState({batchId:'',minutes:'',group:''}),[orderContextOpen,setOrderContextOpen]=useState(false);
 const update=useCallback((id:string,value:any)=>setSelections(previous=>{if(canonical(previous[id]??null)===canonical(value))return previous;const next={...previous};if(value)next[id]=value;else delete next[id];return next;}),[]);
 const receive=useCallback((value:any,changed:boolean,comparisonId:string)=>{setReport(value);setStale(changed);setOrderContext(current=>current.batchId===comparisonId?current:{batchId:comparisonId,minutes:'',group:''});},[]);
 useEffect(()=>{let current=true;api<Entry[]>('library_catalog').then(v=>{if(current)setEntries(Array.isArray(v)?v:[]);}).catch(e=>{if(current)setError(String(e));});return()=>{current=false;};},[]);
 const selected=(entries??[]).flatMap(entry=>selections[entry.id]??[]);
 const choices=cardOrderChoices(report),context=orderContext.batchId===report?.id?orderContext:{minutes:'',group:''};
 const savedMinutes=choices.timeframes.includes(Number(context.minutes))?context.minutes:choices.timeframes.length===1?String(choices.timeframes[0]):'';
 const groups=choices.groups.filter(group=>group.minutes.includes(Number(savedMinutes)));
 const savedGroup=groups.some(group=>group.key===context.group)?context.group:groups.length===1?groups[0].key:'';
 const groupNumber=groups.find(group=>group.key===savedGroup)?.number;
 const ordered=orderCards(entries??[],report,savedMinutes?Number(savedMinutes):null,savedGroup,orderMetric,orderDirection);
 const comparisonReady=isSelectionComparison(report),metricOrder=orderMetric!=='name';
 const needsOrderContext=metricOrder&&comparisonReady&&(!savedMinutes||!savedGroup);
 useEffect(()=>{if(needsOrderContext)setOrderContextOpen(true);},[needsOrderContext]);
 const savedPeriod=Number.isFinite(report?.snapshot.start)&&Number.isFinite(report?.snapshot.end)?`${new Date(report.snapshot.start*1000).toISOString().replace('.000Z','')} — ${new Date(report.snapshot.end*1000).toISOString().replace('.000Z','')} UTC (end exclusive)`:'Saved evaluation period unavailable';
 const batchFrames=entries?.[0]?.timeframes.filter(m=>entries.every(e=>e.timeframes.includes(m)))??[];
 const [lastBatchFrames,setLastBatchFrames]=useState([240,1440]);
 function batch(){setTestRequest(v=>({id:null,request:(v?.request??0)+1,frames:lastBatchFrames.filter(m=>batchFrames.includes(m))}));}
 function changeBatchFrame(m:number){const frames=(testRequest?.frames??[]).includes(m)?(testRequest?.frames??[]).filter(v=>v!==m):[...(testRequest?.frames??[]),m].sort((a,b)=>a-b);setLastBatchFrames(frames);setTestRequest(v=>v?{...v,frames}:v);}
 const batchControls=testRequest?.id===null?<fieldset className="batch-timeframes"><legend>Batch timeframes · all {entries?.length??0} strategies</legend><p>One shared history, period, capital, sizing and cost profile. Each strategy keeps its current card parameters across timeframes. Incompatible rows remain visible in the saved comparison.</p><div>{batchFrames.map(m=><label key={m}><input type="checkbox" aria-label={`Batch timeframe ${timeframe(m)}`} checked={testRequest.frames?.includes(m)??false} onChange={()=>changeBatchFrame(m)}/>{timeframe(m)}</label>)}</div>{!testRequest.frames?.length&&<p role="alert">Choose at least one timeframe.</p>}</fieldset>:null;
 const visible=(entry:Entry)=>(!family||entry.family===family)&&`${entry.name} ${familyName(entry.family)}`.toLowerCase().includes(search.toLowerCase());
 return <section ref={scrollSurface} onScroll={e=>{if(!suspendSetup&&!e.currentTarget.closest('[hidden]'))viewScroll.current[view]=e.currentTarget.scrollTop;}} className={`content research-studio lab-studio ${view==='saved'?'saved-studio':''}`}><div className="studio-heading" hidden={view==='saved'}><div><h1>Strategy lab</h1><p>Choose an idea, use saved history, then compare the results.</p></div><div className="studio-stats">{profile&&<button className="primary" disabled={!entries?.length} onClick={batch}>Test all strategies</button>}<strong>{entries?.length??'—'}</strong><span>reviewed templates<br/>your results, saved locally</span></div></div>
  <div className="studio-filterbar" hidden={view==='saved'}><label className="strategy-search"><span>⌕</span><input aria-label="Search strategies" placeholder="Search strategies…" value={search} onChange={e=>setSearch(e.target.value)}/></label><div className="family-filters"><button aria-pressed={!family} onClick={()=>setFamily('')}>All strategies</button>{[...new Set(entries?.map(e=>e.family)??[])].map(f=><button key={f} aria-pressed={family===f} onClick={()=>setFamily(f)}>{familyName(f)}</button>)}</div></div>
  <section className="card-ordering" aria-label="Card ordering" hidden={view==='saved'}><div className="card-order-controls"><label>Order cards<select aria-label="Order cards" value={orderMetric} onChange={e=>{const metric=e.target.value as CardOrderMetric;setOrderMetric(metric);setOrderDirection(metric==='name'||metric==='max_drawdown'?'asc':'desc');}}>{Object.entries(cardMetricLabels).map(([key,label])=><option key={key} value={key} disabled={key!=='name'&&!comparisonReady}>{label}</option>)}</select></label><label>Direction<select aria-label="Card order direction" value={orderDirection} onChange={e=>setOrderDirection(e.target.value as CardOrderDirection)}><option value="asc">{metricOrder?'Lowest first':'A–Z'}</option><option value="desc">{metricOrder?'Highest first':'Z–A'}</option></select></label>
   {comparisonReady?<details className="card-order-context" open={orderContextOpen||needsOrderContext} onToggle={e=>{if(needsOrderContext&&!e.currentTarget.open)e.currentTarget.open=true;else setOrderContextOpen(e.currentTarget.open);}}><summary className="card-order-comparison"><strong>{report.metadata?.name||String(report.id).slice(0,12)}</strong>{metricOrder&&<span> · {savedMinutes?timeframe(Number(savedMinutes)):'Choose timeframe'} · {groupNumber?`Group ${groupNumber}`:'Choose group'}{needsOrderContext?' · ordering not applied':''}</span>}<small>{savedPeriod}</small></summary>
    <div className="card-order-config"><button onClick={onSaved}>Change saved comparison</button>{metricOrder&&<><div className="card-order-controls"><label>Saved timeframe<select aria-label="Card saved timeframe" value={savedMinutes} onChange={e=>setOrderContext({batchId:report.id,minutes:e.target.value,group:''})}><option value="">Choose saved timeframe</option>{choices.timeframes.map(minutes=><option key={minutes} value={minutes}>{timeframe(minutes)}</option>)}</select></label><label className="card-order-group">Compatible group<select aria-label="Card compatible group" value={savedGroup} disabled={!savedMinutes} onChange={e=>setOrderContext({batchId:report.id,minutes:savedMinutes,group:e.target.value})}><option value="">Choose compatible group</option>{groups.map(group=><option key={group.key} value={group.key}>Group {group.number} · {group.profile.symbol} {group.profile.market} · {timeframe(Number(group.profile.execution_minutes??1))} source / execution · {group.profile.capital} USDT · model {group.profile.version}</option>)}</select></label></div><p role="status">{needsOrderContext?'Choose a saved timeframe and compatible group. Metric ordering is not applied; cards remain in name order.':'This comparison, saved timeframe and group only. N/A cards stay last; multiple saved parameter variants are not ranked.'}</p></>}</div>
   </details>:<button onClick={onSaved}>Choose saved comparison</button>}
  </div>{!comparisonReady&&<p>{metricOrder?'Metric ordering is not applied. ':''}Choose a saved selection comparison in Saved tests to order cards by its results.</p>}<DisplayTrackingNotice/></section>
  {error&&<p role="alert">{error}</p>}{!entries&&!error&&<p role="status">Loading library…</p>}
  {view==='saved'&&<div className="studio-heading"><div><h1>Saved tests</h1></div><div className="saved-actions"><button onClick={onRunHistory}>Individual run reports</button><button className="primary" onClick={onCatalog}>New test</button></div></div>}<div className="studio-body"><div className="strategy-grid" hidden={view==='saved'}>{ordered.map(({entry,rank})=><Card key={`${entry.id}:${entry.version}`} entry={entry} rank={rank} orderMetric={orderMetric} groupNumber={groupNumber} onTest={()=>test(entry.id)} testRequest={testRequest} onCopy={onCopy} profile={profile} editorProfile={editorProfile} onSelection={profile?update:undefined} report={report} stale={stale} market={profile?.market} hidden={!visible(entry)} onOpenRun={onOpenRun}/>)}{entries&&!entries.some(visible)&&<p>No strategies match this search.</p>}</div>{profile&&<LibraryResearch onObservation={onObservation} preferredBatch={preferredBatch} batchControls={batchControls} suspendSetup={suspendSetup} setupRequest={testRequest?.request??0} view={view} onSaved={onSaved} catalog={entries??[]} selections={selected} datasets={datasets} profile={profile} onProfile={onProfile} onHistory={onHistory} preferredDataset={preferredDataset} onActive={onActive} onOpenRun={onOpenRun} onReport={receive}/>}</div><p className="research-footnote">Strategies are research hypotheses. Saved performance includes configured costs; past returns do not establish future returns.</p>
 </section>;
}
