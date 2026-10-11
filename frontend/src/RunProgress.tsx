/** Computation percentage is independent of durable result publication. */
export function RunProgress({status}:{status:any}) {
 const f=status?.finalization;
 const terminal:Record<string,string>={completed:'Result saved.',cancelled:'Cancelled. No completed result was published.',failed:'Calculation failed. No completed result was published.',interrupted:'Work was interrupted. No automatic retry.'};
 if(status?.status==='completed'&&status?.worker_active===true)return <span role="status">Result saved; waiting for worker cleanup.</span>;
 if(status?.worker_active!==true&&terminal[status?.status])return <span>{terminal[status.status]}</span>;
 if(f&&f.phase!=='computing'&&status?.worker_active!==false)return <span role="status">{status.status==='cancel_requested'?'Cancellation requested; waiting for cleanup. ':''}Finalizing result · {f.phase} · {f.staged_rows??0}/{f.total_rows??'?'} rows · {f.staged_bytes??0} bytes staged. {f.oversized_rows>0&&`${f.oversized_rows} oversized rows written separately. `}Waiting for durable completion and worker cleanup.</span>;
 if(status?.status==='finalizing')return <span role="status">Loading finalization status…</span>;
 if(status?.status==='cancel_requested')return <span>Cancellation requested; waiting for worker cleanup.</span>;
 return <span>{status?.progress?`${Math.round((status.progress.fraction??0)*100)}% computed`:'Worker preparation'}</span>;
}
