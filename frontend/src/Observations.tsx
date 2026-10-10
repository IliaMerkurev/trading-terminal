import {useEffect,useId,useRef,useState} from 'react';
import {api} from './api';
import {historyLabel,canonical} from './LibraryResearch';
import {timeframe} from './research';
import {displayRecorder,DisplayTrackingNotice} from './DisplayedEvidence';
import ObservationChart from './ObservationChart';

export type ObservationContext={id:string;revision:number;source:any;start:number;end:number};
export type HistoryRequest={id:string;request:number;target?:'later';observation?:ObservationContext};
type HistoryCursor={id:string;created_at:string};
type ListState={status:'loading'|'ready'}|{status:'error';message:string;before:HistoryCursor|null;afterSave:boolean};
const utc=(v:number)=>new Date(v*1000).toISOString().slice(0,16);
const seconds=(v:string)=>Date.parse(v+'Z')/1000;
const context=(v:any):ObservationContext=>({id:v.id,revision:v.revision,source:v.source,start:v.start,end:v.end});

function periodIssue(range:string[],source:any,step:number){
 if(!source)return null;
 const values=range.map(seconds),missing=values.map(v=>!Number.isSafeInteger(v));
 if(missing.some(Boolean))return {fields:missing,message:'Enter a valid start and end time (UTC).'};
 if(values[0]>=values[1])return {fields:[true,true],message:'The observation end must be after its start. The end is exclusive.'};
 const outside=values.map(v=>v<source.range[0]||v>source.range[1]);
 if(outside.some(Boolean))return {fields:outside,message:'Keep both dates within the available saved history below.'};
 const unaligned=values.map(v=>v%step!==0);
 if(unaligned.some(Boolean))return {fields:unaligned,message:`Use ${timeframe(step/60)} UTC candle boundaries for ${unaligned.every(Boolean)?'both dates':unaligned[0]?'the start':'the end'}.`};
 return null;
}

