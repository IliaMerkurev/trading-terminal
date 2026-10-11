import {it, expect} from 'vitest';
import {indicatorValue, vwapStatus} from './indicatorReadout';
import {defaults, validateIndicators, utcAnchorInput, type ChartIndicator} from './ChartIndicators';
const item = (type: ChartIndicator['type']): ChartIndicator => ({id:type,type,params:{...defaults[type]},color:'#123456',visible:true});
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
