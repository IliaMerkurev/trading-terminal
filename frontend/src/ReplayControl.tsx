import {useEffect,useState} from 'react';
import {api} from './api';
import {poll} from './poll';

type Replay={id:string;session_id:string;status:string;error?:string;result?:{match:boolean;checked_events:number};progress?:{processed:number;total:number}};
export default function ReplayControl({sessionId,active}:{sessionId?:string;active:boolean}){
 const [job,setJob]=useState<Replay|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>poll(()=>api<Replay|null>('replay_status',{replay_id:null}),setJob,()=>setError('Replay status unavailable; retrying.'),500),[]);
 const running=job&&['running','cancel_requested'].includes(job.status);
 async function act(cancel=false){
  setBusy(true);setError('');
  try{
   if(cancel&&job)await api('replay_cancel',{replay_id:job.id});
   else await api('live_replay',{session_id:sessionId});
   setJob(await api<Replay>('replay_status',{replay_id:null}));
  }catch(e){setError(String(e instanceof Error?e.message:e));}
  finally{setBusy(false);}
 }
 return <div aria-label="Recorded replay">
  <button disabled={!sessionId||active||busy||!!running} onClick={()=>act()}>Verify recorded signals with replay</button>
  {running&&<button disabled={busy||job.status==='cancel_requested'} onClick={()=>act(true)}>Cancel replay</button>}
  {job&&<p role="status">Replay: {job.status}{running&&job.progress?` · ${job.progress.processed} / ${job.progress.total} candles`:''}
   {job.session_id!==sessionId?' · another saved session':''}
   {job.status==='completed'&&job.result?job.result.match?` · MATCH — ${job.result.checked_events} recorded signal events`:' · MISMATCH — inspect session before continuation':''}
  </p>}
  {(error||job?.error)&&<p role="alert">{error||job?.error}</p>}
 </div>;
}
