import {useEffect, useId, useRef, useState} from 'react';
import {api} from './api';
import './fear-greed.css';

const preference = 'terminal.fear-greed.collapsed.v1';
const source = 'https://alternative.me/crypto/fear-and-greed-index/';
type RecordValue = {value:number; category:string; timestamp:number; fetched_at:number; next_update_at:number; next_attempt_at:number};
type Snapshot = {record:RecordValue|null; loading:boolean; outdated:boolean; error:{kind:string;detail:string}|null; cache_warning:string|null; retry_after:number; refresh_after:number; closed:boolean};
const colors:Record<string,string> = {'Extreme Fear':'#ed727d',Fear:'#e9a15e',Neutral:'#dac96b',Greed:'#80c9a3','Extreme Greed':'#4dbdaf'};
function validRecord(value:unknown):value is RecordValue {
 const r=value as RecordValue,now=Date.now()/1000;
 return !!r&&Number.isInteger(r.value)&&r.value>=0&&r.value<=100&&typeof r.category==='string'&&r.category.length>0&&r.category.length<=40&&
  Number.isSafeInteger(r.timestamp)&&r.timestamp>=1517443200&&r.timestamp<=now&&Number.isSafeInteger(r.fetched_at)&&r.fetched_at>=r.timestamp&&r.fetched_at<=now&&
  Number.isSafeInteger(r.next_update_at)&&r.next_update_at>=r.fetched_at&&r.next_update_at<=r.fetched_at+86400;
}
function snapshot(value:unknown):Snapshot {
 const s=value as Snapshot;
 if(!s||typeof s.loading!=='boolean'||typeof s.outdated!=='boolean'||typeof s.closed!=='boolean'||
  !Number.isFinite(s.retry_after)||s.retry_after<0||s.retry_after>86460||!Number.isFinite(s.refresh_after)||s.refresh_after<0||s.refresh_after>60||
  (s.record!==null&&!validRecord(s.record))||(s.error!==null&&(!s.error||typeof s.error.detail!=='string'||typeof s.error.kind!=='string'))||
  (s.cache_warning!==null&&typeof s.cache_warning!=='string'))throw new Error('Invalid sentiment response');
 return s;
}
const empty:Snapshot={record:null,loading:true,outdated:false,error:null,cache_warning:null,retry_after:3600,refresh_after:0,closed:false};

