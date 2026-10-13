import {useEffect,useRef,useState} from 'react';
import {api} from './api';

type Output='entry_long'|'exit_long'|'entry_short'|'exit_short';
const outputs:Output[]=['entry_long','exit_long','entry_short','exit_short'];
type Evaluation={time:number;values:Record<string,number|boolean|null>;signals:Record<Output,boolean>;evaluation_evidence:{ordinal:number;observed_at:number;engine_event_time_ns:string;source_open:number;source_close:number;primary_open:number;primary_close:number;outputs:Record<Output,boolean|null>}};
type Page={version:number;run_id:string;status:string;detail:string;notice:string;scope_notice:string;rows:Evaluation[];offset:number;next:number|null;total:number;identity?:string;snapshot_sha256?:string;graph?:{outputs:Record<Output,string|null>;nodes:unknown[]};header?:{status:string;reason:string|null;observed:number;recorded:number;omitted:number;metadata_bytes:number}};
const utc=(time:number)=>new Date(time*1000).toISOString().replace('T',' ').replace('.000Z',' UTC');
const valueText=(value:unknown)=>value===null?'Unknown (null)':value===true?'True':value===false?'False':String(value);

function Journal({runId}:{runId:string}){
  const [open,setOpen]=useState(false),[pending,setPending]=useState(false),[page,setPage]=useState<Page|null>(null),[error,setError]=useState('');
  const owner=useRef({alive:true,generation:0}),controller=useRef<AbortController|null>(null),identity=useRef<string|null>(null),history=useRef<number[]>([]);
  const request=useRef({offset:0,history:[] as number[]});
  useEffect(()=>{owner.current.alive=true;return()=>{owner.current.alive=false;owner.current.generation++;controller.current?.abort();};},[]);
  async function read(offset=0,previous:number[]=[]){
    const generation=++owner.current.generation;controller.current?.abort();controller.current=new AbortController();
    request.current={offset,history:previous};setOpen(true);setPending(true);setPage(null);setError('');
    const current=()=>owner.current.alive&&generation===owner.current.generation;
    try{
      const result=await api<Page>('run_evaluation_page',{run_id:runId,offset,limit:25,expected_identity:identity.current},{signal:controller.current.signal});
      if(!current())return;
      if(result.version!==1||result.run_id!==runId||result.offset!==offset||!Array.isArray(result.rows))throw Error('Evaluation response does not match this run and page.');
      if(result.status==='available'){
        const end=offset+result.rows.length;
        if(typeof result.identity!=='string'||!/^[a-f0-9]{64}$/.test(result.identity)||!/^[a-f0-9]{64}$/.test(result.snapshot_sha256??'')||!result.header||!result.graph||!Number.isSafeInteger(result.total)||result.total<end
          ||result.rows.some((row,i)=>row.evaluation_evidence?.ordinal!==offset+i)
          ||result.next!==null&&result.next!==offset+result.rows.length
          ||(result.next===null)!==(end===result.total)
          ||result.next!==null&&result.next<=offset||identity.current&&identity.current!==result.identity)throw Error('Evaluation response identity or cursor changed. Reopen the journal.');
        identity.current=result.identity;history.current=previous;
      }else if(result.rows.length)throw Error('Unavailable evaluation response contains unexpected rows.');
      setPage(result);
    }catch(e){if(current())setError(e instanceof Error?e.message:String(e));}
    finally{if(current())setPending(false);}
  }
  function close(){owner.current.generation++;controller.current?.abort();setOpen(false);setPending(false);setPage(null);setError('');identity.current=null;history.current=[];}
  return <section className="run-evaluations" aria-label="Recorded graph evaluations">
    <h3>Recorded graph evaluations</h3>
    <p>Review values observed during this run. This run-level journal does not explain an individual trade, order or fill.</p>
    {!open?<button onClick={()=>void read()}>Read recorded evaluations</button>:<>
      <button onClick={close}>Close evaluation journal</button>
      {pending&&<p role="status">Reading a bounded page of saved evaluations…</p>}
      {error&&<p role="alert">{error} <button onClick={()=>void read(request.current.offset,request.current.history)}>Retry evaluations</button></p>}
      {page&&<>
        <p className={page.status==='invalid'?'assumption':''} role={page.status==='invalid'?'alert':undefined}>{page.detail}</p>
        {page.status!=='available'?<p>{page.scope_notice}</p>:<>
          <p className="assumption">{page.notice} Output levels can remain true without a new entry. Stops, liquidation, end-of-run closing and partial reductions are not graph evaluations.</p>
          <p>{page.header!.status==='complete'?`All ${page.header!.recorded} eligible closed-bar evaluations have recorded metadata.`:`Incomplete metadata: ${page.header!.recorded} of ${page.header!.observed} evaluations retained; ${page.header!.omitted} omitted. ${page.header!.status==='recording_failed'?'Recording stopped after an instrumentation failure.':'The recording limit was reached.'}`}
            {' '}The limits cover added metadata only: 10,000 annotations or 4 MiB, plus a small completion record. Existing simulation and indicator memory is not capped by this journal.</p>
          {!page.header!.observed&&<p>No complete eligible primary candle produced an evaluation. This is a recorded empty journal, not missing historical evidence.</p>}
          <p>Graph availability uses the candle close. The engine event clock is close minus one nanosecond under the saved simulation contract. These are different clocks; no fill association is inferred.</p>
          {page.rows.map(row=><details key={row.evaluation_evidence.ordinal} className="evaluation-row">
            <summary>Evaluation {row.evaluation_evidence.ordinal+1} · {utc(row.evaluation_evidence.observed_at)}</summary>
            <dl className="evaluation-clocks">
              <div><dt>Observed source candle</dt><dd>{utc(row.evaluation_evidence.source_open)} → {utc(row.evaluation_evidence.source_close)}</dd></div>
              <div><dt>Completed primary candle</dt><dd>{utc(row.evaluation_evidence.primary_open)} → {utc(row.evaluation_evidence.primary_close)}</dd></div>
              <div><dt>Engine event time · exact nanoseconds</dt><dd>{row.evaluation_evidence.engine_event_time_ns}</dd></div>
            </dl>
            <div className="table-scroll"><table><thead><tr><th>Graph output</th><th>Saved reference</th><th>Observed condition</th><th>Signal level</th></tr></thead><tbody>{outputs.map(key=><tr key={key}><td>{key.replaceAll('_',' ')}</td><td>{page.graph!.outputs[key]??'Not connected'}</td><td>{page.graph!.outputs[key]===null?'Not connected':valueText(row.evaluation_evidence.outputs[key])}</td><td>{valueText(row.signals[key])}</td></tr>)}</tbody></table></div>
            <details><summary>Observed node values</summary><div className="table-scroll"><table><thead><tr><th>Node output</th><th>Recorded value</th></tr></thead><tbody>{Object.entries(row.values).map(([key,value])=><tr key={key}><td>{key}</td><td>{valueText(value)}</td></tr>)}</tbody></table></div></details>
          </details>)}
          <div className="pagination"><button disabled={!history.current.length} onClick={()=>void read(history.current.at(-1)!,history.current.slice(0,-1))}>Previous evaluations</button><span>{page.rows.length?page.offset+1:0}–{page.offset+page.rows.length} of {page.total} recorded</span><button disabled={page.next===null} onClick={()=>void read(page.next!,[...history.current,page.offset])}>Next evaluations</button></div>
          <details><summary>Original graph and snapshot identity</summary><p className="evaluation-hash">Snapshot SHA-256: {page.snapshot_sha256}</p><p>Definitions are from the original immutable run snapshot. No current editor values or formulas are substituted.</p><pre>{JSON.stringify(page.graph,null,2)}</pre></details>
        </>}
      </>}
    </>}
  </section>;
}

export default function RunEvaluations({runId}:{runId:string}){
  // Keyed ownership also protects isolated rerenders, not only the Results tab.
  return <Journal key={runId} runId={runId}/>;
}
