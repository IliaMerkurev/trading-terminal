import {useEffect,useRef,useState} from 'react';
import {api} from './api';
import {poll} from './poll';
import {storageFailureReleased,type SchedulerStatus} from './storageSafety';

type Failure=NonNullable<SchedulerStatus['storage_failure']>;

export default function StorageFailureNotice({connected,onReleased}:{connected:boolean;onReleased?:()=>void}){
  const released=useRef(onReleased);released.current=onReleased;
  const [failure,setFailure]=useState<Failure|null>(null);
  const [unavailable,setUnavailable]=useState(false);
  useEffect(()=>{
    if(!connected)return;
    return poll(()=>api<SchedulerStatus>('scheduler_status'),status=>{
      setFailure(status.storage_failure);setUnavailable(false);
      if(storageFailureReleased(status))released.current?.();
    },()=>setUnavailable(true),1000);
  },[connected]);
  if(!failure)return unavailable?<div role="alert" className="banner error">Calculation safety status unavailable. Check the local service connection before starting work.</div>:null;
  return <div role="alert" className="banner error" aria-label="Storage finalization failure">
    <strong>{failure.message}</strong>
    <span> Affected {failure.kind}: {failure.id}. This warning is held in memory for this application session. Persisted run statuses and completed reports are unchanged.</span>
    {unavailable&&<span> Local service status is currently unavailable.</span>}
  </div>;
}
