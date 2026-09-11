export default function DownloadPanel({start,end,setStart,setEnd,status,onStart,onCancel,disabled}:{start:string;end:string;setStart:(s:string)=>void;setEnd:(s:string)=>void;status:any;onStart:()=>void;onCancel:()=>void;disabled:boolean}) {
  const active=['running','cancel_requested'].includes(status?.status);
  return <div className="download-panel"><h3>Prepare Bybit history</h3><p>Download public M1 trade candles, plus separate mark and funding history for perpetuals. Finished datasets remain available offline.</p>
    <div className="two-columns"><label className="field"><span>From (UTC, inclusive)</span><input aria-label="History start UTC" type="datetime-local" value={start} onChange={e=>setStart(e.target.value)}/></label><label className="field"><span>Until (UTC, exclusive)</span><input aria-label="History end UTC" type="datetime-local" value={end} onChange={e=>setEnd(e.target.value)}/></label></div>
    <button disabled={disabled||active} onClick={onStart}>Download selected market / instrument</button>{active&&<button className="danger" disabled={status.status==='cancel_requested'} onClick={onCancel}>Cancel download</button>}
    {status&&status.status!=='idle'&&<p role="status">{status.status} · {status.stage} {active?'— public API pagination; coverage is checked after download.':''}{status.error&&` · ${status.error}`}</p>}
  </div>;
}
