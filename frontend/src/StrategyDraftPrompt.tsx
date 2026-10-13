import {useEffect,useRef} from 'react';
import './strategy-draft.css';

export default function StrategyDraftPrompt({label,saving,onChoice}:{label:string;saving:boolean;onChoice:(choice:'save'|'discard'|'cancel')=>void}){
  const dialog=useRef<HTMLDialogElement>(null),cancel=useRef<HTMLButtonElement>(null),choice=useRef(onChoice);choice.current=onChoice;
  useEffect(()=>{
    const previous=document.activeElement,element=dialog.current!;
    element.showModal();cancel.current?.focus();
    const escape=(event:Event)=>{event.preventDefault();choice.current('cancel');};element.addEventListener('cancel',escape);
    return()=>{element.removeEventListener('cancel',escape);element.close();if(previous instanceof HTMLElement&&previous.isConnected)previous.focus();};
  },[]);
  return <dialog className="strategy-draft-dialog" ref={dialog} aria-labelledby="strategy-draft-title" aria-describedby="strategy-draft-description">
    <h2 id="strategy-draft-title">Keep your strategy changes?</h2>
    <p id="strategy-draft-description">{label} will replace the current draft, including its graph, layout, name and simulation settings. Save first, discard these changes, or cancel to keep editing.</p>
    {saving&&<p>A previous save is still pending. Cancel keeps this draft.</p>}
    <div><button disabled={saving} onClick={()=>onChoice('save')}>Save and continue</button><button onClick={()=>onChoice('discard')}>Discard and continue</button><button ref={cancel} onClick={()=>onChoice('cancel')}>Cancel</button></div>
  </dialog>;
}
