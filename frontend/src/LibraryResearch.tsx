import {useEffect,useState} from 'react';
import {api} from './api';
import {poll} from './poll';
import type {Profile} from './model';

export const canonical=(value:any):string=>JSON.stringify(value,(_key,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
const utc=(value:number)=>new Date(value*1000).toISOString().slice(0,16);
const number=(value:any,percent=false)=>value===null||value===undefined?'N/A':(Number(value)*(percent?100:1)).toFixed(percent?2:4)+(percent?'%':'');
export function cohortKey(spec:any){const p={...spec.profile};delete p.primary_minutes;return canonical({profile:p,dataset:spec.dataset?.id});}
export function sortedLibraryRows(report:any,sort:string){return [...report.rows].sort((a,b)=>{
 const ca=cohortKey(report.snapshot.rows[a.ordinal]),cb=cohortKey(report.snapshot.rows[b.ordinal]);if(ca!==cb)return ca.localeCompare(cb);
 const av=a.metrics?.[sort],bv=b.metrics?.[sort];if(av==null)return bv==null?a.ordinal-b.ordinal:1;if(bv==null)return -1;
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

export default function LibraryResearch({selections,datasets,profile,onActive,onOpenRun,onReport}:{selections:any[];datasets:any[];profile:Profile;onActive:(id:string|null)=>void;onOpenRun:(id:string)=>void;onReport:(report:any,stale:boolean)=>void}){
 const [dataset,setDataset]=useState(''),[spot,setSpot]=useState(''),[range,setRange]=useState(['','']),[interval,setInterval]=useState('weekly');
 const [preview,setPreview]=useState<any>(null),[list,setList]=useState<any[]>([]),[selected,setSelected]=useState(''),[report,setReport]=useState<any>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[sort,setSort]=useState('net_pnl'),[equity,setEquity]=useState<any>(null);
 const request={selections,dataset_id:dataset,profile,start:Date.parse(range[0]+'Z')/1000,end:Date.parse(range[1]+'Z')/1000,interval,spot_dataset_id:profile.market==='spot'?null:spot||null};
 const requestKey=canonical(request),stale=!!report&&canonical(report.snapshot.inputs)!==requestKey;
 const active=report?.active_id??null;
 async function refresh(){const v=await api<any[]>('library_batches');if(Array.isArray(v))setList(v);}
 async function action(work:()=>Promise<void>){setBusy(true);setError('');try{await work();await refresh();}catch(e){setError(String(e instanceof Error?e.message:e));}finally{setBusy(false);}}
 useEffect(()=>{refresh().catch(e=>setError(String(e)));},[]);
 useEffect(()=>{setPreview(null);},[requestKey]);
 useEffect(()=>{onReport(report,stale);},[report,stale]);
 useEffect(()=>{if(!selected)return;return poll(()=>api<any>('library_batch_status',{batch_id:selected}),r=>{setReport(r);setList(rows=>rows.map(row=>row.id===r.id?{...row,status:r.status}:row));onActive(r.active_id);},e=>setError(String(e)),700);},[selected]);
 function choose(id:string){setDataset(id);const d=datasets.find(d=>d.id===id);if(d)setRange([utc(d.range[0]),utc(d.range[1])]);}
 return <section className="panel"><h3>Batch research</h3><p>Select cards, choose cached fine-grained history, and leave sufficient history before evaluation for warmup. Prepare missing history through the existing Backtest download controls.</p>
 <p>Common settings: {profile.market} {profile.symbol} · capital {String(profile.capital)} USDT · leverage {String(profile.leverage)} · fee {number(profile.fee_rate,true)} · slippage {number(profile.slippage,true)}. Edit simulation settings in the right panel. Every row has its own account.</p>
 {error&&<p role="alert">{error}</p>}
 <label className="field">Batch dataset<select aria-label="Batch dataset" value={dataset} onChange={e=>choose(e.target.value)}><option value="">Choose cached history</option>{datasets.filter(d=>d.market===profile.market&&d.symbol===profile.symbol).map(d=><option key={d.id} value={d.id}>{d.source} · {utc(d.range[0])} — {utc(d.range[1])}</option>)}</select></label>
 {profile.market!=='spot'&&<label className="field">Spot alternative dataset<select aria-label="Spot alternative dataset" value={spot} onChange={e=>setSpot(e.target.value)}><option value="">Unavailable · N/A</option>{datasets.filter(d=>d.market==='spot'&&d.symbol===profile.symbol).map(d=><option key={d.id} value={d.id}>{d.source} · {utc(d.range[0])}</option>)}</select></label>}
 <div className="two-columns">{['Evaluation start (UTC)','Evaluation end, exclusive (UTC)'].map((label,i)=><label className="field" key={label}>{label}<input aria-label={label} type="datetime-local" value={range[i]} onChange={e=>setRange(r=>r.map((v,j)=>i===j?e.target.value:v))}/></label>)}</div>
 <label>DCA schedule<select aria-label="DCA schedule" value={interval} onChange={e=>setInterval(e.target.value)}>{['daily','weekly','monthly'].map(v=><option key={v}>{v}</option>)}</select></label>
 <p>Buy &amp; Hold and DCA use the same initial capital, cash yield 0, no deposits, and full close with costs. Passive spot alternatives are not risk-equivalent to perpetual strategies. Annualized geometric return is N/A below 365 days.</p>
 <button disabled={busy||!!active||!dataset||!selections.length} onClick={()=>action(async()=>setPreview(await api('library_batch_preview',request)))}>Preview batch</button>
 {preview&&<div className="assumption"><strong>{preview.rows.length} rows · {preview.modeled_minutes.toLocaleString()} modeled minutes including warmup</strong>{preview.rows.map((r:any,i:number)=><p key={i}>{r.name}: {r.error??'Ready for asynchronous data verification'}</p>)}<button disabled={busy||!!active||!preview.rows.some((r:any)=>r.kind!=='benchmark'&&!r.error)} onClick={()=>action(async()=>{const r=await api<any>('library_batch_start',{...request,expected_contract:preview.contract_sha256});setSelected(r.batch_id);onActive(r.batch_id);})}>Start frozen batch</button></div>}
 <label className="field">Saved batches<select aria-label="Saved library batches" value={selected} disabled={busy||!!active} onChange={e=>{setSelected(e.target.value);setReport(null);setEquity(null);}}><option value="">Select saved batch</option>{list.map(r=><option key={r.id} value={r.id}>{r.created_at} · {r.status}</option>)}</select></label>
 {report&&<><p role="status">{report.status} · {report.rows.filter((r:any)=>r.status==='completed').length}/{report.rows.length} completed · {stale?'Prior run — inputs changed; rerun required':'Matches current inputs'}</p>{report.error&&<p role="alert">{report.error}</p>}
 {active&&<button onClick={()=>action(async()=>{await api('library_batch_cancel',{active_id:active});})}>Cancel batch</button>}
 {!active&&['cancelled','interrupted','failed'].includes(report.status)&&report.rows.some((r:any)=>r.status==='pending')&&<button disabled={busy} onClick={()=>action(async()=>{await api('library_batch_resume',{batch_id:selected});onActive(selected);})}>Resume pending rows with frozen inputs</button>}
 <label>Sort within matching cohorts<select aria-label="Library sort" value={sort} onChange={e=>setSort(e.target.value)}>{[['net_pnl','Net PnL'],['max_drawdown','Lowest drawdown'],['completed_positions','Completed positions'],['win_rate','Win rate']].map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
 <p>Groups retain identical dataset, capital, leverage, costs and execution profile. Strategy timeframes may differ. Passive baselines are shown separately. Failed or unavailable rows have N/A metrics.</p>
 <div className="table-scroll"><table><thead><tr><th>Strategy / cohort</th><th>State</th><th>Net PnL / return</th><th>Equity</th><th>Drawdown</th><th>Positions / win rate</th><th>Fees / funding</th><th>Annualized</th><th>vs Buy &amp; Hold / DCA</th><th>Report</th></tr></thead><tbody>{sortedLibraryRows(report,sort).map((r:any)=>{
 const s=report.snapshot.rows[r.ordinal],m=r.metrics,baselines=report.rows.filter((v:any)=>report.snapshot.rows[v.ordinal].kind==='benchmark');
 return <tr key={r.ordinal}><td>{s.name}<small>{s.profile?`${s.profile.market} · ${s.profile.primary_minutes}m · capital ${s.profile.capital} · leverage ${s.profile.leverage} · model ${s.profile.version}`:'No compatible data'}</small></td><td>{r.status}{r.reused?' · cached':''}{r.progress&&` · ${Math.round((r.progress.fraction??0)*100)}%`}{r.error&&<small>{r.error}</small>}</td><td>{number(m?.net_pnl)} / {number(m?.period_return,true)}</td><td>{number(m?.final_equity)}</td><td>{number(m?.max_drawdown,true)}</td><td>{m?.completed_positions??'N/A'} / {number(m?.win_rate,true)}</td><td>{number(m?.fees)} / {number(m?.funding)}</td><td title={m?.annualized_unavailable_reason??''}>{number(m?.annualized_geometric_return,true)}</td><td>{s.kind==='benchmark'?'—':baselines.map((b:any,i:number)=><small key={i}>{m&&b.metrics?`${number(Number(m.net_pnl)-Number(b.metrics.net_pnl))} USDT / ${number(100*(Number(m.period_return)-Number(b.metrics.period_return)))} pp`:'N/A'}</small>)}</td><td>{r.status==='completed'&&<><button onClick={()=>onOpenRun(r.run_id)}>Open report</button>{s.kind!=='benchmark'&&<button onClick={()=>action(async()=>setEquity(await api('library_batch_equity',{batch_id:selected,ordinal:r.ordinal})))}>Compare equity</button>}</>}</td></tr>;
 })}</tbody></table></div>{equity&&<Equity data={equity}/>}<details><summary>Frozen input and source contract</summary><pre>{JSON.stringify(report.snapshot,null,2)}</pre></details></>}
 </section>;
}
