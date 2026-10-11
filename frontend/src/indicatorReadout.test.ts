import {it, expect} from 'vitest';
import {indicatorValue, vwapStatus} from './indicatorReadout';
import {defaults, validateIndicators, utcAnchorInput, type ChartIndicator} from './ChartIndicators';
const item = (type: ChartIndicator['type']): ChartIndicator => ({id:type,type,params:{...defaults[type]},color:'#123456',visible:true} as ChartIndicator);
it('describes Supertrend direction without price formatting and reports every VWAP reason',()=>{
 expect(indicatorValue(item('supertrend'),'direction',1)).toBe('direction Up (+1)');
 expect(indicatorValue(item('supertrend'),'direction',-1)).toBe('direction Down (−1)');
 for(const reason of ['before_anchor','missing_session_start','incomplete_coverage','zero_total_volume']) {
  expect(vwapStatus({status:'unavailable',reason})).toContain('Unavailable:');
  expect(vwapStatus({status:'unavailable',reason})).not.toContain(reason);
 }
 expect(vwapStatus({status:'ready'})).toContain('complete coverage');
 expect(vwapStatus(undefined)).toContain('Awaiting');
});
it('accepts every catalog default and rejects invalid bounded boundary inputs',()=>{
 for(const type of Object.keys(defaults) as ChartIndicator['type'][])expect(validateIndicators([item(type)])).toBe('');
 for(const anchor of [NaN,-1,253402300800,1.5])expect(validateIndicators([{...item('vwap'),params:{mode:1,anchor}}])).not.toBe('');
 for(const step of [NaN,Infinity,0,0.3])expect(validateIndicators([{...item('sar'),params:{step,max:0.2}}])).not.toBe('');
 expect(utcAnchorInput(NaN)).toBe('');expect(utcAnchorInput(0)).toBe('1970-01-01T00:00:00');
});


it('keeps tiny residues compact without changing source values or hiding meaningful small values',()=>{
 const value=0.000000000000051;
 expect(indicatorValue(item('vmc_cipher_b'),'stoch_k',value)).toBe('Stoch RSI K 0');
 expect(indicatorValue(item('vmc_cipher_b'),'stoch_d',-value)).toBe('Stoch RSI D 0');
 expect(value).toBe(0.000000000000051);
 expect(indicatorValue(item('ema'),'value',1e-12)).toMatch(/1E-12/i);
 expect(indicatorValue(item('vmc_cipher_b'),'wt1',0.00000005)).toMatch(/5E-8/i);
 expect(indicatorValue(item('vmc_cipher_b'),'wt1',Infinity)).toContain('N/A');
});

it('keeps hidden fixed-anchor VWAP valid when changing the visible timeframe',()=>{
 const hidden={...item('vwap'),params:{mode:1,anchor:60},visible:false};
 expect(validateIndicators([hidden],60)).toBe('');
 expect(validateIndicators([{...hidden,visible:true}],60)).toContain('align exactly');
});
