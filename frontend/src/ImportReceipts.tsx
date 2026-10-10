export type ImportItem={kind:'run'|'strategy';ordinal:number;destination_id:string;source_run_id:string|null;publication_state:string;current_status:string;modified_since_import?:boolean|null};
export type ImportReceipt={operation_id:string;phase:string;outcome:string|null;termination_reason:string|null;content_identity:string;artifact_verification:'not_checked';inspection_state:'available'|'unknown';items:ImportItem[]};
export type ImportSummary={operation_id:string;created_at:string;phase:string;outcome:string|null;archive_sha256:string|null};
export type ImportCursor={created_at:string;operation_id:string};
export type ImportPage={rows:ImportSummary[];next:ImportCursor|null};

export function ImportReceiptDetails({receipt,onOpenReport,onOpenStrategy,opening}:{receipt:ImportReceipt;onOpenReport:(id:string)=>void;onOpenStrategy:(id:string)=>void;opening:boolean}){
  const available=receipt.inspection_state==='available';
  return <section className="import-receipt" aria-label="Import receipt">
    <h3>Import {receipt.outcome??receipt.phase}</h3>
    <p className="import-identity">Operation {receipt.operation_id}</p>
    {receipt.termination_reason&&<p>Reason: {receipt.termination_reason.replaceAll('_',' ')}</p>}
    {!available&&<p role="alert">Receipt metadata is inconsistent. Publication outcome is unknown. Do not start another import to repair it.</p>}
    {receipt.content_identity==='not_bound'&&<p>Archive content identity is not bound. A receiving receipt cannot identify a file by its name or size.</p>}
    <p>Artifact verification: not checked. This receipt records committed publication and current database status. Opening a report reads saved database values; it does not verify artifact files or authenticate imported calculations.</p>
    {!receipt.items.length&&<p>No output identities were reserved.</p>}
    <ul>{receipt.items.map(item=><li key={`${item.kind}-${item.ordinal}`}>
      <strong>{item.kind==='run'?`Report ${item.ordinal+1}`:'Strategy'} · {item.publication_state}</strong>
      <span className="import-identity">{item.destination_id}</span>
      <span>Current database status: {item.current_status}</span>
      {item.kind==='strategy'&&item.modified_since_import===true&&<span>Modified since import. Opening shows the current saved strategy.</span>}
      {item.kind==='run'&&available&&item.publication_state==='published'&&item.current_status==='completed'&&<button disabled={opening} onClick={()=>onOpenReport(item.destination_id)}>Open report {item.ordinal+1}</button>}
      {item.kind==='strategy'&&available&&item.publication_state==='published'&&item.current_status==='available'&&<button disabled={opening} onClick={()=>onOpenStrategy(item.destination_id)}>Open saved strategy</button>}
    </li>)}</ul>
    <p>Inspection never retries or resumes an import. Incomplete records and upload bytes are retained; cancellation does not roll back saved reports.</p>
  </section>;
}
