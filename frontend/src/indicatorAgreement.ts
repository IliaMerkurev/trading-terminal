/** Pure description of existing display outputs. Callers must validate the
 * source/revision/origin/window/generation/freshness envelope; see ADR 0057.
 * No formula engine, UI policy, alert transitions, persistence or IO lives here.
 */
import document from '../../terminal/indicator_agreement_v1.json';

export type Direction = 'up' | 'down' | 'neutral';
export type Group = 'trend' | 'momentum' | 'volume';
type Scalar = number | string | boolean | null;
export type Params = Record<string, Scalar>;
export type MemberStatus = Direction | 'unavailable' | 'hidden' | 'context' | 'unsupported';
export interface AgreementMember {id: string; type: string; params: Params; visible: boolean}
export interface RawAgreementCandle {time: number; confirmation: string; open: number; close: number; high: number; low: number; conflict?: boolean}
export interface AgreementSnapshot {
  instances: AgreementMember[];
  candles: RawAgreementCandle[];
  display: {times: number[]; columns: Record<string, Record<string, (number | null)[]>>};
  interval_seconds: number;
}
export interface AgreementInput extends AgreementSnapshot {close_time: number}
interface Rule {
  classification: 'directional' | 'context' | 'unsupported';
  group?: Group; reason?: string; rule?: string; ports?: string[]; parameters?: string[];
  lower?: number; upper?: number; up?: number; down?: number; adx_neutral_below?: number; guard?: string | null;
}
const manifest = document;
const rules = manifest.rules as Record<string, Rule>;
const directions = manifest.directions as Direction[];
const groups = manifest.groups as Group[];
const closed = new Set(manifest.raw_contract.confirmed);
export const AGREEMENT_VERSION = manifest.version;
export const AGREEMENT_WEIGHT_VERSION = manifest.weight_version;
// Pinned SHA-256 of sorted-key, compact ASCII JSON; tests rehash the shared file.
export const AGREEMENT_MANIFEST_HASH = '74cc8337a2e60f56719fc584decb79427609be58450c582d3c72f512355651ff';
export const agreementManifest = () => structuredClone(manifest);

const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
const integer = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value);
export function normalizeAgreementParams(params: Params): Params {
  if (!params || typeof params !== 'object' || Array.isArray(params)) throw new Error('Agreement parameters must be an object');
  const result: Params = {};
  for (const key of Object.keys(params).sort(lexical)) {
    const value = params[key];
    if (value !== null && typeof value !== 'string' && typeof value !== 'boolean' && !(finite(value) && Math.abs(value) <= Number.MAX_SAFE_INTEGER)) {
      throw new Error('Agreement parameters must be finite JSON scalars with safe numbers');
    }
    Object.defineProperty(result, key, {value: typeof value === 'number' && value === 0 ? 0 : value, enumerable: true});
  }
  return result;
}
export function agreementVariantKey(kind: string, params: Params): string {
  const normalized = normalizeAgreementParams(params);
  const tokens = Object.entries(normalized).map(([key, value]) => {
    let token: [string, Scalar];
    if (typeof value === 'number') {
      const data = new DataView(new ArrayBuffer(8));
      data.setFloat64(0, value, false);
      token = ['number', Array.from(new Uint8Array(data.buffer), n => n.toString(16).padStart(2, '0')).join('')];
    } else token = [value === null ? 'null' : typeof value, value];
    return [key, token];
  });
  return JSON.stringify([kind, tokens]);
}
function checkParams(kind: string, params: Params, rule: Rule) {
  if (rule.classification !== 'directional') return;
  if (JSON.stringify(Object.keys(params).sort(lexical)) !== JSON.stringify([...rule.parameters!].sort(lexical))) throw new Error('Agreement directional parameters do not match the manifest');
  for (const [key, value] of Object.entries(params)) {
    if (['step', 'max'].includes(key)) {
      if (!finite(value) || !(value > 0 && value <= 1)) throw new Error('Invalid SAR parameter');
    } else if (['deviations', 'multiplier'].includes(key)) {
      if (!finite(value) || !(value > 0 && value <= 10)) throw new Error('Invalid band parameter');
    } else if (key === 'mode') {
      if (!integer(value) || ![0, 1].includes(value)) throw new Error('Invalid VWAP mode');
    } else if (key === 'anchor') {
      if (!integer(value) || value < 0 || value > 253402300799) throw new Error('Invalid VWAP anchor');
    } else if (!integer(value) || value < 1 || value > 1000) throw new Error('Invalid indicator period');
  }
  if (kind === 'sar' && Number(params.step) > Number(params.max)) throw new Error('Invalid SAR step');
  if (kind === 'vwap' && params.mode === 0 && params.anchor !== 0) throw new Error('Invalid day VWAP anchor');
  if (kind === 'macd' && Number(params.fast) >= Number(params.slow)) throw new Error('Invalid MACD periods');
}

