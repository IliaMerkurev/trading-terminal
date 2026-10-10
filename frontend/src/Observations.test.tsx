import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,within} from '@testing-library/react';
import Observations from './Observations';
import LibraryResearch from './LibraryResearch';
import {defaultProfile} from './model';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
vi.mock('./ObservationChart',()=>({default:({candles,missing,seconds,displaySeconds,start,end,reference}:any)=><div data-testid="observation-chart" data-chart-page={JSON.stringify({candles,missing,seconds,displaySeconds,start,end,reference})}>Chart: {candles.length} candles</div>}));
const source={id:'source',source:'Synthetic workflow',market:'spot',symbol:'BTCUSDT',range:[0,3600],interval_seconds:60,classification:'synthetic'};
const record={id:'note',revision:1,latest_revision:1,source,start:600,end:1200,hypothesis:'Rising prices',falsification:'Lower close',source_error:null,links:[]};
const selections=[{entry_id:'rsi-threshold',version:1,minutes:1,parameters:{period:2}}];
const page={source,start:0,end:3600,candles:[{time:600,open:100,high:102,low:99,close:101}],missing:[]};
function mock(){vi.mocked(api).mockImplementation(async(command,p:any)=>{if(command==='observation_history')return {rows:[record],next:null};if(command==='observation_get')return record;if(command==='local_history_window')return {...page,start:p.start,end:p.end};if(command==='library_batch_history')return {rows:[],next:null};return {};});}

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
 vi.mocked(api).mockImplementation(async(c,p:any)=>{
  if(c==='local_history_window'){reads++;if(reads===1)return new Promise(r=>{resolveOld=r;});return {...page,start:p.start,end:p.end,candles:[...page.candles,{...page.candles[0],time:660}]};}
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

const hourlySource={...source,range:[1704067200,1704240000],interval_seconds:3600}; // Jan 1–3, 2024 UTC, end exclusive.
const periodLabels=['Observation start (UTC)','Observation end, exclusive (UTC)'];
function mockPeriod(d=hourlySource){
 mock();vi.mocked(api).mockClear();
 const previous=vi.mocked(api).getMockImplementation()!;
 vi.mocked(api).mockImplementation(async(c,p:any)=>{
  if(c==='local_history_window')return {...page,source:d,start:p.start,end:p.end};
  if(c==='observation_save')return {...record,source:d,start:p.start,end:p.end,hypothesis:p.hypothesis,falsification:p.falsification};
  return previous(c,p);
 });
}

it.each([
 ['missing start',3600,'','2024-01-03T00:00','Enter a valid start and end time (UTC).',[true,false]],
 ['missing end',3600,'2024-01-01T00:00','','Enter a valid start and end time (UTC).',[false,true]],
 ['reversed dates',3600,'2024-01-02T00:00','2024-01-01T00:00','The observation end must be after its start. The end is exclusive.',[true,true]],
 ['equal dates',3600,'2024-01-02T00:00','2024-01-02T00:00','The observation end must be after its start. The end is exclusive.',[true,true]],
 ['start before history',3600,'2023-12-31T23:00','2024-01-03T00:00','Keep both dates within the available saved history below.',[true,false]],
 ['end after history',3600,'2024-01-01T00:00','2024-01-03T01:00','Keep both dates within the available saved history below.',[false,true]],
 ['half-hour start',3600,'2024-01-01T00:30','2024-01-03T00:00','Use 1h UTC candle boundaries for the start.',[true,false]],
 ['half-hour end',3600,'2024-01-01T00:00','2024-01-02T23:30','Use 1h UTC candle boundaries for the end.',[false,true]],
 ['both off 4h boundaries',14400,'2024-01-01T01:00','2024-01-02T06:00','Use 4h UTC candle boundaries for both dates.',[true,true]],
 ['partial minute',60,'2024-01-01T00:00:30.000','2024-01-03T00:00','Use 1m UTC candle boundaries for the start.',[true,false]],
] as const)('explains %s, preserves exact input and clears the error only after correction',async(_name,step,start,end,message,invalid)=>{
 const d={...hourlySource,interval_seconds:step};mockPeriod(d);const onTest=vi.fn();
 render(<Observations datasets={[d]} request={{dataset:d.id,request:1}} onTest={onTest} onBatch={vi.fn()}/>);
 await screen.findByText('Chart: 1 candles');
 fireEvent.change(screen.getByLabelText('Observation hypothesis'),{target:{value:'Synthetic draft, no implicit save'}});
 fireEvent.change(screen.getByLabelText('Observation falsification'),{target:{value:'Keep this draft too'}});
 fireEvent.change(screen.getByLabelText(periodLabels[0]),{target:{value:start}});
 fireEvent.change(screen.getByLabelText(periodLabels[1]),{target:{value:end}});
 const error=screen.getByText(message),live=error.parentElement!;
 expect(live.getAttribute('aria-live')).toBe('polite');
 expect(live.getAttribute('aria-atomic')).toBe('true');
 const help=screen.getByText(/Available saved history: 2024-01-01 00:00 to 2024-01-03 00:00 UTC \(end exclusive\)/);
 const inputs=periodLabels.map(label=>screen.getByLabelText(label) as HTMLInputElement);
 inputs.forEach((input,i)=>{
  expect(input.value).toBe(i===0?start:end);
  expect(input.getAttribute('aria-invalid')).toBe(String(invalid[i]));
  expect(input.getAttribute('aria-describedby')?.split(' ')).toEqual(invalid[i]?[help.id,live.id]:[help.id]);
 });
 for(const name of ['Return to observation start','Save observation','Test observation in Lab']){
  const button=screen.getByRole('button',{name}) as HTMLButtonElement;
  expect(button.disabled).toBe(true);fireEvent.click(button);
 }
 expect(vi.mocked(api).mock.calls.map(([c])=>c)).toEqual(['observation_history','local_history_window']);
 expect(onTest).not.toHaveBeenCalled();
 fireEvent.change(inputs[0],{target:{value:'2024-01-01T00:00'}});
 fireEvent.change(inputs[1],{target:{value:'2024-01-03T00:00'}});
 expect(screen.queryByText(message)).toBeNull();
 inputs.forEach(input=>{expect(input.getAttribute('aria-invalid')).toBe('false');expect(input.getAttribute('aria-describedby')).toBe(help.id);});
 expect((screen.getByRole('button',{name:'Return to observation start'}) as HTMLButtonElement).disabled).toBe(false);
 expect((screen.getByRole('button',{name:'Save observation'}) as HTMLButtonElement).disabled).toBe(false);
 // A valid period is not a saved note: Lab still requires an explicit save.
 expect((screen.getByRole('button',{name:'Test observation in Lab'}) as HTMLButtonElement).disabled).toBe(true);
 expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).value).toBe('Synthetic draft, no implicit save');
 expect((screen.getByLabelText('Observation falsification') as HTMLTextAreaElement).value).toBe('Keep this draft too');
 expect(vi.mocked(api).mock.calls.map(([c])=>c)).toEqual(['observation_history','local_history_window']);
});

