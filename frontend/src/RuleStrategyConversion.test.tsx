import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import {RuleStrategyAction,RuleStrategyProvider,pendingRuleStrategyKey} from './RuleStrategyConversion';
import {conversionPreview,conversionRule} from './ruleStrategyTestFixture';
import type {FrozenRule} from './alertResearch';
const mock=vi.hoisted(()=>({api:vi.fn()}));
vi.mock('./api',()=>({api:mock.api}));
let rule=conversionRule();
const opened=vi.fn(async(_id:string,_isCurrent:()=>boolean)=>{}),refreshed=vi.fn(async()=>{});
const deferred=()=>{let resolve!:(value:any)=>void,reject!:(error:any)=>void;const promise=new Promise<any>((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};
async function service(command:string,p:any) {
  if(command==='alert_strategy_preview')return conversionPreview(p,rule);
  if(command==='alert_strategy_create')return {strategy_id:'saved-strategy',request_id:p.request_id};
  if(command==='alert_strategy_request')return null;
  throw Error('Unexpected command '+command);
}
const app=(scope='source-a',source:FrozenRule=rule)=><RuleStrategyProvider onOpenStrategy={opened} onRefresh={refreshed}><RuleStrategyAction rule={source} scopeKey={scope}/></RuleStrategyProvider>;
async function review() {
  fireEvent.click(screen.getByRole('button',{name:'Create strategy from rule'}));
  fireEvent.change(screen.getByLabelText('Strategy entry direction'),{target:{value:'long'}});
  fireEvent.click(screen.getByRole('button',{name:'Preview strategy conversion'}));
  await screen.findByRole('region',{name:'Strategy conversion review'});
}
async function confirm() {fireEvent.click(screen.getByLabelText('Reviewed strategy conversion'));fireEvent.click(screen.getByRole('button',{name:'Confirm create strategy'}));}
beforeEach(()=>{localStorage.clear();rule=conversionRule();mock.api.mockReset();mock.api.mockImplementation(service);opened.mockClear();refreshed.mockClear();});
it('requires explicit entry direction and frozen review; cancel is read-only',async()=>{
  render(app());fireEvent.click(screen.getByRole('button',{name:'Create strategy from rule'}));
  expect((screen.getByLabelText('Strategy entry direction') as HTMLSelectElement).value).toBe('');
  expect((screen.getByRole('button',{name:'Preview strategy conversion'}) as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByRole('option',{name:/unavailable for unborrowed spot/}) as HTMLOptionElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText('Strategy entry direction'),{target:{value:'long'}});fireEvent.click(screen.getByText('Preview strategy conversion'));
  await screen.findByRole('region',{name:'Strategy conversion review'});
  expect(screen.getByText(/No exit, stop-loss or take-profit is invented/)).toBeTruthy();
  for(const field of ['capital','allocation','fee rate','slippage','stop loss','take profit','execution minutes','primary minutes','gap policy','leverage'])expect(screen.getByText(field,{selector:'dt'})).toBeTruthy();
  expect((screen.getByRole('button',{name:'Confirm create strategy'}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByText('Cancel conversion'));expect(screen.queryByRole('dialog')).toBeNull();expect(mock.api.mock.calls.map(call=>call[0])).toEqual(['alert_strategy_preview']);expect(localStorage.getItem(pendingRuleStrategyKey)).toBeNull();
});
it('invalidates reviewed preview on name or direction changes',async()=>{
  rule.definition.context.market='linear';render(app());await review();fireEvent.click(screen.getByLabelText('Reviewed strategy conversion'));
  fireEvent.change(screen.getByLabelText('New strategy name'),{target:{value:'Explicit short'}});expect(screen.queryByText('Confirm create strategy')).toBeNull();
  fireEvent.change(screen.getByLabelText('Strategy entry direction'),{target:{value:'short'}});fireEvent.click(screen.getByText('Preview strategy conversion'));await screen.findByText('Confirm create strategy');
  expect((screen.getByLabelText('Reviewed strategy conversion') as HTMLInputElement).checked).toBe(false);
  expect(mock.api).toHaveBeenLastCalledWith('alert_strategy_preview',{rule_id:rule.id,revision:3,name:'Explicit short',direction:'short'});
});
it('persists exact payload before sending, prevents repeated clicks and opens only the created strategy',async()=>{
  const gate=deferred();mock.api.mockImplementation((command,p)=>{if(command==='alert_strategy_create'){expect(JSON.parse(localStorage.getItem(pendingRuleStrategyKey)!).params).toEqual(p);return gate.promise;}return service(command,p);});
  render(app());await review();await confirm();fireEvent.click(screen.getByText('Confirm create strategy'));
  expect(mock.api.mock.calls.filter(call=>call[0]==='alert_strategy_create')).toHaveLength(1);
  const params=mock.api.mock.calls.find(call=>call[0]==='alert_strategy_create')![1];
  await act(async()=>gate.resolve({strategy_id:'saved-strategy',request_id:params.request_id}));
  await waitFor(()=>expect(opened).toHaveBeenCalledTimes(1));expect(opened.mock.calls[0][0]).toBe('saved-strategy');expect(refreshed).toHaveBeenCalledTimes(1);expect(localStorage.getItem(pendingRuleStrategyKey)).toBeNull();
  expect(mock.api.mock.calls.every(call=>['alert_strategy_preview','alert_strategy_create'].includes(call[0]))).toBe(true);
});
it('drops late previews after cancellation and after a source selection change',async()=>{
  const gate=deferred();mock.api.mockImplementation((command,p)=>command==='alert_strategy_preview'?gate.promise:service(command,p));
  const ui=render(app());fireEvent.click(screen.getByText('Create strategy from rule'));fireEvent.change(screen.getByLabelText('Strategy entry direction'),{target:{value:'long'}});fireEvent.click(screen.getByText('Preview strategy conversion'));
  ui.rerender(app('source-b'));await act(async()=>gate.resolve(conversionPreview({name:`${rule.name} strategy`,direction:'long'})));
  expect(screen.queryByRole('dialog')).toBeNull();expect(screen.queryByText('Confirm create strategy')).toBeNull();expect(opened).not.toHaveBeenCalled();
});
it('retains late accepted creation without navigating away from a newer source',async()=>{
  const gate=deferred();mock.api.mockImplementation((command,p)=>command==='alert_strategy_create'?gate.promise:service(command,p));
  const ui=render(app());await review();await confirm();const p=JSON.parse(localStorage.getItem(pendingRuleStrategyKey)!).params;
  ui.rerender(app('source-b'));await act(async()=>gate.resolve({strategy_id:'original-strategy',request_id:p.request_id}));
  expect(opened).not.toHaveBeenCalled();expect(refreshed).toHaveBeenCalledTimes(1);expect(screen.getByText('Open created strategy')).toBeTruthy();
  fireEvent.click(screen.getByText('Open created strategy'));await waitFor(()=>expect(opened).toHaveBeenCalledTimes(1));
});
it('fails visibly for unsupported source and rejects malformed or stale preview contracts',async()=>{
  mock.api.mockRejectedValue(new Error('Only native Bybit M1 rules are supported'));
  render(app());fireEvent.click(screen.getByText('Create strategy from rule'));fireEvent.change(screen.getByLabelText('Strategy entry direction'),{target:{value:'long'}});fireEvent.click(screen.getByText('Preview strategy conversion'));
  await screen.findByText('Only native Bybit M1 rules are supported');expect(screen.queryByText('Confirm create strategy')).toBeNull();
  mock.api.mockImplementation(async(_command,p)=>({...conversionPreview(p),contract:'future-unsupported'}));fireEvent.click(screen.getByText('Preview strategy conversion'));await screen.findByText(/Unsupported or stale frozen strategy preview/);
});
it('reconciles lost accepted responses read-only without resubmitting',async()=>{
  let saved:any=null;mock.api.mockImplementation((command,p)=>{if(command==='alert_strategy_create'){saved={strategy_id:'accepted',request_id:p.request_id};return Promise.reject(new Error('lost response'));}if(command==='alert_strategy_request')return Promise.resolve(saved);return service(command,p);});
  render(app());await review();await confirm();await waitFor(()=>expect(opened).toHaveBeenCalledTimes(1));
  expect(mock.api.mock.calls.filter(call=>call[0]==='alert_strategy_create')).toHaveLength(1);expect(mock.api.mock.calls.filter(call=>call[0]==='alert_strategy_request')).toHaveLength(1);expect(localStorage.getItem(pendingRuleStrategyKey)).toBeNull();
});
it('reload only reconciles and explicit absent retry preserves exact identity and content',async()=>{
  mock.api.mockImplementation((command,p)=>command==='alert_strategy_create'?Promise.reject(new Error('network uncertain')):service(command,p));
  const ui=render(app());await review();await confirm();await screen.findByText('Retry exact strategy request');
  const original=JSON.parse(localStorage.getItem(pendingRuleStrategyKey)!).params;ui.unmount();mock.api.mockClear();
  render(app());await screen.findByText('Retry exact strategy request');expect(mock.api.mock.calls).toEqual([['alert_strategy_request',{request_id:original.request_id}]]);expect(opened).not.toHaveBeenCalled();
  mock.api.mockImplementation(service);fireEvent.click(screen.getByText('Retry exact strategy request'));await screen.findByText('Open created strategy');
  expect(mock.api).toHaveBeenCalledWith('alert_strategy_create',original);expect(opened).not.toHaveBeenCalled();expect(localStorage.getItem(pendingRuleStrategyKey)).toBeNull();
});
it('reload reconciles accepted identity without automatic editor navigation',async()=>{
  const params={rule_id:rule.id,revision:3,name:'Saved from earlier session',direction:'long',preview_hash:'c'.repeat(64),request_id:'request-123'};
  localStorage.setItem(pendingRuleStrategyKey,JSON.stringify({version:1,params,createdAt:'2026-10-12T12:00:00Z',hadUnknown:true}));
  mock.api.mockResolvedValue({strategy_id:'already-created',request_id:'request-123'});render(app());await screen.findByText('Open created strategy');
  expect(mock.api.mock.calls).toEqual([['alert_strategy_request',{request_id:'request-123'}]]);expect(opened).not.toHaveBeenCalled();expect(refreshed).toHaveBeenCalledTimes(1);
});
it('does not submit when durable local request storage fails',async()=>{
  render(app());await review();const storage=vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw Error('quota');});
  try {await confirm();await screen.findAllByText(/storage is unavailable/);expect(mock.api.mock.calls.some(call=>call[0]==='alert_strategy_create')).toBe(false);}finally{storage.mockRestore();}
});
it('blocks creation for malformed durable state instead of replacing its identity',()=>{
  localStorage.setItem(pendingRuleStrategyKey,'{broken');render(app());expect(screen.getByRole('alert').textContent).toContain('New creation is blocked');expect((screen.getByText('Create strategy from rule') as HTMLButtonElement).disabled).toBe(true);expect(localStorage.getItem(pendingRuleStrategyKey)).toBe('{broken');
});
it('source edits invalidate an open review without altering its already captured definition',async()=>{
  const ui=render(app());await review();const original=conversionPreview({name:'Original',direction:'long'}).graph.nodes[0].params.snapshot;
  const edited=structuredClone(rule);edited.revision++;edited.definition_revision++;edited.definition_hash='d'.repeat(64);edited.definition.instances[0].params.period=9;
  ui.rerender(app('source-a',edited));expect(screen.queryByRole('dialog')).toBeNull();expect(JSON.parse(String(original)).definition.instances[0].params.period).toBe(3);expect(mock.api.mock.calls.some(call=>call[0]==='alert_strategy_create')).toBe(false);
});
it('requires a fresh preview after a definite stale creation rejection with absent readback',async()=>{
  mock.api.mockImplementation((command,p)=>command==='alert_strategy_create'?Promise.reject(Object.assign(Error('Saved rule revision changed'),{definiteRejection:true})):service(command,p));
  render(app());await review();await confirm();await screen.findByText(/Strategy creation was rejected/);expect(localStorage.getItem(pendingRuleStrategyKey)).toBeNull();expect(screen.queryByText('Confirm create strategy')).toBeNull();
});
