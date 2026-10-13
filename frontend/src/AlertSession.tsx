import {createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode} from 'react';
import {api} from './api';
import {poll} from './poll';
import type {IndicatorSettings} from './ChartIndicators';

export type AlertContext = {source:string; market:string; symbol:string; minutes:number; visible:boolean};
export type AlertView = AlertContext & {settings:IndicatorSettings; available:boolean};
export type AlertRuntime = {rule_id:string; phase:'PAUSED'|'ARMING'|'ARMED'; reason:string; confirmed_at:number|null};
export type AlertEvent = {id:string; sequence:number; rule_id:string; current_name:string; is_read:boolean; banner_claimed:boolean; evidence:any};
export type PendingAlert = {command:string; params:Record<string,any>; contextKey:string; settingsRevision:number; createdAt:string};
export const pendingAlertKey='terminal.local-alert.pending.v1';
export const alertIdentity=()=>crypto.randomUUID().replaceAll('-','');
export const alertContextKey=(value:AlertContext)=>JSON.stringify([value.source,value.market,value.symbol,value.minutes,value.visible]);
const message=(error:unknown)=>error instanceof Error?error.message:String(error);

// This controller lives above the keyed chart. Revisions describe transitions,
// not unique context values: A -> B -> A must never restore an old capability.
export class AlertSessionController {
 readonly sessionId=alertIdentity();
 revision=0; view:AlertView|null=null; ready=false; error='';
 private signature=''; private queue:Promise<unknown>=Promise.resolve();
 private started=false; private listeners=new Set<()=>void>();
 subscribe=(fn:()=>void)=>{this.listeners.add(fn);return()=>{this.listeners.delete(fn);};};
 private publish=()=>this.listeners.forEach(fn=>fn());
 start=()=>{
  if(this.started)return;this.started=true;
  this.queue=api('alert_session_init',{session_id:this.sessionId}).then(()=>{if(!this.view){this.ready=true;this.publish();}}).catch(error=>{this.error=message(error);this.publish();throw error;});
  // Attach a rejection observer even before a chart is mounted.
  void this.queue.catch(()=>{});
 };
 register=(view:AlertView)=>{
  this.start();this.view=view;const signature=alertContextKey(view);
  if(signature===this.signature){this.publish();return;}
  this.signature=signature;const revision=++this.revision;this.ready=false;this.error='';this.publish();
  const params={session_id:this.sessionId,context_revision:revision,source:view.source,market:view.market,symbol:view.symbol,minutes:view.minutes,visible:view.visible};
  this.queue=this.queue.then(()=>api('alert_context',params)).then(()=>{
   if(revision===this.revision){this.ready=true;this.error='';this.publish();}
  }).catch(error=>{if(revision===this.revision){this.ready=false;this.error=message(error);this.publish();}});
 };
 invalidate=(error:string)=>{this.ready=false;this.error=error;this.publish();};
 retry=()=>{
  // Explicit recovery reuses the session identity and registers a newer fence.
  this.started=false;this.ready=false;this.signature='';this.start();if(this.view)this.register(this.view);
 };
 fence=async()=>{
  if(!this.view)throw new Error('Open Market before recovering this Arm request');
  this.signature='';this.register({...this.view});const revision=this.revision;await this.queue;
  if(!this.ready||revision!==this.revision)throw new Error('Context fence is not confirmed');
 };
 isCurrent=(revision:number)=>this.ready&&this.revision===revision&&!!this.view?.visible;
}

type Session = {controller:AlertSessionController; view:AlertView|null; ready:boolean; revision:number;
 pending:PendingAlert|null; storageError:string; retain:(value:PendingAlert|null)=>void;
 runtimes:AlertRuntime[]; statusKnown:boolean; refresh:()=>void;};
const AlertSessionContext=createContext<Session|null>(null);
export const useAlertSession=()=>useContext(AlertSessionContext);

