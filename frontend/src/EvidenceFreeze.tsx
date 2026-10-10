import {useRef,useState} from 'react';
import {api} from './api';
import TestSetupSurface from './TestSetupSurface';
export function EvidenceSummary({value}:{value:any}){
 if(!value)return null;
 return <div className="assumption"><strong>Recorded period overlap</strong><p>{value.message}</p>{value.range&&<p>Evaluation: {value.range.map((t:number)=>new Date(t*1000).toISOString().slice(0,16)).join(' — ')} UTC (end exclusive).</p>}<p>{value.symbol} · {value.source} · provenance: {value.provenance}. Coverage begins {value.coverage_start}.</p><p>{value.limitation.split('Started means')[0]}</p><details><summary>Sources, cohorts and recording limits</summary>{value.groups.map((g:any,i:number)=><p key={i}>{g.route} · {g.kind} · {g.role} · {g.market} · {g.source} ({g.provenance}): {g.count} · {g.primary_minutes}m signals / {g.execution_minutes}m execution · model {g.model_version} · cohort {g.cohort.slice(0,12)}</p>)}{value.groups_truncated&&<p>First 50 groups shown; total includes all matching events.</p>}<p>{value.limitation}</p></details></div>;
}
export default function EvidenceFreeze({label,disabled,request,onFreeze}:{label:string;disabled:boolean;request:{dataset_id:string;start:number;end:number};onFreeze:()=>Promise<void>}){
 const [review,setReview]=useState<any>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const lock=useRef(false),epoch=useRef(0);
 async function check(){if(lock.current)return;lock.current=true;const current=++epoch.current;setBusy(true);setError('');try{const value=await api<any>('research_evidence_preview',request);if(current===epoch.current)setReview(value);}catch(e){if(current===epoch.current)setError(String(e));}finally{if(current===epoch.current){lock.current=false;setBusy(false);}}}
 async function freeze(){if(lock.current)return;lock.current=true;setBusy(true);try{await onFreeze();setReview(null);}finally{lock.current=false;setBusy(false);}}
 return <><button disabled={disabled||busy} onClick={check}>{label}</button>{error&&<p role="alert">{error}</p>}<TestSetupSurface open={!!review} label="Review recorded period overlap" backLabel="Cancel freeze" onClose={()=>{if(!lock.current){epoch.current++;setReview(null);}}}><div id="test-setup" tabIndex={-1}><EvidenceSummary value={review}/><p>This review does not reserve the period. Later admissions can add overlap. Freeze saves a candidate; it does not start computation.</p><button disabled={disabled||busy} onClick={freeze}>Confirm candidate freeze</button></div></TestSetupSurface></>;
}
