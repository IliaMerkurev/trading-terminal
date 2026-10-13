import {readFrozenRule} from './frozenRule';
import type {IRNode} from './model';

export const frozenExecutionLimits='Matching Bybit source, market and symbol only; native M1, closed primary bars and M1 execution. Contiguous data must include the full frozen calculation origin. Maximum 10,000 bars and estimated 256 MiB replay memory. No reseeding, aggregation or provider fallback. Parameter experiments and live/PAPER execution are unsupported.';
function originUtc(value:unknown) {
  if(typeof value!=='number'||!Number.isSafeInteger(value))return 'Unavailable UTC timestamp';
  const date=new Date(value*1000);
  return Number.isFinite(date.getTime())?date.toISOString().replace('T',' ').replace('.000Z',' UTC'):'Unavailable UTC timestamp';
}
export default function FrozenRuleDetails({node}:{node:IRNode}) {
  const snapshot=readFrozenRule(node);
  if(!snapshot)return <p role="alert">Unsupported or malformed frozen-rule snapshot. Reopen a valid saved strategy before execution.</p>;
  const {rule,definition}=snapshot,context=definition.context;
  return <section aria-label="Frozen strategy source" className="frozen-strategy-source">
    <h3>{rule.name}</h3><p>Read-only frozen source. Editing, rebinding or archiving the saved alert never rewrites this strategy or its existing runs.</p>
    <p>Rule ID: {rule.id} · revision {rule.revision} · definition revision {rule.definition_revision}</p>
    <p>Definition SHA-256: <span className="frozen-hash">{rule.definition_hash}</span></p>
    <p>{context.source} / {context.market} / {context.symbol} / native interval {context.minutes}m</p>
    <p>Calculation origin raw OPEN: {originUtc(definition.origin?.time)} · Unix seconds: {definition.origin?.time??'Missing'} · origin contract: {definition.origin?.contract??'Missing'}</p>
    <p>{frozenExecutionLimits}</p>
    <p>Uses the original replay engine's actionable hit at each confirmed close. Unknown condition truth stays unknown; state edges, pulses, formula contracts, agreement weights and divergence confirmation timing remain frozen.</p>
    <details><summary>Exact frozen parameters and provenance</summary><pre>{JSON.stringify(snapshot,null,2)}</pre></details>
  </section>;
}
