import {useEffect,useRef,type ReactNode} from 'react';
import {createPortal} from 'react-dom';

// One controller renders its setup here; opening never duplicates its state or jobs.
export default function TestSetupSurface({open,onClose,children,label="Set up backtest",backLabel="Back to strategies"}:{open:boolean;onClose:()=>void;children:ReactNode;label?:string;backLabel?:string}){
 const dialog=useRef<HTMLDialogElement>(null);
 useEffect(()=>{
  if(!open)return;
  const trigger=document.activeElement instanceof HTMLElement?document.activeElement:null;
  dialog.current?.showModal();
  dialog.current?.querySelector<HTMLElement>('#test-setup')?.focus();
  return()=>{if(trigger?.isConnected&&!trigger.closest('[hidden]'))trigger.focus({preventScroll:true});};
 },[open]);
 if(!open)return null;
 return createPortal(<dialog ref={dialog} className="test-dialog" aria-label={label} onCancel={e=>{e.preventDefault();onClose();}}>
  <div className="test-dialog-heading"><span>{label}</span><button onClick={onClose}>{backLabel}</button></div>
  {children}
 </dialog>,document.body);
}
