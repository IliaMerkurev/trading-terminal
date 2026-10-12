import {useEffect,useRef,useState} from 'react';
import {api} from './api';
import RunChart from './RunChart';
import PositionLifecycle from './PositionLifecycle';
import FrozenRuleDetails from './FrozenRuleDetails';
import './trade-review.css';

export type SavedClock={time_ns:string;utc:string;source_open:number;source_close:number;available_through:number;interval_seconds:number};
export type TradeFocus={time:number;request:number;clock?:SavedClock;label?:string};
export const savedValue=(value:unknown)=>value===null||value===undefined?'Unavailable':String(value);
export function exactClock(value:any):SavedClock|null{
  return value&&typeof value.time_ns==='string'&&/^\d+$/.test(value.time_ns)&&typeof value.utc==='string'
    &&[value.source_open,value.source_close,value.available_through,value.interval_seconds].every(Number.isSafeInteger)
    &&value.interval_seconds>0&&value.source_close-value.source_open===value.interval_seconds?value:null;
}
const shortClock=(clock:any)=>exactClock(clock)?.utc.replace(/\.\d{9} UTC$/,' UTC')??'Exact time unavailable';

function OriginalConditions({runId}:{runId:string}){
  const [open,setOpen]=useState(false),[manifest,setManifest]=useState<any>(null),[error,setError]=useState('');
  useEffect(()=>{
    if(!open||manifest)return;
    let current=true;setError('');
    api('run_manifest',{run_id:runId}).then(value=>{if(current)setManifest(value);}).catch(e=>{if(current)setError(e.message);});
    return()=>{current=false;};
  },[open,runId,manifest]);
  const strategy=manifest?.strategy,graph=Array.isArray(strategy?.nodes)?strategy:null;
  return <details className="trade-source" onToggle={e=>setOpen(e.currentTarget.open)}>
    <summary>Original strategy conditions and execution settings</summary>
    <p>Only the immutable run snapshot is shown. Current editor settings and current alerts are never used.</p>
    {error?<p role="alert">Original snapshot unavailable: {error}</p>:!manifest?<p role="status">Reading original snapshot…</p>:<>
      {graph?<><dl className="trade-output-list">{Object.entries(graph.outputs??{}).map(([output,source])=><div key={output}><dt>{output.replaceAll('_',' ')}</dt><dd>{source===null?'Not connected':String(source)}</dd></div>)}</dl>
        <p>Per-fill condition evidence was not archived. Recorded node outputs are limited context, not proof of why an individual fill occurred. Frozen-rule leaf values and agreement member votes are unavailable in these backtest results.</p>
        {graph.nodes.map((node:any)=><details key={node.id}><summary>{node.id} · {node.type}</summary>{node.type==='frozen_rule'?<FrozenRuleDetails node={node}/>:<pre>{JSON.stringify({inputs:node.inputs,parameters:node.params},null,2)}</pre>}</details>)}
      </>:<p>Native or unsupported strategy: per-fill signal conditions are unavailable. The original full snapshot remains available below; no imported code is executed to inspect it.</p>}
      <details><summary>Saved simulation settings</summary><pre>{JSON.stringify(manifest.profile??null,null,2)}</pre></details>
    </>}
  </details>;
}

