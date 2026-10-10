import {useEffect,useRef,useState} from 'react';
import {api,stopLocalService} from './api';
import {poll} from './poll';

export const hasActiveWork = (value: any) => ['starting','pending','running','cancel_requested'].includes(value?.status);

export default function BrowserServiceControls({active,onStopped}:{active:boolean;onStopped:()=>void}) {
  const [background,setBackground]=useState<boolean|null>(null),[statusError,setStatusError]=useState('');
  const [stopping,setStopping]=useState(false),[error,setError]=useState('');
  const stoppingRef=useRef(false),activeRef=useRef(true);
  activeRef.current=active||background!==false;
  useEffect(()=>poll(async()=>{
    const [runs,download,replay,experiments,batches,live,scheduler]=await Promise.all([
      api<any[]>('list_runs'),api('download_status'),api('replay_status',{replay_id:null}),
      api<any[]>('list_experiments'),api<any[]>('library_batches'),api('live_status'),api<any>('scheduler_status'),
    ]);
    return Boolean(scheduler?.reservation?.startsWith('archive:'))||runs.some(hasActiveWork)||hasActiveWork(download)||hasActiveWork(replay)
      ||experiments.some(hasActiveWork)||batches.some(hasActiveWork)||live?.active===true||live?.market?.active===true;
  },value=>{setBackground(value);setStatusError('');},()=>{
    setBackground(null);setStatusError('Service status is unavailable. Work may still be running; check the launcher.');
  },2000),[]);
  useEffect(()=>{
    const warn=(event:BeforeUnloadEvent)=>{
      if(!activeRef.current)return;
      event.preventDefault();event.returnValue='';
    };
    // Leaving a page never cancels work or shuts down the local service.
    window.addEventListener('beforeunload',warn);
    return()=>window.removeEventListener('beforeunload',warn);
  },[]);
  async function stop(){
    if(stoppingRef.current)return;
    if(!window.confirm('Stop the local service? This cancels active tests, archive imports, downloads and replays, and stops live monitoring. Saved results are retained.'))return;
    stoppingRef.current=true;setStopping(true);setError('');
    try{await stopLocalService();onStopped();}
    catch{setError('Could not confirm shutdown. The service may have stopped; check the launcher before trying again.');}
    finally{stoppingRef.current=false;setStopping(false);}
  }
  return <div className="banner info browser-service" aria-label="Local browser service">
    <span>Browser mode · closing this tab keeps work running.</span>
    <button className="danger" disabled={stopping} onClick={stop}>{stopping?'Stopping local service…':'Stop local service'}</button>
    {statusError&&<p role="status">{statusError}</p>}{error&&<p role="alert">{error}</p>}
  </div>;
}
