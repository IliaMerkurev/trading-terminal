import {alertTime} from './AlertSession';
import {truthLabel, type HistoryRow} from './alertResearch';
import type {AgreementDistribution, AgreementResult} from './indicatorAgreement';
import {agreementGroups, agreementWarning} from './agreementAlert';

const directions = ['up','down','neutral'] as const;
const label = (value:string) => value[0].toUpperCase()+value.slice(1);
export type SavedAgreementCondition = {
 index:number; predicate:'agreement'; kind:'state'; truth:boolean|null; reason:string;
 agreement:AgreementResult;
 threshold:{direction:'up'|'down';threshold:number;required_groups:string[];overall_pass:boolean|null;group_pass:Record<string,boolean|null>;truth:boolean|null;reason:string};
};
const distributionText=(value:AgreementDistribution|null|undefined)=>value
 ? directions.map(direction=>`${label(direction)} ${value.percentages[direction]}%`).join(' · ')
 : 'Unknown (unavailable, not neutral)';
// Presentation consumes saved distributions/verdicts verbatim. It never calls an
// evaluator, derives a vote from current ports, or recomputes threshold truth.
export function AgreementTimeline({rows,conditionIndex,selectedIndex,onSelect}:{rows:HistoryRow[];conditionIndex:number;selectedIndex:number|null;onSelect:(row:HistoryRow)=>void}) {
 return <section aria-label="Saved agreement timeline" className="saved-agreement-timeline">
  <h4>Saved agreement timeline · condition {conditionIndex+1}</h4>
  <p>{agreementWarning} Every returned candle is selectable, including nonhits. Up / Down / Neutral are saved shares; striped ? is Unknown. State T / F / ? is this condition's saved truth; ● is a new rule match; ◆ is opposing group-majority conflict. A True state is not itself a new event.</p>
  <div className="agreement-timeline-scroll" tabIndex={0} aria-label="Scrollable four-lane saved timeline">
   <div className="agreement-timeline-lane"><strong>State / event</strong>{rows.map(row=>{
    const condition=row.evaluation.conditions[conditionIndex] as SavedAgreementCondition|undefined;
    return <span className="agreement-timeline-state" key={row.row_index} title={`Row ${row.row_index+1}: condition ${truthLabel(condition?.truth)}, new rule match ${row.evaluation.hit?'Yes':'No'}, conflict ${condition?.agreement?.group_conflict?'Yes':'No'}`}>
     <span>{condition?.truth===true?'T':condition?.truth===false?'F':'?'}</span><span className="agreement-hit">{row.in_range&&row.evaluation.hit?'●':'·'}</span><span className="agreement-conflict">{condition?.agreement?.group_conflict?'◆':'·'}</span>
    </span>;
   })}</div>
   {(['overall',...agreementGroups] as const).map(lane=><div className="agreement-timeline-lane" key={lane} aria-label={`${label(lane)} timeline lane`}><strong>{label(lane)}</strong>{rows.map(row=>{
    const result=(row.evaluation.conditions[conditionIndex] as SavedAgreementCondition|undefined)?.agreement;
    const distribution=lane==='overall'?result?.overall:result?.groups.find(group=>group.group===lane)?.distribution;
    const title=`${label(lane)} · row ${row.row_index+1} · confirmed CLOSE ${alertTime(row.evaluation.confirmed_at)} · raw OPEN ${alertTime(row.evaluation.raw_open_time)} · ${distributionText(distribution)}`;
    return <button key={row.row_index} type="button" className={`agreement-timeline-cell${distribution?'':' agreement-timeline-unknown'}`} aria-label={title} title={title} aria-pressed={selectedIndex===row.row_index} onClick={()=>onSelect(row)}>
     {distribution?directions.map(direction=><span aria-hidden="true" key={direction} className={`saved-share-${direction}`} style={{height:`${distribution.percentages[direction]}%`}}/>):<span aria-hidden="true">?</span>}
    </button>;
   })}</div>)}
   <div className="agreement-timeline-lane agreement-timeline-axis"><strong>Raw OPEN UTC</strong>{rows.map((row,index)=><span key={row.row_index}>{index===0||index===rows.length-1||index%10===0?new Date(row.candle.time*1000).toISOString().slice(11,16):''}</span>)}</div>
  </div>
  <p className="saved-agreement-legend"><span className="saved-share-up">Up</span><span className="saved-share-down">Down</span><span className="saved-share-neutral">Neutral</span><span className="agreement-timeline-unknown">? Unknown</span><span>● New rule match</span><span>◆ Group conflict</span></p>
 </section>;
}

