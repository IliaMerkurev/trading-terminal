export type ResearchContext={source:string;market:string;symbol:string;minutes:number};
export type FrozenRule={id:string;name:string;revision:number;definition_revision:number;definition_hash:string;definition:any};
export type HistoryStatus='queued'|'running'|'cancel_requested'|'completed'|'cancelled'|'error'|'interrupted';
export type HistoryRun={id:string;sequence:number;request_id:string;created_at:number;status:HistoryStatus;cancel_requested:boolean;rule_id:string;rule_name:string;rule_revision:number;definition_revision:number;definition_hash:string;context:ResearchContext;origin:any;start:number;end:number;input_count:number;input_hash:string;coverage_complete:boolean;summary:any;error:string|null;definition?:any};
export type HistoryPreview={rule:FrozenRule;cached_start:number|null;cached_end:number|null;cached_count:number;origin_raw_open:number;max_inputs:number;max_working_bytes:number;max_unfinished:number;note:string};
export type HistoryStart={request_id:string;rule_id:string;revision:number;definition_hash:string;start:number;end:number};
export type PendingHistory={params:HistoryStart;createdAt:string;hadUnknown:boolean};
export type HistoryEvaluation={raw_open_time:number;confirmed_at:number;truth:boolean|null;state_truth:boolean|null;hit:boolean;conditions:any[];values:Record<string,Record<string,number|null>>};
export type HistoryMatch=HistoryEvaluation&{row_index:number};
export type RawCandle={time:number;open:number;high:number;low:number;close:number;volume:number;confirmation?:string};
export type HistoryRow={row_index:number;candle:RawCandle;evaluation:HistoryEvaluation;in_range:boolean};
export type HistoryMarker={row_index:number;confirmed_at:number;raw_open_time:number};
export type HistoryWindow={run_id:string;total_rows:number;start_index:number;next_index:number|null;rows:HistoryRow[];markers:HistoryMarker[];target:{confirmed_at:number;raw_open_time:number;row_index:number|null;included:boolean;status:'available'|'missing'}|null;byte_limited:boolean};
export type EventEvidence={event:{id:string;rule_id:string;current_name:string;evidence:any};context:ResearchContext;warning:string;price_context_source:'current_cache';target_raw_open_time:number;target_confirmed_at:number;target_status:'confirmed'|'missing'|'unconfirmed'|'conflict';target_candle:RawCandle|null;candles:RawCandle[];byte_limited:boolean;target_in_window:boolean};
export const pendingHistoryKey='terminal.alert-history.pending.v1';
export const terminalHistory=(run:HistoryRun)=>['completed','cancelled','error','interrupted'].includes(run.status);
export const utcField=(value:number|null)=>value===null?'':new Date(value*1000).toISOString().slice(0,19);
// datetime-local is deliberately interpreted as UTC, never the browser timezone.
export function parseUtcField(value:string):number|null{
 if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(value))return null;
 const normalized=value.length===16?value+':00':value,ms=Date.parse(normalized+'Z');
 return Number.isFinite(ms)&&ms>0&&new Date(ms).toISOString().slice(0,19)===normalized?ms/1000:null;
}
export function historyRangeError(start:string,end:string,minutes:number){
 const first=parseUtcField(start),last=parseUtcField(end);
 if(first===null||last===null)return 'Enter valid UTC dates and times for both inclusive confirmed-close bounds.';
 if(first%(minutes*60)!==0||last%(minutes*60)!==0)return `Both confirmed-close bounds must align to the native ${minutes}m interval.`;
 if(first>last)return 'Start must be at or before End.';
 return '';
}
export const truthLabel=(value:boolean|null|undefined)=>value===true?'True':value===false?'False':'Unknown';
