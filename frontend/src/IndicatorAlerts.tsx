import {useEffect, useRef, useState} from 'react';
import {api} from './api';
import {poll} from './poll';
import {useAlertSession, alertContextKey, alertIdentity, alertTime, type AlertEvent, type PendingAlert} from './AlertSession';
import type {ChartIndicator} from './ChartIndicators';
import './indicator-alerts.css';

export type AlertCatalog={version:1;ports:Record<string,Record<string,string>>;predicates:string[];divergences:string[];oscillators:string[];combine:string[];max_conditions:number;price_ports:string[];price_unit:string};
export type Operand={kind:'price';port:string}|{kind:'series';instance_id:string;port:string}|{kind:'level';value:number;unit:string};
export type Condition={predicate:string;left?:Operand;right?:Operand;instance_id?:string;event_kind?:string;oscillator?:string};
type SavedRule={id:string;name:string;revision:number;definition_revision:number;deleted:boolean;definition_hash:string;definition:any;runtime:any;rebind_required:boolean};
type Preview={definition:any;definition_hash:string;settings_revision:number};
type Option={key:string;label:string;unit:string;operand:Operand};
const message=(error:unknown)=>error instanceof Error?error.message:String(error);
export function alertOperands(catalog:AlertCatalog,instances:ChartIndicator[]):Option[]{return [
 ...catalog.price_ports.map(port=>({key:`price:${port}`,label:`Raw ${port}`,unit:catalog.price_unit,operand:{kind:'price' as const,port}})),
 ...instances.flatMap(instance=>Object.entries(catalog.ports[instance.type]??{}).map(([port,unit])=>({key:`series:${instance.id}:${port}`,label:`${instance.type} · ${instance.id} · ${port}`,unit,operand:{kind:'series' as const,instance_id:instance.id,port}})))];}
const operandKey=(operand?:Operand)=>operand?.kind==='series'?`series:${operand.instance_id}:${operand.port}`:operand?.kind==='price'?`price:${operand.port}`:'level';
const initialCondition=():Condition=>({predicate:'cross_above',left:{kind:'price',port:'close'},right:{kind:'level',value:10,unit:'price'}});
function ConditionEditor({condition,index,catalog,instances,onChange,onRemove,canRemove}:{condition:Condition;index:number;catalog:AlertCatalog;instances:ChartIndicator[];onChange:(value:Condition)=>void;onRemove:()=>void;canRemove:boolean}){
 const options=alertOperands(catalog,instances),left=options.find(option=>option.key===operandKey(condition.left)),unit=left?.unit??'';
 const compatible=options.filter(option=>option.unit===unit);
 const divergence=condition.predicate==='divergence',vmc=instances.filter(instance=>instance.type==='vmc_cipher_b');
 const changePredicate=(predicate:string)=>onChange(predicate==='divergence'?{predicate,instance_id:vmc[0]?.id??'',event_kind:catalog.divergences[0],oscillator:catalog.oscillators[0]}:{predicate,left:condition.left??{kind:'price',port:'close'},right:predicate==='above'||predicate==='below'||divergence?{kind:'level',value:10,unit:unit||catalog.price_unit}:condition.right});
 return <fieldset className="alert-condition"><legend>Condition {index+1}</legend>
  <label>Predicate<select aria-label={`Condition ${index+1} predicate`} value={condition.predicate} onChange={event=>changePredicate(event.target.value)}>{catalog.predicates.map(predicate=><option key={predicate} value={predicate} disabled={predicate==='divergence'&&!vmc.length}>{predicate.replaceAll('_',' ')}</option>)}</select></label>
  {divergence?<><label>VMC B instance<select aria-label={`Condition ${index+1} VMC B`} value={condition.instance_id} onChange={event=>onChange({...condition,instance_id:event.target.value})}>{vmc.map(instance=><option key={instance.id}>{instance.id}</option>)}</select></label><label>Confirmed divergence<select aria-label={`Condition ${index+1} divergence`} value={condition.event_kind} onChange={event=>onChange({...condition,event_kind:event.target.value})}>{catalog.divergences.map(kind=><option key={kind}>{kind}</option>)}</select></label><label>Oscillator<select aria-label={`Condition ${index+1} oscillator`} value={condition.oscillator} onChange={event=>onChange({...condition,oscillator:event.target.value})}>{catalog.oscillators.map(kind=><option key={kind}>{kind}</option>)}</select></label></>:<>
   <label>Left operand<select aria-label={`Condition ${index+1} left operand`} value={operandKey(condition.left)} onChange={event=>{const next=options.find(option=>option.key===event.target.value)!;onChange({...condition,left:next.operand,right:{kind:'level',value:condition.right?.kind==='level'?condition.right.value:10,unit:next.unit}});}}>{options.map(option=><option key={option.key} value={option.key}>{option.label} · {option.unit}</option>)}</select></label>
   <label>Right operand<select aria-label={`Condition ${index+1} right operand`} value={operandKey(condition.right)} onChange={event=>onChange({...condition,right:event.target.value==='level'?{kind:'level',value:10,unit}:compatible.find(option=>option.key===event.target.value)!.operand})}><option value="level">Numeric level · {unit}</option>{!['above','below'].includes(condition.predicate)&&compatible.map(option=><option key={option.key} value={option.key}>{option.label}</option>)}</select></label>
   {condition.right?.kind==='level'&&<label>Level<input aria-label={`Condition ${index+1} level`} type="number" step="any" value={Number.isFinite(condition.right.value)?condition.right.value:''} onChange={event=>onChange({...condition,right:{kind:'level',unit,value:event.target.value===''?NaN:Number(event.target.value)}})}/></label>}
  </>}
  <button disabled={!canRemove} onClick={onRemove}>Remove condition {index+1}</button>
 </fieldset>;
}
export function FrozenAlert({definition}:{definition:any}){return <section aria-label="Frozen alert definition" className="alert-frozen"><p>{definition.context.source} / {definition.context.market} / {definition.context.symbol} / {definition.context.minutes}m · applied revision {definition.settings_revision} · {definition.combine}</p><p>Raw confirmed OHLC. Unknown values remain unknown. ALL impulses must share one confirmed close.</p><details><summary>Frozen parameters, origin and conditions</summary><pre>{JSON.stringify(definition,null,2)}</pre></details></section>;}

