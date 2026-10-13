import React from 'react';
import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,cleanup,fireEvent} from '@testing-library/react';
import {currentAgreement,type CurrentAgreementInput} from './currentAgreement';
import IndicatorAgreementPanel from './IndicatorAgreementPanel';
import * as evaluator from './indicatorAgreement';
const origin=()=>({time:1800000000,generation:1,contract:'native-close-engine-seeds-v1'});
function input():CurrentAgreementInput {
 const rows=Array.from({length:7},(_,i)=>({time:1800000000+i*60,open:10,high:11,low:9,close:10,volume:1,confirmation:'synthetic_closed'}));
 const instances:any[]=[{id:'e',type:'ema',params:{period:2},visible:true,color:'#fff'},{id:'m',type:'macd',params:{fast:2,slow:3,signal:2},visible:true,color:'#fff'},{id:'c',type:'cmf',params:{period:2},visible:true,color:'#fff'}];
 const settings:any={version:1,revision:3,instances,origins:{'1':origin()}};
 const context={source:'bybit',market:'spot',symbol:'BTCUSDT',minutes:1,start:rows[0].time,end:rows.at(-1)!.time,settings_revision:3,generation:1,origin:origin().time};
 const response:any={status:'ready',revision:'a'.repeat(64),settings:structuredClone(settings),origin:origin(),times:rows.map(r=>r.time+60),columns:{e:{value:Array(7).fill(9)},m:{histogram:Array(7).fill(1)},c:{value:Array(7).fill(-.2)}},projections:{version:1,contract:'ichimoku-raw-ordinal-v1',horizon:context.end+60,raw_times:rows.map(r=>r.time+60),context:{...context}},indicator_events:{version:1,contract:'confirmed-vmc-events-v1',horizon:context.end+60,context:{...context}}};
 const rawSnapshotKey=JSON.stringify(rows);
 return {source:'bybit',market:'spot',symbol:'BTCUSDT',minutes:1,windowEpoch:4,priceStyle:'candles',settings,rows:rows as any,response,rawSnapshotKey,receipt:{response,rawSnapshotKey,requestKey:JSON.stringify(['bybit','spot','BTCUSDT',1,'candles']),windowEpoch:4,settingsRevision:3,generation:1,calculationEpoch:1,responseRevision:response.revision,origin:JSON.stringify(response.origin)},active:true,fresh:true,historical:false,loading:false,loaded:true,saving:false,error:''};
}
const clone=(value:CurrentAgreementInput)=>{const x=structuredClone(value);x.receipt!.response=x.response;return x;};
const refreshRaw=(x:CurrentAgreementInput)=>{x.rawSnapshotKey=JSON.stringify(x.rows);x.receipt!.rawSnapshotKey=x.rawSnapshotKey;};
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('uses three equally weighted groups and unrounded two-thirds agreement',()=>{
 const x=input(),result=currentAgreement(x).result!;expect(result.overall?.exact).toEqual({up:['2','3'],down:['1','3'],neutral:['0','1']});expect(result.overall?.percentages).toEqual({up:67,down:33,neutral:0});expect(result.group_conflict).toBe(true);expect(result.close_time).toBe(x.rows.at(-1)!.time+60);
});
it('rejects independently tampered source, revision, origin, raw and output envelope boundaries',()=>{
 const mutations:((x:CurrentAgreementInput)=>void)[]=[x=>x.source='okx',x=>x.minutes=5,x=>x.windowEpoch++,x=>x.settings.revision++,x=>x.rawSnapshotKey+=' ',x=>x.receipt!.response={},x=>x.receipt!.generation=0,x=>x.receipt!.calculationEpoch=0,x=>x.response.revision='bad',x=>x.response.origin.generation++,x=>x.response.settings.instances[0].params.period=3,x=>x.response.settings.instances[0].visible=false,x=>x.response.projections.context.symbol='ETHUSDT',x=>x.response.indicator_events.context.generation++,x=>x.response.indicator_events.horizon++,x=>x.response.projections.raw_times[2]++,x=>x.response.times.reverse(),x=>x.response.columns.e.value.pop(),x=>{x.rows[2].time++;refreshRaw(x);}];
 for(const change of mutations){const x=clone(input());change(x);expect(currentAgreement(x).result).toBeNull();}
});
it('suppresses inactive, stale, saving, loading, error and detached history before preparing the evaluator',()=>{
 const prepare=vi.spyOn(evaluator,'prepareAgreement');
 for(const change of [{active:false},{fresh:false},{saving:true},{loading:true},{loaded:false},{error:'lost source'},{historical:true}]){const state=currentAgreement({...input(),...change});expect(state.result).toBeNull();expect(state.reason.length).toBeGreaterThan(0);}
 expect(prepare).not.toHaveBeenCalled();
});
it('missing output at newest confirmed close is unavailable without substituting the older ready close',()=>{
 const x=input();x.response.times.pop();for(const p of Object.values(x.response.columns) as any[])for(const values of Object.values(p) as any[])values.pop();
 const result=currentAgreement(x).result!;expect(result.close_time).toBe(x.rows.at(-1)!.time+60);expect(result.overall).toBeNull();expect(result.coverage.fully_covered_types).toBe(0);
});
it('forming rows and synthetic price candles cannot choose the reference or change the raw result',()=>{
 const x=input();(x.rows.at(-1)! as any).confirmation='forming';refreshRaw(x);x.response.price_candles=x.rows.map(r=>({...r,close:99999}));x.priceStyle='heikin_ashi';x.receipt!.requestKey=JSON.stringify(['bybit','spot','BTCUSDT',1,'heikin_ashi']);
 const result=currentAgreement(x).result!;expect(result.close_time).toBe(x.rows.at(-2)!.time+60);expect(result.overall?.exact.up).toEqual(['2','3']);
});
it('applied visibility changes current composition but response identity mismatch never uses a draft',()=>{
 const x=input();const draft=structuredClone(x.settings);draft.instances[2].visible=false;
 expect(currentAgreement(x).result?.overall?.exact.up).toEqual(['2','3']);expect(currentAgreement({...x,settings:draft}).result).toBeNull();
 x.settings=draft;x.response.settings=structuredClone(draft);const result=currentAgreement(x).result!;expect(result.overall?.exact.up).toEqual(['1','1']);expect(result.members.find(m=>m.id==='c')?.status).toBe('hidden');
});
it('accepts first persisted origin and a consistently acknowledged reanchor without stale local-origin comparison',()=>{
 const x=input();x.settings.origins={};expect(currentAgreement(x).result?.overall).not.toBeNull();
 x.response.origin={time:1799999940,generation:2,contract:'native-close-engine-seeds-v1'};x.response.settings.origins={'1':x.response.origin};for(const e of [x.response.projections,x.response.indicator_events]){e.context.origin=x.response.origin.time;e.context.generation=2;}x.receipt!.origin=JSON.stringify(x.response.origin);expect(currentAgreement(x).result?.overall?.exact.up).toEqual(['2','3']);
});
it('keeps compact summary visible with details initially collapsed and preserves expansion across ordinary refresh',()=>{
 const x=input();const mounted=render(<IndicatorAgreementPanel {...x}/>);expect(screen.getByLabelText('Overall agreement')).toBeTruthy();const details=screen.getByText(/Agreement details ·/).closest('details')!;expect(details.open).toBe(false);
 fireEvent.click(screen.getByText(/Agreement details ·/));expect(details.open).toBe(true);const next=clone(x);next.response.revision='b'.repeat(64);next.receipt!.responseRevision=next.response.revision;mounted.rerender(<IndicatorAgreementPanel {...next}/>);expect(screen.getByText(/Agreement details ·/).closest('details')!.open).toBe(true);
 mounted.rerender(<IndicatorAgreementPanel {...next} historical/>);expect(screen.queryByLabelText('Overall agreement')).toBeNull();expect(screen.getAllByText(/Historical buffer. Return to latest/).length).toBeGreaterThan(0);expect(screen.getByText(/Percentages are not probabilities/)).toBeTruthy();
});
