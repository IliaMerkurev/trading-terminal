import {createContext,useContext,useEffect,useRef,useState,type ReactNode} from 'react';
import {api} from './api';
import {alertIdentity} from './AlertSession';
import type {FrozenRule} from './alertResearch';
import {frozenRuleContract,readFrozenRule,type FrozenRuleIdentity} from './frozenRule';
import FrozenRuleDetails,{frozenExecutionLimits} from './FrozenRuleDetails';
import type {Graph,Layout,Profile} from './model';
import './rule-strategy-conversion.css';

type Direction='long'|'short';
type PreviewParams={rule_id:string;revision:number;name:string;direction:Direction};
export type RuleStrategyPreview={preview_hash:string;rule:FrozenRuleIdentity;name:string;direction:Direction;graph:Graph;layout:Layout;profile:Profile;warnings:string[];contract:typeof frozenRuleContract};
export type StrategyCreateParams=PreviewParams&{preview_hash:string;request_id:string};
type Pending={version:1;params:StrategyCreateParams;createdAt:string;hadUnknown:boolean};
type Receipt={strategy_id:string;request_id:string};
type Review={rule:FrozenRule;token:object};
export const pendingRuleStrategyKey='terminal.rule-strategy.pending.v1';
const message=(error:unknown)=>error instanceof Error?error.message:String(error);
const Context=createContext<{open:(rule:FrozenRule,token:object)=>void;invalidate:(token:object)=>void;blocked:boolean}|null>(null);
function readPending():{pending:Pending|null;error:string} {
  try {
    const raw=localStorage.getItem(pendingRuleStrategyKey);
    if(!raw)return {pending:null,error:''};
    const value=JSON.parse(raw),p=value?.params;
    if(value.version!==1||!p||typeof p.rule_id!=='string'||!Number.isInteger(p.revision)||typeof p.name!=='string'||!['long','short'].includes(p.direction)||typeof p.preview_hash!=='string'||typeof p.request_id!=='string'||!p.request_id||typeof value.createdAt!=='string'||typeof value.hadUnknown!=='boolean')throw Error('Unsupported pending request');
    return {pending:value,error:''};
  } catch(error) {return {pending:null,error:'Pending strategy creation could not be read. New creation is blocked to avoid duplicate strategies. '+message(error)};}
}
function checkedReceipt(value:any,requestId:string):Receipt {
  if(!value||typeof value.strategy_id!=='string'||!value.strategy_id||value.request_id!==requestId)throw Error('Unsupported strategy creation receipt');
  return value;
}
function checkedPreview(value:RuleStrategyPreview,params:PreviewParams,rule:FrozenRule):RuleStrategyPreview {
  const frozen=value?.graph?.nodes?.filter(node=>node.type==='frozen_rule')??[];
  const snapshot=frozen.length===1?readFrozenRule(frozen[0]):null;
  if(value?.contract!==frozenRuleContract||typeof value.preview_hash!=='string'||!value.preview_hash||value.name!==params.name||value.direction!==params.direction||value.rule?.id!==rule.id||value.rule.revision!==rule.revision||value.rule.definition_hash!==rule.definition_hash||value.rule.definition_revision!==rule.definition_revision||!snapshot||(['id','name','revision','definition_revision','definition_hash'] as const).some(key=>snapshot.rule[key]!==value.rule[key])||!Array.isArray(value.warnings)||!value.profile)throw Error('Unsupported or stale frozen strategy preview. Select the saved rule and review again.');
  return value;
}
export function RuleStrategyAction({rule,scopeKey,disabled=false}:{rule:FrozenRule;scopeKey:string;disabled?:boolean}) {
  const bridge=useContext(Context),token=useRef<object>({});
  // A source switch, rule edit, selection change or panel unmount cancels only
  // the review. Already-submitted identities remain available for readback.
  useEffect(()=>{const current=token.current={};return()=>bridge?.invalidate(current);},[scopeKey,rule.id,rule.revision,rule.definition_hash]);
  if(!bridge)return null;
  return <button disabled={disabled||bridge.blocked} onClick={()=>bridge.open(structuredClone(rule),token.current)}>Create strategy from rule</button>;
}
export function RuleStrategyProvider({children,onOpenStrategy,onRefresh}:{children:ReactNode;onOpenStrategy:(id:string,isCurrent:()=>boolean)=>Promise<void>;onRefresh:()=>Promise<void>}) {
  const [initial]=useState(readPending);
  const [pending,setPending]=useState<Pending|null>(initial.pending),pendingRef=useRef(initial.pending);
  const [storageError,setStorageError]=useState(initial.error),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const [review,setReview]=useState<Review|null>(null),reviewRef=useRef<Review|null>(null);
  const [name,setName]=useState(''),[direction,setDirection]=useState<Direction|''>('');
  const [preview,setPreview]=useState<RuleStrategyPreview|null>(null),[reviewed,setReviewed]=useState(false);
  const [busy,setBusy]=useState(false),[absent,setAbsent]=useState(false),[receipt,setReceipt]=useState<Receipt|null>(null);
  const alive=useRef(true),epoch=useRef(0),lock=useRef(false),readLock=useRef(false);
  const callbacks=useRef({onOpenStrategy,onRefresh});callbacks.current={onOpenStrategy,onRefresh};
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;++epoch.current;};},[]);
  function retain(value:Pending|null) {
    try {
      if(value)localStorage.setItem(pendingRuleStrategyKey,JSON.stringify(value));else localStorage.removeItem(pendingRuleStrategyKey);
      pendingRef.current=value;if(alive.current)setPending(value);
    } catch(error) {
      const text='Strategy request storage is unavailable. Creation is blocked until durable storage is restored. '+message(error);
      if(alive.current)setStorageError(text);throw Error(text);
    }
  }
  function cancelReview(token?:object) {
    if(token&&reviewRef.current?.token!==token)return;
    ++epoch.current;reviewRef.current=null;setReview(null);setPreview(null);setReviewed(false);
  }
  function open(rule:FrozenRule,token:object) {
    if(pendingRef.current||storageError||lock.current)return;
    ++epoch.current;const next={rule,token};reviewRef.current=next;setReview(next);
    setName(`${rule.name} strategy`);setDirection('');setPreview(null);setReviewed(false);setError('');setNotice('');setReceipt(null);
  }
  function edit(change:()=>void) {++epoch.current;change();setPreview(null);setReviewed(false);setError('');}
  async function requestPreview() {
    if(!review||!direction||!name.trim()||[...name.trim()].length>120||readLock.current||pendingRef.current||storageError)return;
    const current=epoch.current,params:PreviewParams={rule_id:review.rule.id,revision:review.rule.revision,name:name.trim(),direction};
    readLock.current=true;setBusy(true);setError('');setPreview(null);setReviewed(false);
    try {
      const value=checkedPreview(await api<RuleStrategyPreview>('alert_strategy_preview',params),params,review.rule);
      if(alive.current&&current===epoch.current)setPreview(value);
    } catch(error) {if(alive.current&&current===epoch.current)setError(message(error));}
    finally {readLock.current=false;if(alive.current)setBusy(false);}
  }
  async function accept(value:Receipt,current?:number) {
    // Capture the accepted receipt even when local cleanup or editor refresh fails.
    if(alive.current){setReceipt(value);setAbsent(false);setNotice('Strategy saved independently. Its frozen source and existing run snapshots are preserved.');}
    retain(null);
    try {
      await callbacks.current.onRefresh();
      if(alive.current&&current!==undefined&&current===epoch.current&&reviewRef.current) {
        await callbacks.current.onOpenStrategy(value.strategy_id,()=>alive.current&&current===epoch.current);
        if(alive.current&&current===epoch.current)cancelReview();
      }
    } catch(error) {if(alive.current)setError('The strategy was saved, but the editor or library could not refresh. Use Open created strategy. '+message(error));}
  }
  async function reconcile() {
    const original=pendingRef.current;if(!original||lock.current)return;
    lock.current=true;setBusy(true);setError('');setAbsent(false);
    try {
      const value=await api<Receipt|null>('alert_strategy_request',{request_id:original.params.request_id});
      if(value)await accept(checkedReceipt(value,original.params.request_id));
      else if(alive.current){setAbsent(true);setNotice('No accepted request is recorded. The exact original request is retained. Retry only this identity and content.');}
    } catch(error) {if(alive.current)setError('Creation outcome remains unknown. Reconcile the retained request before another creation. '+message(error));}
    finally {lock.current=false;if(alive.current)setBusy(false);}
  }
  useEffect(()=>{if(initial.pending)void reconcile();},[]);
  async function create(original?:Pending) {
    if(lock.current||storageError||(!original&&pendingRef.current)||(!original&&(!review||!preview||!reviewed)))return;
    const operation:Pending=original??{version:1,params:{rule_id:preview!.rule.id,revision:preview!.rule.revision,name:preview!.name,direction:preview!.direction,preview_hash:preview!.preview_hash,request_id:alertIdentity()},createdAt:new Date().toISOString(),hadUnknown:false};
    const current=epoch.current;lock.current=true;setBusy(true);setError('');setAbsent(false);setReviewed(false);
    let submitted=false;
    try {
      retain(operation); // Synchronous durable write must succeed before transmission.
      submitted=true;
      const value=await api<Receipt>('alert_strategy_create',operation.params);
      await accept(checkedReceipt(value,operation.params.request_id),original?undefined:current);
    } catch(error) {
      if(!submitted){if(alive.current)setError(message(error));return;}
      // Even a completed error can follow a committed write; read its identity.
      try {
        const value=await api<Receipt|null>('alert_strategy_request',{request_id:operation.params.request_id});
        if(value){await accept(checkedReceipt(value,operation.params.request_id),original?undefined:current);return;}
        if((error as any)?.definiteRejection&&!operation.hadUnknown) {
          retain(null);if(alive.current){setPreview(null);setError('Strategy creation was rejected; no accepted request is recorded. Preview and review again. '+message(error));}
        } else {
          retain({...operation,hadUnknown:true});if(alive.current){setAbsent(true);setError('Creation outcome is unknown; no accepted request is recorded yet. The original identity is retained. '+message(error));}
        }
      } catch(readError) {
        try {retain({...operation,hadUnknown:true});}catch{/* Keep the already-durable original payload. */}
        if(alive.current)setError('Creation outcome is unknown. Reconcile the original request before another write. '+message(readError));
      }
    } finally {lock.current=false;if(alive.current)setBusy(false);}
  }
  async function openReceipt() {
    if(!receipt||lock.current)return;
    const current=epoch.current;lock.current=true;setBusy(true);setError('');
    try {await callbacks.current.onOpenStrategy(receipt.strategy_id,()=>alive.current&&current===epoch.current);if(alive.current&&current===epoch.current)cancelReview();}
    catch(error) {if(alive.current)setError('Could not open the saved strategy. '+message(error));}
    finally {lock.current=false;if(alive.current)setBusy(false);}
  }
  const blocked=busy||!!pending||!!storageError;
  return <Context.Provider value={{open,invalidate:cancelReview,blocked:!!pending||!!storageError||lock.current}}>{children}
    {(pending||storageError||receipt||(!review&&(error||notice)))&&<section className="rule-strategy-recovery" aria-label="Strategy creation recovery">
      {storageError&&<p role="alert">{storageError}</p>}{!review&&error&&<p role="alert">{error}</p>}{!review&&notice&&<p role="status">{notice}</p>}
      {pending&&<><strong>Original strategy request retained</strong><p>{pending.params.name} · {pending.params.direction} · rule {pending.params.rule_id} revision {pending.params.revision}</p><p>Request {pending.params.request_id} · {pending.createdAt}</p><button disabled={busy} onClick={()=>void reconcile()}>Reconcile strategy creation</button>{absent&&<button disabled={busy||!!storageError} onClick={()=>void create(pending)}>Retry exact strategy request</button>}</>}
      {receipt&&<><button disabled={busy} onClick={()=>void openReceipt()}>Open created strategy</button>{!pending&&!storageError&&<button onClick={()=>{setReceipt(null);setNotice('');setError('');}}>Dismiss strategy receipt</button>}</>}
    </section>}
    {review&&<div className="rule-strategy-overlay"><section className="rule-strategy-dialog" role="dialog" aria-modal="true" aria-labelledby="rule-strategy-title">
      <h2 id="rule-strategy-title">Create strategy from saved rule</h2><p>Review an independent visual strategy from {review.rule.name}. Choose the entry direction explicitly.</p>
      {error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
      <label>New strategy name<input aria-label="New strategy name" maxLength={120} value={name} disabled={!!pending||lock.current} onChange={event=>edit(()=>setName(event.target.value))}/></label>
      <label>Entry direction<select aria-label="Strategy entry direction" value={direction} disabled={!!pending||lock.current} onChange={event=>edit(()=>setDirection(event.target.value as Direction|''))}><option value="">Choose direction</option><option value="long">Long</option><option value="short" disabled={review.rule.definition.context.market==='spot'}>Short{review.rule.definition.context.market==='spot'?' (unavailable for unborrowed spot)':''}</option></select></label>
      <p>{frozenExecutionLimits}</p>
      <button disabled={blocked||!direction||!name.trim()||[...name.trim()].length>120} onClick={()=>void requestPreview()}>Preview strategy conversion</button>
      {preview&&<section aria-label="Strategy conversion review"><FrozenRuleDetails node={preview.graph.nodes.find(node=>node.type==='frozen_rule')!}/>
        <h3>Entry and simulation defaults</h3><p>{preview.direction==='long'?'Long':'Short'} entry from the exact replay hit. No exit, stop-loss or take-profit is invented. Configure exits and risk settings in the strategy editor before running.</p>
        <dl className="conversion-defaults">{Object.entries(preview.profile).map(([key,value])=><div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{typeof value==='object'?JSON.stringify(value):String(value)}</dd></div>)}</dl>
        <p>Fee and slippage values are fractions: 0.001 means 0.1%. Allocation follows the displayed sizing mode. Settings and ordinary graph nodes stay editable; the frozen source remains read-only.</p>
        {preview.warnings.map((warning,index)=><p key={index} className="assumption">{warning}</p>)}
        <label><input type="checkbox" aria-label="Reviewed strategy conversion" checked={reviewed} disabled={blocked} onChange={event=>setReviewed(event.target.checked)}/>I reviewed the exact frozen source, entry direction, full simulation defaults and execution limits.</label>
        <button className="primary" disabled={blocked||!reviewed} onClick={()=>void create()}>Confirm create strategy</button>
      </section>}
      <p>Creation only saves a strategy. It does not start a backtest, acquire data, Arm an alert or trade.</p>
      <button onClick={()=>cancelReview()}>{pending?'Close review; keep pending request':'Cancel conversion'}</button>
    </section></div>}
  </Context.Provider>;
}