function Distribution({value}:{value:AgreementDistribution|null|undefined}) {
 return <span>{distributionText(value)}{value&&<small> · exact fractions: {directions.map(direction=>`${label(direction)} ${value.exact[direction].join('/')}`).join(' · ')}</small>}</span>;
}
export function SavedAgreementEvidence({condition}:{condition:SavedAgreementCondition}) {
 const result=condition.agreement,threshold=condition.threshold;
 if(!result||!threshold)return <p role="alert">Saved agreement evidence is unavailable. No current-panel result is substituted.</p>;
 return <section aria-label={`Saved agreement condition ${condition.index+1} evidence`} className="saved-agreement-evidence">
  <h5>Agreement condition {condition.index+1} · saved verdict {truthLabel(condition.truth)}</h5>
  <p>Raw OPEN {alertTime(result.open_time)} · confirmed CLOSE {alertTime(result.close_time)} · native interval {result.interval_seconds} seconds ({result.interval_seconds/60}m).</p>
  <p>Overall: <Distribution value={result.overall}/></p>
  <p>Group conflict: {result.group_conflict?'Yes. Opposing groups have strict directional majorities.':'No opposing directional majorities.'} Conflict is separate from a new match.</p>
  <p>Coverage: {result.coverage.fully_covered_types}/{result.coverage.total_types} fully covered types · {result.coverage.available_types} available types · {result.coverage.available_variants}/{result.coverage.total_variants} available parameter variants · {result.coverage.available_groups}/3 available groups.</p>
  <ul>{agreementGroups.map(name=>{const group=result.groups.find(group=>group.group===name);return <li key={name}>{label(name)}: <Distribution value={group?.distribution}/> · {group?.available_types??0}/{group?.total_types??0} types available</li>;})}</ul>
  <p>Saved threshold verdict: {truthLabel(threshold.truth)} · {label(threshold.direction)} ≥ {threshold.threshold} fraction (0–1), inclusive on unrounded shares. Overall pass: {truthLabel(threshold.overall_pass)}. Required groups: {threshold.required_groups.join(', ')||'none; no separate group requirement'}. Each required group must be strictly &gt;50%.</p>
  {threshold.required_groups.length>0&&<p>Saved required-group passes: {threshold.required_groups.map(group=>`${label(group)} ${truthLabel(threshold.group_pass[group])}`).join(' · ')}.</p>}
  <p>Saved reasons: {condition.reason} · {threshold.reason}{result.reasons.length?` · ${result.reasons.join(', ')}`:''}.</p>
  <details><summary>Saved members, types, variants and contracts</summary>
   <p>{result.version} · {result.weight_version} · manifest SHA-256 {result.manifest_hash}</p>
   <ul>{result.members.map(member=><li key={member.id}><strong>{member.id} · {member.type} · {member.group??'no group'} · {member.status==='unavailable'?'Unknown':label(member.status)}</strong><p>Normalized parameters: {JSON.stringify(member.params)}. Consumed values: {JSON.stringify(member.values)}. Saved reason: {member.reason}.</p></li>)}</ul>
   <p>Full saved condition verdict, type/variant distributions, exclusions and consumed values:</p><pre>{JSON.stringify(condition,null,2)}</pre>
  </details>
 </section>;
}
