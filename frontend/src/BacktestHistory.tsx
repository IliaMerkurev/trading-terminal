import type {Profile} from './model';
import {timeframe} from './research';
import {historyIntervalSeconds,historyMatchesProfile,historyMismatch} from './historyCompatibility';

const text=(value:unknown,fallback:string)=>typeof value==='string'&&value.trim()?value:fallback;
export const historyCount=(value:unknown)=>typeof value==='number'&&Number.isSafeInteger(value)&&value>=0?value.toLocaleString():'Unknown';
export function historyUtc(value:unknown):string {
  if(typeof value!=='number'||!Number.isFinite(value))return 'Unknown';
  const date=new Date(value*1000);
  return Number.isFinite(date.getTime())?date.toISOString().replace('T',' ').replace('.000Z',' UTC'):'Unknown';
}
const period=(start:unknown,end:unknown)=>`${historyUtc(start)} → ${historyUtc(end)} (end exclusive)`;
const nativeTimeframe=(d:any)=>{
  const seconds=historyIntervalSeconds(d);
  return seconds===null?'Unknown native timeframe':`${timeframe(seconds/60)} native${d.interval_seconds===undefined?' (legacy default)':''}`;
};
const coverageLabel=(value:unknown)=>value===true?'Complete requested coverage':value===false?'Gaps present':'Coverage unknown';

export default function BacktestHistory({datasets,profile,datasetId,onChange}:{datasets:any[];profile:Profile;datasetId:string;onChange:(id:string)=>void}) {
  const selected=datasets.find(d=>d.id===datasetId&&historyMatchesProfile(d,profile));
  const compatible=datasets.filter(d=>historyMatchesProfile(d,profile));
  return <>
    <label className="field"><span>Prepared dataset</span><select aria-label="Prepared dataset" value={selected?.id??''} onChange={e=>onChange(e.target.value)}>
      <option value="">Select matching history</option>
      {datasets.map(d=>{const reason=historyMismatch(d,profile);return <option key={d.id} value={d.id} disabled={!!reason}>
        {text(d.symbol,'Unknown instrument')} · {text(d.market,'Unknown market')} · {nativeTimeframe(d)} · {historyCount(d.coverage?.trade?.count)} bars · {text(d.source,'Unknown source')} · {String(d.id).slice(0,8)}{reason?` · Unavailable: ${reason}`:''}
      </option>;})}
    </select></label>
    <p className="muted">History must match {profile.market} / {profile.symbol} / {timeframe(Number(profile.execution_minutes??1))} execution. Other histories are disabled; no resampling is applied.</p>
    {!compatible.length&&<p role="status">No matching history is available. Prepare matching history in Data, or review the strategy settings.</p>}
    {selected&&<section aria-label="Selected history details">
      <p>Source: {text(selected.source,'Unknown source')} · {nativeTimeframe(selected)}</p>
      <p>Actual trade coverage: {period(selected.coverage?.trade?.actual_start,selected.coverage?.trade?.actual_end)}</p>
      <p className="muted">Requested range: {period(selected.range?.[0],selected.range?.[1])}</p>
      <div className="coverage"><div><span>Trade bars</span><strong>{historyCount(selected.coverage?.trade?.count)}</strong><small>{coverageLabel(selected.coverage?.trade?.complete)}</small></div>
        {selected.market==='linear'&&<><div><span>Mark bars</span><strong>{historyCount(selected.coverage?.mark?.count)}</strong><small>{coverageLabel(selected.coverage?.mark?.complete)}</small></div><div><span>Funding events</span><strong>{historyCount(selected.coverage?.funding?.count)}</strong><small>{selected.coverage?.funding?.complete_against_current_interval===true?'Matches declared interval':'Coverage not verified'}</small></div></>}
      </div>
    </section>}
  </>;
}