type Rational = [bigint, bigint];
type Shares = [Rational, Rational, Rational];
const gcd = (a: bigint, b: bigint): bigint => {while (b) [a, b] = [b, a % b]; return a < 0n ? -a : a;};
function rational(n: bigint, d = 1n): Rational {const g = gcd(n, d); return [n / g, d / g];}
const add = (a: Rational, b: Rational) => rational(a[0] * b[1] + b[0] * a[1], a[1] * b[1]);
const compare = (a: Rational, b: Rational) => {const value = a[0] * b[1] - b[0] * a[1]; return value > 0n ? 1 : value < 0n ? -1 : 0;};
const mean = (rows: Shares[]): Shares => directions.map((_, i) => {
  const value = rows.reduce((total, row) => add(total, row[i]), [0n, 1n] as Rational);
  return rational(value[0], value[1] * BigInt(rows.length));
}) as Shares;
const vote = (status: MemberStatus): Shares => directions.map(d => [BigInt(status === d), 1n]) as Shares;
export interface AgreementDistribution {
  fractions: Record<Direction, number>;
  exact: Record<Direction, [string, string]>;
  percentages: Record<Direction, number>;
}
function distribution(values: Shares | null): AgreementDistribution | null {
  if (values === null) return null;
  const scaled = values.map(([n, d]) => [n * BigInt(manifest.rounding.total), d] as Rational);
  const rounded = scaled.map(([n, d]) => Number(n / d));
  const remainder = scaled.map(([n, d]) => rational(n % d, d));
  const order = [0, 1, 2].sort((a, b) => -compare(remainder[a], remainder[b]) || a - b);
  for (const i of order.slice(0, 100 - rounded.reduce((a, b) => a + b, 0))) rounded[i]++;
  return {
    fractions: Object.fromEntries(directions.map((d, i) => [d, Number(values[i][0]) / Number(values[i][1])])) as Record<Direction, number>,
    exact: Object.fromEntries(directions.map((d, i) => [d, values[i].map(String)])) as Record<Direction, [string, string]>,
    percentages: Object.fromEntries(directions.map((d, i) => [d, rounded[i]])) as Record<Direction, number>,
  };
}
interface PreparedMember extends AgreementMember {variant_key: string; rule: Rule}
export interface MemberEvidence {
  id: string; type: string; params: Params; variant_key: string; group: Group | null;
  status: MemberStatus; reason: string; values: Record<string, number | null>;
}
export interface VariantEvidence {
  key: string; type: string; group: Group; params: Params; member_ids: string[];
  status: MemberStatus; reason: string; values: Record<string, number | null>;
}
export interface TypeEvidence {
  type: string; group: Group; available_variants: number; total_variants: number;
  fully_covered: boolean; variant_keys: string[]; distribution: AgreementDistribution | null;
}
export interface GroupEvidence {
  group: Group; available_types: number; total_types: number; types: string[];
  distribution: AgreementDistribution | null;
}
export interface AgreementResult {
  version: string; weight_version: string; manifest_hash: string;
  close_time: number; open_time: number; interval_seconds: number;
  state: 'available' | 'unavailable'; reasons: string[]; overall: AgreementDistribution | null;
  groups: GroupEvidence[]; types: TypeEvidence[]; variants: VariantEvidence[]; members: MemberEvidence[];
  coverage: {fully_covered_types: number; available_types: number; total_types: number; available_variants: number; total_variants: number; available_groups: number};
  exclusions: Record<'hidden' | 'context' | 'unsupported' | 'unavailable', string[]>; group_conflict: boolean;
}
interface RawIndexed {row: RawAgreementCandle; runs: Record<string, number>; closed: boolean}
function lexical(a: string, b: string): number {
  const left = Array.from(a, c => c.codePointAt(0)!), right = Array.from(b, c => c.codePointAt(0)!);
  for (let i = 0; i < Math.min(left.length, right.length); i++) if (left[i] !== right[i]) return left[i] < right[i] ? -1 : 1;
  return left.length - right.length;
}

