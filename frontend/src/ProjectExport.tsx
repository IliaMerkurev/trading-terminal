import {useEffect,useRef,useState} from 'react';
import {api,downloadArchive,transportCapabilities,type ExportDescriptor} from './api';
import {poll} from './poll';

type Receipt={export_id:string;status:'running'|'cancel_requested'|'completed'|'cancelled'|'failed';phase:string;descriptor:ExportDescriptor|null;error:string|null};
type Props={strategy:()=>any;profile:any;runIds:string[];disabled:boolean};
export default function ProjectExport({strategy,profile,runIds,disabled}:Props){
  const [receipt,setReceipt]=useState<Receipt|null>(null),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const [recent,setRecent]=useState<Pick<Receipt,'export_id'|'status'|'phase'>[]|null>(null),[downloading,setDownloading]=useState(false),[uncertain,setUncertain]=useState(false);
  const downloadController=useRef<AbortController|null>(null);
  const latest=useRef<Receipt|null>(null);
  const generation=useRef(0),mounted=useRef(true),automatic=useRef(''),transfer=useRef(0),frozen=useRef<Record<string,unknown>|null>(null);
  const transport=transportCapabilities(),active=receipt&&['running','cancel_requested'].includes(receipt.status);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;generation.current++;transfer.current++;downloadController.current?.abort();};},[]);
  function accept(value:Receipt){latest.current=value;setReceipt(value);if(['cancelled','failed'].includes(value.status))setNotice(`Export ${value.status}. No downloadable archive was published.`);else if(value.status==='completed')setNotice('Export completed. The archive is ready.');setRecent(rows=>rows?.map(row=>row.export_id===value.export_id?{export_id:value.export_id,status:value.status,phase:value.phase}:row)??null);}
  async function download(value:Receipt){
    if(!value.descriptor)return;const current=generation.current,key=++transfer.current,isCurrent=()=>mounted.current&&generation.current===current&&transfer.current===key;
    downloadController.current?.abort();const controller=new AbortController();downloadController.current=controller;
    setDownloading(true);setError('');setNotice('Downloading and verifying archive…');
    try{await downloadArchive(value.descriptor,isCurrent,bytes=>{if(isCurrent())setNotice(`Verified transfer: ${Math.round(bytes/value.descriptor!.bytes*100)}%. Final checksum required before saving.`);},controller.signal);if(isCurrent())setNotice(`${value.descriptor.filename} · ${(value.descriptor.bytes/1024).toFixed(1)} KiB. Verified download presented.`);}
    catch(e){if(isCurrent())setError(String(e));}
    finally{if(isCurrent())setDownloading(false);}
  }
  useEffect(()=>{
    if(!receipt||!active)return;const id=receipt.export_id,current=generation.current;
    return poll(()=>api<Receipt>('archive_export_status',{export_id:id}),value=>{
      if(!mounted.current||current!==generation.current)return;
      accept(value);setError('');setUncertain(false);
      if(value.status==='completed'&&automatic.current===id){automatic.current='';if(transport.downloadArchives)void download(value);}
    },e=>{if(mounted.current&&current===generation.current)setError(`Export inspection unavailable. No restart was requested. ${String(e)}`);},500);
  },[receipt?.export_id,active]);
  async function start(retry=false){
    let current=generation.current;
    try{
      let params=frozen.current;
      if(!retry){frozen.current=null;automatic.current='';const request_id=crypto.randomUUID().replaceAll('-','');params=JSON.parse(JSON.stringify({request_id,strategy:strategy(),profile,run_ids:runIds}));frozen.current=params;current=++generation.current;automatic.current=request_id;const value:Receipt={export_id:request_id,status:'running',phase:'starting',descriptor:null,error:null};latest.current=value;setReceipt(value);}
      if(!params)return;setError('');setNotice('');setUncertain(false);
      const value=await api<Receipt>('archive_export_start',params);
      if(mounted.current&&generation.current===current){accept(value);if(value.status==='completed'&&automatic.current===value.export_id){automatic.current='';if(transport.downloadArchives)void download(value);}}
    }catch(e){if(mounted.current&&generation.current===current){setUncertain(Boolean(frozen.current));setError(frozen.current?`Start response uncertain. Inspect or retry this exact request; it will not create a second export. ${String(e)}`:String(e));}}
  }
  async function inspect(id:string){
    generation.current++;transfer.current++;downloadController.current?.abort();automatic.current='';frozen.current=null;setUncertain(false);setDownloading(false);const current=generation.current;
    // Stop polling a previous identity immediately, including on failed inspect.
    latest.current=null;setReceipt(null);setNotice('');
    try{const value=await api<Receipt>('archive_export_status',{export_id:id});if(mounted.current&&generation.current===current){accept(value);setError('');}}
    catch(e){if(mounted.current&&generation.current===current)setError(String(e));}
  }
  return <section aria-label="Project export">
    <button disabled={disabled||Boolean(active)||downloading||!transport.localService} onClick={()=>void start()}>Export project archive</button>
    <button disabled={downloading||!transport.localService} onClick={()=>void api<Pick<Receipt,'export_id'|'status'|'phase'>[]>('archive_export_list').then(rows=>{if(mounted.current)setRecent(rows);}).catch(e=>{if(mounted.current)setError(String(e));})}>Recent exports</button>
    {receipt&&<p role="status">Export {receipt.export_id}: {receipt.status} · {receipt.phase.replaceAll('_',' ')}{receipt.status==='completed'&&receipt.descriptor?`. ${receipt.descriptor.note}`:''}</p>}
    {receipt&&<button disabled={downloading} onClick={()=>void inspect(receipt.export_id)}>Inspect export</button>}
    {uncertain&&frozen.current&&<button onClick={()=>void start(true)}>Retry exact export start</button>}
    {active&&<button onClick={()=>{const id=receipt!.export_id,current=generation.current;void api<{status:string}>('archive_export_cancel',{export_id:id}).then(value=>{if(mounted.current&&generation.current===current&&latest.current&&['running','cancel_requested'].includes(latest.current.status))setNotice(value.status==='cancel_requested'?'Cancellation requested. Waiting for the export worker to stop.':'Export already terminal; inspect its outcome.');}).catch(e=>{if(mounted.current&&generation.current===current)setError(String(e));});}}>Cancel export</button>}
    {receipt?.status==='completed'&&transport.downloadArchives&&<button disabled={downloading} onClick={()=>void download(receipt)}>Download verified archive</button>}
    {downloading&&<button onClick={()=>{transfer.current++;downloadController.current?.abort();setDownloading(false);setNotice('Transfer stopped. The completed export is retained.');}}>Stop archive download</button>}
    {recent&&<ul aria-label="Recent exports">{recent.map(row=><li key={row.export_id}><button disabled={downloading} onClick={()=>void inspect(row.export_id)}>{row.export_id} · {row.status}</button></li>)}</ul>}
    <p>Exports run in the background. Closing this view keeps work running. Operations and download access last until the service stops; unfinished exports never resume automatically.</p>
    {notice&&<p role="status">{notice}</p>}{(error||receipt?.error)&&<p role="alert">{error||receipt?.error}</p>}
  </section>;
}
