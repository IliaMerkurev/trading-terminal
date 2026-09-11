import {useEffect,useState} from 'react';
import {api} from './api';
export default function RunSnapshot({runId}:{runId:string}){
  const [open,setOpen]=useState(false),[text,setText]=useState('');
  useEffect(()=>{if(!open)return;let live=true;api('run_manifest',{run_id:runId}).then(r=>{if(live)setText(JSON.stringify(r,null,2));}).catch(e=>{if(live)setText(e.message);});return()=>{live=false;};},[open,runId]);
  return <details onToggle={e=>setOpen(e.currentTarget.open)}><summary>Immutable strategy, simulation, data and runtime snapshot</summary><pre className="worker-log">{text}</pre></details>;
}
