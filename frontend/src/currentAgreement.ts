/** Current-only caller boundary for the accepted pure agreement evaluator.
 * No requests, formulas, historical lookup, cursor or synthetic price inputs. */
import {agreementManifest, agreementVariantKey, prepareAgreement, type AgreementResult} from './indicatorAgreement';
import type {IndicatorSettings} from './ChartIndicators';
import type {LiveCandle} from './liveChartData';
import {displayIntervals} from './liveChartData';
import type {IndicatorResponseReceipt} from './useChartIndicators';

export interface CurrentAgreementInput {
  source: string; market: string; symbol: string; minutes: number; windowEpoch: number;
  priceStyle: 'candles' | 'heikin_ashi' | 'line';
  settings: IndicatorSettings; rows: LiveCandle[]; response: any;
  receipt: IndicatorResponseReceipt | null; rawSnapshotKey: string;
  active: boolean; fresh: boolean; historical: boolean; loading: boolean;
  loaded: boolean; saving: boolean; error: string;
}
export interface CurrentAgreementState {result: AgreementResult | null; reason: string}
const manifest = agreementManifest();
const confirmed = new Set<string>(manifest.raw_contract.confirmed);
const stamp = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 && value <= 253402300799;
const unavailable = (reason: string): CurrentAgreementState => ({result: null, reason});
const memberIdentity = (settings: IndicatorSettings) => JSON.stringify(settings.instances.map(item =>
  [item.id, item.visible, agreementVariantKey(item.type, item.params)]).sort((a, b) => String(a[0]).localeCompare(String(b[0]))));

export function currentAgreement(input: CurrentAgreementInput): CurrentAgreementState {
  const {rows, response, receipt, settings, minutes} = input;
  // Stop before preparing or evaluating a historical/stale snapshot.
  if (input.historical) return unavailable('Historical buffer. Return to latest to see current agreement.');
  if (!input.active) return unavailable('Chart inactive. Current agreement is paused.');
  if (!input.fresh) return unavailable('Market feed paused or stale. Waiting for fresh data.');
  if (input.saving) return unavailable('Applying settings. Waiting for the saved revision.');
  if (input.error) return unavailable('Chart or indicator error. Current agreement is unavailable.');
  if (input.loading || !input.loaded) return unavailable('Loading the current chart and applied settings.');
  if (!rows.length) return unavailable('No raw candles available.');
  if (!response || response.status === 'calculating' || response.status === 'empty') return unavailable('Waiting for the matching display calculation.');
  const mismatch = () => unavailable('Snapshot mismatch. Waiting for matching raw candles, applied settings and display output.');
  try {
    const width = minutes * 60;
    if (!displayIntervals.some(value => value === minutes) || response.status !== 'ready' || response.error || response.settings?.warning
      || !receipt || receipt.response !== response || receipt.responseRevision !== response.revision
      || typeof response.revision !== 'string' || !/^[a-f0-9]{64}$/.test(response.revision)
      || receipt.origin !== JSON.stringify(response.origin)
      || receipt.requestKey !== JSON.stringify([input.source, input.market, input.symbol, minutes, input.priceStyle])
      || receipt.windowEpoch !== input.windowEpoch || receipt.settingsRevision !== settings.revision
      || !Number.isSafeInteger(settings.revision) || settings.revision < 0
      || !Number.isSafeInteger(receipt.generation) || receipt.generation < 1
      || !Number.isSafeInteger(receipt.calculationEpoch) || receipt.calculationEpoch < 1
      || receipt.rawSnapshotKey !== input.rawSnapshotKey || input.rawSnapshotKey !== JSON.stringify(rows)) return mismatch();
    if (rows.some(row => row.confirmation === 'conflict' || (row as LiveCandle & {conflict?: boolean}).conflict === true)) return unavailable('Raw candle conflict. Current agreement is unavailable.');
    if (rows.some((row, index) => !stamp(row.time) || row.time % width || !stamp(row.time + width)
      || index > 0 && row.time <= rows[index - 1].time)) return mismatch();
    const origin = response.origin, applied = response.settings;
    if (!origin || !stamp(origin.time) || origin.time % width || origin.time > rows.at(-1)!.time || !Number.isSafeInteger(origin.generation) || origin.generation < 1
      || origin.contract !== 'native-close-engine-seeds-v1' || applied?.version !== 1
      || applied.revision !== settings.revision || memberIdentity(applied) !== memberIdentity(settings)
      || ['time', 'generation', 'contract'].some(key => applied.origins?.[String(minutes)]?.[key] !== origin[key])) return mismatch();
    // Origins may be established/reanchored without changing the applied member revision.
    // The accepted response's settings owns that origin; both existing output envelopes
    // must attest the same context, generation, requested range and close horizon.
    const expected = {source: input.source, market: input.market, symbol: input.symbol, minutes,
      start: rows[0].time, end: rows.at(-1)!.time, settings_revision: settings.revision,
      generation: origin.generation, origin: origin.time};
    const projections = response.projections, events = response.indicator_events;
    if (projections?.version !== 1 || projections.contract !== 'ichimoku-raw-ordinal-v1'
      || events?.version !== 1 || events.contract !== 'confirmed-vmc-events-v1'
      || [projections, events].some(envelope => envelope.horizon !== expected.end + width
        || Object.entries(expected).some(([key, value]) => envelope.context?.[key] !== value))
      || JSON.stringify(projections.raw_times) !== JSON.stringify(rows.map(row => row.time + width))) return mismatch();
    if (!Array.isArray(response.times) || response.times.some((time: unknown, index: number) => !stamp(time)
      || time % width || time < expected.start + width || time > expected.end + width
      || index > 0 && time <= response.times[index - 1])
      || !response.columns || typeof response.columns !== 'object' || Array.isArray(response.columns)) return mismatch();
    for (const ports of Object.values(response.columns)) {
      if (!ports || typeof ports !== 'object' || Array.isArray(ports)
        || Object.values(ports).some(values => !Array.isArray(values) || values.length !== response.times.length)) return mismatch();
    }
    // Select the exact newest confirmed raw close even if its output is missing.
    // Never walk back to an older close because its indicators happen to be ready.
    const target = [...rows].reverse().find(row => confirmed.has(row.confirmation ?? ''));
    if (!target) return unavailable('No confirmed raw close available.');
    const prepared = prepareAgreement({instances: settings.instances,
      candles: rows.map(row => ({...row, confirmation: row.confirmation ?? 'legacy_unknown'})),
      display: {times: response.times, columns: response.columns}, interval_seconds: width});
    return {result: prepared.evaluate(target.time + width), reason: ''};
  } catch {
    return mismatch();
  }
}

