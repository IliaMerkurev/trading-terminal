import {describe, expect, it, vi} from 'vitest';
import fixtures from '../../tests/fixtures/indicator_agreement_v1.json';
import {AGREEMENT_MANIFEST_HASH, agreementManifest, agreementVariantKey, evaluateAgreement,
  prepareAgreement, thresholdEvidence, type AgreementInput, type AgreementResult, type Group} from './indicatorAgreement';
const cases = fixtures.cases as unknown as {name: string; input: AgreementInput; expected: Record<string, any>}[];
const byName = new Map(cases.map(row => [row.name, row]));
const stringifyExact = (value: Record<string, number[]>) => Object.fromEntries(Object.entries(value).map(([d, f]) => [d, f.map(String)]));
const single = (kind = 'sma', params: Record<string, any> = {period: 2}, ports: Record<string, number | null> = {value: 100}): AgreementInput => ({
  instances: [{id: 'x', type: kind, params, visible: true}],
  candles: Array.from({length: 5}, (_, i) => ({time: i * 60, open: 100 + i, close: 100 + i, high: 101 + i, low: 99 + i, confirmation: 'synthetic_closed'})),
  display: {times: [60, 120, 180, 240, 300], columns: {x: Object.fromEntries(Object.entries(ports).map(([p, v]) => [p, Array(5).fill(v)]))}},
  interval_seconds: 60, close_time: 300,
});
const status = (input: AgreementInput) => evaluateAgreement(input).members[0].status;

describe('independently authored shared agreement vectors', () => {
  for (const test of cases) it(test.name, () => {
    const result = evaluateAgreement(test.input), expected = test.expected;
    if (expected.overall === null) expect(result.overall).toBeNull();
    else {
      expect(result.overall?.exact).toEqual(stringifyExact(expected.overall));
      expect(Object.values(result.overall!.percentages).reduce((a, b) => a + b, 0)).toBe(100);
    }
    if (expected.trend) expect(result.groups.find(row => row.group === 'trend')?.distribution?.exact).toEqual(stringifyExact(expected.trend));
    if ('group_conflict' in expected) expect(result.group_conflict).toBe(expected.group_conflict);
    for (const [expectedKey, resultKey] of [['fully_available_types','fully_covered_types'],['total_supported_types','total_types'],['available_variants','available_variants'],['total_variants','total_variants']] as const) {
      if (expectedKey in expected) expect(result.coverage[resultKey]).toBe(expected[expectedKey]);
    }
    if (expected.percentages) expect(result.overall?.percentages).toEqual(expected.percentages);
    for (const [id, direction] of Object.entries(expected.member_direction ?? {})) expect(result.members.find(row => row.id === id)?.status).toBe(direction);
    for (const id of expected.member_unavailable ?? []) expect(result.members.find(row => row.id === id)?.status).toBe('unavailable');
    expect(JSON.parse(JSON.stringify(result))).toEqual(result);
  });
  for (const test of fixtures.threshold_cases) it(test.name, () => {
    const result = evaluateAgreement(byName.get(test.result_case)!.input);
    expect(thresholdEvidence(result, test.direction as 'up' | 'down', test.threshold, test.required_groups as Group[]).truth).toBe(test.expected);
  });
});

it('pins the shared manifest SHA and returns a detached manifest', async () => {
  const {createHash} = await vi.importActual<any>('node:crypto');
  const canonical = (value: any): string => value && typeof value === 'object'
    ? Array.isArray(value) ? '[' + value.map(canonical).join(',') + ']' : '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}'
    : JSON.stringify(value);
  expect(AGREEMENT_MANIFEST_HASH).toBe('74cc8337a2e60f56719fc584decb79427609be58450c582d3c72f512355651ff');
  expect(createHash('sha256').update(canonical(agreementManifest())).digest('hex')).toBe(AGREEMENT_MANIFEST_HASH);
  expect(Object.keys(agreementManifest().rules)).toHaveLength(33);
  const changed = agreementManifest(); changed.rules.sma.group = 'volume';
  expect(agreementManifest().rules.sma.group).toBe('trend');
});