/** Detached indexed snapshot. Preparation is linear; flat checks use run lengths
 * rather than scanning/replaying each historical prefix. No result rows cached. */
export class PreparedAgreement {
  private readonly width: number;
  private readonly members: PreparedMember[] = [];
  private readonly raw = new Map<number, RawIndexed>();
  private readonly times = new Map<number, number>();
  private readonly columns: AgreementSnapshot['display']['columns'];
  constructor(snapshot: AgreementSnapshot) {
    const width = snapshot.interval_seconds;
    if (!integer(width) || width <= 0) throw new Error('Agreement interval must be positive integer seconds');
    this.width = width;
    const seen = new Set<string>();
    for (const item of snapshot.instances) {
      if (!item || typeof item !== 'object' || typeof item.id !== 'string' || !item.id || seen.has(item.id) || typeof item.type !== 'string' || typeof item.visible !== 'boolean') {
        throw new Error('Agreement members require unique IDs, type and explicit visibility');
      }
      seen.add(item.id);
      const params = normalizeAgreementParams(item.params);
      const rule = Object.hasOwn(rules, item.type) ? rules[item.type] : {classification: 'unsupported', reason: 'Unknown indicator type'} as Rule;
      checkParams(item.type, params, rule);
      if (item.type === 'vwap' && Number(params.anchor) % width) throw new Error('VWAP anchor must align to the raw interval');
      this.members.push({id: item.id, type: item.type, params, visible: item.visible, variant_key: agreementVariantKey(item.type, params), rule});
    }
    this.members.sort((a, b) => lexical(a.type, b.type) || lexical(a.variant_key, b.variant_key) || lexical(a.id, b.id));
    let previous: RawAgreementCandle | null = null;
    const runs = {closes: 0, flat_closes: 0, ranges: 0, flat_ranges: 0};
    for (const original of snapshot.candles) {
      const row = {...original}, stamp = row.time;
      if (!integer(stamp) || stamp < 0 || stamp % width || (previous !== null && stamp <= previous.time)) throw new Error('Agreement raw times must be aligned and strictly increasing');
      const contiguous = previous !== null && stamp === previous.time + width;
      const isClosed = closed.has(row.confirmation) && (row.conflict === undefined || row.conflict === false)
        && [row.open, row.high, row.low, row.close].every(finite)
        && row.low <= Math.min(row.open, row.close) && Math.max(row.open, row.close) <= row.high;
      const closeOk = isClosed && finite(row.close);
      const rangeOk = isClosed && finite(row.high) && finite(row.low) && row.high >= row.low;
      runs.closes = closeOk ? (contiguous ? runs.closes : 0) + 1 : 0;
      runs.flat_closes = closeOk ? (contiguous && previous?.close === row.close ? runs.flat_closes : 0) + 1 : 0;
      runs.ranges = rangeOk ? (contiguous ? runs.ranges : 0) + 1 : 0;
      runs.flat_ranges = rangeOk && row.high === row.low ? (contiguous && previous?.high === row.high ? runs.flat_ranges : 0) + 1 : 0;
      this.raw.set(stamp + width, {row, runs: {...runs}, closed: isClosed});
      previous = row;
    }
    let previousTime: number | null = null;
    snapshot.display.times.forEach((stamp, index) => {
      if (!integer(stamp) || stamp < width || stamp % width || (previousTime !== null && stamp <= previousTime)) throw new Error('Agreement output times must be aligned and strictly increasing');
      this.times.set(stamp, index);
      previousTime = stamp;
    });
    this.columns = structuredClone(snapshot.display.columns);
  }
  private value(id: string, port: string, closeTime: number): number | null {
    const index = this.times.get(closeTime);
    const item = Object.hasOwn(this.columns, id) ? this.columns[id] : undefined;
    const column = item && Object.hasOwn(item, port) ? item[port] : undefined;
    const value = index !== undefined && Array.isArray(column) ? column[index] : null;
    return finite(value) ? value : null;
  }
  private assess(item: PreparedMember, closeTime: number): MemberEvidence {
    const {rule, params} = item;
    const result: MemberEvidence = {id: item.id, type: item.type, params: {...params}, variant_key: item.variant_key,
      group: rule.group ?? null, status: 'unavailable', reason: 'target_missing', values: {}};
    if (!item.visible) return {...result, status: 'hidden', reason: 'Hidden instances do not vote'};
    if (rule.classification !== 'directional') return {...result, status: rule.classification, reason: rule.reason!};
    const current = this.raw.get(closeTime);
    if (!current) return result;
    if (!current.closed || !finite(current.row.close)) return {...result, reason: 'target_not_confirmed_or_invalid'};
    const values = Object.fromEntries(rule.ports!.map(port => [port, this.value(item.id, port, closeTime)]));
    if (rule.rule === 'adx_di' && values.adx !== null && values.adx < rule.adx_neutral_below!) return {...result, status: 'neutral', reason: 'adx_below_threshold', values: {adx: values.adx}};
    result.values = values;
    if (Object.values(values).some(value => value === null)) return {...result, reason: 'output_unavailable_at_requested_close'};
    const guard = rule.guard;
    if (['flat_closes', 'flat_range', 'flat_smoothed_range'].includes(guard ?? '')) {
      const length = Number(params.period) + (guard === 'flat_closes' ? 1 : guard === 'flat_smoothed_range' ? Number(params.smooth) - 1 : 0);
      const category = guard === 'flat_closes' ? 'closes' : 'ranges';
      result.values = {...values, guard_bars: length};
      if (current.runs[category] < length) return {...result, reason: 'raw_guard_unavailable'};
      if (current.runs['flat_' + category] >= length) return {...result, status: 'neutral', reason: 'flat_raw_window'};
    }
    const mode = rule.rule;
    let status: Direction;
    if (mode === 'raw_close_compare') {
      const left = current.row.close, right = values[rule.ports![0]]!;
      result.values = {...values, raw_close: left};
      status = left > right ? 'up' : left < right ? 'down' : 'neutral';
    } else if (mode === 'signed_direction') {
      const value = values[rule.ports![0]]!;
      if (value !== rule.up && value !== rule.down) return {...result, reason: 'invalid_direction'};
      status = value === rule.up ? 'up' : 'down';
    } else if (mode === 'adx_di') {
      status = values.plus_di! > values.minus_di! ? 'up' : values.plus_di! < values.minus_di! ? 'down' : 'neutral';
    } else if (mode === 'adjacent_change') {
      const previous = this.raw.get(closeTime - this.width), before = this.value(item.id, rule.ports![0], closeTime - this.width);
      if (!previous || !previous.closed || !finite(previous.row.close) || before === null) return {...result, reason: 'adjacent_confirmed_output_unavailable'};
      result.values = {...values, previous: before};
      const value = values[rule.ports![0]]!;
      status = value > before ? 'up' : value < before ? 'down' : 'neutral';
    } else {
      const value = values[rule.ports![0]]!;
      status = value > rule.upper! ? 'up' : value < rule.lower! ? 'down' : 'neutral';
    }
    return {...result, status, reason: mode!};
  }
  evaluate(closeTime: number): AgreementResult {
    if (!integer(closeTime) || closeTime < this.width || closeTime % this.width) throw new Error('Agreement close must align exactly to the raw interval');
    const members = this.members.map(item => this.assess(item, closeTime));
    const variantMembers = new Map<string, MemberEvidence[]>();
    for (const member of members) {
      if (member.group !== null && member.status !== 'hidden') {
        const copies = variantMembers.get(member.variant_key) ?? [];
        copies.push(member); variantMembers.set(member.variant_key, copies);
      }
    }
    const variants: VariantEvidence[] = [], byType = new Map<string, VariantEvidence[]>();
    for (const [key, copies] of variantMembers) {
      const first = copies[0];
      const same = copies.every(item => JSON.stringify([item.status, item.reason, item.values]) === JSON.stringify([first.status, first.reason, first.values]));
      const variant: VariantEvidence = {key, type: first.type, group: first.group!, params: {...first.params}, member_ids: copies.map(item => item.id),
        status: same ? first.status : 'unavailable', reason: same ? first.reason : 'duplicate_variant_conflict', values: same ? {...first.values} : {}};
      variants.push(variant);
      const rows = byType.get(first.type) ?? []; rows.push(variant); byType.set(first.type, rows);
    }
    const types: TypeEvidence[] = [], typeFractions = new Map<string, Shares | null>();
    for (const [kind, rows] of byType) {
      const available = rows.filter(row => directions.includes(row.status as Direction));
      const fractions = available.length ? mean(available.map(row => vote(row.status))) : null;
      typeFractions.set(kind, fractions);
      types.push({type: kind, group: rows[0].group, available_variants: available.length, total_variants: rows.length,
        fully_covered: available.length === rows.length, variant_keys: rows.map(row => row.key), distribution: distribution(fractions)});
    }
    const groupRows: GroupEvidence[] = [], groupFractions = new Map<Group, Shares | null>();
    for (const group of groups) {
      const rows = types.filter(row => row.group === group);
      const available = rows.map(row => typeFractions.get(row.type)!).filter((row): row is Shares => row !== null);
      const fractions = available.length ? mean(available) : null;
      groupFractions.set(group, fractions);
      groupRows.push({group, available_types: available.length, total_types: rows.length, types: rows.map(row => row.type), distribution: distribution(fractions)});
    }
    const availableGroups = [...groupFractions.values()].filter((row): row is Shares => row !== null);
    const full = types.filter(row => row.fully_covered).length;
    const minimum = manifest.coverage.minimum_fully_covered_type_fraction.map(BigInt) as Rational;
    const reasons: string[] = [];
    if (availableGroups.length < manifest.coverage.minimum_available_groups) reasons.push('insufficient_available_groups');
    if (!types.length || compare([BigInt(full), BigInt(types.length)], minimum) < 0) reasons.push('insufficient_fully_covered_types');
    const overall = reasons.length ? null : mean(availableGroups);
    const conflict = availableGroups.some(row => compare(row[0], [1n, 2n]) > 0) && availableGroups.some(row => compare(row[1], [1n, 2n]) > 0);
    return {version: AGREEMENT_VERSION, weight_version: AGREEMENT_WEIGHT_VERSION, manifest_hash: AGREEMENT_MANIFEST_HASH,
      close_time: closeTime, open_time: closeTime - this.width, interval_seconds: this.width,
      state: overall === null ? 'unavailable' : 'available', reasons, overall: distribution(overall),
      groups: groupRows, types, variants, members,
      coverage: {fully_covered_types: full, available_types: types.filter(row => row.distribution !== null).length, total_types: types.length,
        available_variants: variants.filter(row => directions.includes(row.status as Direction)).length, total_variants: variants.length, available_groups: availableGroups.length},
      exclusions: Object.fromEntries(['hidden', 'context', 'unsupported', 'unavailable'].map(status => [status, members.filter(row => row.status === status).map(row => row.id)])) as AgreementResult['exclusions'],
      group_conflict: conflict};
  }
}
export const prepareAgreement = (snapshot: AgreementSnapshot) => new PreparedAgreement(snapshot);
export const evaluateAgreement = (input: AgreementInput) => prepareAgreement(input).evaluate(input.close_time);
function decimalRational(value: number): Rational {
  const [digits, exp = '0'] = String(value).split('e');
  const [whole, fraction = ''] = digits.split('.');
  const power = Number(exp) - fraction.length;
  const numerator = BigInt(whole + fraction);
  return power >= 0 ? rational(numerator * 10n ** BigInt(power)) : rational(numerator, 10n ** BigInt(-power));
}
export function thresholdEvidence(result: AgreementResult, direction: 'up' | 'down', threshold: number, requiredGroups: Group[] = []) {
  if (!['up', 'down'].includes(direction) || !finite(threshold) || threshold < 0 || threshold > 1) throw new Error('Agreement threshold requires up/down and a finite fraction from 0 to 1');
  if (new Set(requiredGroups).size !== requiredGroups.length || requiredGroups.some(group => !groups.includes(group))) throw new Error('Agreement required groups must be distinct known groups');
  if (result.version !== AGREEMENT_VERSION || result.weight_version !== AGREEMENT_WEIGHT_VERSION || result.manifest_hash !== AGREEMENT_MANIFEST_HASH) throw new Error('Agreement result contract mismatch');
  const fraction = (value: AgreementDistribution | null): Rational | null => value === null ? null : value.exact[direction].map(BigInt) as Rational;
  const overall = fraction(result.overall);
  const values = new Map(result.groups.map(row => [row.group, fraction(row.distribution)]));
  const overallPass = overall === null ? null : compare(overall, decimalRational(threshold)) >= 0;
  const groupPass = Object.fromEntries(requiredGroups.map(group => {const value = values.get(group)!; return [group, value === null ? null : compare(value, [1n, 2n]) > 0];}));
  const unavailable = overallPass === null || Object.values(groupPass).some(value => value === null);
  return {direction, threshold, required_groups: [...requiredGroups], overall_pass: overallPass, group_pass: groupPass,
    truth: unavailable ? null : overallPass && Object.values(groupPass).every(Boolean),
    reason: unavailable ? 'agreement_unavailable' : 'exact_threshold_and_group_majorities'};
}
