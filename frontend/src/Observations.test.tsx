import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,within} from '@testing-library/react';
import Observations from './Observations';
import LibraryResearch from './LibraryResearch';
import {defaultProfile} from './model';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
vi.mock('./ObservationChart',()=>({default:({candles}:any)=><div>Chart: {candles.length} candles</div>}));
const source={id:'source',source:'Synthetic workflow',market:'spot',symbol:'BTCUSDT',range:[0,3600],interval_seconds:60,classification:'synthetic'};
const record={id:'note',revision:1,latest_revision:1,source,start:600,end:1200,hypothesis:'Rising prices',falsification:'Lower close',source_error:null,links:[]};
const selections=[{entry_id:'rsi-threshold',version:1,minutes:1,parameters:{period:2}}];
const page={source,start:0,end:3600,candles:[{time:600,open:100,high:102,low:99,close:101}],missing:[]};
function mock(){vi.mocked(api).mockImplementation(async command=>{if(command==='observation_history')return {rows:[record],next:null};if(command==='observation_get')return record;if(command==='local_history_window')return page;if(command==='library_batch_history')return {rows:[],next:null};return {};});}

it('opens exact saved local history without live fetch or any execution, and preserves failed note edits',async()=>{
 mock();const onTest=vi.fn();render(<Observations datasets={[source]} onTest={onTest} onBatch={()=>{}}/>);
 fireEvent.click(await screen.findByRole('button',{name:/Rising prices/}));
 expect(await screen.findByText('Chart: 1 candles')).toBeTruthy();
 expect(screen.getByText(/Synthetic fixture/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Test observation in Lab'}));
 expect(onTest).toHaveBeenCalledWith(expect.objectContaining({id:'note',revision:1,start:600,end:1200,source}));
 fireEvent.change(screen.getByLabelText('Observation hypothesis'),{target:{value:'Edited hypothesis'}});
 expect((screen.getByRole('button',{name:'Test observation in Lab'}) as HTMLButtonElement).disabled).toBe(true);
 const previous=vi.mocked(api).getMockImplementation()!;vi.mocked(api).mockImplementation(async (c,p)=>{if(c==='observation_save')throw Error('storage conflict');return previous(c,p);});
 fireEvent.click(screen.getByRole('button',{name:'Save note revision'}));
 expect(await screen.findByText(/storage conflict/)).toBeTruthy();expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).value).toBe('Edited hypothesis');
 expect(vi.mocked(api).mock.calls.some(([c])=>['market_open','market_chart','start_run','library_batch_start','history_prepare'].includes(c))).toBe(false);
});

it('discloses unavailable exact source without substituting another snapshot',async()=>{
 mock();const previous=vi.mocked(api).getMockImplementation()!;vi.mocked(api).mockImplementation(async(c,p)=>c==='observation_get'?{...record,source_error:'Exact saved history unavailable'}:previous(c,p));
 render(<Observations datasets={[]} request={{id:'note',revision:1,request:1}} onTest={()=>{}} onBatch={()=>{}}/>);
 expect(await screen.findByText(/No replacement or network download/)).toBeTruthy();
 expect((screen.getByRole('button',{name:'Test observation in Lab'}) as HTMLButtonElement).disabled).toBe(true);
 expect(vi.mocked(api).mock.calls.some(([c])=>c==='local_history_window')).toBe(false);
});

it('hands off locked exact dates, survives late warmup, blocks insufficient warmup and requires explicit detach',async()=>{
 mock();let resolveWarmup:(v:any)=>void=()=>{};
 const previous=vi.mocked(api).getMockImplementation()!;vi.mocked(api).mockImplementation(async(c,p)=>c==='library_warmup'?await new Promise(r=>{resolveWarmup=r;}):previous(c,p));
 const props={selections,datasets:[source],profile:defaultProfile,onActive:vi.fn(),onOpenRun:vi.fn(),onReport:vi.fn(),preferredDataset:{id:'source',request:1,observation:record}};
 const view=render(<LibraryResearch {...props}/>);
 expect(await screen.findByRole('dialog')).toBeTruthy();
 await waitFor(()=>expect((screen.getByLabelText('Evaluation start (UTC)') as HTMLInputElement).value).toBe('1970-01-01T00:10'));
 resolveWarmup({start:900,end:3600,available:true});
 expect(await screen.findByText(/Not enough preceding warmup/)).toBeTruthy();
 expect((screen.getByLabelText('Evaluation start (UTC)') as HTMLInputElement).value).toBe('1970-01-01T00:10');
 expect((screen.getByRole('button',{name:'Use suggested period'}) as HTMLButtonElement).disabled).toBe(true);
 expect((screen.getByRole('button',{name:'Review test'}) as HTMLButtonElement).disabled).toBe(true);
 view.rerender(<LibraryResearch {...props} profile={{...defaultProfile,symbol:'ETHUSDT'}}/>);
 expect(await screen.findByText(/Observation source and period are fixed/)).toBeTruthy();
 view.rerender(<LibraryResearch {...props}/>);
 expect((screen.getByLabelText('Batch dataset') as HTMLSelectElement).value).toBe('source');
 fireEvent.click(screen.getByRole('button',{name:'Detach observation to change source or dates'}));
 expect((screen.getByLabelText('Evaluation start (UTC)') as HTMLInputElement).disabled).toBe(false);
 expect(vi.mocked(api).mock.calls.some(([c])=>c==='library_batch_start')).toBe(false);
});

