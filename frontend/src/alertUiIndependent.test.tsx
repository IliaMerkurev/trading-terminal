import React from 'react';
import {it,expect,vi,beforeEach,afterEach} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup,act} from '@testing-library/react';
import {AlertSessionProvider,AlertSessionController,AlertChartBridge,pendingAlertKey} from './AlertSession';
import IndicatorAlerts from './IndicatorAlerts';
const mock=vi.hoisted(()=>({api:vi.fn(),calls:[] as {command:string,params:any}[],session:'',rules:[] as any[],events:[] as any[]}));
vi.mock('./api',()=>({api:mock.api}));
const ctx={source:'bybit',market:'spot',symbol:'BTCUSDT',minutes:1,visible:true};
const settings=(revision=1):any=>({version:1,revision,instances:[],origins:{}});
const rule=(id='rule1'):any=>({id,name:'Frozen original',revision:1,definition_revision:1,deleted:false,definition_hash:'hash',rebind_required:false,definition:{context:{source:'bybit',market:'spot',symbol:'BTCUSDT',minutes:1},settings_revision:1,combine:'ALL',conditions:[{predicate:'above',left:{kind:'price',port:'close'},right:{kind:'level',value:10,unit:'price'}}]},runtime:{rule_id:id,phase:'PAUSED',reason:'Explicit Arm required',confirmed_at:null}});
const catalog={version:1,ports:{},predicates:['above','below','cross_above','cross_below','divergence'],divergences:['bullish_regular'],oscillators:['wt'],combine:['ALL','ANY'],max_conditions:16,price_ports:['close'],price_unit:'price'};
const respond=async(command:string,params:any)=>{
 if(command==='alert_session_init'){mock.session=params.session_id;return {session_id:mock.session};}
 if(command==='alert_context')return {...params};
 if(command==='alert_catalog')return catalog;
 if(command==='alert_status')return {session_id:mock.session,rules:mock.rules.map(x=>x.runtime)};
 if(command==='alert_list')return {rules:structuredClone(mock.rules.filter(x=>x.deleted===params.trashed)),next_cursor:null};
 if(command==='alert_get')return structuredClone(mock.rules.find(x=>x.id===params.rule_id));
 if(command==='alert_events'){const all=mock.events.filter(x=>x.sequence>params.after);return {events:structuredClone(all.slice(0,params.limit)),next_cursor:all.length>params.limit?all[params.limit-1].sequence:null};}
 if(command==='alert_claim_banner'){const e=mock.events.find(x=>x.id===params.event_id);if(e.banner_claimed)return {claimed:false};e.banner_claimed=true;return {claimed:true};}
 if(command==='alert_event')return structuredClone(mock.events.find(x=>x.id===params.event_id));
 if(command==='alert_pause')return {phase:'PAUSED'};
 if(command==='alert_arm')return {phase:'ARMING'};
 if(command==='alert_request')return null;
 throw new Error('Unexpected independent test API '+command);
};
beforeEach(()=>{mock.calls=[];mock.rules=[rule()];mock.events=[];mock.session='';localStorage.clear();mock.api.mockReset();mock.api.mockImplementation((command,params={})=>{mock.calls.push({command,params:structuredClone(params)});return respond(command,params);});});
afterEach(()=>{cleanup();vi.useRealTimers();});
const app=(revision=1)=><AlertSessionProvider><AlertChartBridge {...ctx} settings={settings(revision)} available/><IndicatorAlerts/></AlertSessionProvider>;
const open=async()=>{fireEvent.click(screen.getByRole('button',{name:'Local alerts'}));await screen.findByRole('option',{name:/Frozen original/});if(!localStorage.getItem(pendingAlertKey))await waitFor(()=>expect((screen.getByRole('button',{name:'Preview frozen alert'}).closest('fieldset') as HTMLFieldSetElement).disabled).toBe(false));};
const select=async()=>{fireEvent.change(screen.getByLabelText('Saved alert rule'),{target:{value:'rule1'}});await screen.findByRole('heading',{name:'Current name: Frozen original'});};
it('uses strictly newer backend context fences for A to B to A without old capability reuse',async()=>{
 const controller=new AlertSessionController();const a={...ctx,settings:settings(),available:true};
 controller.register(a);controller.register({...a,symbol:'ETHUSDT'});controller.register(a);
 await waitFor(()=>expect(controller.ready).toBe(true));
 const sent=mock.calls.filter(x=>x.command==='alert_context');expect(sent.map(x=>x.params.context_revision)).toEqual([1,2,3]);expect(sent.map(x=>x.params.symbol)).toEqual(['BTCUSDT','ETHUSDT','BTCUSDT']);expect(controller.isCurrent(1)).toBe(false);expect(controller.isCurrent(3)).toBe(true);
});
it('requires a checked review and acknowledged Pause before the Arm command',async()=>{
 render(app());await open();await select();const arm=screen.getByRole('button',{name:'Arm / Resume alert'});expect((arm as HTMLButtonElement).disabled).toBe(true);
 fireEvent.click(screen.getByLabelText('Reviewed saved alert for Arm'));expect((arm as HTMLButtonElement).disabled).toBe(false);
 let finish!:()=>void;const normal=mock.api.getMockImplementation()!;mock.api.mockImplementation((command,params)=>command==='alert_pause'?new Promise(resolve=>{mock.calls.push({command,params});finish=()=>resolve({phase:'PAUSED'});}):normal(command,params));
 fireEvent.click(arm);await waitFor(()=>expect(finish).toBeTypeOf('function'));expect(mock.calls.some(x=>x.command==='alert_arm')).toBe(false);
 await act(async()=>finish());await waitFor(()=>expect(mock.calls.some(x=>x.command==='alert_arm')).toBe(true));
 const sent=mock.calls.filter(x=>['alert_pause','alert_arm'].includes(x.command));expect(sent.map(x=>x.command)).toEqual(['alert_pause','alert_arm']);expect(sent[1].params.reviewed).toBe(true);
});
it('same Saved selector value retains the loaded rows and selection',async()=>{
 render(app());await open();await select();const before=mock.calls.filter(x=>x.command==='alert_list').length;
 fireEvent.change(screen.getByLabelText('Alert library view'),{target:{value:'saved'}});
 expect((screen.getByLabelText('Saved alert rule') as HTMLSelectElement).value).toBe('rule1');expect(screen.getByRole('option',{name:/Frozen original/})).toBeTruthy();expect(mock.calls.filter(x=>x.command==='alert_list')).toHaveLength(before);
});
it('retains an uncertain original create across remount and context change without another create',async()=>{
 const pending={command:'alert_create',params:{request_id:'originalrequest',name:'original',definition:rule().definition,definition_hash:'hash',settings_revision:1},contextKey:JSON.stringify(['bybit','spot','BTCUSDT',1,true]),settingsRevision:1,createdAt:'2026-10-12T00:00:00Z'};
 localStorage.setItem(pendingAlertKey,JSON.stringify(pending));let mounted=render(app());await open();
 fireEvent.click(screen.getByRole('button',{name:'Reconcile original alert write'}));await screen.findByText(/No accepted request is recorded/);expect(JSON.parse(localStorage.getItem(pendingAlertKey)!)).toEqual(pending);expect(mock.calls.some(x=>x.command==='alert_create')).toBe(false);
 mounted.unmount();mounted=render(<AlertSessionProvider><AlertChartBridge {...ctx} symbol="ETHUSDT" settings={settings(2)} available/><IndicatorAlerts/></AlertSessionProvider>);await open();fireEvent.click(screen.getByRole('button',{name:'Reconcile original alert write'}));await screen.findByText(/No accepted request is recorded/);expect((screen.getByRole('button',{name:'Retry exact original create'}) as HTMLButtonElement).disabled).toBe(true);expect(JSON.parse(localStorage.getItem(pendingAlertKey)!)).toEqual(pending);
});
it('banner traversal reaches an unclaimed event after twenty already claimed records',async()=>{
 mock.events=Array.from({length:21},(_,i)=>({id:'e'+i,sequence:i+1,rule_id:'rule1',current_name:'Current renamed',is_read:false,banner_claimed:i<20,evidence:{confirmed_at:1000+i}}));
 render(app());await screen.findByText('Local alert · current name: Current renamed',{}, {timeout:4000});
 const claims=mock.calls.filter(x=>x.command==='alert_claim_banner');expect(claims.map(x=>x.params.event_id)).toEqual(['e20']);expect(mock.calls.filter(x=>x.command==='alert_events').some(x=>x.params.after===20)).toBe(true);
});
it('selected rule still refreshes durable rebind state after an applied revision change',async()=>{
 const mounted=render(app());await open();await select();mock.rules[0].rebind_required=true;mock.rules[0].runtime.reason='Changed parameters';mounted.rerender(app(2));
 await screen.findByText(/Surviving indicator parameters changed/,{}, {timeout:3500});expect((screen.getByLabelText('Saved alert rule') as HTMLSelectElement).value).toBe('rule1');expect((screen.getByRole('button',{name:'Arm / Resume alert'}) as HTMLButtonElement).disabled).toBe(true);
});
it('an absent retained Arm is cleared only after a newer acknowledged fence and Pause, never replayed',async()=>{
 const pending={command:'alert_arm',params:{request_id:'oldarmrequest',rule_id:'rule1',revision:1,definition_hash:'hash',session_id:'oldsession',context_revision:1,reviewed:true},contextKey:JSON.stringify(['bybit','spot','BTCUSDT',1,true]),settingsRevision:1,createdAt:'2026-10-12T00:00:00Z'};
 localStorage.setItem(pendingAlertKey,JSON.stringify(pending));render(app());await open();fireEvent.click(screen.getByRole('button',{name:'Reconcile original alert write'}));await screen.findByRole('button',{name:'Recover paused Arm'});
 const previous=Math.max(...mock.calls.filter(x=>x.command==='alert_context').map(x=>x.params.context_revision));const start=mock.calls.length;
 fireEvent.click(screen.getByRole('button',{name:'Recover paused Arm'}));await waitFor(()=>expect(localStorage.getItem(pendingAlertKey)).toBeNull());const actions=mock.calls.slice(start);const fence=actions.findIndex(x=>x.command==='alert_context'),pause=actions.findIndex(x=>x.command==='alert_pause');expect(fence).toBeGreaterThanOrEqual(0);expect(pause).toBeGreaterThan(fence);expect(actions[fence].params.context_revision).toBeGreaterThan(previous);expect(mock.calls.some(x=>x.command==='alert_arm')).toBe(false);
 await select();expect((screen.getByLabelText('Reviewed saved alert for Arm') as HTMLInputElement).checked).toBe(false);
});
it('drops a preview reply whose applied settings revision changed while awaiting it',async()=>{
 let finish!:(x:any)=>void;const normal=mock.api.getMockImplementation()!;mock.api.mockImplementation((command,params)=>command==='alert_preview'?new Promise(resolve=>{finish=resolve;}):normal(command,params));
 const mounted=render(app());await open();fireEvent.click(screen.getByRole('button',{name:'Preview frozen alert'}));await waitFor(()=>expect(finish).toBeTypeOf('function'));mounted.rerender(app(2));await act(async()=>finish({definition:rule().definition,definition_hash:'hash',settings_revision:1}));expect(screen.queryByLabelText('Reviewed frozen alert preview')).toBeNull();expect(mock.calls.some(x=>x.command==='alert_create')).toBe(false);
});
it('resolves a post-commit error through original request readback without a second create',async()=>{
 let accepted=false;const normal=mock.api.getMockImplementation()!;
 mock.api.mockImplementation((command,params)=>{
  if(command==='alert_preview')return Promise.resolve({definition:rule().definition,definition_hash:'hash',settings_revision:1});
  if(command==='alert_create'){mock.calls.push({command,params:structuredClone(params)});accepted=true;return Promise.reject(Object.assign(new Error('post-commit read failed'),{definiteRejection:true}));}
  if(command==='alert_request'&&accepted){mock.calls.push({command,params});return Promise.resolve({kind:'create',rule_id:'rule1'});}
  return normal(command,params);
 });
 render(app());await open();fireEvent.change(screen.getByLabelText('Alert name'),{target:{value:'Recovered create'}});fireEvent.click(screen.getByRole('button',{name:'Preview frozen alert'}));await screen.findByLabelText('Reviewed frozen alert preview');fireEvent.click(screen.getByLabelText('Reviewed frozen alert preview'));fireEvent.click(screen.getByRole('button',{name:'Save alert paused'}));
 await screen.findByText(/original write was committed/);expect(localStorage.getItem(pendingAlertKey)).toBeNull();const creates=mock.calls.filter(x=>x.command==='alert_create');expect(creates).toHaveLength(1);expect(mock.calls.find(x=>x.command==='alert_request')?.params.request_id).toBe(creates[0].params.request_id);expect(mock.calls.some(x=>x.command==='alert_arm')).toBe(false);
});
