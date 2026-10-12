import {useMemo} from 'react';
import {indicatorName} from './ChartIndicators';
import {agreementManifest, type AgreementDistribution} from './indicatorAgreement';
import {agreementClassification, agreementRuleDescription, currentAgreement, type CurrentAgreementInput} from './currentAgreement';
import './indicatorAgreement.css';

const manifest = agreementManifest();
const label = (value: string) => value.charAt(0).toUpperCase() + value.slice(1);
const utc = (time: number) => new Date(time * 1000).toISOString().replace('T', ' ').replace('.000Z', ' UTC');
const reasonText: Record<string, string> = {
  output_unavailable_at_requested_close: 'Missing output at this exact close; no older value substituted.',
  target_missing: 'The requested raw close is missing.',
  target_not_confirmed_or_invalid: 'The requested raw close is unconfirmed, invalid or conflicted.',
  raw_guard_unavailable: 'Insufficient consecutive confirmed raw candles for the flat-window check.',
  adjacent_confirmed_output_unavailable: 'The immediately preceding confirmed raw candle or its output is missing.',
  flat_raw_window: 'The complete raw window is flat: neutral.',
  adx_below_threshold: 'ADX is below the directional threshold: neutral.',
  invalid_direction: 'The existing direction output is unsupported.',
  duplicate_variant_conflict: 'Exact copies have inconsistent output; this variant is excluded.',
};
function Distribution({value, name}: {value: AgreementDistribution; name: string}) {
  return <span className="agreement-shares" aria-label={name}>{manifest.directions.map(direction =>
    <span className={`agreement-${direction}`} key={direction}>{label(direction)} {value.percentages[direction as keyof typeof value.percentages]}%</span>)}</span>;
}
export default function IndicatorAgreementPanel(props: CurrentAgreementInput) {
  const {settings, rows, response, receipt, rawSnapshotKey, source, market, symbol, minutes, priceStyle, windowEpoch,
    active, fresh, historical, loading, loaded, saving, error} = props;
  const state = useMemo(() => currentAgreement(props), [settings, rows, response, receipt, rawSnapshotKey,
    source, market, symbol, minutes, priceStyle, windowEpoch, active, fresh, historical, loading, loaded, saving, error]);
  const result = state.result;
  const evidence = new Map(result?.members.map(member => [member.id, member]));
  const variants = new Map(result?.variants.map(variant => [variant.key, variant]));
  const minimumCoverage = manifest.coverage.minimum_fully_covered_type_fraction;
  return <section className="indicator-agreement" aria-label="Current indicator agreement">
    <div className="agreement-summary"><strong>Current indicator agreement</strong>
      {result?.overall ? <Distribution value={result.overall} name="Overall agreement"/> : <span>Overall unavailable</span>}
      {result && <span>Confirmed raw close · <time dateTime={new Date(result.close_time * 1000).toISOString()}>{utc(result.close_time)}</time></span>}
    </div>
    <small className="agreement-warning">Descriptive heuristic. Percentages are not probabilities, confidence, price strength or trading advice.</small>
    {!result && <p role="status">{state.reason}</p>}
    {result && <>
      <div className="agreement-summary" aria-label="Agreement coverage"><span>Coverage: {result.coverage.fully_covered_types}/{result.coverage.total_types} fully covered supported visible types</span><span>{result.coverage.available_variants}/{result.coverage.total_variants} available parameter variants</span><span>{result.coverage.available_groups}/{manifest.groups.length} available groups</span></div>
      {!result.overall && <p role="status">Overall needs at least {manifest.coverage.minimum_available_groups} available groups and {100 * minimumCoverage[0] / minimumCoverage[1]}% fully covered supported visible types.</p>}
      <div className="agreement-groups">{result.groups.map(group => <div key={group.group}><strong>{label(group.group)}</strong>{group.distribution
        ? <Distribution value={group.distribution} name={`${label(group.group)} agreement`}/>
        : <span>Unavailable</span>}<small>{group.available_types}/{group.total_types} types available</small></div>)}</div>
      <small>Group conflict: {result.group_conflict ? 'Yes. Opposing groups have directional majorities.' : 'No opposing directional majorities.'}</small>
    </>}
    <details className="agreement-details"><summary>Agreement details · {settings.instances.length} applied instances</summary>
      <p>Only visible applied settings vote. Exact type/parameter copies count once. Available variants have equal weight within a type, types within a group, and groups overall. Neutral is a known direction and stays in the denominator. Missing, hidden, context-only and unsupported values do not vote. Coverage describes data availability. Correlated indicators are not independent evidence.</p>
      <p>Reference: the latest confirmed raw close in the recent buffer. Forming candles, chart style, cursor and panning inside that buffer do not select a different close. No fallback to older values. Draft indicator edits do not affect this summary.</p>
      {!settings.instances.length && <p>No applied indicator instances.</p>}
      <ul className="agreement-members">{settings.instances.map((item, index) => {
        const member = evidence.get(item.id), classification = agreementClassification(item.type);
        const status = member?.status ?? (!item.visible ? 'hidden' : classification.classification === 'directional' ? 'unavailable' : classification.classification);
        const variant = member ? variants.get(member.variant_key) : undefined;
        const reason = member ? reasonText[member.reason] ?? (member.status === 'up' || member.status === 'down' || member.status === 'neutral'
          ? 'Existing display output evaluated at the reference close.' : member.reason) : status === 'hidden' ? 'Hidden instances do not vote.' : classification.reason ?? state.reason;
        return <li key={item.id}><div><strong>{indicatorName(item)}</strong><span>#{index + 1} · {item.id}</span><strong className={`agreement-${status}`}>{status === 'context' ? 'Context only' : label(status)}</strong>{member?.group && <span>{label(member.group)}</span>}</div>
          <div>Parameters: {Object.entries(item.params).map(([key, value]) => `${key}=${String(value)}`).join(', ') || 'none'}</div>
          <div>{agreementRuleDescription(item.type)}</div><div>{reason}</div>
          {member && Object.keys(member.values).length > 0 && <div>Observed: {Object.entries(member.values).map(([key, value]) => `${key}=${value === null ? 'unavailable' : value}`).join(', ')}</div>}
          {variant && variant.member_ids.length > 1 && <div>{variant.member_ids.length} exact copies share one variant vote.{variant.reason === 'duplicate_variant_conflict' ? ` ${reasonText.duplicate_variant_conflict}` : ''}</div>}
        </li>;
      })}</ul>
      <small>{manifest.version} · {manifest.weight_version}</small>
    </details>
  </section>;
}
