import {describe, expect, it} from 'vitest';
import {currentAgreement, type CurrentAgreementInput} from './currentAgreement';
import {makeAgreementInput, renewReceipt} from './currentAgreementTestFixture';

describe('current agreement accepted-response boundary', () => {
  it('uses one exact confirmed raw close with independent expected votes, including neutral', () => {
    const input = makeAgreementInput();
    const result = currentAgreement(input).result!;
    expect(result.close_time).toBe(180);
    expect(result.overall?.percentages).toEqual({up: 67, down: 0, neutral: 33});
    expect(result.coverage).toEqual({fully_covered_types: 3, available_types: 3, total_types: 3, available_variants: 3, total_variants: 3, available_groups: 3});
    expect(result.members.find(member => member.id === 'sma')?.values).toEqual({value: 105, raw_close: 110});
  });
  it('never substitutes the prior display value for a missing exact target', () => {
    const input = makeAgreementInput(); input.response.columns.sma.value[2] = null;
    const result = currentAgreement(input).result!;
    expect(result.close_time).toBe(180);
    expect(result.members.find(member => member.id === 'sma')?.status).toBe('unavailable');
    expect(result.coverage.fully_covered_types).toBe(2);
    expect(result.overall?.percentages).toEqual({up: 50, down: 0, neutral: 50});
  });
  it('does not search backward when the exact output timestamp itself is absent', () => {
    const input = makeAgreementInput(); input.response.times.splice(2, 1);
    for (const ports of Object.values(input.response.columns) as any[]) for (const values of Object.values(ports) as any[]) values.splice(2, 1);
    const result = currentAgreement(input).result!;
    expect(result.close_time).toBe(180); expect(result.overall).toBeNull();
    expect(result.members.filter(member => member.status === 'unavailable')).toHaveLength(3);
  });
  it('does not consume forming outputs or Heikin Ashi prices', () => {
    const input = makeAgreementInput(); input.priceStyle = 'heikin_ashi';
    input.response.price_candles = [{time: 180, close: -100000}];
    input.response.columns.sma.value[3] = -100000; input.rows[3].close = -100000;
    renewReceipt(input);
    expect(currentAgreement(input).result?.overall?.percentages).toEqual({up: 67, down: 0, neutral: 33});
  });
  it('accepts internally coherent first-origin establishment and explicit reanchor without an applied revision change', () => {
    const input = makeAgreementInput(); input.settings.origins = {1: {time: 60, generation: 1, contract: 'native-close-engine-seeds-v1'}};
    expect(currentAgreement(input).result).not.toBeNull();
    input.response.origin.generation = 2; input.response.settings.origins['1'].generation = 2;
    input.response.projections.context.generation = 2; input.response.indicator_events.context.generation = 2;
    renewReceipt(input); expect(currentAgreement(input).result).not.toBeNull();
  });
  it('excludes hidden members and labels context/unsupported without inflating coverage', () => {
    const input = makeAgreementInput();
    input.settings.instances.push({id:'hidden',type:'ema',params:{period:20},visible:false,color:'#ffffff'},
      {id:'volume',type:'volume',params:{},visible:true,color:'#ffffff'},
      {id:'cloud',type:'ichimoku',params:{conversion:9,base:26,span_b:52,displacement:26},visible:true,color:'#ffffff'});
    input.response.settings.instances = structuredClone(input.settings.instances);
    const result = currentAgreement(input).result!;
    expect(result.exclusions).toEqual({hidden:['hidden'],context:['volume'],unsupported:['cloud'],unavailable:[]});
    expect(result.coverage.total_types).toBe(3);
  });
  it('retains a single known neutral group without publishing an overall score', () => {
    const input = makeAgreementInput(); input.settings.instances = input.settings.instances.filter(item => item.id === 'cmf');
    input.response.settings.instances = structuredClone(input.settings.instances);
    const result = currentAgreement(input).result!;
    expect(result.overall).toBeNull(); expect(result.groups.find(group => group.group === 'volume')?.distribution?.percentages).toEqual({up:0,down:0,neutral:100});
  });
  const invalid: [string, (input: CurrentAgreementInput) => void][] = [
    ['source', i => {i.source = 'okx';}], ['market', i => {i.market = 'linear';}], ['symbol', i => {i.symbol = 'ETHUSDT';}],
    ['native interval', i => {i.minutes = 5;}], ['unsupported interval', i => {i.minutes = 2;}],
    ['window epoch', i => {i.windowEpoch++;}], ['response identity', i => {i.response = structuredClone(i.response);}],
    ['response revision', i => {i.response.revision = 'b'.repeat(64);}], ['missing response revision', i => {delete i.response.revision;}],
    ['raw snapshot receipt', i => {i.rawSnapshotKey = 'stale';}], ['raw values', i => {i.rows[2].close = 111;}],
    ['settings revision', i => {i.settings.revision++;}], ['returned settings revision', i => {i.response.settings.revision++;}],
    ['applied parameter mismatch', i => {i.response.settings.instances[0].params.period = 2;}],
    ['applied visibility mismatch', i => {i.response.settings.instances[0].visible = false;}],
    ['response origin', i => {i.response.origin.time = 60;}], ['settings origin generation', i => {i.response.settings.origins['1'].generation++;}],
    ['projection origin', i => {i.response.projections.context.origin = 60;}], ['event generation', i => {i.response.indicator_events.context.generation++;}],
    ['origin contract', i => {i.response.origin.contract = 'wrong'; renewReceipt(i);}],
    ['future coherent origin', i => {i.response.origin.time = 300; i.response.settings.origins['1'].time = 300; i.response.projections.context.origin = 300; i.response.indicator_events.context.origin = 300; renewReceipt(i);}],
    ['fractional generation', i => {i.response.origin.generation = .5; renewReceipt(i);}],
    ['projection bounds', i => {i.response.projections.context.start = 60;}], ['event bounds', i => {i.response.indicator_events.context.end = 120;}],
    ['projection horizon', i => {i.response.projections.horizon = 180;}], ['raw clock identity', i => {i.response.projections.raw_times[2] = 181;}],
    ['duplicate raw time', i => {i.rows[2].time = 60; renewReceipt(i);}], ['unsorted raw time', i => {i.rows.reverse(); renewReceipt(i);}],
    ['fractional raw time', i => {i.rows[0].time = .5; renewReceipt(i);}], ['invalid UTC time', i => {i.rows[0].time = Number.MAX_SAFE_INTEGER; renewReceipt(i);}],
    ['duplicate output time', i => {i.response.times[2] = 120;}], ['unsorted output time', i => {i.response.times.reverse();}],
    ['fake close', i => {i.response.times[2] = 181;}], ['future output', i => {i.response.times[3] = 300;}],
    ['short column', i => {i.response.columns.sma.value.pop();}], ['null column', i => {i.response.columns.sma = null;}],
    ['error response', i => {i.response.status = 'error';}], ['response warning', i => {i.response.settings.warning = 'Invalid settings';}],
  ];
  it.each(invalid)('rejects %s without retaining stale votes', (_name, mutate) => {
    const input = makeAgreementInput(); expect(currentAgreement(input).result).not.toBeNull(); mutate(input);
    expect(currentAgreement(input)).toEqual({result:null, reason:expect.stringContaining('Snapshot mismatch')});
  });
  it.each([
    ['historical', 'Historical buffer'], ['active', 'inactive'], ['fresh', 'paused or stale'], ['loading', 'Loading'],
    ['loaded', 'Loading'], ['saving', 'Applying settings'], ['error', 'error'],
  ])('suppresses %s before touching the output snapshot', (key, reason) => {
    const input = makeAgreementInput(); Object.assign(input, {[key]: key === 'error' ? 'Error' : !['active','fresh','loaded'].includes(key)});
    Object.defineProperty(input.response, 'status', {get: () => {throw new Error('Must not evaluate');}});
    expect(currentAgreement(input)).toEqual({result:null,reason:expect.stringContaining(reason)});
  });
});
