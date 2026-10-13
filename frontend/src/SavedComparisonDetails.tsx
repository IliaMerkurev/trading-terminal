import {useEffect,useRef,useState} from 'react';
import {api} from './api';

type Details={name:string;notes:string;revision:number};
export default function SavedComparisonDetails({batchId,initial,onSaved,onEditingChange}:{batchId:string;initial:Details;onEditingChange?:(locked:boolean)=>void;onSaved:(value:Details)=>void}){
 const [editing,setEditing]=useState(false);
 const [saved,setSaved]=useState(initial),[draft,setDraft]=useState(initial),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
 const lock=useRef(false);
 const dirty=draft.name!==saved.name||draft.notes!==saved.notes;
 useEffect(()=>{onEditingChange?.(dirty||busy);return()=>onEditingChange?.(false);},[dirty,busy,onEditingChange]);
 async function save(){if(lock.current)return;lock.current=true;setBusy(true);setError('');setMessage('');try{
  const value=await api<Details>('library_batch_save_metadata',{batch_id:batchId,name:draft.name,notes:draft.notes,expected_revision:saved.revision});
  setSaved(value);setDraft(value);setEditing(false);setMessage('Comparison details saved.');onSaved(value);
 }catch(e){setError(`Details were not confirmed saved. Your text is retained. ${String(e instanceof Error?e.message:e)}`);}finally{lock.current=false;setBusy(false);}}
 async function reload(){if(lock.current)return;lock.current=true;setBusy(true);setError('');try{const value=await api<Details>('library_batch_metadata',{batch_id:batchId});setSaved(value);setDraft(value);setMessage('Saved details reloaded.');onSaved(value);}catch(e){setError(String(e instanceof Error?e.message:e));}finally{lock.current=false;setBusy(false);}}
 const expanded=editing||dirty||busy||!!error;
 return <section className="comparison-contract saved-comparison-details" aria-label="Comparison details"><div className="results-heading"><h3>{saved.name||'Untitled comparison'}</h3><div className="saved-metadata-actions">{!expanded&&saved.notes&&<details className="saved-notes"><summary>Saved notes</summary><p>{saved.notes}</p></details>}<button aria-expanded={expanded} disabled={dirty||busy||!!error} onClick={()=>setEditing(v=>!v)}>{expanded?'Hide details':'Edit details'}</button></div></div>
 {expanded&&<><small>Editable name and notes; original settings and results stay fixed.</small>
 <label className="field">Comparison name<input aria-label="Comparison name" maxLength={120} value={draft.name} disabled={busy} onChange={e=>{setDraft(v=>({...v,name:e.target.value}));setMessage('');}} placeholder="Name this research"/></label>
 <label className="field">Research notes<textarea aria-label="Research notes" maxLength={4000} rows={3} value={draft.notes} disabled={busy} onChange={e=>{setDraft(v=>({...v,notes:e.target.value}));setMessage('');}}/></label>
 <button disabled={busy||!dirty} onClick={save}>{busy?'Saving / loading details…':'Save details'}</button>
 {(dirty||error)&&<button disabled={busy} onClick={reload}>Discard edits and reload saved details</button>}
 {dirty&&<small>Unsaved details. Save or discard before choosing another comparison.</small>}</>}{message&&<p role="status">{message}</p>}{error&&<p role="alert">{error}</p>}
 </section>;
}