it('sends revision-bound link only on explicit reviewed Start and retains context after admission failure',async()=>{
 mock();const previous=vi.mocked(api).getMockImplementation()!;vi.mocked(api).mockImplementation(async(c,p)=>{
  if(c==='library_warmup')return {start:120,end:3600,available:true};
  if(c==='library_batch_preview')return {contract_sha256:'contract',modeled_minutes:20,rows:[{kind:'graph',name:'RSI',error:null}]};
  if(c==='library_batch_start')throw Error('link persistence failed');
  return previous(c,p);
 });
 render(<LibraryResearch selections={selections} datasets={[source]} profile={defaultProfile} onActive={()=>{}} onOpenRun={()=>{}} onReport={()=>{}} preferredDataset={{id:'source',request:1,observation:record}}/>);
 await waitFor(()=>expect((screen.getByRole('button',{name:'Review test'}) as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(screen.getByRole('button',{name:'Review test'}));fireEvent.click(await screen.findByRole('button',{name:'Start 1 tests'}));
 expect((await screen.findAllByText(/link persistence failed/)).length).toBeGreaterThan(0);
 expect(api).toHaveBeenCalledWith('library_batch_start',expect.objectContaining({dataset_id:'source',start:600,end:1200,observation:{id:'note',revision:1}}));
 expect(screen.getByRole('region',{name:'Observation test context'})).toBeTruthy();
});

it('reloads the same observation after Lab handoff, then saves edits without rereading on keystrokes',async()=>{
 mock();vi.mocked(api).mockClear();const onTest=vi.fn();
 const previous=vi.mocked(api).getMockImplementation()!;
 vi.mocked(api).mockImplementation(async(c,p:any)=>c==='observation_save'?{...record,revision:2,latest_revision:2,hypothesis:p.hypothesis}:previous(c,p));
 const props={datasets:[source],onTest,onBatch:vi.fn(),request:{id:'note',revision:1,request:1}};
 const view=render(<Observations {...props}/>);
 expect(await screen.findByText('Chart: 1 candles')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Test observation in Lab'}));
 expect(onTest).toHaveBeenCalledOnce();
 // App preserves this mounted component while Lab is visible; returning opens
 // exactly the same source/start/revision, which previously cleared it forever.
 view.rerender(<Observations {...props} request={{...props.request,request:2}}/>);
 await waitFor(()=>expect(vi.mocked(api).mock.calls.filter(([c])=>c==='local_history_window')).toHaveLength(2));
 expect(await screen.findByText('Chart: 1 candles')).toBeTruthy();
 fireEvent.change(screen.getByLabelText('Observation hypothesis'),{target:{value:'Edited after the test'}});
 fireEvent.change(screen.getByLabelText('Observation falsification'),{target:{value:''}});
 expect(vi.mocked(api).mock.calls.filter(([c])=>c==='local_history_window')).toHaveLength(2);
 expect((screen.getByRole('button',{name:'Save note revision'}) as HTMLButtonElement).disabled).toBe(false);
 fireEvent.click(screen.getByRole('button',{name:'Save note revision'}));
 expect(await screen.findByRole('heading',{name:'Observation · revision 2'})).toBeTruthy();
 expect(api).toHaveBeenCalledWith('observation_save',expect.objectContaining({observation_id:'note',expected_revision:1,hypothesis:'Edited after the test',falsification:''}));
});

it('keeps a newer reopen page when an older page response resolves later',async()=>{
 mock();vi.mocked(api).mockClear();const previous=vi.mocked(api).getMockImplementation()!;
 let resolveOld:(v:any)=>void=()=>{};let reads=0;
 vi.mocked(api).mockImplementation(async(c,p)=>{
  if(c==='local_history_window'){reads++;if(reads===1)return new Promise(r=>{resolveOld=r;});return {...page,candles:[...page.candles,{...page.candles[0],time:660}]};}
  return previous(c,p);
 });
 const props={datasets:[source],onTest:vi.fn(),onBatch:vi.fn(),request:{id:'note',revision:1,request:1}};
 const view=render(<Observations {...props}/>);
 await waitFor(()=>expect(reads).toBe(1));
 view.rerender(<Observations {...props} request={{...props.request,request:2}}/>);
 expect(await screen.findByText('Chart: 2 candles')).toBeTruthy();
 resolveOld(page);
 await waitFor(()=>expect(screen.getByText('Chart: 2 candles')).toBeTruthy());
 expect(screen.queryByText('Chart: 1 candles')).toBeNull();
});

it('shows verified page provenance for a dataset-list source without a classification',async()=>{
 mock();render(<Observations datasets={[{...source,classification:undefined}]} onTest={()=>{}} onBatch={()=>{}}/>);
 fireEvent.change(screen.getByLabelText('Observation history'),{target:{value:'source'}});
 expect(await screen.findByText('Chart: 1 candles')).toBeTruthy();
 expect(screen.getByText(/Local snapshot · synthetic/)).toBeTruthy();
 expect(screen.queryByText(/Provenance shown after page verification/)).toBeNull();
});


it('keeps the draft attachment visible with setup closed and returns to its exact historical revision without mutation',async()=>{
 mock();vi.mocked(api).mockClear();const onObservation=vi.fn();
 const historical={...record,id:'original-note-123',revision:2,latest_revision:4};
 const props={selections,datasets:[source],profile:defaultProfile,onActive:vi.fn(),onOpenRun:vi.fn(),onReport:vi.fn(),onObservation,preferredDataset:{id:'source',request:1,observation:historical}};
 const view=render(<LibraryResearch {...props} view="catalog"/>);
 await screen.findByRole('dialog');
 fireEvent.click(screen.getByRole('button',{name:'Back to strategies'}));
 expect(screen.queryByRole('dialog')).toBeNull();
 const attachment=screen.getByRole('region',{name:'Attached observation for draft test'});
 expect(within(attachment).getByText('Attached to draft test')).toBeTruthy();
 expect(within(attachment).getByText('Observation original · revision 2')).toBeTruthy();
 expect(within(attachment).getByText('1970-01-01 00:10 — 1970-01-01 00:20 UTC · fixed period (end exclusive)')).toBeTruthy();
 expect(within(attachment).queryByText(record.hypothesis)).toBeNull();
 fireEvent.click(within(attachment).getByRole('button',{name:'Return to observation'}));
 expect(onObservation).toHaveBeenCalledExactlyOnceWith('original-note-123',2);
 // Ordinary route suspension and Saved tests do not replace the draft attachment.
 view.rerender(<LibraryResearch {...props} view="saved" suspendSetup/>);
 expect(screen.queryByRole('region',{name:'Attached observation for draft test'})).toBeNull();
 view.rerender(<LibraryResearch {...props} view="catalog"/>);
 expect(screen.getByRole('region',{name:'Attached observation for draft test'})).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Edit test setup'}));
 expect((screen.getByLabelText('Evaluation start (UTC)') as HTMLInputElement).value).toBe('1970-01-01T00:10');
 expect((screen.getByLabelText('Evaluation end, exclusive (UTC)') as HTMLInputElement).value).toBe('1970-01-01T00:20');
 expect((screen.getByLabelText('Batch dataset') as HTMLSelectElement).value).toBe('source');
 expect((screen.getByLabelText('Evaluation start (UTC)') as HTMLInputElement).disabled).toBe(true);
 expect(vi.mocked(api).mock.calls.some(([c])=>/save|start|preview|resume|prepare/.test(c))).toBe(false);
});

it('adds no observation controls to an unattached Lab draft',async()=>{
 mock();render(<LibraryResearch selections={selections} datasets={[source]} profile={defaultProfile} onActive={()=>{}} onOpenRun={()=>{}} onReport={()=>{}} view="catalog"/>);
 await waitFor(()=>expect(api).toHaveBeenCalledWith('library_batch_history',{before:null}));
 expect(screen.queryByRole('region',{name:'Attached observation for draft test'})).toBeNull();
 expect(screen.queryByRole('button',{name:'Return to observation'})).toBeNull();
});
