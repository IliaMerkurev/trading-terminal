import {useEffect,useState} from 'react';

export default function PositionLifecycle({trades,selectedTrade,onFill}:{trades:any[];selectedTrade?:any;onFill?:(clock:any,label:string)=>void}){
 const [selected,setSelected]=useState(''),[offset,setOffset]=useState(0);
 const managed=trades.filter(t=>t.position_id!=null),trade=selectedTrade??managed.find(t=>String(t.position_id)===selected)??managed[0];
 useEffect(()=>{setOffset(0);},[trade]);
 if(!trade||trade.position_id==null)return null;
 const events=trade.events??[],rows=events.slice(offset,offset+50);
 return <section className="position-lifecycle" aria-label="Position lifecycle"><h3>Position lifecycle</h3>
 {!selectedTrade&&<label>Position <select aria-label="Lifecycle position" value={String(trade.position_id)} onChange={e=>{setSelected(e.target.value);setOffset(0);}}>{managed.map(t=><option key={t.position_id} value={String(t.position_id)}>#{t.position_id} · {t.side} · {t.entry_count} entries</option>)}</select></label>}
 <div className="paper-stats">{[['Peak quantity',trade.peak_quantity],['Maximum observed notional',trade.max_notional],['Realized gross PnL',trade.gross_pnl],['Fees',trade.fees],['Funding',trade.funding],['Net PnL',trade.net_pnl]].map(([label,value])=><div key={label}><small>{label}</small><strong>{value}</strong></div>)}</div>
 <p>Entries and reductions belong to one position. Reduction PnL attributes the corresponding entry fees and funding; account costs are charged when they occur.</p>
 <div className="table-scroll"><table><thead><tr><th>Time (UTC)</th><th>Event</th><th>Quantity</th><th>Price / stop</th><th>Remaining</th><th>Average entry at event</th><th>Fee / funding</th><th>Reduction net PnL</th><th>Reason</th>{onFill&&<th>Chart</th>}</tr></thead><tbody>{rows.map((e:any,i:number)=><tr key={offset+i}><td>{trade.review?.events?.[offset+i]?.utc??'Exact event time unavailable'}</td><td>{e.type.replaceAll('_',' ')}</td><td>{e.quantity??'—'}</td><td>{e.price??'—'}</td><td>{e.remaining_quantity??'—'}</td><td>{e.average_entry??'—'}</td><td>{e.fee??e.amount??'—'}</td><td>{e.reduction_net_pnl??'—'}</td><td>{(e.reason??e.message??'').replaceAll('_',' ')}</td>{onFill&&<td>{['entry','scale','reduction','exit'].includes(e.type)?<button className="lifecycle-event-button" disabled={!trade.review?.events?.[offset+i]} onClick={()=>onFill(trade.review.events[offset+i],`${e.type} fill ${offset+i+1}`)}>Show fill {offset+i+1}</button>:'Not a fill'}</td>}</tr>)}</tbody></table></div>
 <div className="pagination"><button disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-50))}>Previous events</button><span>{Math.min(offset+1,events.length)}–{offset+rows.length} of {events.length}</span><button disabled={offset+50>=events.length} onClick={()=>setOffset(offset+50)}>Next events</button></div>
 </section>;
}