export default function TradeReview({runId,page,offset,onPage,onRetry,pageHistory}:{runId:string;page:any;offset:number;onPage:(offset:number)=>void;onRetry:()=>void;pageHistory?:{current:number[]}}){
  const [selected,setSelected]=useState<number|null>(null),[focus,setFocus]=useState<TradeFocus|null>(null);
  const request=useRef(0),inspector=useRef<HTMLElement>(null),localPages=useRef<number[]>([]);
  const pageStarts=pageHistory??localPages;
  useEffect(()=>{setSelected(null);setFocus(null);if(offset===0)pageStarts.current=[];},[runId,offset]);
  const rows:any[]=page?.rows??[],trade=selected===null?null:rows[selected];
  function navigate(clock:any,label:string){const exact=exactClock(clock);if(exact)setFocus({time:exact.source_open,clock:exact,label,request:++request.current});}
  function select(index:number,scroll=false){
    setSelected(index);setFocus(null);navigate(rows[index]?.review?.entry,`Trade ${offset+index+1} · first entry`);
    if(scroll)requestAnimationFrame(()=>inspector.current?.scrollIntoView?.({block:'start',behavior:'smooth'}));
  }
  const entryClock=exactClock(trade?.review?.entry),exitClock=exactClock(trade?.review?.exit);
  return <section className="trade-review" aria-label="Saved trade review">
    <section ref={inspector} className="trade-inspector" aria-label="Selected trade">
      {trade?<><div className="trade-review-heading"><div><h3>Trade {offset+selected!+1} · {trade.side??(trade.entry?.side==='buy'?'long':'short')}{trade.position_id!=null?` · position ${trade.position_id}`:''}</h3><p>{trade.exit?'Completed position':'Open position · no final exit recorded'}</p></div>
        <div className="trade-review-actions"><button disabled={selected===0} onClick={()=>select(selected!-1)}>Previous trade</button><button disabled={selected===rows.length-1} onClick={()=>select(selected!+1)}>Next trade</button><button onClick={()=>{setSelected(null);setFocus(null);}}>Close trade review</button></div></div>
        <dl className="trade-costs">{[['Gross PnL',trade.gross_pnl],['Fees',trade.fees],['Funding (signed)',trade.funding],['Net PnL',trade.net_pnl]].map(([label,value])=><div key={label}><dt>{label} · USDT</dt><dd>{savedValue(value)}</dd></div>)}</dl>
        <p className="trade-accounting-note">Saved position totals: gross − fees + signed funding = net. Positive funding is received. Slippage is already reflected in fill prices; it is not deducted again. These are exact saved decimal values.</p>
        <div className="trade-fill-cards">{[['First entry',trade.entry,entryClock],['Final exit',trade.exit,exitClock]].map(([label,fill,clock]:any)=><div key={label}><strong>{label}</strong>{fill?<><p>{clock?.utc??'Exact fill time unavailable'}</p><p>Price {savedValue(fill.price)} · filled quantity {savedValue(fill.quantity)} · fee {savedValue(fill.fee)} USDT</p><p>Reason: {savedValue(fill.reason)}</p><button disabled={!clock} onClick={()=>navigate(clock,`Trade ${offset+selected!+1} · ${label.toLowerCase()}`)}>Show {label.toLowerCase()} on chart</button></>:<p>No final exit recorded.</p>}</div>)}</div>
        {trade.position_id!=null&&<p>{savedValue(trade.entry_count)} entry fills · peak quantity {savedValue(trade.peak_quantity)} · maximum observed notional {savedValue(trade.max_notional)} USDT. First-entry and final-exit prices/quantities are individual fills, not lifecycle averages or total entered size.</p>}
        {(!entryClock||trade.exit&&!exitClock)&&<p className="assumption">Exact source-candle metadata is unavailable for this record. Chart targeting is disabled rather than guessing from rounded nanoseconds.</p>}
      </>:<p>Select a trade below to review its saved costs, actual fills and original strategy context.</p>}
    </section>
    <RunChart runId={runId} focus={focus}/>
    {trade&&<><OriginalConditions key={runId} runId={runId}/>{trade.position_id!=null?<details><summary>Position lifecycle · entries, reductions and other events</summary><PositionLifecycle trades={rows} selectedTrade={trade} onFill={(clock,label)=>navigate(clock,`Trade ${offset+selected!+1} · ${label}`)}/></details>:<p className="assumption">This legacy trade has no archived position lifecycle. Its saved entry, exit and cost totals are shown above.</p>}</>}
    <h3>Trades · select a row to review</h3>{page?.review_notice&&<p className="assumption">{page.review_notice}</p>}
    {!page?<p role="status">Loading saved trades…</p>:page.error?<p role="alert">Could not read saved trades: {page.error} <button onClick={onRetry}>Retry trades</button></p>:!rows.length?<p>No completed trades in this report. Open-position equity, if any, is included in the saved run metrics.</p>:<div className="table-scroll"><table className="trade-review-table"><thead><tr><th>Trade</th><th>Direction</th><th>First entry (UTC)</th><th>Final exit (UTC)</th><th>First entry price</th><th>Final exit price</th><th>First fill quantity</th><th>Net PnL (USDT)</th><th>Exit reason</th></tr></thead><tbody>{rows.map((t,i)=><tr key={offset+i} tabIndex={0} aria-selected={i===selected} onClick={()=>select(i,true)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(i,true);}}}><td>{offset+i+1}</td><td>{t.side??(t.entry?.side==='buy'?'Long':'Short')}</td><td>{shortClock(t.review?.entry)}</td><td>{t.exit?shortClock(t.review?.exit):'Open'}</td><td>{savedValue(t.entry?.price)}</td><td>{savedValue(t.exit?.price)}</td><td>{savedValue(t.entry?.quantity)}</td><td className={Number(t.net_pnl)>=0?'positive':'negative'}>{savedValue(t.net_pnl)}</td><td>{t.exit?.reason??'No final exit'}</td></tr>)}</tbody></table></div>}
    {page&&!page.error&&<div className="pagination"><button disabled={offset===0} onClick={()=>onPage(pageStarts.current.pop()??0)}>Previous</button><span>{rows.length?offset+1:0}–{offset+rows.length} of {page.total}</span><button disabled={page.next===null} onClick={()=>{pageStarts.current.push(offset);onPage(page.next);}}>Next</button></div>}
  </section>;
}
