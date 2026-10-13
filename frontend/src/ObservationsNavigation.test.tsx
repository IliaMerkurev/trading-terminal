import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import Observations from './Observations';
import {api} from './api';
import {navigationUTC} from './observationNavigation';

vi.mock('./api',()=>({api:vi.fn()}));
vi.mock('./ObservationChart',()=>({default:(props:any)=><div data-testid="navigation-chart" data-page={JSON.stringify({start:props.start,end:props.end,seconds:props.seconds,display:props.displaySeconds,missing:props.missing,reference:props.reference})}>Verified page</div>}));
const S=1704067200,H=3600;
const source={id:'saved-history-snapshot-long-identifier',source:'Synthetic navigation',market:'spot',symbol:'BTCUSDT',interval_seconds:H,range:[S,S+1200*H],content_sha256:'immutable-a',classification:'synthetic'};
const note={id:'note',revision:2,latest_revision:2,source,start:S+600*H,end:S+624*H,hypothesis:'Original note',falsification:'Original falsification',source_error:null,links:[]};
const props={datasets:[source],onTest:vi.fn(),onBatch:vi.fn()};
const calls=()=>vi.mocked(api).mock.calls.filter(([c])=>c==='local_history_window');
const chart=()=>JSON.parse(screen.getByTestId('navigation-chart').getAttribute('data-page')!);
const input=(label='Go to UTC date')=>screen.getByLabelText(label) as HTMLInputElement;
const button=(name:string)=>screen.getByRole('button',{name}) as HTMLButtonElement;
const type=(value:string)=>fireEvent.change(input(),{target:{value}});
const target=(slot:number)=>navigationUTC(S+slot*H);
function deferred(){let resolve!:(v:any)=>void,reject!:(e:Error)=>void;const promise=new Promise<any>((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};}
function page(p:any,d=source,missingSlots:number[]=[]){
 const times=Array.from({length:(p.end-p.start)/d.interval_seconds},(_,i)=>p.start+i*d.interval_seconds),missing=times.filter(t=>missingSlots.includes((t-S)/H));
 return {source:d,start:p.start,end:p.end,candles:times.filter(t=>!missing.includes(t)).map(time=>({time,open:10,high:12,low:9,close:11,volume:2})),missing,display_reference:{surface:'observation_chart',page_id:`${d.content_sha256}-${p.start}`}};
}
function mock(read:(p:any)=>any=(p)=>page(p),get:(p:any)=>any=()=>note){
 vi.mocked(api).mockImplementation(async(c,p:any)=>{
  if(c==='observation_history')return {rows:[note],next:null};
  if(c==='observation_get')return get(p);
  if(c==='local_history_window')return read(p);
  if(c==='observation_save')return {...note,revision:3,latest_revision:3,start:p.start,end:p.end,hypothesis:p.hypothesis,falsification:p.falsification};
  throw Error(`Unexpected command: ${c}`);
 });
}
async function ready(start=S){await waitFor(()=>expect(chart().start).toBe(start));}
async function go(slot:number){type(target(slot));fireEvent.submit(input().closest('form')!);await ready(S+slot*H);}
beforeEach(()=>{vi.mocked(api).mockReset();props.onTest.mockClear();props.onBatch.mockClear();});

it('keeps typing and invalid submission local, then loads the exact arbitrary opening and relative pages',async()=>{
 mock();render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await ready();
 const original=chart();type('2024-02-31T00:00');fireEvent.submit(input().closest('form')!);
 expect(input().value).toBe('2024-02-31T00:00');expect(input().getAttribute('aria-invalid')).toBe('true');expect(chart()).toEqual(original);expect(calls()).toHaveLength(1);
 expect(input('Observation start (UTC)').getAttribute('aria-invalid')).toBe('false');
 type(target(613)+':00');expect(calls()).toHaveLength(1);fireEvent.submit(input().closest('form')!);await ready(S+613*H);
 expect(input().value).toBe(target(613)+':00');expect(calls().at(-1)?.[1]).toEqual({dataset_id:source.id,start:S+613*H,end:S+1113*H});
 fireEvent.click(button('Later candles'));await ready(S+1113*H);expect(chart().end).toBe(S+1200*H);
 fireEvent.click(button('Earlier candles'));await ready(S+613*H);
 expect(input('Observation start (UTC)').value).toBe(target(0));expect(input('Observation end, exclusive (UTC)').value).toBe(target(1200));
 expect(vi.mocked(api).mock.calls.every(([c])=>['observation_save_history','observation_history','local_history_window'].includes(c))).toBe(true);
});

it('anchors Latest independently of arbitrary windows reaching the end and leaves First/Latest independent of invalid input',async()=>{
 mock();render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await ready();
 expect(button('First saved page').disabled).toBe(true);await go(1100);expect(chart().end).toBe(S+1200*H);expect(button('Latest saved page').disabled).toBe(false);
 type('incomplete');expect(button('Go').disabled).toBe(true);fireEvent.click(button('Latest saved page'));await ready(S+1000*H);
 expect(input().value).toBe(target(1000));expect(button('Latest saved page').disabled).toBe(true);
 type('bad again');fireEvent.click(button('First saved page'));await ready();expect(input().value).toBe(target(0));
 expect(calls().map(([,p]:any)=>[p.start-S,p.end-S])).toEqual([[0,500*H],[1100*H,1200*H],[1000*H,1200*H],[0,500*H]]);
});

it('accepts the final native opening, rejects the exclusive end and misalignment without replacing that chart',async()=>{
 mock();render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await ready();await go(1199);
 expect(chart().end).toBe(S+1200*H);expect(button('Later candles').disabled).toBe(true);
 for(const value of [target(1200),'2024-01-01T00:30','2024-01-01T01:00:01']){type(value);fireEvent.submit(input().closest('form')!);expect(button('Go').disabled).toBe(true);expect(chart().start).toBe(S+1199*H);}
 expect(calls()).toHaveLength(2);
});

it('treats a missing requested opening and wholly missing final page as successful exact reads',async()=>{
 mock(p=>page(p,source,[24,1199]));render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await ready();await go(24);
 expect(screen.getByText(/No recorded candle exists at the requested opening/)).toBeTruthy();expect(chart().missing).toEqual([S+24*H]);
 await go(1199);expect(chart().missing).toEqual([S+1199*H]);expect(screen.getByText(/0 source candles/)).toBeTruthy();expect(screen.queryByText(/Could not read saved history/)).toBeNull();
});

it('browses a dirty unsaved note despite invalid observation dates, then saves only the original corrected note range',async()=>{
 mock();render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await ready();
 fireEvent.change(input('Observation start (UTC)'),{target:{value:target(20)}});fireEvent.change(input('Observation end, exclusive (UTC)'),{target:{value:target(19)}});
 fireEvent.change(input('Observation hypothesis'),{target:{value:'Keep unsaved hypothesis'}});
 expect(button('Return to observation start').disabled).toBe(true);expect(button('Latest saved page').disabled).toBe(false);
 fireEvent.click(button('Latest saved page'));await ready(S+1000*H);await go(613);
 expect(input('Observation start (UTC)').value).toBe(target(20));expect(input('Observation hypothesis').value).toBe('Keep unsaved hypothesis');
 fireEvent.change(input('Observation end, exclusive (UTC)'),{target:{value:target(30)}});fireEvent.click(button('Return to observation start'));await ready(S+20*H);
 await go(800);fireEvent.click(button('Save observation'));await screen.findByRole('heading',{name:'Observation · revision 3'});
 expect(api).toHaveBeenCalledWith('observation_save',expect.objectContaining({start:S+20*H,end:S+30*H,hypothesis:'Keep unsaved hypothesis'}),expect.objectContaining({onRequest:expect.any(Function),onPhase:expect.any(Function)}));expect(chart().start).toBe(S+800*H);
});

it('preserves saved revision, dirty text, original range and display during browsing and explicit save',async()=>{
 mock();render(<Observations {...props} request={{id:note.id,revision:2,request:1}}/>);await ready(note.start);
 fireEvent.change(screen.getByLabelText('Saved-history display interval'),{target:{value:'14400'}});
 fireEvent.change(input('Observation hypothesis'),{target:{value:'New unsaved wording'}});fireEvent.change(input('Observation falsification'),{target:{value:'Keep this too'}});
 await go(613);expect(chart().display).toBe(14400);expect(input('Observation start (UTC)').value).toBe(target(600));expect(input('Observation end, exclusive (UTC)').value).toBe(target(624));
 type('invalid browse date');fireEvent.click(button('Return to observation start'));await ready(note.start);expect(input().value).toBe(target(600));
 const count=calls().length;fireEvent.click(button('Save note revision'));await screen.findByRole('heading',{name:'Observation · revision 3'});expect(calls()).toHaveLength(count);
 expect(api).toHaveBeenCalledWith('observation_save',expect.objectContaining({observation_id:'note',expected_revision:2,dataset_id:source.id,start:note.start,end:note.end,hypothesis:'New unsaved wording',falsification:'Keep this too'}),expect.objectContaining({onRequest:expect.any(Function),onPhase:expect.any(Function)}));
 fireEvent.click(button('Test observation in Lab'));expect(props.onTest).toHaveBeenCalledWith({id:'note',revision:3,source,start:note.start,end:note.end});
});

it('retains same-source display while an explicit historical reopen resets only browsing to that revision start',async()=>{
 mock(undefined,p=>({...note,revision:p.revision??3,latest_revision:3}));const view=render(<Observations {...props} request={{id:note.id,revision:2,request:1}}/>);await ready(note.start);
 fireEvent.change(screen.getByLabelText('Saved-history display interval'),{target:{value:'86400'}});await go(613);
 view.rerender(<Observations {...props} request={{id:note.id,revision:2,request:2}}/>);await ready(note.start);
 expect(input().value).toBe(target(600));expect(chart().display).toBe(86400);expect(input('Observation hypothesis').disabled).toBe(true);
 fireEvent.click(button('Open latest revision'));await screen.findByRole('heading',{name:'Observation · revision 3'});await ready(note.start);expect(input('Observation hypothesis').disabled).toBe(false);expect(chart().display).toBe(86400);
});

it('retries the immutable failed first window even after invalid typing, preserves errors on repeated failure and bounds duplicate activation',async()=>{
 const pending=deferred();let reads=0;mock(p=>{if(++reads<3)throw Error(`Read failure ${reads}`);return pending.promise;});
 render(<Observations {...props} request={{dataset:source.id,request:1}}/>);
 await screen.findByText('Could not read saved history: Read failure 1');expect(screen.queryByTestId('navigation-chart')).toBeNull();expect(screen.getByText(`Snapshot: ${source.id}`,{exact:false})).toBeTruthy();
 type('invalid retry draft');fireEvent.click(button('Retry reading'));await screen.findByText('Could not read saved history: Read failure 2');
 const retry=button('Retry reading');act(()=>{fireEvent.click(retry);fireEvent.click(retry);fireEvent.submit(input().closest('form')!);});
 expect(calls()).toHaveLength(3);expect(calls().every(([,p])=>JSON.stringify(p)===JSON.stringify({dataset_id:source.id,start:S,end:S+500*H}))).toBe(true);
 await act(async()=>pending.resolve(page({start:S,end:S+500*H})));await ready();expect(input().value).toBe('invalid retry draft');expect(input().getAttribute('aria-invalid')).toBe('true');expect(screen.queryByText(/Could not read saved history/)).toBeNull();
});

it('removes a prior chart on later failure, retains dirty notes/display and separates list recovery',async()=>{
 let reads=0;mock(p=>{if(++reads===2)throw Error('Page unavailable');return page(p);});const previous=vi.mocked(api).getMockImplementation()!;
 vi.mocked(api).mockImplementation((c,p)=>c==='observation_history'?Promise.reject(Error('List unavailable')):previous(c,p));
 render(<Observations {...props} request={{id:note.id,revision:2,request:1}}/>);await ready(note.start);
 fireEvent.change(screen.getByLabelText('Saved-history display interval'),{target:{value:'86400'}});fireEvent.change(input('Observation hypothesis'),{target:{value:'Still dirty'}});
 fireEvent.click(button('First saved page'));await screen.findByText('Could not read saved history: Page unavailable');expect(screen.queryByTestId('navigation-chart')).toBeNull();
 expect(button('Earlier candles').disabled).toBe(true);expect(button('Later candles').disabled).toBe(true);expect(input('Observation hypothesis').value).toBe('Still dirty');
 type('invalid');fireEvent.click(button('Retry reading'));await ready();expect(chart().display).toBe(86400);expect(screen.getByText(/Could not load saved observations: List unavailable/)).toBeTruthy();expect(input().value).toBe('invalid');
 fireEvent.click(button('Latest saved page'));await ready(S+1000*H);expect(input('Observation hypothesis').value).toBe('Still dirty');
});

it('does not overwrite keystrokes typed during a pending read or queue duplicate Go/Enter',async()=>{
 const pending=deferred();let reads=0;mock(p=>++reads===1?page(p):pending.promise);render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await ready();
 type(target(613));const form=input().closest('form')!;act(()=>{fireEvent.submit(form);fireEvent.submit(form);fireEvent.click(button('Go'));});
 expect(calls()).toHaveLength(2);expect(screen.queryByTestId('navigation-chart')).toBeNull();expect(button('Latest saved page').disabled).toBe(true);type('next draft, not submitted');
 await act(async()=>pending.resolve(page({start:S+613*H,end:S+1113*H})));await ready(S+613*H);expect(input().value).toBe('next draft, not submitted');expect(calls()).toHaveLength(2);
});

it.each(['success','failure'] as const)('ignores an older source %s after the next source has loaded',async outcome=>{
 const old=deferred(),b={...source,id:'second-source',content_sha256:'immutable-b'};mock(p=>p.dataset_id===source.id?old.promise:page(p,b));
 render(<Observations {...props} datasets={[source,b]} request={{dataset:source.id,request:1}}/>);await waitFor(()=>expect(calls()).toHaveLength(1));
 fireEvent.change(input('Observation history'),{target:{value:b.id}});await ready();expect(chart().reference.page_id).toContain('immutable-b');
 await act(async()=>{if(outcome==='success')old.resolve(page({start:S,end:S+500*H}));else old.reject(Error('Stale source failure'));});
 expect(chart().reference.page_id).toContain('immutable-b');expect(screen.queryByText(/Stale source failure/)).toBeNull();expect(button('Latest saved page').disabled).toBe(false);
});

it('ignores old rejection and finally while a newer exact reopen is still pending',async()=>{
 const old=deferred(),fresh=deferred();let reads=0;mock(()=>++reads===1?old.promise:fresh.promise);const view=render(<Observations {...props} request={{id:note.id,revision:2,request:1}}/>);await waitFor(()=>expect(calls()).toHaveLength(1));
 view.rerender(<Observations {...props} request={{id:note.id,revision:2,request:2}}/>);await waitFor(()=>expect(calls()).toHaveLength(2));
 await act(async()=>old.reject(Error('Stale rejection')));expect(screen.queryByText(/Stale rejection/)).toBeNull();expect(button('Go').disabled).toBe(true);expect(screen.getByText(/Reading verified local history/)).toBeTruthy();
 await act(async()=>fresh.resolve(page({start:note.start,end:note.start+500*H})));await ready(note.start);
});

it('fails closed on a same-ID declaration change and retains the dirty note instead of reading a substitute',async()=>{
 const pending=deferred();mock(()=>pending.promise);const view=render(<Observations {...props} request={{id:note.id,revision:2,request:1}}/>);await waitFor(()=>expect(calls()).toHaveLength(1));
 fireEvent.change(input('Observation hypothesis'),{target:{value:'Retain across source change'}});
 view.rerender(<Observations {...props} datasets={[{...source,content_sha256:'changed-declaration'}]} request={{id:note.id,revision:2,request:1}}/>);
 await act(async()=>pending.resolve(page({start:note.start,end:note.start+500*H})));expect(screen.queryByTestId('navigation-chart')).toBeNull();expect(calls()).toHaveLength(1);
 expect(screen.getByText(/Exact saved source changed. Note dates and text are retained/)).toBeTruthy();expect(input('Observation hypothesis').value).toBe('Retain across source change');expect(input('Observation start (UTC)').value).toBe(target(600));expect(button('Go').disabled).toBe(true);
});

it('rejects changed verified identity during ordinary paging but permits an explicit same-ID reselection with Source display',async()=>{
 let identity='immutable-a';mock(p=>page(p,{...source,content_sha256:identity}));const view=render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await ready();
 fireEvent.change(screen.getByLabelText('Saved-history display interval'),{target:{value:'86400'}});identity='immutable-replacement';fireEvent.click(button('Latest saved page'));
 await screen.findByText(/Could not read saved history: Exact saved source changed/);expect(screen.queryByTestId('navigation-chart')).toBeNull();expect(button('Retry reading').disabled).toBe(true);
 view.rerender(<Observations {...props} request={{dataset:source.id,request:2}}/>);await ready();expect(chart().display).toBe(H);expect(input().value).toBe(target(0));
});

it('resets A to B to A source-scoped dates and display without resurrecting bookmarks',async()=>{
 const b={...source,id:'b',content_sha256:'b'};mock(p=>page(p,p.dataset_id==='b'?b:source));render(<Observations {...props} datasets={[source,b]} request={{dataset:source.id,request:1}}/>);await ready();
 fireEvent.change(screen.getByLabelText('Saved-history display interval'),{target:{value:'86400'}});await go(613);
 fireEvent.change(input('Observation history'),{target:{value:'b'}});await ready();expect(chart().display).toBe(H);await go(800);
 fireEvent.change(input('Observation history'),{target:{value:source.id}});await ready();expect(chart().display).toBe(H);expect(input().value).toBe(target(0));
});

it.each(['dataset','window','saved identity'] as const)('rejects a response with the wrong %s without showing a chart',async mismatch=>{
 mock(p=>mismatch==='dataset'?page(p,{...source,id:'other'}):mismatch==='window'?page({...p,start:p.start+H}):page(p,{...source,content_sha256:'wrong'}));
 render(<Observations {...props} request={mismatch==='saved identity'?{id:note.id,revision:2,request:1}:{dataset:source.id,request:1}}/>);
 await screen.findByText(/Could not read saved history:/);expect(screen.queryByTestId('navigation-chart')).toBeNull();expect(calls()).toHaveLength(1);
});

it('uses retained verified native metadata after a failure rather than the reduced list declaration',async()=>{
 const listed={...source,interval_seconds:60,range:[S,S+4*H],provenance:[{kind:'fixture'}]};let reads=0;mock(p=>{if(++reads===2)throw Error('Temporary read failure');return page(p);});
 render(<Observations {...props} datasets={[listed]} request={{dataset:source.id,request:1}}/>);await ready();expect(chart().seconds).toBe(H);expect(button('First saved page').disabled).toBe(false);
 fireEvent.click(button('Latest saved page'));await screen.findByText(/Temporary read failure/);expect(calls().at(-1)?.[1]).toEqual({dataset_id:source.id,start:S+1000*H,end:S+1200*H});
 fireEvent.click(button('First saved page'));await ready();expect(calls().at(-1)?.[1]).toEqual({dataset_id:source.id,start:S,end:S+500*H});
});

it('does not bypass unavailable saved sources or malformed metadata',async()=>{
 mock(undefined,()=>({...note,source_error:'Exact source unavailable'}));const view=render(<Observations {...props} request={{id:note.id,revision:2,request:1}}/>);
 await screen.findByText(/Exact source unavailable/);for(const name of ['Go','First saved page','Latest saved page','Return to observation start'])expect(button(name).disabled).toBe(true);expect(calls()).toHaveLength(0);
 view.rerender(<Observations {...props} datasets={[{...source,range:[NaN,Infinity]}]} request={{dataset:source.id,request:2}}/>);
 await screen.findByText('Saved-history navigation is unavailable: invalid or unrepresentable source boundaries.');expect(calls()).toHaveLength(0);
});

it('ignores completion after unmount',async()=>{
 const pending=deferred();mock(()=>pending.promise);const view=render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await waitFor(()=>expect(calls()).toHaveLength(1));view.unmount();
 await act(async()=>pending.resolve(page({start:S,end:S+500*H})));expect(screen.queryByTestId('navigation-chart')).toBeNull();expect(calls()).toHaveLength(1);
});

it('keeps the missing-source guard after New observation until an explicit source choice',async()=>{
 mock(undefined,()=>({...note,source_error:'Exact source unavailable'}));render(<Observations {...props} request={{id:note.id,revision:2,request:1}}/>);
 await screen.findByText(/Exact source unavailable/);fireEvent.click(button('New observation'));expect(button('Go').disabled).toBe(true);expect(button('First saved page').disabled).toBe(true);expect(calls()).toHaveLength(0);
 fireEvent.change(input('Observation history'),{target:{value:''}});fireEvent.change(input('Observation history'),{target:{value:source.id}});await ready();expect(calls()).toHaveLength(1);
});

it('fails closed when a save response changes exact source identity and preserves the local note text',async()=>{
 mock();const previous=vi.mocked(api).getMockImplementation()!;vi.mocked(api).mockImplementation((c,p)=>c==='observation_save'?Promise.resolve({...note,source:{...source,content_sha256:'different-at-save'}}):previous(c,p));
 render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await ready();fireEvent.change(input('Observation hypothesis'),{target:{value:'Keep this original draft'}});fireEvent.click(button('Save observation'));
 await screen.findByText(/The save returned a different exact source/);expect(screen.queryByTestId('navigation-chart')).toBeNull();expect(input('Observation hypothesis').value).toBe('Keep this original draft');expect(button('Go').disabled).toBe(true);expect(screen.getByRole('heading',{name:'New observation'})).toBeTruthy();
});


it('retains source_error returned with a saved revision even after clearing the note',async()=>{
 mock();const previous=vi.mocked(api).getMockImplementation()!;vi.mocked(api).mockImplementation((c,p)=>c==='observation_save'?Promise.resolve({...note,source_error:'Saved source became unavailable'}):previous(c,p));
 render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await ready();fireEvent.change(input('Observation hypothesis'),{target:{value:'Explicit save'}});fireEvent.click(button('Save observation'));
 await screen.findByText(/Saved source became unavailable/);expect(screen.queryByTestId('navigation-chart')).toBeNull();expect(button('Go').disabled).toBe(true);fireEvent.click(button('New observation'));expect(button('First saved page').disabled).toBe(true);expect(calls()).toHaveLength(1);
});
