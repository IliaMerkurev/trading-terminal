/** Presentation only: persisted machine statuses and row outcomes stay unchanged. */
export function comparisonStatusLabel(status: string): string {
 const labels: Record<string,string> = {
  completed:'Completed',
  completed_with_errors:'Finished with unavailable or failed rows',
  incompatible:'Unavailable', unavailable:'Unavailable',
  failed:'Failed', error:'Error', cancelled:'Cancelled', interrupted:'Interrupted',
  running:'Running', preparing:'Preparing', pending:'Pending',
  frozen:'Frozen · not started',
 };
 return Object.hasOwn(labels,status)?labels[status]:`Unknown status (${status || 'missing'})`;
}

export function comparisonStatusSummary(report: {
 status: string;
 rows: {status: string}[];
 snapshot: {rows: unknown[]};
 error?: string | null;
}): string {
 const counts = new Map<string,number>();
 for (const row of report.rows) {
  const key = row.status==='incompatible'?'unavailable':row.status==='error'?'failed':row.status;
  counts.set(key,(counts.get(key)??0)+1);
 }
 const count = (key:string)=>counts.get(key)??0;
 const finishedRows = count('completed')+count('unavailable')+count('failed');
 const complete = report.rows.length>0 && report.rows.length===report.snapshot.rows.length && finishedRows===report.rows.length;
 let label = comparisonStatusLabel(report.status);
 if (report.status==='completed' || report.status==='completed_with_errors') {
  label = !complete?'Incomplete results':report.error?'Finished with an error':count('failed')?'Completed with failures':'Completed';
 }
 const details = [`${count('completed')} completed`,`${count('unavailable')} unavailable`,`${count('failed')} failed`];
 for (const [status,total] of counts) {
  if (!['completed','unavailable','failed'].includes(status)) {
   details.push(`${total} ${comparisonStatusLabel(status).toLowerCase()}`);
  }
 }
 if (report.rows.length!==report.snapshot.rows.length) details.push('Row details incomplete');
 return [label,...details].join(' · ');
}
