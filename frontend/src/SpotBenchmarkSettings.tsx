import {useEffect,useState} from 'react';
import {api} from './api';
import type {Profile} from './model';

export const spotConstraints=['tick_size','quantity_step','min_quantity','max_quantity','min_notional','max_notional'] as const;
const labels:Record<string,string>={tick_size:'Tick size',quantity_step:'Quantity step',min_quantity:'Minimum quantity',max_quantity:'Maximum quantity',min_notional:'Minimum notional',max_notional:'Maximum notional'};
export type SpotDraft={datasetId:string;key:string;value:any|null};
export function buildSpotBenchmark(strategy:Profile,fields:Record<string,string>,assumptions:any,path='OLHC'){
 const minutes=Number(strategy.execution_minutes??1);
 return {version:1,profile:{market:'spot',symbol:strategy.symbol,capital:String(strategy.capital),leverage:'1',
  sizing:'percent',allocation:'100',fee_rate:fields.fee_rate,slippage:fields.slippage,
  ...Object.fromEntries(spotConstraints.map(key=>[key,fields[key]])),stop_loss:'0',take_profit:'0',maintenance_rate:'0',
  primary_minutes:minutes,...(minutes===1?{}:{execution_minutes:minutes}),evaluation:'closed',path,
  funding_mode:'assumed_zero',mark_mode:'last_proxy',gap_policy:'reject',
  tier_assumption:'Unleveraged passive spot account; no funding or margin',version:1},assumptions};
}

export function PassiveAssumptions({rows,label='Frozen passive execution settings'}:{rows:any[];label?:string}){
 const row=rows?.find(r=>r.kind==='benchmark'&&r.contract);
 if(!row)return <p>{label}: N/A. Spot comparisons unavailable; strategy tests can still run.</p>;
 const p=row.contract.profile,a=row.contract.execution_assumptions;
 return <section aria-label={label} className="comparison-contract"><strong>{label}</strong>
  <p>{row.contract.source} · {p.symbol} · spot · {p.capital} USDT · leverage 1<br/>
  Fee {Number(p.fee_rate)*100}% (fraction {p.fee_rate}) · slippage {Number(p.slippage)*100}% (fraction {p.slippage}) per fill · {p.path} modeled path<br/>
  Precision / limits: {spotConstraints.map(key=>`${labels[key]} ${p[key]}`).join(' · ')}<br/>
  {a?`Fee origin: ${a.fee_source}. Slippage origin: ${a.slippage_source}. ${a.fee_note}`:'Legacy contract: cost and precision provenance was not recorded separately.'}<br/>
  {a&&`Precision origin: ${a.precision_source}. ${a.precision_note}`}</p>
  <p>Same evaluation-start capital and dates; unused cash retained; full close with costs. Passive spot alternatives are not leverage/risk equivalent.</p>
 </section>;
}

