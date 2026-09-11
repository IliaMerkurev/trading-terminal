import {useEffect,useState} from 'react';
import {api} from './api';
import {poll} from './poll';
import type {Profile} from './model';

type Status={active?:boolean;options?:{paper:boolean;channels:string[]};sessions?:Array<{id:string;name:string;status:string}>;session?:{id:string;status:string;detail:string;last_minute:number|null;snapshot:{strategy_name:string;profile:Profile}};price?:string;mark?:string;price_time?:number;forming?:{open:number;high:number;low:number;close:number};evaluation?:{time:number;values:Record<string,number|boolean|null>;signals:Record<string,boolean>};events?:Array<{id:string;type:string;time:number;source:string;delivery:string}>;log?:Array<{time:number;message:string}>;paper?:{cash:string;equity:string;net_pnl?:string;waiting_funding?:boolean;pending_observations?:number;position:{side:string;quantity:string;entry:string}|null};paper_paused?:boolean;paper_history?:Array<{time_ns:number;fills:Array<{reason:string;side:string;quantity:string;price:string;fee:string}>}>;telegram?:{configured:boolean;storage:string}};
const when=(seconds:number)=>new Date(seconds*1000).toLocaleString();

export default function Live({strategyId,profile}:{strategyId:string|null;profile:Profile}){
 const [status,setStatus]=useState<Status>({}),[paper,setPaper]=useState(false),[channels,setChannels]=useState<string[]>([]),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [token,setToken]=useState(''),[chat,setChat]=useState(''),[configure,setConfigure]=useState(false),[busy,setBusy]=useState(false);
 useEffect(()=>poll(()=>api<Status>('live_status'),setStatus,e=>setError(String(e)),1000),[]);
 useEffect(()=>{if(status.session&&status.options){setPaper(status.options.paper);setChannels(status.options.channels);}},[status.session?.id]);
 async function act(command:string,params:Record<string,unknown>={}){setBusy(true);setError('');try{const result=await api<any>(command,params);if(command==='live_replay')setNotice(result.match?`MATCH — ${result.checked_events} recorded signal events`:'MISMATCH — inspect session before continuation');if(command==='notification_test')setNotice('Test queued. Check the event log for delivery status.');if(command==='telegram_configure'){setToken('');setChat('');setConfigure(false);}setStatus(await api<Status>('live_status'));}catch(e){setError(String(e));}finally{setBusy(false);}}
 const session=status.session,signals=status.evaluation?.signals??{},activeProfile=session?.snapshot.profile??profile;
 return <section className="live-workspace">
  <header><h2>Live monitoring <small>No real orders</small></h2><strong className={session?.status==='CONNECTED'?'positive':'warning'}>{session?.status??'PAUSED'}</strong></header>
  {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status">{notice}</p>}
  <p>Confirmed M1 updates drive the same strategy logic as historical runs. Forming mode evaluates the partial primary candle at each minute close. Market prices update separately.</p>
  <div className="live-controls">
   <div><strong>{session?.snapshot.strategy_name??'Use the selected saved visual strategy'}</strong><p>{activeProfile.symbol} · {activeProfile.market} · {activeProfile.primary_minutes}m · {activeProfile.evaluation}</p><small>New sessions use the selected strategy and simulation settings. Existing sessions retain their frozen snapshot.</small></div>
   <label><input type="checkbox" checked={paper} disabled={status.active} onChange={e=>setPaper(e.target.checked)}/> Paper trading</label>
   <button disabled={!strategyId||status.active||busy} onClick={()=>act('live_start',{strategy_id:strategyId,profile,paper,channels})}>Start new live session</button>
   <button disabled={!status.active||busy} onClick={()=>act('live_pause')}>Pause</button>
   {session&&<button disabled={status.active||busy} onClick={()=>act('live_resume',{session_id:session.id,revalidate_paper:false})}>Recover monitoring</button>}
  </div>
  {!!status.sessions?.length&&<label>Saved live session<select disabled={status.active||busy} value={session?.id??''} onChange={e=>act('live_select',{session_id:e.target.value})}>{status.sessions.map(s=><option key={s.id} value={s.id}>{s.name} · {s.id.slice(0,8)} · {s.status}</option>)}</select></label>}
  {session&&<p>{session.detail} · Last valid minute: {session.last_minute===null?'None':when(session.last_minute+60)}</p>}
  <div className="live-metrics"><article><small>Observed last price</small><strong>{status.price??'Waiting'}</strong>{status.mark&&<small>Mark {status.mark}</small>}</article>
   <article><small>Strategy</small><strong>Live: {status.active?'Running':'Paused'}</strong><small>Paper: {status.paper?(!status.active||status.paper_paused?'Revalidation required':status.paper.waiting_funding?'Waiting for confirmed funding':'Running'):'Disabled'}</small></article>
   {['entry_long','exit_long','entry_short','exit_short'].map(key=><article key={key}><small>{key.replaceAll('_',' ')}</small><strong>{status.evaluation?(signals[key]?'TRUE':'FALSE'):'Awaiting evaluation'}</strong></article>)}
  </div>
  {status.forming&&<p>Current exchange candle: O {status.forming.open} · H {status.forming.high} · L {status.forming.low} · C {status.forming.close}</p>}
  <details><summary>Current strategy values</summary><table><tbody>{Object.entries(status.evaluation?.values??{}).map(([name,value])=><tr key={name}><td>{name}</td><td>{value===null?'Warming up':String(value)}</td></tr>)}</tbody></table></details>
  <section><h3>Notification channels</h3><div className="live-controls">{['windows','sound','telegram'].map(channel=><div key={channel}><label><input type="checkbox" checked={channels.includes(channel)} disabled={status.active} onChange={e=>setChannels(xs=>e.target.checked?[...xs,channel]:xs.filter(x=>x!==channel))}/>{channel==='windows'?'Windows':channel==='sound'?'Sound':'Telegram'}</label><button disabled={busy} onClick={()=>act('notification_test',{channel})}>Test {channel}</button></div>)}</div>
   <p>Telegram: {status.telegram?.configured?'Configured in Windows Credential Manager':'Not configured'}. Delivery failures do not stop evaluation.</p>
   <button onClick={()=>setConfigure(v=>!v)}>Configure Telegram</button> <button disabled={busy||!status.telegram?.configured} onClick={()=>act('telegram_clear')}>Clear stored credentials</button>
   {configure&&<form autoComplete="off" onSubmit={e=>{e.preventDefault();act('telegram_configure',{token,chat_id:chat});}}><label>Bot token<input type="password" autoComplete="new-password" value={token} onChange={e=>setToken(e.target.value)}/></label><label>Chat ID<input type="password" autoComplete="off" value={chat} onChange={e=>setChat(e.target.value)}/></label><button disabled={busy}>Save to protected storage</button><p>Credentials stay local and are excluded from exports. Saved values are never displayed.</p></form>}
  </section>
  {status.paper&&<section><h3>Paper account</h3><p>Virtual only. Observed-price fills with configured slippage/fees; no liquidity or exchange-fill guarantee.</p><div className="live-metrics"><article>Cash<strong>{status.paper.cash}</strong></article><article>Equity<strong>{status.paper.equity}</strong></article><article>PnL<strong>{status.paper.net_pnl??'0'}</strong></article></div>
   {status.paper.waiting_funding&&<p role="status">Waiting for confirmed public funding settlement. {status.paper.pending_observations} observed prices are recorded for ordered account recovery; signal evaluation continues.</p>}
   <p>{status.paper.position?`${status.paper.position.side} ${status.paper.position.quantity} @ ${status.paper.position.entry}`:'No position'}</p>
   {status.paper_paused&&session&&<div className="warning"><p>Missing live ticks cannot be reconstructed from candles. Review the position and accept continuation at the next observed price; missed fills are not invented.</p><button disabled={busy} onClick={()=>act('live_resume',{session_id:session.id,revalidate_paper:true})}>Revalidate paper continuity and resume</button></div>}
   <table><thead><tr><th>Observed time</th><th>Side / reason</th><th>Quantity</th><th>Fill</th><th>Fee</th></tr></thead><tbody>{status.paper_history?.flatMap((r,i)=>r.fills.map((f,j)=><tr key={`${i}-${j}`}><td>{when(r.time_ns/1e9)}</td><td>{f.side} / {f.reason}</td><td>{f.quantity}</td><td>{f.price}</td><td>{f.fee}</td></tr>))}</tbody></table>
  </section>}
  <section><h3>Signal history</h3>{session&&<button disabled={busy||status.active} onClick={()=>act('live_replay',{session_id:session.id})}>Verify recorded signals with replay</button>}<table><thead><tr><th>Signal time</th><th>Transition</th><th>Source</th><th>Delivery</th></tr></thead><tbody>{status.events?.map(e=><tr key={e.id}><td>{when(e.time)}</td><td>{e.type.replaceAll('_',' ')}</td><td>{e.source}</td><td>{e.delivery}</td></tr>)}</tbody></table></section>
  <section><h3>Event log</h3><ol className="live-event-log">{status.log?.slice().reverse().map((e,i)=><li key={`${e.time}-${i}`}><time>{when(e.time/1000)}</time> {e.message}</li>)}</ol></section>
 </section>;
}