export function AlertSessionProvider({children}:{children:ReactNode}){
 const [controller]=useState(()=>new AlertSessionController());
 const [,render]=useState(0),[refreshVersion,setRefreshVersion]=useState(0);
 const [pending,setPending]=useState<PendingAlert|null>(null),[storageError,setStorageError]=useState('');
 const [statusKnown,setStatusKnown]=useState(false);
 const [runtimes,setRuntimes]=useState<AlertRuntime[]>([]),[banner,setBanner]=useState<AlertEvent|null>(null),[observationError,setObservationError]=useState('');
 const bannerRef=useRef<AlertEvent|null>(null),cursor=useRef(0);
 useEffect(()=>controller.subscribe(()=>render(n=>n+1)),[controller]);
 useEffect(()=>{controller.start();},[controller]);
 useEffect(()=>{
  try{const raw=localStorage.getItem(pendingAlertKey);if(raw){const value=JSON.parse(raw);if(!value||typeof value.command!=='string'||!value.params||typeof value.contextKey!=='string'||!['alert_create','alert_arm','alert_rename','alert_rebind','alert_archive','alert_restore'].includes(value.command))throw new Error('Unrecognized pending alert record');setPending(value);}}
  catch(error){setStorageError('Pending alert recovery is unavailable. Alert writes are blocked. '+message(error));}
 },[]);
 const retain=useCallback((value:PendingAlert|null)=>{
  try{if(value)localStorage.setItem(pendingAlertKey,JSON.stringify(value));else localStorage.removeItem(pendingAlertKey);setPending(value);}
  catch(error){setStorageError('Cannot retain the alert request safely. Alert writes are blocked. '+message(error));throw error;}
 },[]);
 const refresh=useCallback(()=>setRefreshVersion(n=>n+1),[]);
 useEffect(()=>{
  if(!controller.ready){setStatusKnown(false);return;}
  let gone=false;
  const cancel=poll(async()=>{
   const status=await api<any>('alert_status');
   if(status.session_id!==controller.sessionId){controller.invalidate('Alert session changed. Reload this application before arming.');throw new Error('Alert session changed.');}
   if(!Array.isArray(status.rules))throw new Error('Alert status unavailable');
   const page=await api<{events:AlertEvent[];next_cursor:number|null}>('alert_events',{after:cursor.current,limit:20});
   for(const event of page.events){
    if(gone)return status;
    // Advance even for already claimed/read records so later pages cannot starve.
    cursor.current=event.sequence;
    if(!event.banner_claimed){
     try{const claim=await api<{claimed:boolean}>('alert_claim_banner',{event_id:event.id});
      if(!gone&&claim.claimed===true){bannerRef.current=event;setBanner(event);}
     }catch{/* Lost claim reply may omit this attempt. Never infer permission. */}
    }
   }
   const current=bannerRef.current;
   if(current){const latest=await api<AlertEvent>('alert_event',{event_id:current.id});if(!gone&&bannerRef.current?.id===latest.id){bannerRef.current=latest;setBanner(latest);}}
   return status;
  },status=>{if(!gone){setRuntimes(status.rules);setStatusKnown(true);setObservationError('');}},error=>{if(!gone){setStatusKnown(false);setObservationError(message(error));}},1000);
  return()=>{gone=true;cancel();};
 },[controller,controller.ready,refreshVersion]);
 const value=useMemo(()=>({controller,view:controller.view,ready:controller.ready,revision:controller.revision,pending,storageError,retain,runtimes,statusKnown,refresh}),[controller,controller.view,controller.ready,controller.revision,pending,storageError,retain,runtimes,statusKnown,refresh]);
 return <AlertSessionContext.Provider value={value}>
  {children}
  {(controller.error||storageError)&&<div className="alert-global-warning" role="alert">Local alerts: {controller.error||storageError}{controller.error&&<button onClick={controller.retry}>Reconnect alert session</button>}</div>}
  {pending&&<div className="alert-global-warning" role="status">An alert write is awaiting reconciliation. Open Local alerts to check its original outcome before another write.</div>}
  {observationError&&<div className="alert-global-warning" role="status">Local alert observation unavailable: {observationError}</div>}
  {banner&&<aside className="local-alert-banner" role="status" aria-label="Local alert banner"><strong>Local alert · current name: {banner.current_name}</strong><div>Rule ID: {banner.rule_id}</div><div>Confirmed close: {alertTime(banner.evidence?.confirmed_at??banner.evidence?.evaluation?.confirmed_at)}</div><small>At-most-once display attempt. The durable event remains in the local journal.</small><button onClick={()=>{bannerRef.current=null;setBanner(null);}}>Dismiss alert banner</button></aside>}
 </AlertSessionContext.Provider>;
}
export function alertTime(value:unknown){return typeof value==='number'&&Number.isFinite(value)?new Date(value*1000).toISOString().replace('T',' ').replace('.000Z',' UTC'):'Unknown';}
export function AlertChartBridge({source,market,symbol,minutes,visible,settings,available}:AlertView){
 const session=useAlertSession(),controller=session?.controller;
 useLayoutEffect(()=>{controller?.register({source,market,symbol,minutes,visible,settings,available});},[controller,source,market,symbol,minutes,visible,settings,available]);
 // Chart removal itself is a context leave, independently of panel visibility.
 useLayoutEffect(()=>()=>{if(controller?.view)controller.register({...controller.view,visible:false,available:false});},[controller]);
 return null;
}
