import {useEffect,useRef,useState} from 'react';
import {poll} from './poll';
import {invoke} from '@tauri-apps/api/core';
import {api,transportCapabilities} from './api';
import ProjectExport from './ProjectExport';
import {ImportReceiptDetails,type ImportReceipt,type ImportPage,type ImportCursor} from './ImportReceipts';

type Props={onPrepareImport?:()=>Props['onImported'];strategy:()=>any;profile:any;runIds:string[];onImported:(result:any,isCurrent:()=>boolean)=>Promise<void>;onOpenReport?:(id:string,isCurrent:()=>boolean)=>Promise<void>;onOpenStrategy?:(id:string,isCurrent:()=>boolean)=>Promise<void>};
export default function ProjectTransfer({strategy,profile,runIds,onImported,onOpenReport,onOpenStrategy,onPrepareImport}:Props){
  const [watch,setWatch]=useState(0),[recovering,setRecovering]=useState(false),[recoveryId,setRecoveryId]=useState('');
  const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
  const [operation,setOperation]=useState(''),[phase,setPhase]=useState<'idle'|'uploading'|'finalizing'|'known'>('idle');
  const [receipt,setReceipt]=useState<ImportReceipt|null>(null),[inspectionError,setInspectionError]=useState(''),[inspecting,setInspecting]=useState(false);
  const [recent,setRecent]=useState<ImportPage|null>(null),[listError,setListError]=useState(''),[listing,setListing]=useState(false);
  const [opening,setOpening]=useState(false),[openingError,setOpeningError]=useState('');
  const generation=useRef(0),listGeneration=useRef(0),cancelled=useRef(false),finishSent=useRef(false);
  const mounted=useRef(true), autoOpen=useRef<{id:string;generation:number;complete:Props['onImported']}|null>(null), recoveryTransfer=useRef<string|null>(null), resumeKey=useRef<{id:string;revision:number;key:string}|null>(null);
  function acceptReceipt(value:ImportReceipt){
    setReceipt(value);
    setRecent(previous=>previous?{...previous,rows:previous.rows.map(row=>row.operation_id===value.operation_id?{...row,phase:value.phase,outcome:value.outcome}:row)}:previous);
  }
  useEffect(()=>{
    if(!operation||phase!=='finalizing')return;
    const request=generation.current,isCurrent=()=>mounted.current&&request===generation.current;
    return poll(()=>api<ImportReceipt>('archive_import_status',{operation_id:operation}),value=>{
      if(!isCurrent())return;acceptReceipt(value);setInspectionError('');
      if(value.execution?.state==='terminal'||(!value.execution&&value.phase==='terminal')){
        setPhase('known');setBusy(false);setMessage(`Saved receipt confirms ${value.outcome}. Published reports are retained.`);
        if(value.outcome==='completed'&&autoOpen.current?.id===operation&&autoOpen.current.generation===request){
          const complete=autoOpen.current.complete;autoOpen.current=null;setOpening(true);
          const result={operation_id:operation,receipt:value,strategy_id:value.items.find(item=>item.kind==='strategy')?.destination_id,note:'Import completed. Python was not executed and no trust was granted.'};
          void complete(result,isCurrent).catch(e=>{if(isCurrent())setOpeningError(`Import completed, but refreshing or opening the strategy failed: ${String(e)}. The saved receipt is unchanged.`);}).finally(()=>{if(isCurrent())setOpening(false);});
        }
      }
    },e=>{if(isCurrent())setInspectionError(`Status unavailable; the import may still be running. ${String(e)}`);},500);
  },[operation,phase,watch]);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;generation.current++;listGeneration.current++;};},[]);
  const transport=transportCapabilities();
  async function inspect(id:string){
    const request=++generation.current;setWatch(request);autoOpen.current=null;setOperation(id);setReceipt(null);setInspectionError('');setOpeningError('');setOpening(false);setInspecting(true);
    try{const value=await api<ImportReceipt>('archive_import_status',{operation_id:id});if(request===generation.current){acceptReceipt(value);setPhase(value.execution&&value.execution.state!=='terminal'?'finalizing':'known');setError('');setMessage(value.inspection_state!=='available'?'Receipt metadata is inconsistent. Publication outcome remains unknown.':value.outcome?`Saved receipt confirms ${value.outcome}. Inspection did not retry the import.`:`Saved receipt is ${value.phase}. Finalization outcome is not yet recorded. Inspection did not retry the import.`);}}
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
    if(!operation)return;
    const request=generation.current,isCurrent=()=>mounted.current&&request===generation.current;
    cancelled.current=true;
    try{const current=phase==='finalizing'?(receipt?.execution?receipt:await api<ImportReceipt>('archive_import_status',{operation_id:operation})):null;
      const result=await api<any>('archive_import_cancel',{operation_id:operation,...(current?.execution?{attempt_key:current.execution.attempt_key}:{})});if(isCurrent())setMessage(result.status==='cancelled'?'Upload cancelled. Retained bytes will not be resumed automatically.':result.status==='cancel_requested'?'Cancellation requested. Waiting for the worker to stop; published reports are retained.':'Cancellation is too late or the import is already terminal. Inspect this import.');}
    catch(e){if(isCurrent())setError(`Cancellation outcome is unknown. Inspect this import. ${String(e)}`);}
  }
  async function importProject(file:File){
    const complete=onPrepareImport?.()??onImported,request=++generation.current,isCurrent=()=>mounted.current&&request===generation.current;
    setWatch(request);setInspecting(false);setReceipt(null);setInspectionError('');setOpeningError('');setOperation('');
    setBusy(true);setPhase('uploading');setError('');setMessage('');cancelled.current=false;finishSent.current=false;
    let id='';
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
      setMessage('Starting background import. You can inspect progress or request cancellation.');
      autoOpen.current={id,generation:request,complete};
      const started=await api<ImportReceipt>('archive_import_start',{operation_id:id});
      if(isCurrent())acceptReceipt(started);
    }catch(e){
      autoOpen.current=null;
      if(isCurrent()){setError(String(e));setMessage(finishSent.current?'The start response is uncertain. Inspect this import; repeating start never imports it twice.':'Upload did not finish. Inspect Recent imports if the begin response was lost.');}
      if(id&&!finishSent.current&&!cancelled.current){
        try{await api('archive_import_cancel',{operation_id:id});}catch{/* The exact receipt remains available for explicit inspection. */}
      }
    }finally{if(isCurrent()){setBusy(false);if(!finishSent.current)setPhase('idle');}}
  }
  async function resumeImport(){
    if(!receipt)return;
    const id=receipt.operation_id,revision=receipt.revision??0,request=++generation.current;
    if(!resumeKey.current||resumeKey.current.id!==id||resumeKey.current.revision!==revision)resumeKey.current={id,revision,key:crypto.randomUUID().replaceAll('-','')};
    setWatch(request);setError('');setMessage('Continuation requested. Saved reports and reserved IDs will be retained.');setPhase('finalizing');setOperation(id);autoOpen.current=null;
    try{const value=await api<ImportReceipt>('archive_import_resume',{operation_id:id,expected_revision:revision,attempt_key:resumeKey.current.key});if(mounted.current&&request===generation.current)acceptReceipt(value);}
    catch(e){if(mounted.current&&request===generation.current){setError(`Continuation response uncertain. Inspect before retrying. ${String(e)}`);}}
  }
  async function replaceMissingUpload(file:File){
    if(!receipt)return;const request=generation.current;let uploadId='';
    setBusy(true);setRecovering(true);setError('');
    try{
      const transfer=await api<any>('archive_recovery_begin',{operation_id:receipt.operation_id,size:file.size});
      uploadId=transfer.upload_id;recoveryTransfer.current=uploadId;setRecoveryId(uploadId);
      for(let offset=0;offset<file.size;offset+=transfer.chunk_bytes){
        if(!mounted.current||request!==generation.current||recoveryTransfer.current!==uploadId)throw Error('Recovery upload stopped');
        const bytes=new Uint8Array(await file.slice(offset,offset+transfer.chunk_bytes).arrayBuffer());let binary='';for(const byte of bytes)binary+=String.fromCharCode(byte);
        await api('archive_append',{upload_id:transfer.upload_id,offset,data:btoa(binary)});
      }
      await api('archive_recovery_finish',{upload_id:transfer.upload_id});
      if(mounted.current&&request===generation.current)setMessage('Replacement retained. Explicit continuation will verify exact original ZIP and content hashes before any publication.');
    }catch(e){if(uploadId){try{await api('archive_recovery_cancel',{upload_id:uploadId});}catch{}}if(mounted.current&&request===generation.current)setError(String(e));}
    finally{recoveryTransfer.current=null;if(mounted.current&&request===generation.current){setBusy(false);setRecovering(false);setRecoveryId('');}}
  }
  return <details className="project-transfer"><summary>Project archive</summary>
    <p>Export the current strategy, simulation settings and {runIds.length} selected results. Raw market candles, worker logs and Python consent records are excluded. Native source is included; review it before sharing. Recognized credentials and personal paths block export.</p>
    <ProjectExport strategy={strategy} profile={profile} runIds={runIds} disabled={busy}/>
    {transport.openExportsFolder&&<button onClick={()=>invoke('open_exports').catch(e=>setError(String(e)))}>Open local exports folder</button>}
    <label className="field"><span>Import a project archive (does not execute Python)</span><input aria-label="Import project archive" type="file" accept=".zip" disabled={busy||opening||!transport.localService} onChange={e=>{const file=e.target.files?.[0];if(file)void importProject(file);e.target.value='';}}/></label>
    {operation&&<p className="import-identity">Current operation: {operation}</p>}
    {operation&&(phase==='uploading'||phase==='finalizing')&&<button onClick={()=>void cancelUpload()}>{phase==='uploading'?'Cancel upload':'Cancel import'}</button>}
    {busy&&recoveryId&&<button onClick={()=>{const id=recoveryTransfer.current;recoveryTransfer.current=null;setRecoveryId('');if(id)void api('archive_recovery_cancel',{upload_id:id});}}>Cancel recovery upload</button>}
    {message&&<p role="status">{message}</p>}{error&&<p role="alert">{error}</p>}
    <div className="import-inspection-actions">
      {operation&&<button disabled={(busy&&(phase==='uploading'||recovering))||inspecting||!transport.localService} onClick={()=>void inspect(operation)}>{receipt?'Refresh this import':'Inspect this import'}</button>}
      <button disabled={(busy&&(phase==='uploading'||recovering))||listing||!transport.localService} onClick={()=>void list()}>Recent imports</button>
    </div>
    <p>Imports run in the background. Leaving this view does not cancel publication. Explicit continuation verifies the original archive and retains the same reserved IDs. Windows/native acceptance remains pending.</p>
    {inspecting&&<p role="status">Inspecting saved receipt…</p>}{inspectionError&&<p role="alert">{inspectionError}</p>}{listError&&<p role="alert">{listError}</p>}
    {recent&&<section aria-label="Recent imports"><h3>Recent imports</h3>{!recent.rows.length&&<p>No recorded imports. Older imports have no receipt.</p>}<ul className="recent-imports">{recent.rows.map(row=><li key={row.operation_id}><button disabled={busy&&(phase==='uploading'||recovering)} onClick={()=>void inspect(row.operation_id)} aria-label={`Inspect import ${row.operation_id}`}><strong>{row.outcome??row.phase}</strong> · {new Date(row.created_at).toISOString().slice(0,19).replace('T',' ')+' UTC'}<span className="import-identity">{row.operation_id}</span>{!row.archive_sha256&&<span>Content identity not bound</span>}</button></li>)}</ul>{recent.next&&<button disabled={listing} onClick={()=>void list(recent.next)}>Older imports</button>}</section>}
    {receipt&&receipt.inspection_state==='available'&&['partial','failed','interrupted','cancelled'].includes(receipt.outcome??'')&&(!receipt.execution||receipt.execution.state==='terminal')&&<div><button disabled={busy} onClick={()=>void resumeImport()}>Continue this import with retained progress</button>{receipt.content_identity==='bound'&&<label>Replace missing original upload (exact same ZIP)<input type="file" aria-label="Recovery archive" disabled={busy} onChange={e=>{const file=e.target.files?.[0];if(file)void replaceMissingUpload(file);e.target.value='';}}/></label>}</div>}
    {receipt&&<ImportReceiptDetails receipt={receipt} opening={opening} onOpenReport={id=>void openSaved('report',id)} onOpenStrategy={id=>void openSaved('strategy',id)}/>}
    {openingError&&<p role="alert">{openingError}</p>}
  </details>;
}
