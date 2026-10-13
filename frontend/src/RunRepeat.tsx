import {useEffect,useRef,useState} from 'react';
import {api} from './api';
import type {Graph,Profile} from './model';

export type RepeatDraft={run_id:string;review_sha256:string;runtime_changed:boolean;name:string;graph:Graph;profile:Profile;dataset:any;snapshot_sha256:string};
export type RepeatReview={version:number;run_id:string;review_sha256:string;can_prepare:boolean;runtime_changed:boolean;checks:{key:string;status:string;detail:string;saved?:any;current?:any;source?:string;range?:number[];dataset_id?:string;interval_seconds?:number}[];inspection_limit:string;note:string};
const titles:Record<string,string>={origin:'Saved run',snapshot:'Immutable conditions',strategy:'Strategy',profile:'Simulation profile',runtime:'Runtime evidence',contracts:'Recorded engine and metrics',platform:'Current execution platform',data:'Original local data'};
const labels:Record<string,string>={available:'Available',matched:'Matches recorded evidence',different:'Changed',unknown:'Unknown',unsupported:'Unsupported in this flow',inspection_limit:'Inspection budget exceeded',unavailable:'Unavailable',invalid:'Verification failed'};

export default function RunRepeat({runId,onPrepare,onDismissPrepare}:{runId:string;onDismissPrepare?:()=>void;onPrepare:(review:RepeatReview,acknowledged:boolean,isCurrent:()=>boolean)=>Promise<boolean>}){
  const [review,setReview]=useState<RepeatReview|null>(null),[pending,setPending]=useState(false),[preparing,setPreparing]=useState(false),[error,setError]=useState(''),[ack,setAck]=useState(false);
  const dismiss=useRef(onDismissPrepare);dismiss.current=onDismissPrepare;
  const owner=useRef({generation:0,alive:true}),abort=useRef<AbortController|null>(null);
  useEffect(()=>{owner.current.alive=true;return()=>{owner.current.alive=false;owner.current.generation++;abort.current?.abort();dismiss.current?.();};},[]);
  function current(generation:number){return owner.current.alive&&owner.current.generation===generation;}
  async function check(){
    const generation=++owner.current.generation;abort.current?.abort();const controller=new AbortController();abort.current=controller;
    setPending(true);setReview(null);setError('');setAck(false);
    try{const value=await api<RepeatReview>('run_repeat_review',{run_id:runId},{signal:controller.signal});
      if(!current(generation))return;
      if(value.run_id!==runId||value.version!==1||!Array.isArray(value.checks))throw Error('Saved input review response does not match this run.');
      setReview(value);
    }catch(e){if(current(generation))setError(e instanceof Error?e.message:String(e));}
    finally{if(current(generation))setPending(false);}
  }
  function cancel(){owner.current.generation++;abort.current?.abort();dismiss.current?.();setPending(false);setPreparing(false);setError('Inspection result dismissed. A bounded service read may still finish; it cannot replace your draft.');}
  async function prepare(){
    if(!review||!review.can_prepare||review.runtime_changed&&!ack)return;
    const generation=++owner.current.generation;setPreparing(true);setError('');
    try{await onPrepare(review,ack,()=>current(generation));}
    catch(e){if(current(generation)){setError(e instanceof Error?e.message:String(e));setReview(null);setAck(false);}}
    finally{if(current(generation))setPreparing(false);}
  }
  return <section className="run-repeat" aria-label="Repeat saved research">
    <h3>Prepare independent research</h3>
    <p>Check whether the original saved inputs are still available. This copies frozen conditions into a new unsaved draft; you decide whether to run it.</p>
    <button disabled={pending||preparing} onClick={()=>void check()}>{review?'Check availability again':'Check original input availability'}</button>
    {(pending||preparing)&&<><span role="status"> {preparing?'Preparing saved conditions…':'Checking local inputs…'}</span><button onClick={cancel}>Dismiss pending inspection</button></>}
    {error&&<p role="alert">{error}</p>}
    {review&&<>
      <dl>{review.checks.map(row=><div key={row.key}><dt>{titles[row.key]??row.key} · {labels[row.status]??row.status}</dt><dd>{row.detail}
        {row.source&&<p>Recorded source: {row.source} · {row.interval_seconds! / 60} minute native bars</p>}
        {row.dataset_id&&<p>Dataset: {row.dataset_id}</p>}
        {row.range&&<p>Input range: {row.range.map(t=>new Date(t*1000).toISOString()).join(' to ')} (UTC, end exclusive)</p>}
        {(row.saved||row.current)&&<details><summary>Saved and current evidence</summary><pre>{JSON.stringify({saved:row.saved,current:row.current},null,2)}</pre></details>}
      </dd></div>)}</dl>
      <p className="assumption">{review.note}</p>
      <p className="muted">{review.inspection_limit} At M1, 100,000 bars cover about 69 days. Size limits can apply sooner; these are admission estimates, not measured peak memory.</p>
      {review.can_prepare&&review.runtime_changed&&<label className="repeat-ack"><input type="checkbox" checked={ack} onChange={e=>setAck(e.target.checked)}/> I understand this is new research using the changed current runtime, with no guarantee of the same result.</label>}
      <button disabled={!review.can_prepare||pending||preparing||review.runtime_changed&&!ack} onClick={()=>void prepare()}>Create independent draft</button>
    </>}
  </section>;
}
