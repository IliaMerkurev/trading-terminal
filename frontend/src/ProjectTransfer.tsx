import {useState} from 'react';
import {invoke} from '@tauri-apps/api/core';
import {api,isDesktop} from './api';
export default function ProjectTransfer({strategy,profile,runIds,onImported}:{strategy:()=>any;profile:any;runIds:string[];onImported:(result:any)=>Promise<void>}){
  const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
  async function exportProject(){setBusy(true);setError('');try{const result=await api<any>('archive_export',{strategy:strategy(),profile,run_ids:runIds});setMessage(`${result.filename} · ${(result.bytes/1024).toFixed(1)} KiB. ${result.note}`);}catch(e){setError(String(e));}finally{setBusy(false);}}
  async function importProject(file:File){
    setBusy(true);setError('');let active=false;
    try{
      if(file.size>64*1024*1024)throw Error('Archive exceeds 64 MiB');
      const transfer=await api<any>('archive_begin',{size:file.size});active=true;
      for(let offset=0;offset<file.size;offset+=transfer.chunk_bytes){
        const bytes=new Uint8Array(await file.slice(offset,offset+transfer.chunk_bytes).arrayBuffer());
        let binary='';for(const byte of bytes)binary+=String.fromCharCode(byte);
        await api('archive_append',{upload_id:transfer.upload_id,offset,data:btoa(binary)});
        setMessage(`Reading archive: ${Math.round(Math.min(file.size,offset+bytes.length)/file.size*100)}%`);
      }
      const result=await api<any>('archive_finish',{upload_id:transfer.upload_id});active=false;
      setMessage(result.note);await onImported(result);
    }catch(e){setError(String(e));if(active)await api('archive_cancel').catch(()=>{});}finally{setBusy(false);}
  }
  return <details className="project-transfer"><summary>Project archive</summary><p>Export the current strategy, simulation settings and {runIds.length} selected results. Raw market candles, worker logs and Python consent records are excluded. Native source is included; review it before sharing. Recognized credentials and personal paths block export.</p><button disabled={busy||!isDesktop()} onClick={exportProject}>Export project archive</button><button onClick={()=>invoke('open_exports').catch(e=>setError(String(e)))} disabled={!isDesktop()}>Open local exports folder</button><label className="field"><span>Import a project archive (does not execute Python)</span><input aria-label="Import project archive" type="file" accept=".zip" disabled={busy||!isDesktop()} onChange={e=>{const file=e.target.files?.[0];if(file)importProject(file);e.target.value='';}}/></label>{message&&<p role="status">{message}</p>}{error&&<p role="alert">{error}</p>}</details>;
}