export default function IndicatorAlerts(){
 const session=useAlertSession();
 if(!session)return null;
 return <AlertPanel session={session}/>;
}
function AlertPanel({session}:{session:NonNullable<ReturnType<typeof useAlertSession>>}){
 const {controller,view,pending,storageError}=session;
 const contextKey=view?alertContextKey(view):'',settingsRevision=view?.settings.revision??-1;
 const [opened,setOpened]=useState(false),[catalog,setCatalog]=useState<AlertCatalog|null>(null);
 const [trashed,setTrashed]=useState(false),[rules,setRules]=useState<SavedRule[]>([]),[next,setNext]=useState<string|null>(null),[loading,setLoading]=useState(false),[refresh,setRefresh]=useState(0);
 const [selected,setSelected]=useState<SavedRule|null>(null),[name,setName]=useState(''),[reviewed,setReviewed]=useState(false);
 const [conditions,setConditions]=useState<Condition[]>([initialCondition()]),[combine,setCombine]=useState('ALL'),[composerContext,setComposerContext]=useState(''),[composerRevision,setComposerRevision]=useState(-1),[rebind,setRebind]=useState(false),[preview,setPreview]=useState<Preview|null>(null),[previewReviewed,setPreviewReviewed]=useState(false);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[retryOriginal,setRetryOriginal]=useState(false),[absentArm,setAbsentArm]=useState(false);
 const [events,setEvents]=useState<AlertEvent[]>([]),[eventNext,setEventNext]=useState<number|null>(null),[eventDetail,setEventDetail]=useState<AlertEvent|null>(null),[unread,setUnread]=useState(false),[journalRefresh,setJournalRefresh]=useState(0);
 const alive=useRef(true),listEpoch=useRef(0),selectionEpoch=useRef(0),editorEpoch=useRef(0),journalEpoch=useRef(0),detailEpoch=useRef(0),writeLock=useRef(false),readLock=useRef(false);
 const current=useRef({contextKey,settingsRevision,revision:session.revision});current.current={contextKey,settingsRevision,revision:session.revision};
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;++listEpoch.current;++selectionEpoch.current;++editorEpoch.current;++journalEpoch.current;++detailEpoch.current;};},[]);
 useEffect(()=>{++selectionEpoch.current;++editorEpoch.current;setReviewed(false);setPreviewReviewed(false);setPreview(null);},[contextKey,settingsRevision,session.revision]);
 useEffect(()=>{if(!composerContext&&view){setComposerContext(contextKey);setComposerRevision(settingsRevision);}},[contextKey,settingsRevision,composerContext,view]);
 useEffect(()=>{if(!opened||catalog)return;let gone=false;api<AlertCatalog>('alert_catalog').then(value=>{if(value.version!==1||!value.ports||!Array.isArray(value.predicates)||value.max_conditions!==16)throw new Error('Unsupported alert catalog');if(!gone)setCatalog(value);}).catch(error=>{if(!gone)setError(message(error));});return()=>{gone=true;};},[opened,catalog]);
 const loadRules=async(append=false)=>{
  const epoch=++listEpoch.current;setLoading(true);
  try{const page=await api<{rules:SavedRule[];next_cursor:string|null}>('alert_list',{trashed,after:append?next:null,limit:20});if(alive.current&&epoch===listEpoch.current){setRules(rows=>append?[...rows,...page.rules]:page.rules);setNext(page.next_cursor);}}
  catch(error){if(alive.current&&epoch===listEpoch.current)setError(message(error));}
  finally{if(alive.current&&epoch===listEpoch.current)setLoading(false);}
 };
 useEffect(()=>{if(opened)void loadRules();return()=>{++listEpoch.current;};},[opened,trashed,refresh]);
 useEffect(()=>{
  if(!opened||!selected)return;
  const id=selected.id,epoch=selectionEpoch.current;
  return poll(()=>api<SavedRule>('alert_get',{rule_id:id}),rule=>{if(epoch===selectionEpoch.current){setSelected(rule);setRules(rows=>rows.map(row=>row.id===rule.id?rule:row));if(rule.revision!==selected.revision||rule.rebind_required)setReviewed(false);}},()=>{},1000);
 },[opened,selected?.id,selected?.revision,refresh,session.revision,settingsRevision]);
 const choose=async(id:string)=>{
  const epoch=++selectionEpoch.current;++editorEpoch.current;setSelected(null);setReviewed(false);setPreview(null);setPreviewReviewed(false);setRebind(false);setError('');
  if(!id)return;
  try{const rule=await api<SavedRule>('alert_get',{rule_id:id});if(alive.current&&epoch===selectionEpoch.current){setSelected(rule);setName(rule.name);}}
  catch(error){if(alive.current&&epoch===selectionEpoch.current)setError(message(error));}
 };
 const newComposer=(rebindRule=false)=>{
  ++editorEpoch.current;setConditions(rebindRule?structuredClone(selected!.definition.conditions):[initialCondition()]);setCombine(rebindRule?selected!.definition.combine:'ALL');setComposerContext(contextKey);setComposerRevision(settingsRevision);setRebind(rebindRule);setPreview(null);setPreviewReviewed(false);setReviewed(false);if(!rebindRule){++selectionEpoch.current;setSelected(null);setName('');}setError('');setNotice('');
 };
 const edit=(next:Condition[])=>{++editorEpoch.current;setConditions(next);setPreview(null);setPreviewReviewed(false);};
 const freshComposer=!!view?.visible&&view.available&&controller.isCurrent(session.revision)&&composerContext===contextKey&&composerRevision===settingsRevision;
 const matches=!!selected&&!!view&&['source','market','symbol','minutes'].every(key=>selected.definition.context[key]===view[key as keyof typeof view]);
 const blocked=busy||!!pending||!!storageError;
 const validName=!!name.trim()&&[...name.trim()].length<=120;
 const previewRule=async()=>{
  if(!freshComposer||blocked||readLock.current)return;
  const epoch=editorEpoch.current,context={...current.current};readLock.current=true;setBusy(true);setError('');
  try{const value=await api<Preview>('alert_preview',{source:view!.source,market:view!.market,symbol:view!.symbol,minutes:view!.minutes,settings_revision:settingsRevision,conditions,combine});if(alive.current&&epoch===editorEpoch.current&&JSON.stringify(context)===JSON.stringify(current.current)){setPreview(value);setPreviewReviewed(false);}}
  catch(error){if(alive.current&&epoch===editorEpoch.current)setError(message(error));}
  finally{readLock.current=false;if(alive.current)setBusy(false);}
 };
 const operate=async(command:string,params:Record<string,any>,original?:PendingAlert)=>{
  if(writeLock.current||storageError||pending&&!original)return;
  const operation=original??{command,params,contextKey,settingsRevision,createdAt:new Date().toISOString()};
  const epoch=selectionEpoch.current,editor=editorEpoch.current,context={...current.current};
  writeLock.current=true;setBusy(true);setError('');setNotice('');setReviewed(false);setPreviewReviewed(false);setRetryOriginal(false);setAbsentArm(false);
  try{
   session.retain(operation);
   if(command==='alert_arm'){
    // Establish an authoritative pause before every new review/action. Replaying
    // an old Arm identity is never used to resume monitoring.
    await api('alert_pause',{rule_id:params.rule_id});
    if(!controller.isCurrent(context.revision)||epoch!==selectionEpoch.current)throw Object.assign(new Error('Context changed before Arm. Review again.'),{definiteRejection:true});
   }
   const value=await api<SavedRule>(command,params);session.retain(null);session.refresh();setRefresh(n=>n+1);setJournalRefresh(n=>n+1);
   if(alive.current&&epoch===selectionEpoch.current&&editor===editorEpoch.current&&JSON.stringify(context)===JSON.stringify(current.current)){
    if(command!=='alert_arm'){setSelected(value);setName(value.name);setRebind(false);setPreview(null);}setNotice(command==='alert_arm'?'Arm requested. ARMING is not yet ARMED; status below is authoritative.':'Saved rule change. Monitoring remains paused until a new explicit Arm.');
   }else if(alive.current)setNotice('The original alert operation completed. Reopen its saved rule to review; this editor was not replaced.');
  }catch(error){
   let resolved=false,accepted=false;
   if((error as any)?.definiteRejection){
    // A completed Service error can occur after the durable commit but before
    // its readback. The envelope alone is not proof that no write happened.
    try{
     const request=params.request_id?await api<any>('alert_request',{request_id:params.request_id}):null;
     if(original&&!request)throw new Error('Earlier uncertain attempt is not settled by a rejected retry');
     const ruleId=request?.rule_id??params.rule_id;
     const saved=ruleId?await api<SavedRule>('alert_get',{rule_id:ruleId}):null;
     accepted=!!request||!!saved&&saved.revision!==params.revision;
     session.retain(null);resolved=true;session.refresh();setRefresh(n=>n+1);
     if(saved&&alive.current&&epoch===selectionEpoch.current&&editor===editorEpoch.current&&JSON.stringify(context)===JSON.stringify(current.current)){setSelected(saved);setName(saved.name);}
    }catch{/* Readback failed: retain exact identity/content for reconciliation. */}
   }
   if(alive.current)setError(`${resolved?(accepted?'The original write was committed; its readback reported an error. Review the saved rule.':'Alert operation rejected; request/readback confirms no new accepted write.'):'Alert outcome is unknown. Reconcile the original request before another write.'} ${message(error)}`);
  }finally{writeLock.current=false;if(alive.current)setBusy(false);}
 };
 const reconcile=async()=>{
  if(!pending||writeLock.current)return;writeLock.current=true;setBusy(true);setError('');setReviewed(false);setPreviewReviewed(false);setRetryOriginal(false);setAbsentArm(false);
  try{
   let id=pending.params.rule_id;
   if(pending.params.request_id){const request=await api<any>('alert_request',{request_id:pending.params.request_id});if(!request&&pending.command==='alert_create'){setNotice('No accepted request is recorded. Its exact identity and content remain retained.');setRetryOriginal(true);return;}if(!request&&pending.command==='alert_arm'){setAbsentArm(true);setNotice('No accepted Arm request is recorded. Recover paused state before a fresh review; this request will never be replayed.');return;}if(request)id=request.rule_id;}
   const value=await api<SavedRule>('alert_get',{rule_id:id});
   session.retain(null);setRefresh(n=>n+1);session.refresh();setJournalRefresh(n=>n+1);
   setNotice(`Original ${pending.command.replace('alert_','')} reconciled: current name ${value.name}, rule ID ${value.id}, revision ${value.revision}${pending.params.revision!==undefined?` (submitted revision ${pending.params.revision})`:''}. ${value.runtime.phase}. Select the saved rule and review again before another action.`);
   // A reconciled write never selects or rewrites an unrelated context/editor.
   if(selected?.id===id){++selectionEpoch.current;setSelected(value);}
  }catch(error){setError('Reconciliation is still uncertain. '+message(error));}
  finally{writeLock.current=false;if(alive.current)setBusy(false);}
 };
 const recoverArm=async()=>{
  if(!pending||pending.command!=='alert_arm'||!absentArm||writeLock.current)return;
  writeLock.current=true;setBusy(true);setReviewed(false);setPreviewReviewed(false);setError('');
  try{
   await controller.fence();
   await api('alert_pause',{rule_id:pending.params.rule_id});
   await api('alert_request',{request_id:pending.params.request_id});
   const value=await api<SavedRule>('alert_get',{rule_id:pending.params.rule_id});
   if(value.runtime?.phase!=='PAUSED')throw new Error('Pause is not yet authoritative');
   session.retain(null);setAbsentArm(false);session.refresh();setRefresh(n=>n+1);
   setNotice('Original Arm fenced and Pause confirmed. Select the saved rule and make a fresh review before a new Arm.');
  }catch(error){setError('Arm recovery is still uncertain. '+message(error));}
  finally{writeLock.current=false;setBusy(false);}
 };
 const pause=async(all=false)=>{if(writeLock.current)return;writeLock.current=true;setBusy(true);setReviewed(false);try{await api('alert_pause',selected&&!all?{rule_id:selected.id}:{});session.refresh();setRefresh(n=>n+1);setNotice('Pause confirmed. A fresh review and Arm are required to resume.');}catch(error){setError('Pause could not be confirmed. '+message(error));}finally{writeLock.current=false;setBusy(false);}};
 const loadEvents=async(append=false)=>{const epoch=++journalEpoch.current;try{const page=await api<{events:AlertEvent[];next_cursor:number|null}>('alert_events',{after:append?eventNext??0:0,limit:20,unread_only:unread});if(alive.current&&epoch===journalEpoch.current){setEvents(rows=>append?[...rows,...page.events]:page.events);setEventNext(page.next_cursor);}}catch(error){if(alive.current&&epoch===journalEpoch.current)setError(message(error));}};
 useEffect(()=>{if(opened)void loadEvents();return()=>{++journalEpoch.current;};},[opened,unread,journalRefresh]);
 const inspectEvent=async(id:string)=>{const epoch=++detailEpoch.current;try{const value=await api<AlertEvent>('alert_event',{event_id:id});if(alive.current&&epoch===detailEpoch.current)setEventDetail(value);}catch(error){setError(message(error));}};
 useEffect(()=>{if(!opened||!eventDetail)return;const id=eventDetail.id,epoch=detailEpoch.current;return poll(()=>api<AlertEvent>('alert_event',{event_id:id}),value=>{if(epoch===detailEpoch.current)setEventDetail(value);},()=>{},1000);},[opened,eventDetail?.id,journalRefresh]);
 const markRead=async(event:AlertEvent)=>{try{const value=await api<AlertEvent>('alert_mark_read',{event_id:event.id,is_read:!event.is_read});setEvents(rows=>rows.map(row=>row.id===value.id?value:row));if(eventDetail?.id===value.id)setEventDetail(value);setJournalRefresh(n=>n+1);}catch(error){setError('Read state could not be confirmed. Refresh the journal. '+message(error));}};
 const runtime=selected&&(session.runtimes.find(runtime=>runtime.rule_id===selected.id)??selected.runtime);
 return <section className="indicator-alerts" aria-label="Local indicator alerts">
  <div className="alert-panel-heading"><button aria-expanded={opened} onClick={()=>setOpened(value=>!value)}>Local alerts</button><button disabled={busy} onClick={()=>void pause(true)}>Pause all alerts</button><small>Closing a browser tab does not stop Service. Pause alerts before closing.</small></div>
  {opened&&<>
   <p>Local journal and banners only. Saved rules start paused. Only subsequent observed raw native closes are eligible after Arm; chart style, history browsing and hidden panes do not change the frozen calculation.</p>
   {error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
   {pending&&<div className="alert-uncertain"><strong>Original write awaiting reconciliation: {pending.command}</strong><p>{pending.createdAt} · {pending.contextKey}</p><button disabled={busy} onClick={()=>void reconcile()}>Reconcile original alert write</button>{absentArm&&<button disabled={busy} onClick={()=>void recoverArm()}>Recover paused Arm</button>}{retryOriginal&&<button disabled={busy||pending.contextKey!==contextKey||pending.settingsRevision!==settingsRevision||!session.ready||!view?.visible||!view.available} onClick={()=>void operate(pending.command,pending.params,pending)}>Retry exact original create</button>}</div>}
   <div className="alert-library"><h3>Rule library</h3><label>Alert library view<select aria-label="Alert library view" value={trashed?'archived':'saved'} disabled={busy} onChange={event=>{const value=event.target.value==='archived';if(value===trashed)return;++selectionEpoch.current;setTrashed(value);setSelected(null);setReviewed(false);}}><option value="saved">Saved</option><option value="archived">Archived</option></select></label><button disabled={loading||busy} onClick={()=>setRefresh(n=>n+1)}>Refresh alert library</button><label>Saved rule<select aria-label="Saved alert rule" value={selected?.id??''} disabled={busy} onChange={event=>void choose(event.target.value)}><option value="">Select a rule</option>{rules.map(rule=><option key={rule.id} value={rule.id}>{rule.name} · {rule.id}</option>)}</select></label>{loading&&<span role="status">Loading alert rules…</span>}{next&&<button disabled={loading} onClick={()=>void loadRules(true)}>Load more alert rules</button>}<small>{rules.length} loaded{next?' · more available':' · end of library'}. No fixed saved-rule count quota.</small></div>
   <label>Alert name<input aria-label="Alert name" value={name} maxLength={240} disabled={blocked} onChange={event=>setName(event.target.value)}/></label>
   {selected&&<section aria-label="Saved alert review"><h3>Current name: {selected.name}</h3><p>Rule ID: {selected.id} · revision {selected.revision} · definition revision {selected.definition_revision}</p><p role="status">{runtime?.phase??'Unknown'} · {runtime?.reason??'Runtime status unavailable'} · confirmed baseline {alertTime(runtime?.confirmed_at)}</p><FrozenAlert definition={selected.definition}/>{selected.rebind_required&&<p role="alert">Surviving indicator parameters changed. Review and rebind to applied settings before arming.</p>}{!matches&&<p>Open this rule's exact Market source, market, symbol and native timeframe before arming.</p>}
    <div className="alert-actions"><button disabled={busy} onClick={()=>void pause()}>Pause selected alert</button><button disabled={blocked||!validName||selected.deleted} onClick={()=>void operate('alert_rename',{rule_id:selected.id,revision:selected.revision,name:name.trim()})}>Rename alert</button><button disabled={blocked} onClick={()=>void operate(selected.deleted?'alert_restore':'alert_archive',{rule_id:selected.id,revision:selected.revision})}>{selected.deleted?'Restore alert':'Archive alert'}</button><button disabled={blocked||selected.deleted||!matches||!view?.available} onClick={()=>newComposer(true)}>Edit / rebind from applied settings</button></div>
    <label className="alert-review"><input type="checkbox" aria-label="Reviewed saved alert for Arm" checked={reviewed} disabled={blocked||!matches||selected.deleted||selected.rebind_required||!session.ready||!session.statusKnown||!view?.visible} onChange={event=>setReviewed(event.target.checked)}/>I reviewed this frozen rule, its exact context and parameters. Arm establishes a new baseline without historical signals.</label><button disabled={blocked||!reviewed||!matches||selected.deleted||selected.rebind_required||!view?.visible||!session.ready||!session.statusKnown||runtime?.phase==='ARMING'||runtime?.phase==='ARMED'} onClick={()=>void operate('alert_arm',{request_id:alertIdentity(),rule_id:selected.id,revision:selected.revision,definition_hash:selected.definition_hash,session_id:controller.sessionId,context_revision:session.revision,reviewed:true})}>Arm / Resume alert</button>
   </section>}
   <section aria-label="Alert composer"><h3>{rebind?'Review replacement definition':'New alert'}</h3><button disabled={blocked||!view?.visible||!view.available} onClick={()=>newComposer()}>New rule for current context</button><p>Uses applied indicator settings only, not unapplied chart or preset edits. Applied revision: {settingsRevision}.</p>{!freshComposer&&<p role="status">Composer context or applied settings changed. Start a new rule, or select Edit / rebind to review the current applied settings.</p>}
    <fieldset disabled={blocked||!freshComposer}><label>Combine conditions<select aria-label="Alert condition group" value={combine} onChange={event=>{setCombine(event.target.value);edit(conditions);}}>{(catalog?.combine??['ALL','ANY']).map(value=><option key={value}>{value}</option>)}</select></label>{catalog&&conditions.map((condition,index)=><ConditionEditor key={index} condition={condition} index={index} catalog={catalog} instances={view?.settings.instances??[]} onChange={value=>edit(conditions.map((old,i)=>i===index?value:old))} onRemove={()=>edit(conditions.filter((_,i)=>i!==index))} canRemove={conditions.length>1}/>)}<button disabled={!catalog||conditions.length>=catalog.max_conditions} onClick={()=>edit([...conditions,initialCondition()])}>Add condition</button><span> {conditions.length} / {catalog?.max_conditions??16} conditions</span><button disabled={!catalog||conditions.some(condition=>condition.right?.kind==='level'&&!Number.isFinite(condition.right.value))} onClick={()=>void previewRule()}>Preview frozen alert</button></fieldset>
    {preview&&<><FrozenAlert definition={preview.definition}/><label className="alert-review"><input aria-label="Reviewed frozen alert preview" type="checkbox" checked={previewReviewed} disabled={blocked||!freshComposer} onChange={event=>setPreviewReviewed(event.target.checked)}/>I reviewed the frozen parameters, calculation origin and conditions.</label><button disabled={blocked||!freshComposer||!previewReviewed||!validName||rebind&&!selected} onClick={()=>void operate(rebind?'alert_rebind':'alert_create',rebind?{rule_id:selected!.id,revision:selected!.revision,...preview}:{request_id:alertIdentity(),name:name.trim(),...preview})}>{rebind?'Save reviewed rebind paused':'Save alert paused'}</button></>}
   </section>
   <section aria-label="Local alert journal"><h3>Local alert journal</h3><button onClick={()=>setJournalRefresh(n=>n+1)}>Refresh alert journal</button><label><input type="checkbox" checked={unread} onChange={event=>setUnread(event.target.checked)}/>Unread only</label><p>Names below are CURRENT saved names, separate from immutable evidence. Missing evidence remains unknown. Read state is independent of banner claiming.</p>{events.map(event=><article key={event.id}><strong>Current name: {event.current_name}</strong><small>Rule ID: {event.rule_id}</small><span>{event.is_read?'Read':'Unread'} · {alertTime(event.evidence?.confirmed_at??event.evidence?.evaluation?.confirmed_at)}</span><button onClick={()=>void inspectEvent(event.id)}>Event detail {event.sequence}</button><button onClick={()=>void markRead(event)}>Mark {event.is_read?'unread':'read'} {event.sequence}</button></article>)}{eventNext!==null&&<button onClick={()=>void loadEvents(true)}>Load more alert events</button>}{!events.length&&<p>No journal events in this view.</p>}
    {eventDetail&&<section aria-label="Alert event detail"><h4>Current name: {eventDetail.current_name}</h4><p>Rule ID: {eventDetail.rule_id} · event ID: {eventDetail.id}</p><p>Immutable evidence: raw open {alertTime(eventDetail.evidence?.raw_open_time??eventDetail.evidence?.evaluation?.raw_open_time)} · confirmed close {alertTime(eventDetail.evidence?.confirmed_at??eventDetail.evidence?.evaluation?.confirmed_at)} · observed {alertTime(eventDetail.evidence?.observed_at)}</p><p>JSON null means Unknown, never false or zero. Frozen event data is not rewritten by a later rename or rebind.</p><pre>{JSON.stringify(eventDetail.evidence,null,2)}</pre><button onClick={()=>{++detailEpoch.current;setEventDetail(null);}}>Close event detail</button></section>}
   </section>
  </>}
 </section>;
}
