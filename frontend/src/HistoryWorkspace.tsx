import {useState} from 'react';
import type {Profile} from './model';
import {dateOnly,dateTime,timeframe} from './research';

export default function HistoryWorkspace({datasets,profile,status,onPrepare,onCancel,onUse,disabled}:{datasets:any[];profile:Profile;status:any;onPrepare:(p:any)=>void;onCancel:()=>void;onUse:(d:any)=>void;disabled:boolean}){
 const [market,setMarket]=useState(profile.market),[symbol,setSymbol]=useState(profile.symbol),[minutes,setMinutes]=useState(Number(profile.execution_minutes??60));
 const [start,setStart]=useState(dateOnly(Math.floor(Date.now()/86400000)*86400-2*365*86400)),[end,setEnd]=useState(dateOnly(Math.floor(Date.now()/86400000)*86400));
 const complete=(d:any)=>d.coverage.trade.complete&&(d.market==='spot'||d.coverage.mark?.complete&&d.coverage.funding?.complete_against_current_interval);
 const ready=status?.status==='completed'?datasets.find(d=>d.id===status.dataset_id&&complete(d)):undefined;
 const active=['running','cancel_requested'].includes(status?.status);
 const valid=Number.isFinite(Date.parse(start))&&Number.isFinite(Date.parse(end))&&start<end&&/^[A-Z0-9]{1,24}USDT$/.test(symbol);
 const rows=[...datasets].sort((a,b)=>b.range[1]-a.range[1]);
 return <section className="content history-workspace">
  <div className="studio-heading"><div><h1>Market data</h1><p>Prepare once. Reuse offline. Extend the range as new candles close.</p></div><span className="count-badge">{datasets.length} saved snapshots</span></div>
  <div className="history-layout"><section className="history-form"><h2>Prepare history</h2>
   <label className="field">Market<select aria-label="History market" value={market} onChange={e=>{setMarket(e.target.value);if(e.target.value==='linear')setMinutes(1);}}><option value="spot">Spot</option><option value="linear">Perpetual</option></select></label>
   <label className="field">Instrument<input aria-label="History instrument" value={symbol} onChange={e=>setSymbol(e.target.value.toUpperCase())}/></label>
   <label className="field">Candle resolution<select aria-label="History resolution" value={minutes} onChange={e=>setMinutes(Number(e.target.value))}>{(market==='spot'?[60,240,1440,15,5,1]:[1]).map(m=><option key={m} value={m}>{timeframe(m)}{m===1?' · detailed execution':''}</option>)}</select></label>
   <div className="two-columns"><label className="field">From · UTC<input aria-label="History from" type="date" value={start} onChange={e=>setStart(e.target.value)}/></label><label className="field">Until · exclusive UTC<input aria-label="History until" type="date" value={end} onChange={e=>setEnd(e.target.value)}/></label></div>
   <div className="history-estimate"><strong>{valid?Math.round((Date.parse(end)-Date.parse(start))/(minutes*60000)).toLocaleString():'—'}</strong><span>source candles · missing ranges only</span></div>
   <button className="primary full-width" disabled={disabled||active||!valid} onClick={()=>onPrepare({market,symbol,minutes,start:Date.parse(start+'T00:00:00Z')/1000,end:Date.parse(end+'T00:00:00Z')/1000})}>Prepare / reuse history</button>
   <p className="muted">Public Bybit data. Coarse history is for spot closed-bar research. Perpetuals include separate M1 mark and funding history. Original snapshots stay intact.</p>
  </section><section className="history-snapshots"><h2>Saved history</h2>
   {status&&status.status!=='idle'&&<div className="history-progress" role="status"><strong>{status.status==='completed'?(ready?'History ready':'Checking history coverage'):status.status}</strong>{ready&&<button className="primary" onClick={()=>onUse(ready)}>Continue with this history</button>}<p>{status.stage}{status.error&&` · ${status.error}`}</p>{status.status==='completed'&&!ready&&<p>Only complete history can be used. Review any gaps below and retry preparation if needed.</p>}{active&&<><div className="progress"><div style={{width:`${(status.fraction??0)*100}%`}}/></div><button disabled={status.status==='cancel_requested'} onClick={onCancel}>Cancel download</button></>}</div>}
   {!rows.length&&<div className="history-empty"><span>▤</span><h3>Prepare history for your first test</h3><p>Start with BTCUSDT and 1h candles to compare 1h, 4h and daily strategies from one dataset.</p></div>}
   {rows.map(d=>{const resolution=(d.interval_seconds??60)/60,until=Math.floor(Date.now()/1000/(resolution*60))*resolution*60,complete=d.coverage.trade.complete&&(d.market==='spot'||d.coverage.mark?.complete&&d.coverage.funding?.complete_against_current_interval);return <article className="dataset-card" key={d.id}>
    <div className="dataset-top"><strong>{d.symbol}</strong><span>{d.market} · {timeframe(resolution)}</span><span className={complete?'status-pill ready':'status-pill warning'}>{complete?'Complete coverage':'Incomplete coverage'}</span></div>
    <p>{dateTime(d.range[0]).replace('T',' ')} → {dateTime(d.range[1]).replace('T',' ')} UTC</p>
    <div className="dataset-bottom"><span>{d.coverage.trade.count.toLocaleString()} candles · {d.source}</span><button disabled={disabled||active||until<=d.range[1]} onClick={()=>onPrepare({market:d.market,symbol:d.symbol,minutes:resolution,start:d.range[0],end:until})}>Update to latest</button><button disabled={!complete} onClick={()=>onUse(d)}>Use this history</button></div>
    {!complete&&<p className="warning-text">Trade gaps: {d.coverage.trade.gaps?.length??0}. {d.market==='linear'&&`Mark: ${d.coverage.mark?.complete?'complete':'incomplete'}; funding: ${d.coverage.funding?.complete_against_current_interval?'complete against current schedule':'unverified'}.`} Extend or retry preparation; gaps are never filled with fabricated candles.</p>}
   </article>;})}
  </section></div>
 </section>;
}