it('accepts the last full source candle and preserves the exclusive endpoint through explicit save and Lab handoff',async()=>{
 const d={...hourlySource,interval_seconds:14400};mockPeriod(d);const onTest=vi.fn();
 render(<Observations datasets={[d]} request={{dataset:d.id,request:1}} onTest={onTest} onBatch={vi.fn()}/>);
 await screen.findByText('Chart: 1 candles');
 fireEvent.change(screen.getByLabelText(periodLabels[0]),{target:{value:'2024-01-02T20:00'}});
 expect(screen.getByLabelText(periodLabels[1]).getAttribute('aria-invalid')).toBe('false');
 expect((screen.getByRole('button',{name:'Return to observation start'}) as HTMLButtonElement).disabled).toBe(false);
 expect((screen.getByRole('button',{name:'Save observation'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.change(screen.getByLabelText('Observation hypothesis'),{target:{value:'One final 4h candle'}});
 expect(vi.mocked(api).mock.calls.map(([c])=>c)).toEqual(['observation_history','local_history_window']);
 fireEvent.click(screen.getByRole('button',{name:'Return to observation start'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('local_history_window',{dataset_id:d.id,start:1704225600,end:1704240000}));
 await waitFor(()=>expect((screen.getByRole('button',{name:'Save observation'}) as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(screen.getByRole('button',{name:'Save observation'}));
 await waitFor(()=>expect((screen.getByRole('button',{name:'Test observation in Lab'}) as HTMLButtonElement).disabled).toBe(false));
 expect(vi.mocked(api).mock.calls.filter(([c])=>c==='observation_save')).toEqual([['observation_save',{observation_id:null,expected_revision:0,dataset_id:d.id,start:1704225600,end:1704240000,hypothesis:'One final 4h candle',falsification:''}]]);
 expect(onTest).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Test observation in Lab'}));
 expect(onTest).toHaveBeenCalledExactlyOnceWith({id:'note',revision:1,source:d,start:1704225600,end:1704240000});
 expect(vi.mocked(api).mock.calls.some(([c])=>/start|preview|prepare|resume/.test(c))).toBe(false);
});

it('keeps historical observation dates and notes locked while allowing an explicit exact-revision Lab handoff',async()=>{
 mockPeriod();const onTest=vi.fn(),historical={...record,latest_revision:2};
 const previous=vi.mocked(api).getMockImplementation()!;
 vi.mocked(api).mockImplementation(async(c,p:any)=>c==='observation_get'?historical:c==='local_history_window'?{...page,start:p.start,end:p.end}:previous(c,p));
 render(<Observations datasets={[source]} request={{id:'note',revision:1,request:1}} onTest={onTest} onBatch={vi.fn()}/>);
 await screen.findByText('Chart: 1 candles');
 expect(screen.getByText(/Historical revision. Linked tests keep this exact note/)).toBeTruthy();
 periodLabels.forEach(label=>{const input=screen.getByLabelText(label) as HTMLInputElement;expect(input.disabled).toBe(true);expect(input.getAttribute('aria-invalid')).toBe('false');});
 expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).disabled).toBe(true);
 expect((screen.getByLabelText('Observation falsification') as HTMLTextAreaElement).disabled).toBe(true);
 expect((screen.getByRole('button',{name:'Save note revision'}) as HTMLButtonElement).disabled).toBe(true);
 expect((screen.getByRole('button',{name:'Test observation in Lab'}) as HTMLButtonElement).disabled).toBe(false);
 fireEvent.click(screen.getByRole('button',{name:'Test observation in Lab'}));
 expect(onTest).toHaveBeenCalledExactlyOnceWith({id:'note',revision:1,source,start:600,end:1200});
 expect(vi.mocked(api).mock.calls.some(([c])=>/save|start|preview|prepare|resume/.test(c))).toBe(false);
});


it('passes exact verified OHLCV, source interval, missing slots and evidence reference into the chart without extra reads',async()=>{
 mock();vi.mocked(api).mockClear();const previous=vi.mocked(api).getMockImplementation()!;
 const smallSource={...source,range:[0,180]};
 const verified={...page,source:smallSource,start:0,end:180,candles:[{time:60,open:100,high:103,low:99,close:102,volume:0}],missing:[0,120],display_reference:{surface:'observation_chart',page_id:'verified-page'}};
 vi.mocked(api).mockImplementation(async(c,p)=>c==='local_history_window'?verified:previous(c,p));
 render(<Observations datasets={[smallSource]} request={{dataset:source.id,request:1}} onTest={vi.fn()} onBatch={vi.fn()}/>);
 await screen.findByText('Chart: 1 candles');
 expect(JSON.parse(screen.getByTestId('observation-chart').getAttribute('data-chart-page')!)).toEqual({candles:[{time:60,open:100,high:103,low:99,close:102,volume:0}],missing:[0,120],seconds:60,displaySeconds:60,start:0,end:180,reference:{surface:'observation_chart',page_id:'verified-page'}});
 expect(vi.mocked(api).mock.calls.map(([c])=>c)).toEqual(['observation_history','local_history_window']);
});

const chartPage=()=>JSON.parse(screen.getByTestId('observation-chart').getAttribute('data-chart-page')!);
it('switches display only, keeps source-aligned non-display-aligned dates and dirty text, and restores Source without rereading',async()=>{
 mockPeriod();render(<Observations datasets={[hourlySource]} request={{dataset:hourlySource.id,request:1}} onTest={vi.fn()} onBatch={vi.fn()}/>);
 await screen.findByTestId('observation-chart');const original=chartPage(),select=screen.getByLabelText('Saved-history display interval');
 expect([...((select as HTMLSelectElement).options)].map(o=>o.text)).toEqual(['Source · 1h','4h','1d']);
 fireEvent.change(screen.getByLabelText('Observation start (UTC)'),{target:{value:'2024-01-01T01:00'}});
 fireEvent.change(screen.getByLabelText('Observation end, exclusive (UTC)'),{target:{value:'2024-01-02T03:00'}});
 fireEvent.change(screen.getByLabelText('Observation hypothesis'),{target:{value:'Keep my draft'}});
 for(const [width,expected] of [[14400,14400],[86400,86400],[0,3600]]){
  fireEvent.change(select,{target:{value:String(width)}});expect(chartPage()).toEqual({...original,displaySeconds:expected});
  expect((screen.getByLabelText('Observation start (UTC)') as HTMLInputElement).value).toBe('2024-01-01T01:00');
  expect(screen.getByLabelText('Observation start (UTC)').getAttribute('aria-invalid')).toBe('false');
  expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).value).toBe('Keep my draft');
 }
 expect(vi.mocked(api).mock.calls.map(([c])=>c)).toEqual(['observation_history','local_history_window']);
});
it('retains same-source display across explicit pages, but resets on exact source identity changes including return to the earlier source',async()=>{
 const a={...hourlySource,id:'a',range:[0,900*3600]},b={...a,id:'b'};mock();vi.mocked(api).mockClear();
 vi.mocked(api).mockImplementation(async(c,p:any)=>c==='observation_history'?{rows:[],next:null}:c==='local_history_window'?{source:p.dataset_id==='a'?a:b,start:p.start,end:p.end,candles:[],missing:[],display_reference:{page_id:String(p.start)}}:{});
 render(<Observations datasets={[a,b]} request={{dataset:'a',request:1}} onTest={vi.fn()} onBatch={vi.fn()}/>);await screen.findByTestId('observation-chart');
 fireEvent.change(screen.getByLabelText('Saved-history display interval'),{target:{value:'86400'}});
 fireEvent.click(screen.getByRole('button',{name:'Later candles'}));await waitFor(()=>expect(chartPage().start).toBe(500*3600));
 expect((screen.getByLabelText('Saved-history display interval') as HTMLSelectElement).value).toBe('86400');
 expect(api).toHaveBeenCalledWith('local_history_window',{dataset_id:'a',start:500*3600,end:900*3600});
 fireEvent.click(screen.getByRole('button',{name:'Earlier candles'}));await waitFor(()=>expect(chartPage().start).toBe(0));expect(chartPage().displaySeconds).toBe(86400);
 fireEvent.change(screen.getByLabelText('Observation history'),{target:{value:'b'}});await screen.findByTestId('observation-chart');expect(chartPage().displaySeconds).toBe(3600);
 fireEvent.change(screen.getByLabelText('Observation history'),{target:{value:'a'}});await screen.findByTestId('observation-chart');expect(chartPage().displaySeconds).toBe(3600);
 expect(vi.mocked(api).mock.calls.filter(([c])=>c==='local_history_window')).toHaveLength(5);
});
it.each([[60,'1d','Needs 1440 source slots'],[14400,'1h','Finer than the 4h source'],[10800,'4h','Not a whole multiple'],[172800,'1d','Finer than the 2d source']] as const)('explains unavailable choices for a %s-second verified source without another read',async(step,label,reason)=>{
 const d={...source,interval_seconds:step,range:[0,step*20]};mockPeriod(d);render(<Observations datasets={[d]} request={{dataset:d.id,request:1}} onTest={vi.fn()} onBatch={vi.fn()}/>);
 await screen.findByTestId('observation-chart');expect((screen.getByRole('option',{name:`${label} · unavailable`}) as HTMLOptionElement).disabled).toBe(true);
 expect(screen.getByText(new RegExp(`${label} unavailable: ${reason}`))).toBeTruthy();expect(chartPage().seconds).toBe(step);expect(chartPage().displaySeconds).toBe(step);
 expect(vi.mocked(api).mock.calls.map(([c])=>c)).toEqual(['observation_history','local_history_window']);
});
it('retains display choice for a locked exact revision reopen without changing the Lab handoff',async()=>{
 const d=hourlySource,note={...record,source:d,start:1704070800,end:1704164400,revision:2,latest_revision:3};mock();vi.mocked(api).mockClear();
 vi.mocked(api).mockImplementation(async(c)=>c==='observation_history'?{rows:[note],next:null}:c==='observation_get'?note:c==='local_history_window'?{...page,source:d,start:note.start,end:d.range[1]}:{});
 const onTest=vi.fn(),props={datasets:[d],onTest,onBatch:vi.fn(),request:{id:'note',revision:2,request:1}},view=render(<Observations {...props}/>);
 await screen.findByTestId('observation-chart');fireEvent.change(screen.getByLabelText('Saved-history display interval'),{target:{value:'14400'}});
 fireEvent.click(screen.getByRole('button',{name:'Test observation in Lab'}));expect(onTest).toHaveBeenCalledWith({id:'note',revision:2,source:d,start:1704070800,end:1704164400});
 view.rerender(<Observations {...props} request={{...props.request,request:2}}/>);await waitFor(()=>{expect(vi.mocked(api).mock.calls.filter(([c])=>c==='local_history_window')).toHaveLength(2);expect(chartPage().displaySeconds).toBe(14400);});
 expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).disabled).toBe(true);
 expect((screen.getByLabelText('Observation start (UTC)') as HTMLInputElement).value).toBe('2024-01-01T01:00');
 expect(vi.mocked(api).mock.calls.some(([c])=>/save|start|prepare|preview|resume/.test(c))).toBe(false);
});
it('resets on a changed verified identity with the same dataset ID and derives chart resolution from the verified page',async()=>{
 const listed={...hourlySource,range:[1704067200,1704081600],interval_seconds:60};let hash='first';mock();vi.mocked(api).mockClear();
 vi.mocked(api).mockImplementation(async c=>c==='observation_history'?{rows:[],next:null}:c==='local_history_window'?{...page,start:1704067200,end:1704081600,source:{...hourlySource,content_sha256:hash}}:{});
 const props={datasets:[listed],onTest:vi.fn(),onBatch:vi.fn(),request:{dataset:listed.id,request:1}},view=render(<Observations {...props}/>);
 await screen.findByTestId('observation-chart');expect(chartPage().seconds).toBe(3600);
 fireEvent.change(screen.getByLabelText('Saved-history display interval'),{target:{value:'14400'}});expect(chartPage().displaySeconds).toBe(14400);
 hash='replacement';view.rerender(<Observations {...props} request={{...props.request,request:2}}/>);
 await waitFor(()=>{expect(vi.mocked(api).mock.calls.filter(([c])=>c==='local_history_window')).toHaveLength(2);expect(chartPage().displaySeconds).toBe(3600);});
});