export default function FearGreed({active}:{active:boolean}) {
 const [state,setState]=useState<Snapshot>(empty),[request,setRequest]=useState(0),[clock,setClock]=useState(Date.now());
 const [collapsed,setCollapsed]=useState(()=>{try{return localStorage.getItem(preference)==='true';}catch{return false;}});
 const [preferenceError,setPreferenceError]=useState(false);
 const id=useId(),manualSeen=useRef(0);
 useEffect(()=>{
  if(!active)return;
  let gone=false,polls=0,timer:ReturnType<typeof setTimeout>|undefined;
  const controller=new AbortController();
  async function read(refresh=false){
   try{
    const next=snapshot(await api('fear_greed_status',{refresh},{signal:controller.signal}));
    if(gone)return;
    setState(next);setClock(Date.now());
    // Short bounded local status reads observe one background fetch; they do
    // not initiate repeated external requests. Stable values sleep until due.
    if(next.loading&&++polls<=24)timer=setTimeout(()=>read(),500);
    else if(next.loading){
     setState({...next,loading:false,error:{kind:'offline',detail:'Sentiment request is still pending; check again later.'}});
     timer=setTimeout(()=>{polls=0;read();},3600000);
    }else if(!next.closed)timer=setTimeout(()=>{polls=0;read();},Math.max(900,next.retry_after+1)*1000);
   }catch{
    if(gone)return;
    setState(previous=>({...previous,loading:false,error:{kind:'offline',detail:'Sentiment service is unavailable. Last received value retained when available.'}}));
    setClock(Date.now());timer=setTimeout(()=>read(),3600000);
   }
  }
  const manual=request> manualSeen.current;manualSeen.current=request;read(manual);
  return()=>{gone=true;controller.abort();clearTimeout(timer);};
 },[active,request]);
 const record=state.record,now=clock/1000;
 const outdated=!!record&&(state.outdated||now>record.next_update_at+300||now-record.timestamp>36*3600);
 useEffect(()=>{
  if(!active||!record)return;
  const boundary=Math.min(record.next_update_at+301,record.timestamp+36*3600+1)*1000;
  if(boundary<=Date.now())return;
  const timer=setTimeout(()=>setClock(Date.now()),boundary-Date.now());return()=>clearTimeout(timer);
 },[active,record]);
 const date=record?new Date(record.timestamp*1000).toISOString().slice(0,10):'No dated value';
 const status=!active?'Paused':state.closed?'Service stopped':state.loading?'Updating…':state.error?(state.error.kind==='invalid'?(record?'Saved · invalid update':'Invalid data'):state.error.kind==='access'?(record?'Saved · access blocked':'Access blocked'):(record?'Saved · offline':'Unavailable')):outdated?'Outdated':record?'Latest available':'No data';
 const color=record?(colors[record.category]??'#a2b5c5'):'#637284';
 const angle=record?Math.PI*(1-record.value/100):0;
 const needle=record?{x:90+55*Math.cos(angle),y:78-55*Math.sin(angle)}:null;
 function toggle(){
  const next=!collapsed;setCollapsed(next);
  try{localStorage.setItem(preference,String(next));setPreferenceError(false);}catch{setPreferenceError(true);}
 }
 return <aside className={`fear-greed ${collapsed?'fear-greed--collapsed':''}`} aria-label="Latest daily BTC Fear and Greed index">
  <div className="fear-greed-heading"><strong>Fear &amp; Greed</strong><button type="button" aria-expanded={!collapsed} aria-controls={id} aria-label={collapsed?'Expand Fear and Greed':'Collapse Fear and Greed'} onClick={toggle}>{collapsed?'＋':'−'}</button></div>
  <div className="fear-greed-scope">Latest · BTC · daily</div>
  <div className="fear-greed-reading" style={{color}}>{record?<><strong>{record.value}</strong><span>/ 100 · {record.category}</span></>:<strong>—</strong>}</div>
  <div id={id} hidden={collapsed}>
   <svg className="fear-greed-dial" viewBox="0 0 180 90" role="img" aria-label={record?`Latest BTC sentiment ${record.value} out of 100, ${record.category}`:'No sentiment value available'}>
    <defs><linearGradient id={`${id}-gradient`}><stop offset="0%" stopColor="#ed727d"/><stop offset="50%" stopColor="#dac96b"/><stop offset="100%" stopColor="#4dbdaf"/></linearGradient></defs>
    <path d="M 18 78 A 72 72 0 0 1 162 78" fill="none" stroke={record?`url(#${id}-gradient)`:'#394759'} strokeWidth="10" strokeLinecap="round"/>
    {needle&&<><line x1="90" y1="78" x2={needle.x} y2={needle.y} stroke={color} strokeWidth="3" strokeLinecap="round"/><circle cx="90" cy="78" r="5" fill={color}/></>}
    <text x="12" y="89">0</text><text x="150" y="89">100</text>
   </svg>
   <div className="fear-greed-ends"><span>Extreme fear</span><span>Extreme greed</span></div>
  </div>
  <div className="fear-greed-date">{record?'Value date: ':''}<time dateTime={record?new Date(record.timestamp*1000).toISOString():undefined}>{date}</time>{record?' UTC':''}</div>
  <div className="fear-greed-status" role="status">{status}{outdated&&status!=='Outdated'?' · outdated':''}</div>
  <a href={source} target="_blank" rel="noopener noreferrer">Source: Alternative.me ↗</a>
  {!collapsed&&<><small>BTC sentiment, independent of chart history.</small>{state.error&&<small>{state.error.detail}</small>}{state.cache_warning&&<small>{state.cache_warning}</small>}{!state.loading&&(state.error||outdated)&&<button type="button" className="fear-greed-retry" disabled={!active||state.closed} onClick={()=>setRequest(v=>v+1)}>Check for update</button>}</>}
  {preferenceError&&<small>Collapse preference could not be saved.</small>}
 </aside>;
}