it('compares every raw-price rule against its exact existing output port', () => {
  const parameters: Record<string, Record<string, number>> = Object.fromEntries(['sma','ema','wma','rma','vwma','hma','donchian'].map(kind => [kind, {period: 2}]));
  Object.assign(parameters, {vwap: {mode: 0, anchor: 0}, sar: {step: .02, max: .2}, bb: {period: 2, deviations: 2}, keltner: {period: 2, atr_period: 2, multiplier: 2}});
  for (const [kind, params] of Object.entries(parameters)) {
    const port = ['bb','donchian','keltner'].includes(kind) ? 'middle' : 'value';
    for (const [value, expected] of [[103,'up'],[104,'neutral'],[105,'down'],[null,'unavailable'],[NaN,'unavailable'],[Infinity,'unavailable']] as const) {
      expect(status(single(kind, params, {[port]: value}))).toBe(expected);
    }
  }
});
it('uses exact Supertrend and conditional DMI ports, and sign rules', () => {
  for (const [value, expected] of [[1,'up'],[-1,'down'],[0,'unavailable'],[2,'unavailable'],[null,'unavailable']] as const) expect(status(single('supertrend', {period: 2, multiplier: 2}, {direction: value}))).toBe(expected);
  for (const [adx, plus, minus, expected] of [[19.999,null,null,'neutral'],[20,3,2,'up'],[20,2,2,'neutral'],[20.001,1,2,'down'],[20,null,2,'unavailable']] as const) expect(status(single('dmi', {period: 2, adx_period: 2}, {adx, plus_di: plus, minus_di: minus}))).toBe(expected);
  for (const kind of ['macd','roc','momentum']) for (const [value, expected] of [[-.01,'down'],[0,'neutral'],[.01,'up']] as const) expect(status(single(kind, kind === 'macd' ? {fast: 1, slow: 2, signal: 1} : {period: 2}, {[kind === 'macd' ? 'histogram' : 'value']: value}))).toBe(expected);
});
it('keeps context and unsupported types out of directional coverage', () => {
  for (const kind of ['atr','volume','stddev','bbwidth','ichimoku','stochrsi','vmc_cipher_a','vmc_cipher_b','vmc_swing','future_kind']) {
    const result = evaluateAgreement(single(kind, {}));
    expect(result.members[0].status).toBe(['atr','volume','stddev','bbwidth'].includes(kind) ? 'context' : 'unsupported');
    expect(result.coverage.total_types).toBe(0); expect(result.overall).toBeNull();
  }
});
it('normalizes numeric params and ignores appearance, with conflicts unavailable', () => {
  expect(agreementVariantKey('bb', {period: 20, deviations: 2.0})).toBe(agreementVariantKey('bb', {deviations: 2, period: 20.0}));
  expect(agreementVariantKey('vwap', {mode: 0, anchor: -0})).toBe(agreementVariantKey('vwap', {anchor: 0, mode: 0}));
  expect(agreementVariantKey('sar', {step: 1e-7, max: .2})).not.toBe(agreementVariantKey('sar', {step: 2e-7, max: .2}));
  const input = single(); input.instances.push({...input.instances[0], id: 'z'}); input.display.columns.z = {value: [100,100,100,100,100]};
  expect(evaluateAgreement(input).coverage.total_variants).toBe(1);
  input.display.columns.z.value[4] = 105;
  expect(evaluateAgreement(input).variants[0].reason).toBe('duplicate_variant_conflict');
  expect(evaluateAgreement(input).coverage.fully_covered_types).toBe(0);
});
it('requires full contiguous flat-guard windows including stochastic smoothing', () => {
  for (const [kind, params, port, endpoint] of [['rsi',{period: 2},'value',100],['stochastic',{period: 2, smooth: 3, signal: 1},'k',0],['williamsr',{period: 2},'value',0]] as const) {
    const input = single(kind, params, {[port]: endpoint}); input.candles.forEach(row => Object.assign(row, {open: 42, high: 42, low: 42, close: 42}));
    expect(status(input)).toBe('neutral');
    const needed = params.period + (kind === 'rsi' ? 1 : kind === 'stochastic' ? 2 : 0);
    input.candles = input.candles.slice(-needed + 1); expect(status(input)).toBe('unavailable');
  }
  const input = single('stochastic', {period: 2, smooth: 3, signal: 1}, {k: 0}); input.candles.slice(2).forEach(row => Object.assign(row, {open: 42, high: 42, low: 42, close: 42}));
  expect(status(input)).toBe('down'); input.candles.splice(-2, 1); expect(status(input)).toBe('unavailable');
  const mfi = single('mfi', {period: 2}, {value: null}); mfi.candles.forEach(row => Object.assign(row, {open: 42, high: 42, low: 42, close: 42})); expect(status(mfi)).toBe('unavailable');
});
it('requires both exact raw and display neighbors for OBV', () => {
  const input = single('obv', {}, {value: 10});
  for (const [value, expected] of [[11,'up'],[9,'down'],[10,'neutral']] as const) {input.display.columns.x.value[4] = value; expect(status(input)).toBe(expected);}
  for (const mutation of ['raw_missing','forming','conflict','output_missing']) {
    const changed = structuredClone(input);
    if (mutation === 'raw_missing') changed.candles.splice(-2, 1);
    else if (mutation === 'forming') changed.candles[3].confirmation = 'forming';
    else if (mutation === 'conflict') changed.candles[3].conflict = true;
    else changed.display.columns.x.value[3] = null;
    expect(status(changed)).toBe('unavailable');
  }
});
it('does not search older values or let future values change the requested close', () => {
  const input = structuredClone(byName.get('three_groups_up_up_down')!.input); input.close_time = input.display.times.at(-2)!;
  const baseline = evaluateAgreement(input);
  input.candles.filter(row => row.time + 60 > input.close_time).forEach(row => Object.assign(row, {close: 100000, high: 100001, low: -100000}));
  Object.values(input.display.columns).forEach(columns => Object.values(columns).forEach(values => values[values.length - 1] = -10000));
  expect(evaluateAgreement(input)).toEqual(baseline);
  input.close_time += 60; Object.values(input.display.columns).forEach(columns => Object.values(columns).forEach(values => values[values.length - 1] = null));
  expect(evaluateAgreement(input).overall).toBeNull(); expect(evaluateAgreement(input).close_time).toBe(input.close_time);
});
it('fails closed on conflicts and invalid raw geometry, and rejects duplicate timestamps', () => {
  for (const update of [{conflict: true},{confirmation: 'forming'},{high: 0},{close: Infinity},{open: null}]) {
    const input = single(); Object.assign(input.candles[4], update); expect(status(input)).toBe('unavailable');
  }
  const input = single(); input.candles[1].time = 0; expect(() => evaluateAgreement(input)).toThrow();
  const other = single(); other.display.times[1] = 60; expect(() => evaluateAgreement(other)).toThrow();
});
it('detaches snapshots and returned evidence while reusing prepared indexes', () => {
  const input = structuredClone(byName.get('three_groups_up_up_down')!.input), prepared = prepareAgreement(input), expected = prepared.evaluate(input.close_time);
  input.instances[0].params.period = 999; input.candles.at(-1)!.close = -999; input.display.columns.s.value[input.display.times.length - 1] = null;
  expect(prepared.evaluate(input.close_time)).toEqual(expected);
  for (const time of input.display.times) expect(prepared.evaluate(time).close_time).toBe(time);
  const result = prepared.evaluate(input.close_time); result.members[0].params.period = 900; expect(prepared.evaluate(input.close_time)).toEqual(expected);
});
it('keeps missing required group unknown and rejects malformed threshold contracts', () => {
  const result = evaluateAgreement(byName.get('hidden_down_group_excluded')!.input);
  expect(thresholdEvidence(result, 'up', .1, ['volume']).truth).toBeNull(); expect(thresholdEvidence(result, 'up', 1).truth).toBe(true);
  for (const value of [-.1, 1.01, NaN]) expect(() => thresholdEvidence(result, 'up', value)).toThrow();
  expect(() => thresholdEvidence(result, 'up', .5, ['trend','trend'])).toThrow();
  expect(() => thresholdEvidence({...result, manifest_hash: 'old'}, 'up', .5)).toThrow();
});
it('uses deterministic largest remainder for a three-way tie', () => {
  const input = structuredClone(byName.get('three_groups_up_up_down')!.input); input.display.columns.r.value[input.display.times.length - 1] = 50;
  expect(evaluateAgreement(input).overall?.percentages).toEqual({up: 34, down: 33, neutral: 33});
});
it('matches complete Python evidence for all independently expected vectors and thresholds', async () => {
  const {execFileSync} = await vi.importActual<any>('node:child_process');
  const {platform} = await vi.importActual<any>('node:os');
  const python = platform() === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python';
  const source = `import json\nfrom terminal.indicator_agreement import evaluate_agreement, threshold_evidence\nf=json.load(open('tests/fixtures/indicator_agreement_v1.json'))\nr={c['name']:evaluate_agreement(c['input']) for c in f['cases']}\nt=[threshold_evidence(r[c['result_case']],c['direction'],c['threshold'],c['required_groups']) for c in f['threshold_cases']]\nprint(json.dumps(dict(results=list(r.values()),thresholds=t),allow_nan=False))`;
  const pythonResults = JSON.parse(execFileSync(python, ['-c', source], {encoding: 'utf8', maxBuffer: 4 * 1024 * 1024}));
  const results = cases.map(row => evaluateAgreement(row.input));
  expect(results).toEqual(pythonResults.results);
  const indexed = new Map(cases.map((row, i) => [row.name, results[i]]));
  expect(fixtures.threshold_cases.map(row => thresholdEvidence(indexed.get(row.result_case) as AgreementResult, row.direction as 'up' | 'down', row.threshold, row.required_groups as Group[]))).toEqual(pythonResults.thresholds);
});
