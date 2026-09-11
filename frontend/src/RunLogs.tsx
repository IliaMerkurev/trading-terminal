import {useEffect,useState} from 'react';
import {api} from './api';
import {poll} from './poll';
export default function RunLogs({runId}:{runId:string}){
  const [open,setOpen]=useState(false),[text,setText]=useState('');
  useEffect(()=>{if(!open)return;return poll(()=>api<any>('run_logs',{run_id:runId}),r=>setText((r.truncated?'Earlier output omitted.\n':'')+r.text),e=>setText(String(e)),1500);},[open,runId]);
  return <details onToggle={e=>setOpen(e.currentTarget.open)}><summary>Local worker log (bounded preview)</summary><pre className="worker-log">{text}</pre></details>;
}
