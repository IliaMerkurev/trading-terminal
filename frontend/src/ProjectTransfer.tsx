import {useEffect,useRef,useState} from 'react';
import {invoke} from '@tauri-apps/api/core';
import {api,transportCapabilities,downloadArchive} from './api';
import {ImportReceiptDetails,type ImportReceipt,type ImportPage,type ImportCursor} from './ImportReceipts';

type Props={strategy:()=>any;profile:any;runIds:string[];onImported:(result:any,isCurrent:()=>boolean)=>Promise<void>;onOpenReport?:(id:string,isCurrent:()=>boolean)=>Promise<void>;onOpenStrategy?:(id:string,isCurrent:()=>boolean)=>Promise<void>};
export default function ProjectTransfer({strategy,profile,runIds,onImported,onOpenReport,onOpenStrategy}:Props){
  const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
  const [operation,setOperation]=useState(''),[phase,setPhase]=useState<'idle'|'uploading'|'finalizing'|'known'>('idle');
  const [receipt,setReceipt]=useState<ImportReceipt|null>(null),[inspectionError,setInspectionError]=useState(''),[inspecting,setInspecting]=useState(false);
  const [recent,setRecent]=useState<ImportPage|null>(null),[listError,setListError]=useState(''),[listing,setListing]=useState(false);
  const [opening,setOpening]=useState(false),[openingError,setOpeningError]=useState('');
  const generation=useRef(0),listGeneration=useRef(0),cancelled=useRef(false),finishSent=useRef(false);
  const mounted=useRef(true);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;generation.current++;listGeneration.current++;};},[]);
  const transport=transportCapabilities();
  async function exportProject(){setBusy(true);setError('');try{const result=await api<any>('archive_export',{strategy:strategy(),profile,run_ids:runIds});if(transport.downloadArchives)await downloadArchive(result.filename);setMessage(`${result.filename} · ${(result.bytes/1024).toFixed(1)} KiB. ${result.note}`);}catch(e){setError(String(e));}finally{setBusy(false);}}
  async function inspect(id:string){
    const request=++generation.current;setOperation(id);setReceipt(null);setInspectionError('');setOpeningError('');setOpening(false);setInspecting(true);
    try{const value=await api<ImportReceipt>('archive_import_status',{operation_id:id});if(request===generation.current){setReceipt(value);setError('');setMessage(value.inspection_state!=='available'?'Receipt metadata is inconsistent. Publication outcome remains unknown.':value.outcome?`Saved receipt confirms ${value.outcome}. Inspection did not retry the import.`:`Saved receipt is ${value.phase}. Finalization outcome is not yet recorded. Inspection did not retry the import.`);}}
    catch(e){if(request===generation.current)setInspectionError(`Inspection unavailable. Outcome remains unknown. ${String(e)}`);}
    finally{if(request===generation.current)setInspecting(false);}
  }
  async function list(before:ImportCursor|null=null){
    const request=++listGeneration.current;setListing(true);setListError('');
    try{const value=await api<ImportPage>('archive_import_list',{before,limit:25});if(request===listGeneration.current)setRecent(previous=>({rows:before?[...(previous?.rows??[]),...value.rows]:value.rows,next:value.next}));}
    catch(e){if(request===listGeneration.current)setListError(`Recent imports unavailable. ${String(e)}`);}
    finally{if(request===listGeneration.current)setListing(false);}
  }
  async function openSaved(kind:'report'|'strategy',id:string){
    const request=generation.current,isCurrent=()=>mounted.current&&request===generation.current;
    setOpening(true);setOpeningError('');
    try{const open=kind==='report'?onOpenReport:onOpenStrategy;if(!open)throw Error('Opening is unavailable in this view.');await open(id,isCurrent);}
    catch(e){if(isCurrent())setOpeningError(`The import receipt is unchanged. Could not open the saved ${kind}: ${String(e)}`);}
    finally{if(isCurrent())setOpening(false);}
  }
  async function cancelUpload(){
    if(!operation||finishSent.current)return;
    const request=generation.current,isCurrent=()=>mounted.current&&request===generation.current;
    cancelled.current=true;
    try{const result=await api<any>('archive_import_cancel',{operation_id:operation});if(isCurrent())setMessage(result.status==='cancelled'?'Upload cancelled. Retained bytes will not be resumed.':'Finalization has started; cancellation is too late. Inspect this import.');}
    catch(e){if(isCurrent())setError(`Cancellation outcome is unknown. Inspect this import. ${String(e)}`);}
  }
  async function importProject(file:File){
    const request=++generation.current,isCurrent=()=>mounted.current&&request===generation.current;
    setInspecting(false);setReceipt(null);setInspectionError('');setOpeningError('');setOperation('');
    setBusy(true);setPhase('uploading');setError('');setMessage('');cancelled.current=false;finishSent.current=false;
    let id='';let result:any;
    async function stopObsoleteTransfer(){
      if(isCurrent()&&!cancelled.current)return false;
      if(id&&!finishSent.current&&!cancelled.current){try{await api('archive_import_cancel',{operation_id:id});}catch{/* Inspect the retained receipt after returning. */}}
      return true;
    }
    try{
      if(file.size>64*1024*1024)throw Error('Archive exceeds 64 MiB');
      const transfer=await api<any>('archive_begin',{size:file.size});id=transfer.operation_id??transfer.upload_id;if(await stopObsoleteTransfer())return;setOperation(id);
      for(let offset=0;offset<file.size;offset+=transfer.chunk_bytes){
        if(await stopObsoleteTransfer())return;
        const bytes=new Uint8Array(await file.slice(offset,offset+transfer.chunk_bytes).arrayBuffer());
        if(await stopObsoleteTransfer())return;
        let binary='';for(const byte of bytes)binary+=String.fromCharCode(byte);
        await api('archive_append',{upload_id:id,offset,data:btoa(binary)});
        if(await stopObsoleteTransfer())return;
        setMessage(`Reading archive: ${Math.round(Math.min(file.size,offset+bytes.length)/file.size*100)}%`);
      }
      finishSent.current=true;setPhase('finalizing');
      setMessage('Finalization has started and cannot be cancelled. Inspection waits while this synchronous request is running. A lost response may require a service restart; then inspect Recent imports.');
      result=await api<any>('archive_finish',{upload_id:id});
      if(isCurrent()){setReceipt(result.receipt??null);setPhase('known');setMessage(result.note);}
    }catch(e){
      if(isCurrent()){setError(String(e));setMessage(finishSent.current?'The finish response is uncertain. Inspect this import; do not upload it again.':'Upload did not finish. Inspect Recent imports if the begin response was lost.');}
      if(id&&!finishSent.current&&!cancelled.current){
        try{await api('archive_import_cancel',{operation_id:id});}catch{/* The exact receipt remains available for explicit inspection. */}
      }
    }finally{if(isCurrent()){setBusy(false);if(!finishSent.current)setPhase('idle');}}
    // Opening/refresh errors cannot relabel durable import success as failure.
    if(result&&isCurrent()){
      setOpening(true);
      try{await onImported(result,isCurrent);}catch(e){if(isCurrent())setOpeningError(`Import completed, but refreshing or opening the strategy failed: ${String(e)}. The saved receipt is unchanged.`);}
      finally{if(isCurrent())setOpening(false);}
    }
  }
  return <details className="project-transfer"><summary>Project archive</summary>
    <p>Export the current strategy, simulation settings and {runIds.length} selected results. Raw market candles, worker logs and Python consent records are excluded. Native source is included; review it before sharing. Recognized credentials and personal paths block export.</p>
    <button disabled={busy||!transport.localService} onClick={exportProject}>Export project archive</button>
    {transport.openExportsFolder&&<button onClick={()=>invoke('open_exports').catch(e=>setError(String(e)))}>Open local exports folder</button>}
    <label className="field"><span>Import a project archive (does not execute Python)</span><input aria-label="Import project archive" type="file" accept=".zip" disabled={busy||opening||!transport.localService} onChange={e=>{const file=e.target.files?.[0];if(file)void importProject(file);e.target.value='';}}/></label>
    {operation&&<p className="import-identity">Current operation: {operation}</p>}
    {busy&&phase==='uploading'&&operation&&<button onClick={()=>void cancelUpload()}>Cancel upload</button>}
    {message&&<p role="status">{message}</p>}{error&&<p role="alert">{error}</p>}
    <div className="import-inspection-actions">
      {operation&&<button disabled={busy||inspecting||!transport.localService} onClick={()=>void inspect(operation)}>{receipt?'Refresh this import':'Inspect this import'}</button>}
      <button disabled={busy||listing||!transport.localService} onClick={()=>void list()}>Recent imports</button>
    </div>
    <p>Import finalization is synchronous. Status reads may wait until it finishes or require restart after a lost connection. Native timeout/close recovery has not been verified.</p>
    {inspecting&&<p role="status">Inspecting saved receipt…</p>}{inspectionError&&<p role="alert">{inspectionError}</p>}{listError&&<p role="alert">{listError}</p>}
    {recent&&<section aria-label="Recent imports"><h3>Recent imports</h3>{!recent.rows.length&&<p>No recorded imports. Older imports have no receipt.</p>}<ul className="recent-imports">{recent.rows.map(row=><li key={row.operation_id}><button disabled={busy} onClick={()=>void inspect(row.operation_id)} aria-label={`Inspect import ${row.operation_id}`}><strong>{row.outcome??row.phase}</strong> · {new Date(row.created_at).toISOString().slice(0,19).replace('T',' ')+' UTC'}<span className="import-identity">{row.operation_id}</span>{!row.archive_sha256&&<span>Content identity not bound</span>}</button></li>)}</ul>{recent.next&&<button disabled={listing} onClick={()=>void list(recent.next)}>Older imports</button>}</section>}
    {receipt&&<ImportReceiptDetails receipt={receipt} opening={opening} onOpenReport={id=>void openSaved('report',id)} onOpenStrategy={id=>void openSaved('strategy',id)}/>}
    {openingError&&<p role="alert">{openingError}</p>}
  </details>;
}
