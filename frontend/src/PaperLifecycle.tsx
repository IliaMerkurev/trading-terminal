import {useEffect,useState} from 'react';
import {api} from './api';
import {poll} from './poll';

export default function PaperLifecycle({sessionId}:{sessionId:string}){
 const [cursor,setCursor]=useState<number[]|null>(null),[page,setPage]=useState<any>({rows:[],next:null}),[error,setError]=useState('');
 useEffect(()=>{setCursor(null);},[sessionId]);
 useEffect(()=>poll(()=>api('paper_lifecycle',{session_id:sessionId,before:cursor,limit:50}),value=>{setPage(value);setError('');},()=>setError('Paper lifecycle history unavailable.'),2000),[sessionId,cursor]);
 return <div aria-label="Paper lifecycle history"><strong>PAPER lifecycle history</strong>{error&&<p role="alert">{error}</p>}<button onClick={()=>setCursor(null)}>Latest events</button><button disabled={!page.next} onClick={()=>setCursor(page.next)}>Older events</button>
 <table><thead><tr><th>UTC / position</th><th>Event</th><th>Quantity / remaining</th><th>Price / stop</th><th>Fee / funding</th><th>Reason</th></tr></thead><tbody>{page.rows.map((event:any,i:number)=><tr key={`${event.time_ns}-${i}`}><td>{new Date(event.time_ns/1e6).toISOString().slice(0,19)} · #{event.position_id}</td><td>{event.type.replaceAll('_',' ')}</td><td>{event.quantity??'—'} / {event.remaining_quantity??'—'}</td><td>{event.price??'—'}</td><td>{event.fee??event.amount??'—'}</td><td>{(event.reason??event.message??'').replaceAll('_',' ')}</td></tr>)}</tbody></table>{!page.rows.length&&<p>No managed lifecycle events recorded.</p>}</div>;
}