export default function SpotBenchmarkSettings({datasetId,strategy,onChange}:{datasetId:string;strategy:Profile;onChange:(draft:SpotDraft)=>void}){
 const [fields,setFields]=useState<Record<string,string>>({}),[source,setSource]=useState('dataset_metadata');
 const [note,setNote]=useState(''),[costNote,setCostNote]=useState(''),[feeSource,setFeeSource]=useState('explicit_spot'),[slippageSource,setSlippageSource]=useState('explicit_spot');
 const [loading,setLoading]=useState(false),[error,setError]=useState(''),[reviewed,setReviewed]=useState(false),[path,setPath]=useState('OLHC');
 useEffect(()=>{let current=true;setReviewed(false);setFields({});setNote('');setError('');setSource('dataset_metadata');setLoading(false);
  if(!datasetId)return;setLoading(true);
  api<any>('dataset_profile',{dataset_id:datasetId}).then(value=>{if(!current)return;
   if(typeof value?.tier_assumption!=='string'||!spotConstraints.every(key=>typeof value?.[key]==='string'||typeof value?.[key]==='number'))throw Error('Spot metadata is incomplete. Review manual constraints or leave passive comparisons unavailable.');
   setFields(old=>({...old,...Object.fromEntries(spotConstraints.map(key=>[key,String(value[key])]))}));setNote(value.tier_assumption);
  }).catch(e=>{if(current)setError(String(e instanceof Error?e.message:e));}).finally(()=>{if(current)setLoading(false);});
  return()=>{current=false;};
 },[datasetId]);
 const complete=!!datasetId&&!loading&&[...spotConstraints,'fee_rate','slippage'].every(key=>fields[key]?.trim())&&!!note.trim()&&!!costNote.trim();
 const assumptions={version:1,fee_source:feeSource,fee_note:costNote,slippage_source:slippageSource,precision_source:source,precision_note:note};
 const value=complete&&reviewed?buildSpotBenchmark(strategy,fields,assumptions,path):null;
 const key=JSON.stringify([datasetId,fields,assumptions,reviewed,path,loading,strategy.symbol,strategy.capital,strategy.execution_minutes]);
 useEffect(()=>{onChange({datasetId,key,value});},[key]);
 function update(key:string,text:string){setFields(v=>({...v,[key]:text}));setReviewed(false);if(key==='fee_rate')setFeeSource('explicit_spot');if(key==='slippage')setSlippageSource('explicit_spot');}
 return <section aria-label="Independent spot settings"><h4>Independent spot settings</h4>
 <p>Spot costs and order limits are separate from the strategy. Enter fee and slippage in percent, e.g. 0.1 means 0.1%. Saved contracts retain fractions.</p>
 {loading&&<p role="status">Loading spot instrument settings…</p>}{error&&<p className="warning-text">{error}</p>}
 {['fee_rate','slippage'].map(key=><label className="field" key={key}>{key==='fee_rate'?'Spot fee (%)':'Spot slippage (%)'}<input aria-label={key==='fee_rate'?'Spot fee (%)':'Spot slippage (%)'} type="number" min="0" max="99.999999" step="any" value={fields[key]?.trim()?Number(fields[key])*100:''} onChange={e=>update(key,e.target.value===''?'':String(Number(e.target.value)/100))}/></label>)}
 <button type="button" disabled={!datasetId||loading} onClick={()=>{setFields(v=>({...v,fee_rate:String(strategy.fee_rate),slippage:String(strategy.slippage)}));setFeeSource('explicit_shared');setSlippageSource('explicit_shared');setCostNote('Explicitly copied numerical strategy fee and slippage assumptions; frozen independently at review.');setReviewed(false);}}>Copy strategy cost assumptions explicitly</button>
 <label className="field">Spot cost assumption note<input aria-label="Spot cost assumption note" maxLength={1000} value={costNote} onChange={e=>{setCostNote(e.target.value);setReviewed(false);}}/></label>
 <details><summary>Spot precision and order limits</summary><label>Spot precision source<select aria-label="Spot precision source" disabled={loading} value={source} onChange={e=>{setSource(e.target.value);setNote('');setReviewed(false);}}><option value="dataset_metadata" disabled={source==='reviewed_manual'}>Loaded dataset metadata</option><option value="reviewed_manual">Reviewed manual modeling assumption</option></select></label>
 {spotConstraints.map(key=><label className="field" key={key}>{labels[key]}<input aria-label={`Spot ${labels[key].toLowerCase()}`} readOnly={source==='dataset_metadata'} value={fields[key]??''} onChange={e=>update(key,e.target.value)}/></label>)}
 <label className="field">Spot precision assumption note<textarea aria-label="Spot precision assumption note" maxLength={1000} value={note} readOnly={source==='dataset_metadata'} onChange={e=>{setNote(e.target.value);setReviewed(false);}}/></label>
 <p>Current instrument metadata is a modeling assumption projected over history, not proof of historical exchange rules. Manual limits require an explicit review note.</p>
 <label>Spot modeled path<select aria-label="Spot modeled path" value={path} onChange={e=>{setPath(e.target.value);setReviewed(false);}}><option>OLHC</option><option>OHLC</option></select></label></details>
 <label><input type="checkbox" aria-label="Review independent spot assumptions" disabled={!complete} checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>I reviewed these independent spot costs, precision and order limits</label>
 {!value&&<p>Spot comparisons unavailable; strategy tests can still run.</p>}
 </section>;
}
