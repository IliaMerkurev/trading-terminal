import {createContext,useContext,useEffect,useLayoutEffect,useRef,useState,type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import {api} from './api';
import {poll} from './poll';
import {alertIdentity,alertTime} from './AlertSession';
import ResearchChart from './ResearchChart';
import {AgreementTimeline, SavedAgreementEvidence} from './AgreementHistory';
import {agreementConditionLabel, agreementWarning} from './agreementAlert';
import {pendingHistoryKey,terminalHistory,utcField,parseUtcField,historyRangeError,truthLabel,type FrozenRule,type HistoryPreview,type HistoryRun,type HistoryStart,type PendingHistory,type HistoryMatch,type HistoryRow,type HistoryWindow,type EventEvidence} from './alertResearch';
import './alert-research.css';
const message=(error:unknown)=>error instanceof Error?error.message:String(error);
type Destination={kind:'scan';rule:FrozenRule}|{kind:'saved'}|{kind:'event';eventId:string};
type ResearchAccess={open:(destination:Destination)=>void};
const ResearchContext=createContext<ResearchAccess|null>(null);
export const useAlertResearch=()=>useContext(ResearchContext);
type Recovery={pending:PendingHistory|null;busy:boolean;storageError:string;submit:(params:HistoryStart,retry?:boolean)=>Promise<{run:HistoryRun|null;notice:string}>;reconcile:()=>Promise<{run:HistoryRun|null;notice:string}>};

export function AlertResearchProvider({children}:{children:ReactNode}){
 const [destination,setDestination]=useState<(Destination&{key:number})|null>(null),serial=useRef(0);
 const [pending,setPending]=useState<PendingHistory|null>(null),pendingRef=useRef<PendingHistory|null>(null);
 const [busy,setBusy]=useState(false),lock=useRef(false),[storageError,setStorageError]=useState('');
 const mounted=useRef(true);
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
 useLayoutEffect(()=>{
  try{const raw=localStorage.getItem(pendingHistoryKey);if(raw){const value=JSON.parse(raw);if(!value?.params||!['request_id','rule_id'].every(key=>/^[0-9a-f]{32}$/.test(value.params[key]))||!/^[0-9a-f]{64}$/.test(value.params.definition_hash)||!Number.isInteger(value.params.revision)||!Number.isInteger(value.params.start)||!Number.isInteger(value.params.end)||typeof value.hadUnknown!=='boolean')throw new Error('Invalid saved request');pendingRef.current=value;setPending(value);}}
  catch(error){setStorageError('Request recovery storage is unavailable. New scans are blocked. '+message(error));}
 },[]);
 const retain=(value:PendingHistory|null)=>{
  try{if(value)localStorage.setItem(pendingHistoryKey,JSON.stringify(value));else localStorage.removeItem(pendingHistoryKey);pendingRef.current=value;if(mounted.current)setPending(value);}
  catch(error){if(mounted.current)setStorageError('Cannot safely retain the original scan request. New scans are blocked. '+message(error));throw error;}
 };
 const lookup=async(operation:PendingHistory)=>{
  const result=await api<{request_id:string;found:boolean;run:HistoryRun|null}>('alert_history_request',{request_id:operation.params.request_id});
  if(result.request_id!==operation.params.request_id||result.found&&!result.run)throw new Error('Historical request identity/readback mismatch');
  if(result.found&&result.run){if(result.run.request_id!==operation.params.request_id)throw new Error('Historical run identity mismatch');retain(null);return result.run;}
  return null;
 };
 const submit:Recovery['submit']=async(params,retry=false)=>{
  if(lock.current||storageError||pendingRef.current&&!retry)throw new Error('Resolve the original scan request before starting another.');
  const operation=retry?pendingRef.current:{params,createdAt:new Date().toISOString(),hadUnknown:false};
  if(!operation||JSON.stringify(operation.params)!==JSON.stringify(params))throw new Error('Only the exact retained request may be retried.');
  lock.current=true;setBusy(true);
  try{
   // This synchronous durable write precedes every mutation, including exact retries.
   retain(operation);
   try{
    const run=await api<HistoryRun>('alert_history_start',operation.params);
    if(run.request_id!==params.request_id)throw new Error('Historical start identity mismatch');
    retain(null);return {run,notice:'Scan accepted. Saved scans can reopen this request without rerunning it.'};
   }catch(error){
    let run:HistoryRun|null=null;
    try{run=await lookup(operation);}catch{/* Retain the exact request when readback is unavailable. */}
    if(run)return {run,notice:'The original request was committed; its response failed. Saved request readback recovered the same scan.'};
    // A completed error envelope can follow commit. Only its successful absent
    // ledger read can settle an initial rejection, never an earlier unknown call.
    if((error as any)?.definiteRejection&&!operation.hadUnknown){
     try{const result=await api<any>('alert_history_request',{request_id:params.request_id});if(result.request_id===params.request_id&&result.found===false&&result.run===null){retain(null);throw Object.assign(new Error('Scan rejected; readback confirms no accepted request. '+message(error)),{settled:true});}}
     catch(readError){if((readError as any)?.settled)throw readError;}
    }
    retain({...operation,hadUnknown:true});throw new Error('Scan outcome is unknown. Reconcile the original request before another start. '+message(error));
   }
  }finally{lock.current=false;if(mounted.current)setBusy(false);}
 };
 const reconcile:Recovery['reconcile']=async()=>{
  if(lock.current||!pendingRef.current)throw new Error('No available original request to reconcile.');
  lock.current=true;setBusy(true);
  try{const run=await lookup(pendingRef.current);return {run,notice:run?'Original request recovered. Open its saved scan; no new scan was started.':'No accepted request is recorded yet. Its exact identity and content remain retained. Only an explicit identical retry is available.'};}
  finally{lock.current=false;if(mounted.current)setBusy(false);}
 };
 const recovery={pending,busy,storageError,submit,reconcile};
 return <ResearchContext.Provider value={{open:value=>setDestination({...value,key:++serial.current})}}>
  {children}
  {pending&&!destination&&<div className="alert-global-warning" role="status">A historical scan request needs reconciliation. <button onClick={()=>setDestination({kind:'saved',key:++serial.current})}>Open saved scans and recovery</button></div>}
  {destination&&createPortal(<ResearchModal key={destination.key} destination={destination} recovery={recovery} close={()=>setDestination(null)}/>,document.body)}
 </ResearchContext.Provider>;
}
function ResearchModal({destination,recovery,close}:{destination:Destination;recovery:Recovery;close:()=>void}){
 const dialog=useRef<HTMLDialogElement>(null);
 useLayoutEffect(()=>{
  const previous=document.activeElement as HTMLElement|null,node=dialog.current!;
  if(node.showModal)node.showModal();else node.setAttribute('open','');
  node.querySelector<HTMLButtonElement>('button')?.focus({preventScroll:true});
  const escape=(event:KeyboardEvent)=>{if(event.key==='Escape'&&!event.isComposing){event.preventDefault();event.stopImmediatePropagation();close();}};
  window.addEventListener('keydown',escape,true);
  return()=>{window.removeEventListener('keydown',escape,true);if(node.open&&node.close)node.close();if(previous?.isConnected)previous.focus({preventScroll:true});};
 },[]);
 return <dialog ref={dialog} className="alert-research-dialog" aria-label={destination.kind==='event'?'Original alert evidence':'Frozen-rule historical research'} onCancel={event=>{event.preventDefault();close();}}>
  <header><h2>{destination.kind==='event'?'Original alert evidence':'Frozen-rule historical research'}</h2><button onClick={close}>Close research</button></header>
  <p>Read-only evidence and cache-only research. Matches are not trades, backtest results or profitability estimates. Market settings and monitoring are separate.</p>
  {destination.kind==='event'?<OriginalEvidence eventId={destination.eventId}/>:<HistoryResearch destination={destination} recovery={recovery}/>}
 </dialog>;
}
function FrozenDefinition({rule}:{rule:FrozenRule}){return <section aria-label="Research frozen rule"><h3>Frozen rule: {rule.name}</h3><p>Rule ID {rule.id} · saved revision {rule.revision} · definition revision {rule.definition_revision}</p><ContextLine context={rule.definition.context}/><p>Definition hash: {rule.definition_hash} · raw origin {alertTime(rule.definition.origin?.time)}</p><details><summary>Frozen parameters, origins and conditions</summary><pre>{JSON.stringify(rule.definition,null,2)}</pre></details></section>;}
function ContextLine({context}:{context:{source:string;market:string;symbol:string;minutes:number}}){return <p>{context.source} / {context.market} / {context.symbol} / native interval {context.minutes}m</p>;}
function HistoryResearch({destination,recovery}:{destination:Exclude<Destination,{kind:'event'}>;recovery:Recovery}){
 const [page,setPage]=useState<'new'|'saved'|'run'>(destination.kind==='scan'?'new':'saved');
 const [preview,setPreview]=useState<HistoryPreview|null>(null),[start,setStart]=useState(''),[end,setEnd]=useState('');
 const dirty=useRef({start:false,end:false}),fields=useRef({start:'',end:''});
 const startInput=useRef<HTMLInputElement>(null),endInput=useRef<HTMLInputElement>(null);
 const setField=(field:'start'|'end',value:string,edited:boolean)=>{
  if(edited)dirty.current[field]=true;
  fields.current[field]=value;(field==='start'?setStart:setEnd)(value);
 };
 const visibleFields=()=>{
  // A native date editor can update its DOM value before React onChange. Read
  // both fields before any state update, then preserve independently changed
  // fields against preview defaults. Browsers may omit a zero seconds suffix.
  const visible={start:startInput.current?.value??fields.current.start,end:endInput.current?.value??fields.current.end};
  const normalized=(value:string)=>value.length===16?value+':00':value;
  for(const field of ['start','end'] as const){
   const input=field==='start'?startInput.current:endInput.current;
   if(input&&(normalized(visible[field])!==normalized(fields.current[field])||input.validity.badInput))setField(field,visible[field],true);
  }
  return visible;
 };
 const [runId,setRunId]=useState<string|null>(null),[notice,setNotice]=useState(''),[error,setError]=useState(''),[absent,setAbsent]=useState(false);
 const alive=useRef(true),epoch=useRef(0);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;++epoch.current;};},[]);
 useEffect(()=>{
  if(destination.kind!=='scan')return;let valid=true;
  api<HistoryPreview>('alert_history_preview',{rule_id:destination.rule.id,revision:destination.rule.revision}).then(value=>{if(!valid)return;visibleFields();setPreview(value);if(!dirty.current.start)setField('start',utcField(value.cached_start===null?null:Math.max(value.cached_start,value.origin_raw_open+value.rule.definition.context.minutes*60)),false);if(!dirty.current.end)setField('end',utcField(value.cached_end),false);}).catch(error=>{if(valid)setError(message(error));});
  return()=>{valid=false;};
 },[destination]);
 const navigate=(value:'new'|'saved'|'run',id?:string)=>{++epoch.current;setPage(value);setRunId(id??null);setError('');setNotice('');};
 const act=async(action:()=>Promise<{run:HistoryRun|null;notice:string}>,select:boolean)=>{
  const version=epoch.current;setError('');setAbsent(false);
  try{const result=await action();if(!alive.current||version!==epoch.current)return;setNotice(result.notice);if(result.run&&select){setRunId(result.run.id);setPage('run');}else if(!result.run)setAbsent(true);}
  catch(error){if(alive.current&&version===epoch.current)setError(message(error));}
 };
 const startScan=()=>{
  if(!preview||recovery.busy||recovery.pending||recovery.storageError)return;
  if(!startInput.current||!endInput.current){setError('Open scan setup and review both visible UTC fields before starting.');return;}
  const nativeValid=startInput.current.validity.valid&&endInput.current.validity.valid;
  const visible=visibleFields(),problem=!nativeValid?'Complete both UTC date and time fields before starting.':historyRangeError(visible.start,visible.end,preview.rule.definition.context.minutes);if(problem){setError(problem);return;}
  const params={request_id:alertIdentity(),rule_id:preview.rule.id,revision:preview.rule.revision,definition_hash:preview.rule.definition_hash,start:parseUtcField(visible.start)!,end:parseUtcField(visible.end)!};
  void act(()=>recovery.submit(params),true);
 };
 const rangeError=historyRangeError(start,end,preview?.rule.definition.context.minutes??(destination.kind==='scan'?destination.rule.definition.context.minutes:1));
 return <>
  <nav className="research-actions">{destination.kind==='scan'&&<button onClick={()=>navigate('new')}>Scan setup</button>}<button onClick={()=>navigate('saved')}>Saved scans</button></nav>
  {recovery.storageError&&<p role="alert">{recovery.storageError}</p>}{error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
  {recovery.pending&&<section className="research-uncertain"><h3>Original scan awaiting reconciliation</h3><p>Request {recovery.pending.params.request_id} · retained {recovery.pending.createdAt}</p><p>Rule {recovery.pending.params.rule_id} revision {recovery.pending.params.revision} · {alertTime(recovery.pending.params.start)} through {alertTime(recovery.pending.params.end)}</p><button disabled={recovery.busy} onClick={()=>void act(recovery.reconcile,true)}>Reconcile original scan request</button>{absent&&<button disabled={recovery.busy} onClick={()=>void act(()=>recovery.submit(recovery.pending!.params,true),true)}>Retry exact original scan</button>}</section>}
  {page==='new'&&destination.kind==='scan'&&<section aria-label="Historical scan setup">
   <FrozenDefinition rule={preview?.rule??destination.rule}/>
   {preview?<p>Declared cached confirmed CLOSE bounds: {alertTime(preview.cached_start)} through {alertTime(preview.cached_end)} · {preview.cached_count} raw inputs available. {preview.note}</p>:<p role="status">Reading frozen revision and cached close bounds…</p>}
   <div className="research-dates"><label>Start UTC (inclusive confirmed close)<input ref={startInput} aria-label="Scan Start UTC" type="datetime-local" step="1" value={start} onInput={event=>setField('start',event.currentTarget.value,true)} onChange={event=>setField('start',event.currentTarget.value,true)} onBlur={()=>visibleFields()}/></label><label>End UTC (inclusive confirmed close)<input ref={endInput} aria-label="Scan End UTC" type="datetime-local" step="1" value={end} onInput={event=>setField('end',event.currentTarget.value,true)} onChange={event=>setField('end',event.currentTarget.value,true)} onBlur={()=>visibleFields()}/></label></div>
   {rangeError&&<p role="status">{rangeError}</p>}
   <button disabled={!preview||!!rangeError||recovery.busy||!!recovery.pending||!!recovery.storageError} onClick={startScan}>Start historical scan</button>
   <p>Limits: 10,000 raw inputs from the frozen origin, including all pre-range replay; estimated 256 MiB working memory; eight unfinished scans. Moving only Start later does not reduce warmup or input work. An earlier End may help. Missing origin, gaps, conflicts, unconfirmed data and unsupported formula versions fail visibly.</p>
  </section>}
  {page==='saved'&&<SavedScans onOpen={id=>navigate('run',id)}/>}
  {page==='run'&&runId&&<SavedScan key={runId} runId={runId}/>}
  <p className="research-footnote">Saved scans have no fixed count quota. Metadata and matches use pages of 20; chart windows use at most 200 candles and a 600 KiB response limit. Back up the workspace database: strategy archive export does not include these research records. Browser recovery storage is origin/profile-local and is not a portable backup. Unfinished scans become interrupted after Service restart and never automatically resume.</p>
 </>;
}
function SavedScans({onOpen}:{onOpen:(id:string)=>void}){
 const [rows,setRows]=useState<HistoryRun[]>([]),[cursor,setCursor]=useState<number|null>(null),[back,setBack]=useState<(number|null)[]>([]),[next,setNext]=useState<number|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[refresh,setRefresh]=useState(0);
 useEffect(()=>{let valid=true;setBusy(true);setError('');api<{runs:HistoryRun[];next_cursor:number|null}>('alert_history_list',{after:cursor,limit:20}).then(value=>{if(valid){setRows(value.runs);setNext(value.next_cursor);}}).catch(error=>{if(valid)setError(message(error));}).finally(()=>{if(valid)setBusy(false);});return()=>{valid=false;};},[cursor,refresh]);
 return <section aria-label="Saved historical scans"><h3>Saved scans</h3><button disabled={busy} onClick={()=>setRefresh(n=>n+1)}>Refresh saved scans</button>{error&&<p role="alert">{error}</p>}{busy&&<p role="status">Loading saved scans…</p>}{!busy&&rows.length===0&&<p>No saved scans in this page.</p>}<div className="research-saved-list">{rows.map(run=><article key={run.id}><strong>{run.rule_name}</strong><span>{run.status} · {run.coverage_complete?'Complete coverage':'No complete coverage'} · {alertTime(run.start)} through {alertTime(run.end)}</span><button disabled={busy} onClick={()=>onOpen(run.id)}>Open scan {run.sequence}</button></article>)}</div><div className="research-actions"><button disabled={busy||!back.length} onClick={()=>{setCursor(back.at(-1)!);setBack(back.slice(0,-1));}}>Previous saved scans</button><button disabled={busy||next===null} onClick={()=>{setBack([...back,cursor]);setCursor(next);}}>Next saved scans</button></div></section>;
}
function SavedScan({runId}:{runId:string}){
 const [run,setRun]=useState<HistoryRun|null>(null),runRef=useRef<HistoryRun|null>(null),[error,setError]=useState('');
 const [cancelPending,setCancelPending]=useState(false),cancelFlight=useRef(false),statusEpoch=useRef(0),alive=useRef(true);
 const accept=(value:HistoryRun)=>{if(value.id!==runId)throw new Error('Historical run response identity mismatch');if(runRef.current&&terminalHistory(runRef.current))return;value={...value,definition:value.definition??runRef.current?.definition};runRef.current=value;setRun(value);if(value.cancel_requested===false)setCancelPending(false);else if(value.cancel_requested)setCancelPending(true);};
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;++statusEpoch.current;};},[]);
 useEffect(()=>{
  if(run&&terminalHistory(run))return;
  return poll(async()=>{const epoch=statusEpoch.current;const value=await api<HistoryRun>('alert_history_get',{run_id:runId});return {epoch,value};},({epoch,value})=>{if(epoch===statusEpoch.current&&!cancelFlight.current){accept(value);setError('');}},error=>setError(message(error)),1000);
 },[runId,run?.status]);
 const cancel=async()=>{
  if(cancelFlight.current||!run||terminalHistory(run))return;
  cancelFlight.current=true;++statusEpoch.current;setCancelPending(true);setError('');
  try{const value=await api<HistoryRun>('alert_history_cancel',{run_id:runId});if(alive.current)accept(value);}
  catch(error){if(alive.current)setError('Cancellation outcome is unknown; checking the saved scan. '+message(error));}
  finally{++statusEpoch.current;cancelFlight.current=false;}
 };
 return <section aria-label="Saved scan result">
  {error&&<p role="alert">{error}</p>}{!run&&<p role="status">Reading saved scan…</p>}
  {run&&<><h3>{run.rule_name} · saved scan</h3><ContextLine context={run.context}/><p>Run {run.id} · frozen rule revision {run.rule_revision} · definition revision {run.definition_revision}</p><p role="status">Status: {run.status}{cancelPending?' · cancellation pending':''}</p>{!terminalHistory(run)&&<button disabled={cancelPending} onClick={()=>void cancel()}>Cancel historical scan</button>}<p>Requested inclusive confirmed closes: {alertTime(run.start)} through {alertTime(run.end)}. Raw calculation origin: {alertTime(run.origin?.time)} · {run.input_count} full-origin inputs.</p><p>Snapshot input hash: {run.input_hash}</p>{run.error&&<p role="alert">{run.error}</p>}
   {run.coverage_complete&&run.status==='completed'&&run.summary?<><Coverage summary={run.summary}/><ScanResults run={run}/></>:<p>No complete coverage or calculated result is published for this {run.status} scan. Cancelled, error and interrupted scans never resume automatically.</p>}
   {run.definition&&<details><summary>Saved frozen definition</summary><pre>{JSON.stringify(run.definition,null,2)}</pre></details>}
  </>}
 </section>;
}
function Coverage({summary:s}:{summary:any}){return <section aria-label="Historical coverage"><h4>Complete saved coverage</h4><p>{s.match_count} matches · {s.requested_rows} requested rows · {s.evaluated_rows} evaluated · {s.known_rows} known · {s.unknown_rows} unknown.</p><p>{s.initial_unknown_rows} initial unknown rows in the requested range; {s.pre_range_rows} pre-range replay rows, including {s.pre_range_unknown_rows} unknown. {s.input_rows} total raw input rows.</p><p>Unknown reason: {s.unknown_reason}. Unknown is distinct from False. Unavailable values may reflect warmup or missing values; not every unknown is definitely initialization warmup.</p><p>Evaluated confirmed-close coverage: {alertTime(s.coverage_start)} through {alertTime(s.coverage_end)}.</p></section>;}
function ScanResults({run}:{run:HistoryRun}){
 const [matches,setMatches]=useState<HistoryMatch[]>([]),[after,setAfter]=useState(0),[matchBack,setMatchBack]=useState<number[]>([]),[matchNext,setMatchNext]=useState<number|null>(null),[matchBusy,setMatchBusy]=useState(false),[matchError,setMatchError]=useState('');
 const [window,setWindow]=useState<HistoryWindow|null>(null),[chartBack,setChartBack]=useState<number[]>([]),[chartBusy,setChartBusy]=useState(false),[chartError,setChartError]=useState(''),[chartNotice,setChartNotice]=useState('');
 const [agreementIndex,setAgreementIndex]=useState<number|null>(null);
 const [selected,setSelected]=useState<HistoryRow|null>(null),[target,setTarget]=useState<number|null>(null),chartEpoch=useRef(0),alive=useRef(true);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;++chartEpoch.current;};},[]);
 useEffect(()=>{let valid=true;setMatchBusy(true);setMatchError('');api<{matches:HistoryMatch[];next_cursor:number|null}>('alert_history_matches',{run_id:run.id,after,limit:20}).then(value=>{if(valid){setMatches(value.matches);setMatchNext(value.next_cursor);}}).catch(error=>{if(valid)setMatchError(message(error));}).finally(()=>{if(valid)setMatchBusy(false);});return()=>{valid=false;};},[run.id,after]);
 const loadWindow=async(query:{start_index?:number;target_confirmed_at?:number}={},back:number[]=[] )=>{
  const epoch=++chartEpoch.current;setChartBusy(true);setChartError('');setChartNotice('');setSelected(null);setTarget(query.target_confirmed_at??null);
  const current=()=>alive.current&&epoch===chartEpoch.current;
  try{
   let value=await api<HistoryWindow>('alert_history_chart',{run_id:run.id,limit:200,...query});if(!current())return;
   if(value.run_id!==run.id)throw new Error('Saved chart response identity mismatch');
   const wanted=query.target_confirmed_at;
   if(wanted!==undefined){
    if(value.target?.status==='missing'){setChartNotice('Exact selected confirmation is missing. No nearest candle is substituted.');}
    else if(!value.rows.some(row=>row.evaluation.confirmed_at===wanted)){
     // Byte-limited windows can omit a target even when their start is unchanged.
     const exact=await api<HistoryRow>('alert_history_row',{run_id:run.id,confirmed_at:wanted});if(!current())return;
     if(exact.evaluation.confirmed_at!==wanted)throw new Error('Exact row response does not match the selected confirmation.');
     setSelected(exact);
     try{
      const exactWindow=await api<HistoryWindow>('alert_history_chart',{run_id:run.id,start_index:exact.row_index,limit:200,target_confirmed_at:wanted});if(!current())return;
      if(exactWindow.run_id!==run.id||!exactWindow.rows.some(row=>row.row_index===exact.row_index&&row.evaluation.confirmed_at===wanted))throw new Error('Exact target omitted by the chart response.');
      value=exactWindow;
      setChartNotice('The byte-limited context omitted the target. Showing an exact-index window; 40 preceding candles could not be retained.');
     }catch(error){
      if(!current())return;
      // An exact row can fit while the chart wrapper exceeds the byte budget.
      // Show that returned row alone, with its own saved hit, not a nearby bar.
      value={run_id:run.id,total_rows:value.total_rows,start_index:exact.row_index,next_index:exact.row_index+1<value.total_rows?exact.row_index+1:null,rows:[exact],markers:exact.in_range&&exact.evaluation.hit?[{row_index:exact.row_index,confirmed_at:wanted,raw_open_time:exact.candle.time}]:[],target:{confirmed_at:wanted,raw_open_time:exact.candle.time,row_index:exact.row_index,included:true,status:'available'},byte_limited:true};
      setChartNotice('Only the exact saved row is shown. Adjacent chart context is unavailable; 40 preceding candles could not be retained. '+message(error));
     }
    }
    const exact=value.rows.find(row=>row.evaluation.confirmed_at===wanted);if(exact)setSelected(exact);
   }
   setWindow(value);setChartBack(back);
  }catch(error){if(current()){setWindow(null);setChartError(message(error));}}
  finally{if(current())setChartBusy(false);}
 };
 useEffect(()=>{void loadWindow();},[run.id]);
 const selectMatch=(match:HistoryMatch)=>void loadWindow({target_confirmed_at:match.confirmed_at});
 const chooseRow=(row:HistoryRow)=>{setSelected(row);setTarget(row.evaluation.confirmed_at);};
 const adjacentRow=(delta:number)=>{
  if(!selected||chartBusy)return;
  const index=selected.row_index+delta,local=window?.rows.find(row=>row.row_index===index);
  if(local)chooseRow(local);
  else void loadWindow({target_confirmed_at:selected.evaluation.confirmed_at+delta*run.context.minutes*60},chartBack);
 };
 const agreementConditions=(run.definition?.conditions??window?.rows[0]?.evaluation.conditions??[]).map((condition:any,index:number)=>({condition,index})).filter(({condition}:any)=>condition.predicate==='agreement');
 const selectedAgreement=agreementConditions.some(({index}:any)=>index===agreementIndex)?agreementIndex:agreementConditions[0]?.index;

 return <section aria-label="Saved scan matches and chart">
  <h4>Matches · page {matchBack.length+1}</h4>{matchError&&<p role="alert">{matchError}</p>}{matchBusy&&<p role="status">Loading match page…</p>}
  <div className="research-match-list" aria-label="Historical matches">{matches.map(match=><button key={match.confirmed_at} disabled={matchBusy} aria-pressed={target===match.confirmed_at} onClick={()=>selectMatch(match)}>Confirmed CLOSE {alertTime(match.confirmed_at)} · raw OPEN {alertTime(match.raw_open_time)}</button>)}{!matchBusy&&!matches.length&&<p>No matches on this page.</p>}</div>
  <div className="research-actions"><button disabled={matchBusy||!matchBack.length} onClick={()=>{setAfter(matchBack.at(-1)!);setMatchBack(matchBack.slice(0,-1));}}>Previous matches</button><span>{matches.length} shown · up to 20 per page</span><button disabled={matchBusy||matchNext===null} onClick={()=>{setMatchBack([...matchBack,after]);setAfter(matchNext!);}}>Next matches</button></div>
  <h4>Immutable saved price and indicator snapshot</h4><p>Uses this scan's saved raw candles and calculated values only. Later Market settings and cache changes do not rewrite this chart. Every returned window marker is shown independently of the match page.</p>
  {chartBusy&&<p role="status">Reading saved chart window…</p>}{chartError&&<p role="alert">{chartError}</p>}{chartNotice&&<p role="status">{chartNotice}</p>}
  {window&&!chartBusy&&<><p>Rows {window.rows.length?window.rows[0].row_index+1:0}–{window.rows.at(-1)?.row_index!==undefined?window.rows.at(-1)!.row_index+1:0} of {window.total_rows} · {window.markers.length} saved match markers.{window.byte_limited?' Response shortened by the byte budget.':''}</p><div className="research-row-navigation" aria-label="Exact historical candle navigation"><label>Every saved candle in this window<select aria-label="Select exact saved candle" value={selected&&window.rows.some(row=>row.row_index===selected.row_index)?selected.row_index:''} onChange={event=>{const row=window.rows.find(row=>row.row_index===Number(event.target.value));if(row)chooseRow(row);}}><option value="" disabled>Select an exact candle</option>{window.rows.map(row=><option key={row.row_index} value={row.row_index}>Row {row.row_index+1} · CLOSE {alertTime(row.evaluation.confirmed_at)} · {truthLabel(row.evaluation.truth)} · {row.evaluation.hit?'match':'no match'}</option>)}</select></label><button disabled={!selected||selected.row_index===0} onClick={()=>adjacentRow(-1)}>Previous candle</button><button disabled={!selected||selected.row_index>=window.total_rows-1} onClick={()=>adjacentRow(1)}>Next candle</button></div>
   {selectedAgreement!==undefined&&<><label>Agreement condition<select aria-label="Saved agreement condition" value={selectedAgreement} onChange={event=>setAgreementIndex(Number(event.target.value))}>{agreementConditions.map(({condition,index}:any)=><option key={index} value={index}>Condition {index+1} · {agreementConditionLabel(run.definition?.conditions?.[index]??condition.threshold??condition)}</option>)}</select></label><AgreementTimeline rows={window.rows} conditionIndex={selectedAgreement} selectedIndex={selected?.row_index??null} onSelect={chooseRow}/></>}
   <ResearchChart candles={window.rows.map(row=>row.candle)} rows={window.rows} markers={window.markers} target={selected?.candle.time??null} onSelect={chooseRow}/>
<div className="research-actions"><button disabled={!chartBack.length&&window.start_index===0} onClick={()=>{const previous=chartBack.at(-1)??Math.max(0,window.start_index-200);void loadWindow({start_index:previous},chartBack.slice(0,-1));}}>Previous chart window</button><button disabled={window.next_index===null} onClick={()=>void loadWindow({start_index:window.next_index!},[...chartBack,window.start_index])}>Next chart window</button></div></>}
  {selected&&!chartBusy&&<RowEvidence row={selected} minutes={run.context.minutes}/>}
 </section>;
}
function RowEvidence({row,minutes}:{row:HistoryRow;minutes:number}){const value=row.evaluation;return <section aria-label="Selected historical row evidence"><h4>Exact selected row {row.row_index+1}</h4><p>Confirmed CLOSE {alertTime(value.confirmed_at)} · raw OPEN {alertTime(value.raw_open_time)} · native interval {minutes}m · {row.in_range?'inside requested range':'pre-range replay'}</p><p>Aggregate: {truthLabel(value.truth)} · state: {truthLabel(value.state_truth)} · match: {value.hit?'Yes':'No'}. Unknown is not False.</p><p>Saved raw OHLC: {row.candle.open} / {row.candle.high} / {row.candle.low} / {row.candle.close}</p><h5>Saved calculated values</h5>{Object.entries(value.values).map(([id,ports])=><p key={id}>{id}: {Object.entries(ports).map(([port,number])=>`${port} = ${number===null?'Unknown':number}`).join(' · ')}</p>)}<p>True state and new match are separate. {value.conditions.some(condition=>condition.predicate==='agreement')?agreementWarning:''}</p>{value.conditions.filter(condition=>condition.predicate==='agreement').map((condition,index)=><SavedAgreementEvidence key={condition.index??index} condition={condition}/>)}<details><summary>Saved condition evidence, including previous crossing values and pivots</summary><p>JSON null means Unknown; false means a known False condition.</p><pre>{JSON.stringify(value.conditions,null,2)}</pre></details></section>;}
function OriginalEvidence({eventId}:{eventId:string}){
 const [data,setData]=useState<EventEvidence|null>(null),[error,setError]=useState('');
 useEffect(()=>{let valid=true;api<EventEvidence>('alert_event_evidence',{event_id:eventId,before:40,after:40}).then(value=>{if(valid)setData(value);}).catch(error=>{if(valid)setError(message(error));});return()=>{valid=false;};},[eventId]);
 if(!data)return error?<p role="alert">{error}</p>:<p role="status">Reading original event evidence…</p>;
 const evidence=data.event.evidence;
 // A separately retained exact target remains usable when adjacent bytes clip it.
 // Unconfirmed/conflicting target candles are excluded, never marked as valid.
 const candles=data.candles.filter(c=>c.time!==data.target_raw_open_time||data.target_status==='confirmed');
 if(data.target_candle&&!candles.some(c=>c.time===data.target_raw_open_time))candles.push(data.target_candle);
 candles.sort((a,b)=>a.time-b.time);
 return <section aria-label="Original immutable alert evidence"><h3>Current rule name: {data.event.current_name}</h3><p>Current name is metadata; the evidence below is the original saved event.</p><p>Rule {data.event.rule_id} · event {data.event.id}</p><ContextLine context={data.context}/><p>Original confirmed CLOSE {alertTime(data.target_confirmed_at)} · exact target raw OPEN {alertTime(data.target_raw_open_time)} · observed {alertTime(evidence.observed_at)}</p><p>Navigation targets confirmation. Earlier divergence pivots remain supporting evidence and never replace the confirmation candle.</p><h4>Authoritative saved conditions and values</h4><p>Saved current and previous crossing values, frozen parameters, formula versions and origins below remain authoritative. JSON null means Unknown, never False or zero.</p><pre>{JSON.stringify(evidence,null,2)}</pre><h4>PRICE context from the current local cache</h4><p role="note">{data.warning} Price context source: {data.price_context_source}. These adjacent candles may differ from the original calculation.</p>{data.target_status!=='confirmed'&&<p role="alert">Exact target candle is {data.target_status}. No nearest candle or other interval is substituted.</p>}{data.byte_limited&&<p>Adjacent price context was shortened by the response byte budget.{data.target_candle&&!data.target_in_window?' The separately returned exact target is retained.':''}</p>}<ResearchChart candles={candles} target={data.target_status==='confirmed'?data.target_raw_open_time:null}/></section>;
}
