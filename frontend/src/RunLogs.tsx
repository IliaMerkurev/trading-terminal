import {useEffect,useState} from 'react';
import {api} from './api';
export default function RunLogs({runId}:{runId:string}){
  const [open,setOpen]=useState(false),[text,setText]=useState('');
  useEffect(()=>{if(!open)return;let live=true;const update=()=>api<any>('run_logs',{run_id:runId}).then(r=>{if(live)setText((r.truncated?'Earlier output omitted.\n':'')+r.text);}).catch(e=>{if(live)setText(e.message);});update();const timer=setInterval(update,1500);return()=>{live=false;clearInterval(timer);};},[open,runId]);
  return <details onToggle={e=>setOpen(e.currentTarget.open)}><summary>Local worker log (bounded preview)</summary><pre className="worker-log">{text}</pre></details>;
}