export default function Observations({datasets,request,onTest,onBatch}:{datasets:any[];request?:{dataset?:string;id?:string;revision?:number;request:number};onTest:(value:ObservationContext)=>void;onBatch:(id:string)=>void}){
 const periodHelpId=useId(),periodErrorId=useId();
 const display=useRef<ReturnType<typeof displayRecorder>|null>(null);
 if(!display.current)display.current=displayRecorder();
 const [dataset,setDataset]=useState(''),[range,setRange]=useState(['','']),[pageStart,setPageStart]=useState<number|null>(null),[page,setPage]=useState<any>(null),[pageRequest,setPageRequest]=useState(0);
 const [record,setRecord]=useState<any>(null),[hypothesis,setHypothesis]=useState(''),[falsification,setFalsification]=useState('');
 const [rows,setRows]=useState<any[]>([]),[next,setNext]=useState<HistoryCursor|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[loading,setLoading]=useState(false);
 const [listState,setListState]=useState<ListState>({status:'loading'});
 const listPending=useRef(false),listEpoch=useRef(0);
 const actionEpoch=useRef(0),lock=useRef(false),handledRequest=useRef<number|null>(null);
 const source=record?.source??datasets.find(d=>d.id===dataset),step=source?.interval_seconds??60;
 const dirty=!!record&&(hypothesis!==record.hypothesis||falsification!==record.falsification);
 const draft=!!hypothesis||!!falsification;
 const blocked=busy||dirty||(!record&&draft);
 const issue=periodIssue(range,source,step),valid=!!source&&!issue;
 async function list(before:HistoryCursor|null=null,{afterSave=false,replacePending=false}={}){
  if(listPending.current&&!replacePending)return;
  // Only a confirmed save replaces an in-flight read; its late response is stale.
  const epoch=++listEpoch.current;listPending.current=true;setListState({status:'loading'});
  try{
   const v=await api<any>('observation_history',{before});
   if(epoch!==listEpoch.current)return;
   setRows(old=>{const unique=new Map((before?old:[]).map(r=>[r.id,r]));v.rows.forEach((r:any)=>unique.set(r.id,r));return [...unique.values()];});
   setNext(v.next);setListState({status:'ready'});
  }catch(e){if(epoch===listEpoch.current)setListState({status:'error',message:String(e instanceof Error?e.message:e),before,afterSave});}
  finally{if(epoch===listEpoch.current)listPending.current=false;}
 }
 useEffect(()=>{void list();return()=>{listEpoch.current++;listPending.current=false;};},[]);
 function choose(id:string){actionEpoch.current++;setPageRequest(v=>v+1);const d=datasets.find(d=>d.id===id);setDataset(id);setRecord(null);setHypothesis('');setFalsification('');setError('');setPage(null);setPageStart(d?.range[0]??null);setRange(d?[utc(d.range[0]),utc(d.range[1])]:['','']);}
 async function open(id:string,revision:number|null=null){if(lock.current)return;lock.current=true;setBusy(true);setError('');const epoch=++actionEpoch.current;try{const v=await api<any>('observation_get',{observation_id:id,revision});if(epoch!==actionEpoch.current)return;setPageRequest(n=>n+1);setRecord(v);setDataset(v.source.id);setRange([utc(v.start),utc(v.end)]);setPageStart(v.start);setPage(null);setHypothesis(v.hypothesis);setFalsification(v.falsification);}catch(e){setError(String(e));}finally{lock.current=false;setBusy(false);}}
 useEffect(()=>{if(!request||handledRequest.current===request.request)return;if(blocked){setError('Save or discard note edits before opening the requested observation.');return;}handledRequest.current=request.request;if(request.id){void open(request.id,request.revision??null);}else if(request.dataset)choose(request.dataset);},[request?.request,blocked]);
 useEffect(()=>{let current=true;setPage(null);setLoading(false);if(!source||pageStart===null||record?.source_error)return;setLoading(true);api<any>('local_history_window',{dataset_id:dataset,start:pageStart,end:Math.min(source.range[1],pageStart+500*step)}).then(v=>{if(current){if(record&&canonical(v.source)!==canonical(record.source))throw Error('Exact saved source changed; reopen before continuing');setPage(v);}}).catch(e=>{if(current)setError(String(e));}).finally(()=>{if(current)setLoading(false);});return()=>{current=false;};},[dataset,pageStart,record?.id,record?.revision,pageRequest]);
 async function save(){if(lock.current)return;lock.current=true;setBusy(true);setError('');try{const v=await api<any>('observation_save',{observation_id:record?.id??null,expected_revision:record?.revision??0,dataset_id:dataset,start:seconds(range[0]),end:seconds(range[1]),hypothesis,falsification});setRecord(v);setHypothesis(v.hypothesis);setFalsification(v.falsification);await list(null,{afterSave:true,replacePending:true});}catch(e){setError(String(e));}finally{lock.current=false;setBusy(false);}}
 return <section className="content observations"><div className="studio-heading"><div><h1>Saved history</h1><p>Inspect prepared local candles, record an observation, then test it in Lab.</p></div></div>
 {error&&<p role="alert">{error}</p>}
 <div className="observation-layout"><section><label className="field">Local history<select aria-label="Observation history" disabled={blocked} value={dataset} onChange={e=>choose(e.target.value)}><option value="">Choose prepared local history</option>{record&&!datasets.some(d=>d.id===dataset)&&<option value={dataset}>Saved source · {dataset.slice(0,8)} · unavailable</option>}{datasets.map(d=><option key={d.id} value={d.id}>{historyLabel(d)}</option>)}</select></label>
 {!datasets.length&&<p>No prepared local history. Open Data to prepare a snapshot first.</p>}
 {source&&<><p>{historyLabel(source)}<br/>Local snapshot · {page?.source.classification??source.classification??'Provenance shown after page verification'}</p>{(page?.source.classification??source.classification)==='synthetic'&&<p className="warning-text">Synthetic fixture. Useful for checking the workflow, not evidence of market profitability.</p>}{(page?.source.classification??source.classification)==='unknown'&&<p className="warning-text">Source provenance is uncertain.</p>}
 {record?.source_error&&<p role="alert">{record.source_error}. No replacement or network download is automatic.</p>}
 {loading&&<p role="status">Reading verified local history…</p>}{page&&<><ObservationChart record={display.current} candles={page.candles} seconds={step} reference={page.display_reference}/><p>{utc(page.start).replace('T',' ')} — {utc(page.end).replace('T',' ')} UTC · {page.candles.length} source candles · opening times</p>{page.missing.length>0&&<p role="alert">Missing local history: {page.missing.length} candle slots in this page. No candles are fabricated.</p>}<div className="run-actions"><button disabled={loading||page.start<=source.range[0]} onClick={()=>setPageStart(Math.max(source.range[0],page.start-500*step))}>Earlier candles</button><button disabled={loading||page.end>=source.range[1]} onClick={()=>setPageStart(page.end)}>Later candles</button></div></>}
 <p className="muted">Visible local candles are recorded as displayed in this app, not proof of reading. Notes do not create display evidence. Other views and outside-app exposure remain incomplete.</p>
 <DisplayTrackingNotice/><h2>{record?`Observation · revision ${record.revision}`:'New observation'}</h2>
 {record&&record.revision!==record.latest_revision&&<p className="warning-text">Historical revision. Linked tests keep this exact note. Open the latest revision to edit.</p>}
 <div className="two-columns">{['Observation start (UTC)','Observation end, exclusive (UTC)'].map((label,i)=><label className="field" key={label}>{label}<input aria-label={label} aria-invalid={issue?.fields[i]??false} aria-describedby={`${periodHelpId}${issue?.fields[i]?` ${periodErrorId}`:''}`} type="datetime-local" disabled={busy||!!record} value={range[i]} onChange={e=>setRange(v=>v.map((x,j)=>i===j?e.target.value:x))}/></label>)}</div>
 <div id={periodErrorId} aria-live="polite" aria-atomic="true">{issue&&<p className="warning-text">{issue.message}</p>}</div>
 <p id={periodHelpId} className="muted">Available saved history: {utc(source.range[0]).replace('T',' ')} to {utc(source.range[1]).replace('T',' ')} UTC (end exclusive). Use {timeframe(step/60)} candle boundaries, for example {utc(source.range[0]).replace('T',' ')} UTC.</p>
 <button disabled={!valid||loading||!!record?.source_error} onClick={()=>{setError('');setPageRequest(v=>v+1);setPageStart(seconds(range[0]));}}>Show observation start</button>
 <label className="field">Hypothesis<textarea aria-label="Observation hypothesis" maxLength={2000} disabled={busy||!!record&&record.revision!==record.latest_revision} value={hypothesis} onChange={e=>setHypothesis(e.target.value)}/></label>
 <label className="field">What would disprove it? (optional)<textarea aria-label="Observation falsification" maxLength={2000} disabled={busy||!!record&&record.revision!==record.latest_revision} value={falsification} onChange={e=>setFalsification(e.target.value)}/></label>
 <div className="run-actions"><button disabled={busy||!page||!!record?.source_error||!valid||!hypothesis.trim()||!!record&&(!dirty||record.revision!==record.latest_revision)} onClick={save}>{record?'Save note revision':'Save observation'}</button>
 <button className="primary" disabled={busy||!record||dirty||!page||!valid||!!record.source_error} onClick={()=>onTest(context(record))}>Test observation in Lab</button>
 {(dirty||!record&&draft)&&<button disabled={busy} onClick={()=>{setHypothesis(record?.hypothesis??'');setFalsification(record?.falsification??'');}}>Discard note edits</button>}
 {record&&<button disabled={busy||dirty} onClick={()=>{setRecord(null);setHypothesis('');setFalsification('');}}>New observation</button>}
 {record&&record.revision!==record.latest_revision&&<button disabled={busy} onClick={()=>open(record.id)}>Open latest revision</button>}</div>
 {record&&<><h3>Linked tests</h3>{record.links.length?record.links.map((l:any)=><p key={l.batch_id}><button disabled={blocked} onClick={()=>onBatch(l.batch_id)}>Open test {l.batch_id.slice(0,8)}</button> · revision {l.revision} · {l.status}</p>):<p>No admitted tests linked yet.</p>}{record.more_links&&<p>Showing the latest 100 links.</p>}</>}
 </>}
 </section><aside aria-busy={listState.status==='loading'}><h2>Saved observations</h2>
 {listState.status==='loading'&&<p role="status">Loading saved observations…</p>}
 {listState.status==='error'&&<><p role="alert">{listState.afterSave?'Note saved. Could not refresh saved observations':'Could not load saved observations'}: {listState.message}</p><button disabled={busy} onClick={()=>list(listState.before,{afterSave:listState.afterSave})}>Retry saved observations</button></>}
 {listState.status==='ready'&&!rows.length&&<p>No saved observations yet.</p>}
 {rows.map(r=><button className="observation-item" disabled={blocked} key={r.id} onClick={()=>open(r.id)}><strong>{r.hypothesis}</strong><small>{r.source.symbol} · {r.source.source} · revision {r.revision}<br/>Saved {r.saved_at} · period {utc(r.start)} UTC</small></button>)}{next&&<button disabled={blocked||listState.status!=='ready'} onClick={()=>list(next)}>Older observations</button>}</aside></div>
 </section>;
}