// Text describes the shared manifest rules. It does not calculate directions or
// maintain a second type/group/threshold mapping.
export function agreementRuleDescription(type: string): string {
  const rules = manifest.rules as Record<string, {classification: string; reason?: string; rule?: string; ports?: string[];
    lower?: number; upper?: number; up?: number; down?: number; adx_neutral_below?: number; guard?: string | null}>;
  const rule = Object.hasOwn(rules, type) ? rules[type] : null;
  if (!rule) return 'Directional rule unsupported in this version.';
  if (rule.classification !== 'directional') return rule.reason ?? 'No directional rule.';
  const port = rule.ports?.[0];
  const descriptions: Record<string, string> = {
    raw_close_compare: `Raw close above ${port}: up; below: down; equal: neutral.`,
    signed_direction: `${port} ${rule.up}: up; ${rule.down}: down; other values: unavailable.`,
    adx_di: `ADX below ${rule.adx_neutral_below}: neutral; otherwise compare +DI with −DI; equal: neutral.`,
    adjacent_change: `${port} above the immediately preceding confirmed close's value: up; below: down; equal: neutral.`,
    inclusive_neutral_band: `${port} above ${rule.upper}: up; below ${rule.lower}: down; inclusive band: neutral.`,
  };
  return (descriptions[rule.rule!] ?? 'Directional rule unavailable.') + (rule.guard && rule.guard !== 'adjacent_confirmed'
    ? ' A complete contiguous raw window is required; a flat window is neutral.' : '');
}
export function agreementClassification(type: string): {classification: string; reason?: string} {
  return Object.hasOwn(manifest.rules, type) ? manifest.rules[type as keyof typeof manifest.rules] : {classification: 'unsupported', reason: 'Unknown indicator type'};
}
