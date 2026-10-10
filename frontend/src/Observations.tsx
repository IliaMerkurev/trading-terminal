import {useEffect,useId,useRef,useState} from 'react';
import {api} from './api';
import {historyLabel,canonical} from './LibraryResearch';
import {timeframe} from './research';
import {displayRecorder,DisplayTrackingNotice} from './DisplayedEvidence';
import ObservationChart from './ObservationChart';
import {displayUnavailable,observationDisplayWidths,observationInterval} from './observationChartData';
import {HISTORY_PAGE_SLOTS,SOURCE_NAVIGATION_UNAVAILABLE,navigationBounds,navigationDraft,navigationUTC,navigationWindow} from './observationNavigation';

export type ObservationContext={id:string;revision:number;source:any;start:number;end:number};
export type HistoryRequest={id:string;request:number;target?:'later';observation?:ObservationContext};
type HistoryCursor={id:string;created_at:string};
type ListState={status:'loading'|'ready'}|{status:'error';message:string;before:HistoryCursor|null;afterSave:boolean};
const utc=navigationUTC;
const safeHistoryLabel=(source:any)=>navigationBounds(source)?historyLabel(source):`${source?.symbol??'Unknown instrument'} · ${source?.source??'Unknown source'} · ${String(source?.id??'Unknown snapshot').slice(0,8)} · unavailable boundaries`;
type PageRequest={epoch:number;dataset:string;declaration:string;source:any;expectedSource:string|null;start:number;end:number};
type PageState={status:'idle'}|{status:'loading';request:PageRequest}|{status:'ready';request:PageRequest;value:any}|{status:'error';request:PageRequest;message:string;sourceChanged:boolean};
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
 const periodHelpId=useId(),periodErrorId=useId(),navigationHelpId=useId(),navigationErrorId=useId();
 const display=useRef<ReturnType<typeof displayRecorder>|null>(null);
 if(!display.current)display.current=displayRecorder();
 const [dataset,setDataset]=useState(''),[range,setRange]=useState(['','']);
 const [selectedSource,setSelectedSource]=useState<any>(null),[selectedDeclaration,setSelectedDeclaration]=useState<string|null>(null),[sourceInvalidated,setSourceInvalidated]=useState(false),[sourceUnavailable,setSourceUnavailable]=useState('');
 const [browseInput,setBrowseInput]=useState(''),[browseSource,setBrowseSource]=useState<any>(null),[pageState,setPageState]=useState<PageState>({status:'idle'});
 const pageEpoch=useRef(0),pagePending=useRef(false),datasetsRef=useRef(datasets);datasetsRef.current=datasets;
 const [record,setRecord]=useState<any>(null),[hypothesis,setHypothesis]=useState(''),[falsification,setFalsification]=useState('');
 const [rows,setRows]=useState<any[]>([]),[next,setNext]=useState<HistoryCursor|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [displayChoice,setDisplayChoice]=useState({source:'',width:0});
 const [listState,setListState]=useState<ListState>({status:'loading'});
 const listPending=useRef(false),listEpoch=useRef(0);
 const actionEpoch=useRef(0),lock=useRef(false),handledRequest=useRef<number|null>(null);
 const source=record?.source??selectedSource,step=source?.interval_seconds??60;
 const declaration=canonical(datasets.find(d=>d.id===dataset)??null);
 const declarationChanged=selectedDeclaration!==null&&selectedDeclaration!==declaration;
 const sourceChanged=declarationChanged||sourceInvalidated;
 const page=pageState.status==='ready'&&!sourceChanged&&pageState.request.epoch===pageEpoch.current?pageState.value:null;
 const activeRequest=pageState.status==='idle'?null:pageState.request;
 const loading=pageState.status==='loading'&&!sourceChanged;
 const navigationSource=browseSource??source,bounds=navigationBounds(navigationSource);
 const verifiedSource=browseSource?canonical(browseSource):'',verifiedStep=browseSource?.interval_seconds??step;
 const displayWidth=displayChoice.source===verifiedSource&&!displayUnavailable(verifiedStep,displayChoice.width||verifiedStep)?displayChoice.width:0;
 const dirty=!!record&&(hypothesis!==record.hypothesis||falsification!==record.falsification);
 const draft=!!hypothesis||!!falsification;
 const blocked=busy||dirty||(!record&&draft);
 const issue=navigationBounds(source)?periodIssue(range,source,step):null,valid=!!navigationBounds(source)&&!issue;
 const browseDraft=navigationDraft(browseInput,bounds);
 const navigationDisabled=busy||loading||sourceChanged||!!sourceUnavailable||!bounds;
 function invalidatePage(){pageEpoch.current++;pagePending.current=false;setPageState({status:'idle'});}
 function submitPage(target:number,options:{source?:any;declaration?:string;expectedSource?:string|null;synchronize?:boolean;replace?:boolean;retry?:PageRequest}={}){
  if(!options.replace&&(lock.current||pagePending.current||sourceChanged||sourceUnavailable))return;
  const exactSource=options.source??navigationSource,exactBounds=navigationBounds(exactSource);
  if(!exactBounds)return;
  const window=options.retry??navigationWindow(exactBounds,target);if(!window)return;
  const captured:PageRequest={epoch:++pageEpoch.current,dataset:exactSource.id,declaration:options.declaration??declaration,source:JSON.parse(canonical(exactSource)),expectedSource:options.expectedSource===undefined?(browseSource?canonical(browseSource):record?canonical(record.source):null):options.expectedSource,start:window.start,end:window.end};
  pagePending.current=true;setPageState({status:'loading',request:captured});
  if(options.synchronize)setBrowseInput(utc(captured.start));
 }
 useEffect(()=>{
  if(!declarationChanged)return;
  invalidatePage();setSourceInvalidated(true);
 },[declaration,selectedDeclaration]);
 useEffect(()=>{
  const captured=activeRequest;if(!captured||captured.declaration!==declaration)return;
  let current=true;
  const owns=()=>current&&captured.epoch===pageEpoch.current&&captured.declaration===canonical(datasetsRef.current.find(d=>d.id===captured.dataset)??null);
  api<any>('local_history_window',{dataset_id:captured.dataset,start:captured.start,end:captured.end}).then(value=>{
   if(!owns())return;
   const verifiedBounds=navigationBounds(value?.source);
   if(value?.source?.id!==captured.dataset||value.start!==captured.start||value.end!==captured.end||!verifiedBounds||!Array.isArray(value.candles)||!Array.isArray(value.missing)||!navigationWindow(verifiedBounds,value.start)||value.end>verifiedBounds.end||value.end%verifiedBounds.step!==0||(value.end-value.start)/verifiedBounds.step>HISTORY_PAGE_SLOTS)throw Error('Saved-history response does not match the requested source and page.');
   if(captured.expectedSource&&canonical(value.source)!==captured.expectedSource){
    setSourceInvalidated(true);setPageState({status:'error',request:captured,message:'Exact saved source changed; choose the source or reopen the observation explicitly before continuing.',sourceChanged:true});return;
   }
   setBrowseSource(value.source);setDisplayChoice(old=>old.source===canonical(value.source)?old:{source:canonical(value.source),width:0});
   setPageState({status:'ready',request:captured,value});
  }).catch(e=>{if(owns())setPageState({status:'error',request:captured,message:String(e instanceof Error?e.message:e),sourceChanged:false});})
   .finally(()=>{if(owns())pagePending.current=false;});
  return()=>{current=false;};
 },[activeRequest?.epoch,declaration]);
 useEffect(()=>()=>{pageEpoch.current++;pagePending.current=false;actionEpoch.current++;},[]);
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
 function choose(id:string){
  if(lock.current)return;
  actionEpoch.current++;invalidatePage();
  const d=datasets.find(d=>d.id===id),key=canonical(d??null),available=navigationBounds(d);
  if(id!==dataset)setDisplayChoice({source:'',width:0});
  setDataset(id);setSelectedSource(d?JSON.parse(canonical(d)):null);setSelectedDeclaration(key);setSourceInvalidated(false);setSourceUnavailable('');setBrowseSource(null);
  setRecord(null);setHypothesis('');setFalsification('');setError('');
  setBrowseInput(available?utc(available.start):'');setRange(available?[utc(available.start),utc(available.end)]:['','']);
  if(available)submitPage(available.start,{source:d,declaration:key,expectedSource:null,replace:true});
 }
 async function open(id:string,revision:number|null=null){
  if(lock.current)return;lock.current=true;setBusy(true);setError('');invalidatePage();const epoch=++actionEpoch.current;
  try{
   const v=await api<any>('observation_get',{observation_id:id,revision});if(epoch!==actionEpoch.current)return;
   const key=canonical(datasetsRef.current.find(d=>d.id===v.source.id)??null);
   if(v.source.id!==dataset)setDisplayChoice({source:'',width:0});
   setRecord(v);setDataset(v.source.id);setSelectedSource(v.source);setSelectedDeclaration(key);setSourceInvalidated(false);setSourceUnavailable(v.source_error??'');setBrowseSource(null);
   setRange([utc(v.start),utc(v.end)]);setBrowseInput(utc(v.start));setHypothesis(v.hypothesis);setFalsification(v.falsification);
   if(!v.source_error&&navigationBounds(v.source))submitPage(v.start,{source:v.source,declaration:key,expectedSource:canonical(v.source),replace:true});
  }catch(e){if(epoch===actionEpoch.current)setError(String(e));}
  finally{if(epoch===actionEpoch.current){lock.current=false;setBusy(false);}}
 }
 useEffect(()=>{if(!request||handledRequest.current===request.request)return;if(blocked){setError('Save or discard note edits before opening the requested observation.');return;}handledRequest.current=request.request;if(request.id){void open(request.id,request.revision??null);}else if(request.dataset)choose(request.dataset);},[request?.request,blocked]);
 async function save(){
  if(lock.current||pagePending.current||sourceChanged||sourceUnavailable||!page)return;
  lock.current=true;setBusy(true);setError('');const expectedSource=canonical(browseSource??record?.source);
  try{
   const v=await api<any>('observation_save',{observation_id:record?.id??null,expected_revision:record?.revision??0,dataset_id:dataset,start:seconds(range[0]),end:seconds(range[1]),hypothesis,falsification});
   if(canonical(v.source)!==expectedSource){
    invalidatePage();setSourceInvalidated(true);setError('The save returned a different exact source. Reopen saved observations to verify the saved record before continuing.');
   }else{setRecord(v);setHypothesis(v.hypothesis);setFalsification(v.falsification);setSourceUnavailable(v.source_error??'');if(v.source_error)invalidatePage();}
   await list(null,{afterSave:true,replacePending:true});
  }catch(e){setError(String(e));}finally{lock.current=false;setBusy(false);}
 }

 return <section className="content observations"><div className="studio-heading"><div><h1>Saved history</h1><p>Inspect prepared local candles, record an observation, then test it in Lab.</p></div></div>
 {error&&<p role="alert">{error}</p>}
 <div className="observation-layout"><section><label className="field">Local history<select aria-label="Observation history" disabled={blocked} value={dataset} onChange={e=>choose(e.target.value)}><option value="">Choose prepared local history</option>{record&&!datasets.some(d=>d.id===dataset)&&<option value={dataset}>Saved source · {dataset.slice(0,8)} · unavailable</option>}{datasets.map(d=><option key={d.id} value={d.id}>{safeHistoryLabel(d)}</option>)}</select></label>
 {!datasets.length&&<p>No prepared local history. Open Data to prepare a snapshot first.</p>}
 {source&&<><p>{safeHistoryLabel(source)}<br/>Local snapshot · {page?.source.classification??source.classification??'Provenance shown after page verification'}</p>{(page?.source.classification??source.classification)==='synthetic'&&<p className="warning-text">Synthetic fixture. Useful for checking the workflow, not evidence of market profitability.</p>}{(page?.source.classification??source.classification)==='unknown'&&<p className="warning-text">Source provenance is uncertain.</p>}
 {sourceUnavailable&&<p role="alert">{sourceUnavailable}. No replacement or network download is automatic.</p>}
 {sourceChanged&&<p role="alert">Exact saved source changed. Note dates and text are retained. Discard pending edits before choosing a source or reopening the observation; no replacement is read automatically.</p>}
 {!bounds&&<p role="alert">{SOURCE_NAVIGATION_UNAVAILABLE}</p>}
 <section className="observation-navigation" aria-label="Saved-history page navigation" aria-busy={loading}>
 <form className="observation-date-jump" onSubmit={event=>{event.preventDefault();if(!navigationDisabled&&!browseDraft.issue&&browseDraft.start!==null)submitPage(browseDraft.start);}}>
 <label className="field">Go to UTC date<input aria-label="Go to UTC date" type="text" placeholder="YYYY-MM-DDTHH:mm" value={browseInput} aria-invalid={!!browseDraft.issue} aria-describedby={`${navigationHelpId}${browseDraft.issue?` ${navigationErrorId}`:''}`} onChange={event=>setBrowseInput(event.target.value)}/></label>
 <button type="submit" disabled={navigationDisabled||!!browseDraft.issue}>Go</button></form>
 <div id={navigationErrorId} aria-live="polite" aria-atomic="true">{bounds&&browseDraft.issue&&<p className="warning-text">{browseDraft.issue}</p>}</div>
 <div className="run-actions"><button disabled={navigationDisabled||!!page&&page.start===bounds!.start&&page.end===navigationWindow(bounds!,bounds!.start)?.end} onClick={()=>bounds&&submitPage(bounds.start,{synchronize:true})}>First saved page</button><button disabled={navigationDisabled||!!page&&page.start===bounds!.latest&&page.end===bounds!.end} onClick={()=>bounds&&submitPage(bounds.latest,{synchronize:true})}>Latest saved page</button>
 <button disabled={navigationDisabled||!page||page.start<=bounds!.start} onClick={()=>bounds&&page&&submitPage(Math.max(bounds.start,page.start-HISTORY_PAGE_SLOTS*bounds.step),{synchronize:true})}>Earlier candles</button><button disabled={navigationDisabled||!page||page.end>=bounds!.end} onClick={()=>page&&submitPage(page.end,{synchronize:true})}>Later candles</button>
 <button disabled={navigationDisabled||!valid} onClick={()=>submitPage(record?.start??seconds(range[0]),{synchronize:true})}>Return to observation start</button></div>
 <p id={navigationHelpId} className="muted">{bounds?<>Source interval {observationInterval(bounds.step)}. Available first opening {utc(bounds.start).replace('T',' ')} UTC; last opening {utc(bounds.end-bounds.step).replace('T',' ')} UTC; exclusive end {utc(bounds.end).replace('T',' ')} UTC. </>:null}Typed dates are interpreted as UTC and never rounded. First/latest use pages of up to 500 source slots counted from the saved range's start. Browsing does not change observation dates.</p>
 {loading&&<p role="status">Reading verified local history… Requested page: {utc(activeRequest!.start).replace('T',' ')} to {utc(activeRequest!.end).replace('T',' ')} UTC (end exclusive).</p>}
 {pageState.status==='error'&&!declarationChanged&&<div className="observation-page-error"><p role="alert">Could not read saved history: {pageState.message}</p><p>{safeHistoryLabel(pageState.request.source)}<br/>Snapshot: {pageState.request.dataset}<br/>Requested page: {utc(pageState.request.start).replace('T',' ')} to {utc(pageState.request.end).replace('T',' ')} UTC (end exclusive).</p><button disabled={navigationDisabled||pageState.sourceChanged} onClick={()=>submitPage(pageState.request.start,{retry:pageState.request,source:pageState.request.source,expectedSource:pageState.request.expectedSource})}>Retry saved-history page</button></div>}
 </section>
 {page&&<><div className="observation-display-controls"><label>Display interval<select aria-label="Saved-history display interval" value={displayWidth} onChange={event=>setDisplayChoice({source:verifiedSource,width:Number(event.target.value)})}><option value={0}>Source · {observationInterval(verifiedStep)}</option>{observationDisplayWidths.filter(width=>width!==verifiedStep).map(width=>{const reason=displayUnavailable(verifiedStep,width);return <option key={width} value={width} disabled={!!reason}>{observationInterval(width)}{reason?' · unavailable':''}</option>;})}</select></label><span>Local display only · observation dates and test settings stay unchanged</span></div>
 {observationDisplayWidths.filter(width=>width!==verifiedStep).map(width=>{const reason=displayUnavailable(verifiedStep,width);return reason?<p className="muted observation-display-limit" key={width}>{observationInterval(width)} unavailable: {reason}</p>:null;})}
 <ObservationChart record={display.current} candles={page.candles} missing={page.missing} seconds={verifiedStep} displaySeconds={displayWidth||verifiedStep} start={page.start} end={page.end} reference={page.display_reference}/><p>Loaded page: {utc(page.start).replace('T',' ')} — {utc(page.end).replace('T',' ')} UTC (end exclusive) · {page.candles.length} source candles · opening times</p>{page.missing.includes(page.start)&&<p className="warning-text">No recorded candle exists at the requested opening. The missing slot stays blank; no later candle is selected automatically.</p>}{page.missing.length>0&&<p role="alert">Missing local history: {page.missing.length} candle slots in this page. No candles are fabricated.</p>}</>}
 <p className="muted">Visible local candles are recorded as displayed in this app, not proof of reading. Notes do not create display evidence. Other views and outside-app exposure remain incomplete.</p>
 <DisplayTrackingNotice/><h2>{record?`Observation · revision ${record.revision}`:'New observation'}</h2>
 {record&&record.revision!==record.latest_revision&&<p className="warning-text">Historical revision. Linked tests keep this exact note. Open the latest revision to edit.</p>}
 <div className="two-columns">{['Observation start (UTC)','Observation end, exclusive (UTC)'].map((label,i)=><label className="field" key={label}>{label}<input aria-label={label} aria-invalid={issue?.fields[i]??false} aria-describedby={`${periodHelpId}${issue?.fields[i]?` ${periodErrorId}`:''}`} type="datetime-local" disabled={busy||!!record} value={range[i]} onChange={e=>setRange(v=>v.map((x,j)=>i===j?e.target.value:x))}/></label>)}</div>
 <div id={periodErrorId} aria-live="polite" aria-atomic="true">{issue&&<p className="warning-text">{issue.message}</p>}</div>
 <p id={periodHelpId} className="muted">Available saved history: {utc(source.range?.[0]).replace('T',' ')} to {utc(source.range?.[1]).replace('T',' ')} UTC (end exclusive). Use {timeframe(step/60)} candle boundaries, for example {utc(source.range?.[0]).replace('T',' ')} UTC.</p>
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
