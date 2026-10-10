import {useEffect,useRef,useSyncExternalStore,type ReactNode} from 'react';
import {api} from './api';

const listeners=new Set<()=>void>(),pending=new Set<Promise<void>>();
let incomplete='';
const warn=(message:string)=>{incomplete=message;listeners.forEach(f=>f());};
const subscribe=(f:()=>void)=>{listeners.add(f);return()=>{listeners.delete(f);};};
export function DisplayTrackingNotice(){
 const warning=useSyncExternalStore(subscribe,()=>incomplete);
 return warning?<p role="alert" className="warning-text">{warning}</p>:null;
}
export async function finishDisplayWrites(){while(pending.size)await Promise.all([...pending]);}
export async function prepareDisplayReview(){
 // Include callbacks already scheduled for the next rendered frame.
 await new Promise<void>(resolve=>requestAnimationFrame(()=>resolve()));
 await finishDisplayWrites();
 // A lost transport response may never have reached the backend. Persist the
 // session caveat before freezing; if that cannot be saved, freeze stays blocked.
 if(incomplete)await api('research_display_incomplete');
}

export function displayRecorder(){
 const presentation_id=crypto.randomUUID().replaceAll('-',''),seen=new Set<string>();
 return (reference:any,viewport:number[]|null)=>{
  const key=JSON.stringify([reference,viewport]);if(seen.has(key))return;
  if(pending.size>=256||seen.size>=4096){warn('Display tracking incomplete: the bounded recording budget was reached. Reading remains available; reload the app to resume recording.');return;}
  seen.add(key);
  const task=api<any>('research_displayed',{presentation_id,reference,viewport}).then(result=>{
   if(result?.incomplete)warn(result.warning||'Display tracking incomplete. Reading remains available.');
  }).catch(()=>warn('Display tracking incomplete: a displayed period could not be recorded. Reading remains available; overlap reviews may omit this exposure.'));
  pending.add(task);void task.finally(()=>pending.delete(task));
 };
}

const viewportListeners=new Set<()=>void>();
let modalObserver:MutationObserver|null=null;
function observePresentationChanges(schedule:()=>void){
 viewportListeners.add(schedule);
 if(!modalObserver&&typeof MutationObserver!=='undefined'){
  modalObserver=new MutationObserver(records=>{
   if(records.some(r=>r.type==='attributes'||[...r.addedNodes,...r.removedNodes].some(n=>n instanceof HTMLElement&&(n.tagName==='DIALOG'||n.querySelector('dialog')))))viewportListeners.forEach(f=>f());
  });
  modalObserver.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['open','hidden']});
 }
 return()=>{viewportListeners.delete(schedule);if(!viewportListeners.size){modalObserver?.disconnect();modalObserver=null;}};
}

// Observe the rendered surface, not the request or React mount. No fallback to
// "viewed" when observer support is absent. Hidden tabs and ancestors never count.
export function observeDisplay(element:HTMLElement,onDisplay:()=>void){
 let intersecting=false,frame=0,disposed=false;
 const visible=()=>{const modal=document.querySelector('dialog[open]');return document.visibilityState==='visible'&&intersecting&&!element.closest('[hidden]')&&(!modal||modal.contains(element))&&element.getClientRects().length>0;};
 const schedule=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{if(!disposed&&visible())onDisplay();});};
 if(typeof IntersectionObserver==='undefined'){
  warn('Display tracking incomplete: viewport observation is unavailable. Reading remains available.');return {schedule:()=>{},dispose:()=>{}};
 }
 const observer=new IntersectionObserver(entries=>{intersecting=entries.some(e=>e.target===element&&e.isIntersecting&&e.intersectionRect.width>0&&e.intersectionRect.height>0);schedule();});
 observer.observe(element);document.addEventListener('visibilitychange',schedule);const stopChanges=observePresentationChanges(schedule);
 return {schedule,dispose:()=>{disposed=true;cancelAnimationFrame(frame);observer.disconnect();stopChanges();document.removeEventListener('visibilitychange',schedule);}};
}

export function observeChartDisplay(element:HTMLElement,chart:any,candles:any[],seconds:number,closes:boolean,onDisplay:(viewport:number[])=>void){
 const observer=observeDisplay(element,()=>{
  const range=chart.timeScale().getVisibleRange();if(!range||typeof range.from!=='number'||typeof range.to!=='number')return;
  const times=candles.map(c=>c.time+(closes?seconds:0)).filter(t=>t>=range.from&&t<=range.to);
  if(times.length)onDisplay([Math.min(...times),Math.max(...times)]);
 });
 chart.timeScale().subscribeVisibleTimeRangeChange(observer.schedule);
 return()=>{chart.timeScale().unsubscribeVisibleTimeRangeChange(observer.schedule);observer.dispose();};
}

export function DisplayedMetrics({reference,children}:{reference:any;children:ReactNode}){
 const host=useRef<HTMLDivElement>(null),record=useRef<ReturnType<typeof displayRecorder>|null>(null);
 if(!record.current)record.current=displayRecorder();
 const key=JSON.stringify(reference);
 useEffect(()=>{if(!host.current)return;const observers=[...host.current.querySelectorAll<HTMLElement>('[data-metric]')].map(value=>observeDisplay(value,()=>record.current!(reference,null)));return()=>observers.forEach(o=>o.dispose());},[key]);
 return <div ref={host}>{children}</div>;
}

export function DisplayedComparisonRow({reference,children}:{reference:any;children:ReactNode}){
 const host=useRef<HTMLTableRowElement>(null),record=useRef<ReturnType<typeof displayRecorder>|null>(null);
 if(!record.current)record.current=displayRecorder();
 const key=JSON.stringify(reference);
 useEffect(()=>{if(!host.current)return;const observers=[...host.current.querySelectorAll<HTMLElement>('[data-metric]')].map(cell=>observeDisplay(cell,()=>record.current!(reference,null)));return()=>observers.forEach(o=>o.dispose());},[key]);
 return <tr ref={host}>{children}</tr>;
}
