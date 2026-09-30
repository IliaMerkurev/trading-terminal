import {useEffect,useRef,useState} from 'react';
import {api} from './api';
import {poll} from './poll';
import type {Profile} from './model';
import ResearchSettings from './ResearchSettings';
import {timeframe} from './research';

export const canonical=(value:any):string=>JSON.stringify(value,(_key,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
const utc=(value:number)=>new Date(value*1000).toISOString().slice(0,16);
const number=(value:any,percent=false)=>value===null||value===undefined?'N/A':(Number(value)*(percent?100:1)).toFixed(percent?2:4)+(percent?'%':'');
export function cohortKey(spec:any){const p={...spec.profile};delete p.primary_minutes;return canonical({profile:p,dataset:spec.dataset?.id});}
export const formatLibraryMetric=number;
export function researchProfileSnapshot(profile:Profile){const value={...profile};if(Number(value.execution_minutes??1)===1)delete value.execution_minutes;return value;}
export function librarySortValue(report:any,row:any,sort:string){
 if(!sort.startsWith('delta_'))return row.metrics?.[sort];
 const baselines=report.rows.filter((r:any)=>report.snapshot.rows[r.ordinal].kind==='benchmark');
 const baseline=baselines[sort==='delta_hold'?0:1];
 return row.metrics&&baseline?.metrics&&report.snapshot.rows[row.ordinal].kind!=='benchmark'?Number(row.metrics.period_return)-Number(baseline.metrics.period_return):null;
}
export function filterLibraryRows(report:any,catalog:any[],filters:Record<string,string>):any[]{return report.rows.filter((r:any)=>{const s=report.snapshot.rows[r.ordinal],entry=catalog.find(e=>e.id===s.selection?.entry_id);return (!filters.family||entry?.family===filters.family)&&(!filters.minutes||String(s.profile?.primary_minutes)===filters.minutes)&&(!filters.status||r.status===filters.status)&&(!filters.review||entry?.availability===filters.review);});}
export function sortedLibraryRows(report:any,sort:string){if(report.snapshot.phase==='out_of_sample')return [...report.rows];return [...report.rows].sort((a,b)=>{
 const ca=cohortKey(report.snapshot.rows[a.ordinal]),cb=cohortKey(report.snapshot.rows[b.ordinal]);if(ca!==cb)return ca.localeCompare(cb);
 const av=librarySortValue(report,a,sort),bv=librarySortValue(report,b,sort);if(av==null)return bv==null?a.ordinal-b.ordinal:1;if(bv==null)return -1;
 return (sort==='max_drawdown'?Number(av)-Number(bv):Number(bv)-Number(av))||a.ordinal-b.ordinal;
});}

function Equity({data}:{data:any}){
 const colors=['#7eabff','#42cda8','#e0b95e'],values=data.curves.flatMap((c:any)=>c.points.map((p:any)=>Number(p.equity)));
 const low=Math.min(Number(data.capital),...values),high=Math.max(Number(data.capital),...values),span=high-low||1;
 return <figure><figcaption>Equity · USDT · {utc(data.start)} — {utc(data.end)} UTC</figcaption>
 <svg viewBox="0 0 800 240" role="img" aria-label="Strategy, Buy and Hold, and DCA equity comparison" style={{width:'100%',maxHeight:260}}>
 <text x="0" y="16" fill="currentColor">{high.toFixed(2)}</text><text x="0" y="232" fill="currentColor">{low.toFixed(2)}</text>
 {data.curves.map((c:any,i:number)=><polyline key={i} fill="none" stroke={colors[i]} strokeWidth="2" points={c.points.map((p:any)=>`${70+720*(p.time_ns/1e9-data.start)/(data.end-data.start)},${220-200*(Number(p.equity)-low)/span}`).join(' ')}/>)}</svg>
 <p>{data.curves.map((c:any,i:number)=><span key={i} style={{color:colors[i],marginRight:16}}>{c.name}: {c.status}{!c.points.length?' · N/A':''}</span>)}</p><small>{data.note}</small></figure>;
}

export default function LibraryResearch({selections,datasets,profile,onActive,onOpenRun,onReport,catalog=[],onProfile,onHistory=()=>{},preferredDataset}:{selections:any[];datasets:any[];profile:Profile;catalog?:any[];onActive:(id:string|null)=>void;onOpenRun:(id:string)=>void;onReport:(report:any,stale:boolean)=>void;onProfile?:(p:Profile)=>void;onHistory?:()=>void;preferredDataset?:{id:string;request:number}}){
 const [dataset,setDataset]=useState(''),[spot,setSpot]=useState(''),[range,setRange]=useState(['','']),[interval,setInterval]=useState('weekly');
 const [preview,setPreview]=useState<any>(null),[list,setList]=useState<any[]>([]),[selected,setSelected]=useState(''),[report,setReport]=useState<any>(null);
 const [filters,setFilters]=useState<Record<string,string>>({family:'',minutes:'',status:'',review:''});
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[sort,setSort]=useState('net_pnl'),[equity,setEquity]=useState<any>(null);
 const [warmup,setWarmup]=useState<any>(null),[starting,setStarting]=useState(false);
 const [historyRequest,setHistoryRequest]=useState(0);
 const [warmupLoading,setWarmupLoading]=useState(false),[metadataLoading,setMetadataLoading]=useState(false);
 const selectedRef=useRef(selected);selectedRef.current=selected;
 const editedRange=useRef(false),profileRef=useRef(profile);profileRef.current=profile;
 const compatible=datasets.filter(d=>d.market===profile.market&&d.symbol===profile.symbol&&(d.interval_seconds??60)===Number(profile.execution_minutes??1)*60);
 const request={selections,dataset_id:dataset,profile:researchProfileSnapshot(profile),start:Date.parse(range[0]+'Z')/1000,end:Date.parse(range[1]+'Z')/1000,interval,spot_dataset_id:profile.market==='spot'?null:spot||null};
 const requestKey=canonical(request),stale=!!report&&canonical(report.snapshot.inputs)!==requestKey;
 const active=report?.active_id??(starting?selected:null),holdout=report?.snapshot.phase==='out_of_sample';
 async function refresh(){const v=await api<any[]>('library_batches');if(Array.isArray(v))setList(v);}
 async function action(work:()=>Promise<void>){setBusy(true);setError('');try{await work();await refresh();}catch(e){setError(String(e instanceof Error?e.message:e));}finally{setBusy(false);}}
 useEffect(()=>{refresh().catch(e=>setError(String(e)));},[]);
 useEffect(()=>{setPreview(null);},[requestKey]);
 useEffect(()=>{setEquity(null);setFilters({family:'',minutes:'',status:'',review:''});},[selected]);
 useEffect(()=>{onReport(holdout?null:report,stale);},[report,stale,holdout]);
 useEffect(()=>{if(!selected)return;return poll(()=>api<any>('library_batch_status',{batch_id:selected}),r=>{setReport(r);setStarting(false);setList(rows=>rows.map(row=>row.id===r.id?{...row,status:r.status}:row));onActive(r.active_id);},e=>setError(String(e)),700);},[selected]);
 function choose(id:string){setHistoryRequest(v=>v+1);editedRange.current=false;setDataset(id);setWarmup(null);const d=datasets.find(d=>d.id===id);if(d)setRange([utc(d.range[0]),utc(d.range[1])]);}
 useEffect(()=>{if(preferredDataset&&compatible.some(d=>d.id===preferredDataset.id))choose(preferredDataset.id);},[preferredDataset?.request]);
 useEffect(()=>{setDataset(current=>compatible.some(d=>d.id===current)?current:'');},[profile.market,profile.symbol,profile.execution_minutes]);
 useEffect(()=>{let current=true;setWarmup(null);setWarmupLoading(false);if(!dataset||!selections.length||selections.length>12)return;setWarmupLoading(true);api<any>('library_warmup',{selections,dataset_id:dataset}).then(v=>{if(current&&Number.isFinite(v.start)){setWarmup(v);if(!editedRange.current)setRange([utc(v.start),utc(v.end)]);}}).catch(e=>{if(current)setError(String(e));}).finally(()=>{if(current)setWarmupLoading(false);});return()=>{current=false;};},[dataset,canonical(selections),historyRequest]);
 useEffect(()=>{setMetadataLoading(false);if(!dataset||!onProfile)return;let current=true;setMetadataLoading(true);api<any>('dataset_profile',{dataset_id:dataset}).then(fields=>{if(current&&fields?.tick_size)onProfile({...profileRef.current,...fields});}).catch(e=>{if(current)setError(String(e));}).finally(()=>{if(current)setMetadataLoading(false);});return()=>{current=false;};},[dataset]);
 return <><div className="research-setup-host"><section className="research-setup"><div className="setup-heading"><span className="step-number">2</span><div><h3>Set up your backtest</h3><small>{selections.length} strategy / timeframe tests selected</small></div></div>
 {onProfile?<ResearchSettings profile={profile} onChange={onProfile}/>:<p>{profile.market} {profile.symbol} · capital {String(profile.capital)} USDT · fee {number(profile.fee_rate,true)} · slippage {number(profile.slippage,true)}</p>}
 {error&&<p role="alert">{error}</p>}
 <label className="field">Saved history<select aria-label="Batch dataset" value={dataset} onChange={e=>choose(e.target.value)}><option value="">Choose prepared history</option>{compatible.map(d=><option key={d.id} value={d.id}>{d.symbol} · {utc(d.range[0]).slice(0,10)} — {utc(d.range[1]).slice(0,10)} · {d.source}</option>)}</select></label>
 {!compatible.length&&<div className="setup-empty"><p>No matching history yet.</p><button onClick={onHistory}>Prepare history →</button></div>}
 {profile.market!=='spot'&&<label className="field">Spot alternative dataset<select aria-label="Spot alternative dataset" value={spot} onChange={e=>setSpot(e.target.value)}><option value="">Unavailable · N/A</option>{datasets.filter(d=>d.market==='spot'&&d.symbol===profile.symbol).map(d=><option key={d.id} value={d.id}>{d.source} · {utc(d.range[0])}</option>)}</select></label>}
 <details className="date-settings" open={!!dataset}><summary>Test period & warmup</summary>{['Evaluation start (UTC)','Evaluation end, exclusive (UTC)'].map((label,i)=><label className="field" key={label}>{label}<input aria-label={label} type="datetime-local" value={range[i]} onChange={e=>{editedRange.current=true;setRange(r=>r.map((v,j)=>i===j?e.target.value:v));}}/></label>)}
 {warmup&&<p className={warmup.available?'warmup-note':'warning-text'}>{warmup.available?`Warmup reserved. Suggested start: ${utc(warmup.start).replace('T',' ')} UTC.`:'Not enough preceding history for these parameters. Prepare a longer range.'}<button onClick={()=>{editedRange.current=false;setRange([utc(warmup.start),utc(warmup.end)]);}}>Use suggested period</button></p>}</details>
 <label>DCA schedule<select aria-label="DCA schedule" value={interval} onChange={e=>setInterval(e.target.value)}>{['daily','weekly','monthly'].map(v=><option key={v}>{v}</option>)}</select></label>
 <p className="baseline-note">Includes Buy &amp; Hold + DCA with the same initial capital, costs and full close. Perpetuals use separate spot alternatives. Annualized return is N/A below one year.</p>
 {selections.length>12&&<p className="warning-text">Select at most 12 strategy/timeframe tests.</p>}
 {(warmupLoading||metadataLoading)&&<p role="status">Preparing warmup and instrument settings…</p>}
 <button className="primary full-width" disabled={busy||warmupLoading||metadataLoading||!!active||!dataset||!selections.length||selections.length>12||!range[0]||!range[1]} onClick={()=>action(async()=>setPreview(await api('library_batch_preview',request)))}>Preview batch</button>
 {preview&&<div className="batch-preview"><strong>{preview.rows.length} runs · {preview.modeled_minutes.toLocaleString()} source candles</strong><small>Includes warmup and passive benchmarks</small>{preview.rows.map((r:any,i:number)=><p className={r.error?'warning-text':''} key={i}>{r.error?'!':'✓'} {r.name}{r.contract?.minutes?` · ${timeframe(r.contract.minutes)}`:''}<small>{r.error??'Ready for data verification'}</small></p>)}<button className="primary full-width" disabled={busy||!!active||!preview.rows.some((r:any)=>r.kind!=='benchmark'&&!r.error)} onClick={()=>action(async()=>{const r=await api<any>('library_batch_start',{...request,expected_contract:preview.contract_sha256});setReport(null);setStarting(true);setSelected(r.batch_id);onActive(r.batch_id);})}>Start frozen batch</button></div>}
 {active&&<div className="active-research" role="status"><strong>Backtest running</strong><p>{report?.rows.filter((r:any)=>r.status==='completed').length??0}/{report?.rows.length??preview?.rows.length??0} runs complete</p><button onClick={()=>action(async()=>{await api('library_batch_cancel',{active_id:active});})}>Cancel batch</button></div>}
 </section></div><section className="research-results" id="research-comparisons"><div className="results-heading"><div><div className="eyebrow">SAVED RESEARCH</div><h2>Compare the evidence</h2></div><span className="count-badge">{list.length} batches</span></div>
 <label className="field">Saved batches<select aria-label="Saved library batches" value={selected} disabled={busy||!!active} onChange={e=>{setSelected(e.target.value);setReport(null);setEquity(null);}}><option value="">Select saved batch</option>{list.map(r=><option key={r.id} value={r.id}>{r.created_at} · {r.status} · {r.phase??'selection'}</option>)}</select></label>
 {report&&<>{holdout&&<div className="assumption"><h4>Later-period verification — excluded from selection ranking</h4><p>Selection: {report.snapshot.validation.selection_range.map(utc).join(' — ')} UTC. Verification: {utc(report.snapshot.start)} — {utc(report.snapshot.end)} UTC.</p><p>Attempted selection variants: {report.snapshot.validation.selection_attempted_variants}. Holdout attempt: {report.snapshot.validation.holdout_attempt}. Source version date: {report.snapshot.validation.source_version_date}.</p><p>{report.snapshot.validation.warning}</p>{report.status==='frozen'&&<button disabled={busy||!!active} onClick={()=>action(async()=>{await api('library_validation_start',{batch_id:selected});setStarting(true);onActive(selected);})}>Run frozen later-period verification</button>}</div>}<p role="status">{report.status} · {report.rows.filter((r:any)=>r.status==='completed').length}/{report.rows.length} completed · {holdout?'Separate frozen verification contract':stale?'Prior run — inputs changed; rerun required':'Matches current inputs'}</p>{report.error&&<p role="alert">{report.error}</p>}
 {!active&&['cancelled','interrupted','failed'].includes(report.status)&&report.rows.some((r:any)=>r.status==='pending')&&<button disabled={busy} onClick={()=>action(async()=>{await api('library_batch_resume',{batch_id:selected});setStarting(true);onActive(selected);})}>Resume pending rows with frozen inputs</button>}
 <label>Sort within matching cohorts<select disabled={holdout} aria-label="Library sort" value={sort} onChange={e=>setSort(e.target.value)}>{[['net_pnl','Net PnL'],['period_return','Period return'],['delta_hold','Delta vs Buy & Hold'],['delta_dca','Delta vs DCA'],['max_drawdown','Lowest drawdown'],['completed_positions','Completed positions'],['win_rate','Win rate']].map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
 <div className="two-columns">{[['family','Family',[...new Set(catalog.map(e=>e.family))]],['minutes','Timeframe',[...new Set(report.snapshot.rows.map((s:any)=>String(s.profile?.primary_minutes??'')))].filter(Boolean)],['status','Compatibility / result state',[...new Set(report.rows.map((r:any)=>r.status))]],['review','Review status',[...new Set(catalog.map(e=>e.availability))]]].map(([key,label,options]:any)=><label key={key}>{label}<select aria-label={`Library filter ${label}`} value={filters[key]} onChange={e=>setFilters(f=>({...f,[key]:e.target.value}))}><option value="">All</option>{options.map((v:string)=><option key={v} value={v}>{v}</option>)}</select></label>)}</div>
 <p>Groups retain identical dataset, capital, leverage, costs and execution profile. Strategy timeframes may differ. Passive baselines are shown separately. Failed or unavailable rows have N/A metrics.</p>
 {!holdout&&<p>To verify a completed candidate later, choose a non-overlapping later dataset/range above, then freeze its row. Its saved parameters, timeframe, capital and profile remain fixed; current card/profile edits are ignored. Review the frozen contract before starting.</p>}
 <div className="table-scroll"><table><thead><tr><th>Strategy / cohort</th><th>State</th><th>Net PnL / return</th><th>Equity</th><th>Drawdown</th><th>Positions / win rate</th><th>Fees / funding</th><th>Annualized</th><th>vs Buy &amp; Hold / DCA</th><th>Report</th></tr></thead><tbody>{sortedLibraryRows(report,sort).filter((r:any)=>filterLibraryRows(report,catalog,filters).includes(r)).map((r:any)=>{
 const s=report.snapshot.rows[r.ordinal],m=r.metrics,baselines=report.rows.filter((v:any)=>report.snapshot.rows[v.ordinal].kind==='benchmark');
 return <tr key={r.ordinal}><td>{s.name}<small>{s.profile?`${s.profile.market} · ${timeframe(s.profile.primary_minutes)} · ${timeframe(Number(s.profile.execution_minutes??1))} execution · capital ${s.profile.capital} · leverage ${s.profile.leverage} · model ${s.profile.version}`:'No compatible data'}</small></td><td>{r.status}{r.reused?' · cached':''}{r.progress&&` · ${Math.round((r.progress.fraction??0)*100)}%`}{r.error&&<small>{r.error}</small>}</td><td>{number(m?.net_pnl)} / {number(m?.period_return,true)}</td><td>{number(m?.final_equity)}</td><td>{number(m?.max_drawdown,true)}</td><td>{m?.completed_positions??'N/A'} / {number(m?.win_rate,true)}</td><td>{number(m?.fees)} / {number(m?.funding)}</td><td title={m?.annualized_unavailable_reason??''}>{number(m?.annualized_geometric_return,true)}</td><td>{s.kind==='benchmark'?'—':baselines.map((b:any,i:number)=><small key={i}>{m&&b.metrics?`${number(Number(m.net_pnl)-Number(b.metrics.net_pnl))} USDT / ${number(100*(Number(m.period_return)-Number(b.metrics.period_return)))} pp`:'N/A'}</small>)}</td><td>{r.status==='completed'&&<><button onClick={()=>onOpenRun(r.run_id)}>Open report</button>{s.kind!=='benchmark'&&<button onClick={()=>action(async()=>{const owner=selected;const value=await api('library_batch_equity',{batch_id:owner,ordinal:r.ordinal});if(selectedRef.current===owner)setEquity(value);})}>Compare equity</button>}{s.kind!=='benchmark'&&!holdout&&<button disabled={busy||!!active||!dataset} onClick={()=>action(async()=>{const frozen=await api<any>('library_validation_freeze',{batch_id:selected,ordinal:r.ordinal,dataset_id:dataset,start:request.start,end:request.end,spot_dataset_id:spot||null});setSelected(frozen.batch_id);setReport(null);setEquity(null);})}>Freeze later-period candidate</button>}</>}</td></tr>;
 })}</tbody></table></div>{equity&&<Equity data={equity}/>}<details><summary>Frozen input and source contract</summary><pre>{JSON.stringify(report.snapshot,null,2)}</pre></details></>}
 {!report&&<p className="muted">Completed runs appear here with returns, drawdown, costs and comparisons against passive alternatives. Reopen any saved batch above.</p>}
 </section></>;
}
