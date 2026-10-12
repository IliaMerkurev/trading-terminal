import {useEffect,useRef,useState} from 'react';
import {api} from './api';
import './comparison.css';
const fieldLabel=(field:string)=>({fee_rate:'Fee rate (fraction)',slippage:'Slippage (fraction)',stop_loss:'Stop loss (fraction)',take_profit:'Take profit (fraction)',version:'Execution model version',capital:'Initial capital (USDT)',primary_minutes:'Primary timeframe (minutes)',evaluation:'Condition evaluation',path:'Minute price path',strategy_sha256:'Strategy identity',metric_version:'Metric definition version'}[field.split('.').at(-1)!]??field.replaceAll('_',' ').replaceAll('.',' / '));
type EvidenceCell={known:boolean;value:unknown;reason:string|null};
type EvidenceRow={key:string;group:string;label:string;status:'matched'|'different'|'unknown';note:string;values:EvidenceCell[]};
type Review={version:number;rows:EvidenceRow[];counts:Record<string,number>;note:string};
const label=(value:string)=>value[0].toUpperCase()+value.slice(1);
const utc=(v:number)=>{try{return new Date(v*1000).toISOString().replace('.000Z',' UTC');}catch{return 'Invalid saved timestamp';}};
function display(value:unknown,key=''):string{
 if(value===null||value===undefined)return 'Not recorded';
 if(['range','declared','warmup'].includes(key)&&Array.isArray(value))return `${utc(value[0])} → ${utc(value[1])}`;
 if(typeof value==='object'&&!Array.isArray(value)){
  const v=value as Record<string,any>;
  if(key==='coverage'&&'count' in v)return `${utc(v.actual_start)} → ${utc(v.actual_end)} · ${v.count} / ${v.expected_count} bars · ${v.complete?'complete':'gaps recorded'} · ${v.gaps?.length??'?'} gaps${v.gaps?.length?' · '+JSON.stringify(v.gaps):''}`;
  if(key==='trace')return `${v.first_close_utc} → ${v.last_close_utc}`;
  if(key==='market')return `${v.market} · ${v.symbol}`;
  if(key==='engine')return `${v.engine} ${v.engine_version} · metrics ${v.metric_version}`;
  if(v.display)return `${v.display} · metadata SHA-256 ${v.metadata_sha256}`;
 }
 return typeof value==='string'?value:JSON.stringify(value);
}
function validReview(value:any,count:number):value is Review{
 return value?.version===1&&typeof value.note==='string'&&Array.isArray(value.rows)&&value.rows.length<=60&&value.rows.every((r:any)=>
  typeof r.key==='string'&&typeof r.label==='string'&&typeof r.group==='string'&&typeof r.note==='string'&&
  ['matched','different','unknown'].includes(r.status)&&Array.isArray(r.values)&&r.values.length===count&&r.values.every((v:any)=>typeof v?.known==='boolean'&&(v.reason==null||typeof v.reason==='string')));
}
function Conditions({review,runs}:{review:Review;runs:any[]}){
 const counts=(s:string)=>review.rows.filter(r=>r.status===s).length;
 const groups=[...new Set(review.rows.map(r=>r.group))];
 return <section className="comparability" aria-label="Saved conditions review"><h3>Saved conditions review</h3>
  <p className="comparability-counts">{['different','unknown','matched'].map(s=><span key={s} className={`condition-status ${s}`}>{counts(s)} {s}</span>)}</p>
  <p>{review.note}</p>
  {groups.map(group=><details key={group} open={group==='Data'}><summary>{group} <span>{review.rows.filter(r=>r.group===group&&r.status==='different').length} different · {review.rows.filter(r=>r.group===group&&r.status==='unknown').length} unknown</span></summary>
   <div className="table-scroll" tabIndex={0} role="region" aria-label={`${group} saved evidence`}><table><thead><tr><th>Condition</th>{runs.map(r=><th key={r.id}>Run {r.id.slice(0,8)}</th>)}</tr></thead><tbody>
    {review.rows.filter(r=>r.group===group).map(row=><tr key={row.key}><th scope="row"><span className={`condition-status ${row.status}`}>{label(row.status)}</span><strong>{row.label}</strong><small>{row.note}</small></th>{row.values.map((v,i)=><td key={i}>{v.known?<span>{display(v.value,row.key)}</span>:<span className="condition-unknown">Unknown<small>{v.reason??'Not recorded'}</small></span>}</td>)}</tr>)}
   </tbody></table></div>
  </details>)}
 </section>;
}
export default function ComparisonPanel({runs,selected,onSelect}:{runs:any[];selected:string[];onSelect:(ids:string[])=>void}){
 const [result,setResult]=useState<any>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false),[cancelled,setCancelled]=useState(false);
 const epoch=useRef(0),controller=useRef<AbortController|null>(null),owner=useRef('');
 const selection=JSON.stringify(selected);owner.current=selection;
 useEffect(()=>{epoch.current++;controller.current?.abort();setResult(null);setError('');setLoading(false);setCancelled(false);return()=>{epoch.current++;controller.current?.abort();};},[selection]);
 function cancel(){epoch.current++;controller.current?.abort();setLoading(false);setResult(null);setError('');setCancelled(true);}
 async function compare(){
  const request=++epoch.current,ids=[...selected],key=selection;controller.current?.abort();const abort=new AbortController();controller.current=abort;
  setError('');setResult(null);setLoading(true);setCancelled(false);
  try{
   const value=await api<any>('compare_runs',{run_ids:ids},{signal:abort.signal});
   if(request!==epoch.current||owner.current!==key||abort.signal.aborted)return;
   if(!Array.isArray(value?.runs)||JSON.stringify(value.runs.map((r:any)=>r.id))!==JSON.stringify(ids)||!Array.isArray(value.differences)||!value.differences.every((d:any)=>typeof d?.field==='string'&&Array.isArray(d.values)&&d.values.length===ids.length))throw Error('Saved comparison response does not match the selected runs');
   if(value.comparability!==undefined&&!validReview(value.comparability,ids.length))throw Error('Invalid saved conditions response');
   setResult({...value,selection:key});
  }catch(e){if(request===epoch.current&&owner.current===key&&!abort.signal.aborted)setError(String(e instanceof Error?e.message:e));}
  finally{if(request===epoch.current&&owner.current===key)setLoading(false);}
 }
 const shown=result?.selection===selection?result:null;
 const eligible=runs.filter(r=>r.status==='completed');
 return <details className="comparison" onToggle={e=>{if(!e.currentTarget.open&&loading)cancel();}}><summary>Compare and select runs for export</summary>
  <p>Select two to eight saved runs. Review the recorded test conditions before interpreting the existing metrics.</p>
  <div className="compare-selection">{eligible.map(r=><label key={r.id}><input type="checkbox" checked={selected.includes(r.id)} disabled={!selected.includes(r.id)&&selected.length>=8} onChange={e=>{epoch.current++;controller.current?.abort();onSelect(e.target.checked?[...selected,r.id]:selected.filter(id=>id!==r.id));setResult(null);setLoading(false);setError('');setCancelled(false);}}/>{r.summary?.profile?.symbol??'Instrument unavailable'} · {new Date(r.created_at).toLocaleString()} · {r.id.slice(0,8)}{r.summary?.origin==='imported'?' · imported report':''}</label>)}</div>
  <div className="comparison-actions"><button disabled={selected.length<2||selected.length>8||loading} onClick={compare}>{error||cancelled?'Retry comparison':'Compare selected runs'}</button>{loading&&<button onClick={cancel}>Cancel comparison read</button>}</div>
  {loading&&<p role="status">Reading immutable saved conditions…</p>}{cancelled&&<p role="status">Stopped waiting for comparison. Saved results are unchanged.</p>}{error&&<p role="alert">{error}</p>}
  {shown&&<>
   {shown.comparability?<Conditions review={shown.comparability} runs={shown.runs}/>:<p className="assumption">Conditions review unavailable in this response. Matching metadata alone does not establish comparable tests.</p>}
   {shown.runs.some((r:any)=>r.summary?.origin==='imported')&&<p className="assumption">Imported reports contain saved claims, not independently authenticated calculations or provider data. Raw history may be absent.</p>}
   <h3>Recorded outcomes</h3><p>Net PnL includes recorded commissions and signed funding. Positive funding means received. Slippage is in fill prices; aggregate gross PnL and separate slippage cost are not archived here. No costs are recalculated.</p>
   <div className="table-scroll"><table><thead><tr><th>Run</th><th>Net PnL (USDT)</th><th>Drawdown</th><th>Trades</th><th>Win rate</th><th>Fees (USDT)</th><th>Funding (USDT)</th></tr></thead><tbody>{shown.runs.map((r:any)=>{const m=r.summary?.metrics??{};return <tr key={r.id}><td>{r.id.slice(0,8)}</td><td>{m.net_pnl??'—'}</td><td>{m.max_drawdown==null?'—':(Number(m.max_drawdown)*100).toFixed(3)+'%'}</td><td>{m.trade_count??'—'}</td><td>{m.win_rate==null?'—':(m.win_rate*100).toFixed(1)+'%'}</td><td>{m.fees??'—'}</td><td>{m.funding??'—'}</td></tr>;})}</tbody></table></div>
   <details className="comparison-metadata"><summary>Recorded metadata differences ({shown.difference_count??shown.differences.length})</summary><p>Metadata equality does not fill missing evidence. Strategy and environment differences are included for inspection.</p>
    <div className="table-scroll"><table><thead><tr><th>Field</th>{shown.runs.map((r:any)=><th key={r.id}>{r.id.slice(0,8)}</th>)}</tr></thead><tbody>{shown.differences.map((d:any)=><tr key={d.field}><td>{fieldLabel(d.field)}<small>{d.field}</small></td>{d.values.map((v:any,i:number)=><td key={i}>{display(v)}</td>)}</tr>)}</tbody></table></div>
    {shown.differences_omitted>0&&<p>{shown.differences_omitted} additional metadata differences omitted from this bounded view. Inspect the original saved snapshots for complete details.</p>}
   </details><small>{shown.note}</small>
  </>}
 </details>;
}
