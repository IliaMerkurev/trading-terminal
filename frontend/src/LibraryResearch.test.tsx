import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import LibraryResearch,{sortedLibraryRows,canonical,filterLibraryRows,researchProfileSnapshot,historyLabel} from './LibraryResearch';
import {defaultProfile} from './model';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
const selections=[{entry_id:'rsi-threshold',version:1,minutes:1,parameters:{period:2}}];
const datasets=[{id:'data',market:'spot',symbol:'BTCUSDT',source:'Synthetic',range:[0,3600]}];
const inputs={selections,dataset_id:'data',profile:defaultProfile,start:600,end:3600,interval:'weekly',spot_dataset_id:null};

it('shows completed and unavailable counts separately while keeping history labels conservative',async()=>{
 const states=[...Array(14).fill('completed'),'incompatible','incompatible'];
 const report={id:'matrix',status:'completed_with_errors',active_id:null,
  snapshot:{inputs,rows:states.map((_,ordinal)=>({name:`Candidate ${ordinal}`,kind:'graph',profile:defaultProfile,dataset:{id:'data'}}))},
  rows:states.map((status,ordinal)=>({ordinal,status,run_id:status==='completed'?`run-${ordinal}`:null,
   metrics:status==='completed'?{net_pnl:'-2',period_return:'-.002'}:null,error:status==='incompatible'?'Native execution unavailable':null}))};
 const original=JSON.stringify(report);
 vi.mocked(api).mockImplementation(async command=>command==='library_batch_history'?{rows:[{id:'matrix',status:'completed_with_errors',created_at:'Saved matrix'}],next:null}:command==='library_batch_status'?report:{});
 render(<LibraryResearch view="saved" selections={selections} datasets={datasets} profile={defaultProfile} onActive={vi.fn()} onReport={vi.fn()} onOpenRun={vi.fn()}/>);
 expect(await screen.findByRole('option',{name:'Saved matrix · Finished with unavailable or failed rows · selection'})).toBeTruthy();
 fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'matrix'}});
 expect(await screen.findByText(/^Completed · 14 completed · 2 unavailable · 0 failed ·/)).toBeTruthy();
 expect(screen.getAllByText('Native execution unavailable')).toHaveLength(2);
 expect(screen.getAllByText('-2.0000 / -0.20%')).toHaveLength(14);
 expect(screen.getAllByRole('button',{name:'Open report'})).toHaveLength(14);
 expect(screen.getAllByText('N/A / N/A').length).toBeGreaterThan(0);
 expect(JSON.stringify(report)).toBe(original);
});

it('freezes preview, invalidates changed inputs and preserves an explicit saved result contract',async()=>{
 const onActive=vi.fn(),onReport=vi.fn(),onOpenRun=vi.fn();
 const report={id:'batch',status:'completed',active_id:null,snapshot:{inputs,rows:[{name:'RSI',kind:'graph',profile:defaultProfile,dataset:{id:'data'},selection:selections[0]}]},rows:[{ordinal:0,status:'completed',run_id:'saved',metrics:{net_pnl:'-2',period_return:'-.002',final_equity:'998',max_drawdown:'.01',completed_positions:0,win_rate:null,fees:'2',funding:'0',annualized_geometric_return:null}}]};
 vi.mocked(api).mockImplementation(async(command)=>{
  if(command==='library_batch_history')return {rows:[{id:'batch',status:'completed',created_at:'2026-01-01'}],next:null};
  if(command==='library_batch_preview')return {contract_sha256:'frozen',modeled_minutes:100,rows:[{name:'RSI',kind:'graph',error:null},{name:'Unavailable passive comparison',kind:'benchmark',error:'Independent spot contract unavailable'}]};
  if(command==='library_batch_start')return {batch_id:'batch'};
  if(command==='library_batch_status')return report;
  return {};
 });
 const props={selections,datasets,profile:defaultProfile,onActive,onReport,onOpenRun};
 const {rerender}=render(<LibraryResearch {...props}/>);
 fireEvent.click(screen.getByRole('button',{name:'Edit test setup'}));
 fireEvent.change(screen.getByLabelText('Batch dataset'),{target:{value:'data'}});
 fireEvent.change(screen.getByLabelText('Evaluation start (UTC)'),{target:{value:'1970-01-01T00:10'}});
 await waitFor(()=>expect((screen.getByRole('button',{name:'Review test'}) as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(screen.getByRole('button',{name:'Review test'}));
 const startButton=await screen.findByRole('button',{name:/Start \d+ tests/});
 const selectionSummary=screen.getByText('1 selected test · 1 strategy · 1 timeframe',{selector:'summary'});
 expect(selectionSummary.closest('details')?.open).toBe(false);
 for(const element of [screen.getByRole('region',{name:'Reviewed test settings'}),screen.getByText('Independent spot contract unavailable'),startButton])expect(element.closest('details')).toBeNull();
 expect(screen.getByText(/1 ready · 1 unavailable/)).toBeTruthy();
 fireEvent.click(selectionSummary);fireEvent.click(selectionSummary);
 expect(api).toHaveBeenCalledWith('library_batch_preview',inputs);
 expect(vi.mocked(api).mock.calls.filter(([command])=>command==='library_batch_preview')).toHaveLength(1);
 fireEvent.click(startButton);fireEvent.click(startButton);
 await waitFor(()=>expect(api).toHaveBeenCalledWith('library_batch_start',{...inputs,expected_contract:'frozen'}));
 expect(vi.mocked(api).mock.calls.filter(([command])=>command==='library_batch_start')).toHaveLength(1);
 expect(await screen.findByText(/Matches current inputs/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Open report'}));expect(onOpenRun).toHaveBeenCalledWith('saved');
 expect(screen.getAllByText(/N\/A/).length).toBeGreaterThan(0);
 rerender(<LibraryResearch {...props} profile={{...defaultProfile,capital:'2000'}}/>);
 expect(await screen.findByText(/Saved settings differ from the current draft; saved reports remain available/)).toBeTruthy();
 expect(screen.queryByRole('button',{name:/Start \d+ tests/})).toBeNull();
 expect(report.rows[0].metrics.final_equity).toBe('998');
 expect(screen.queryByText(/rerun required/)).toBeNull();
 const table=screen.getByRole('region',{name:'Saved comparison results'});
 expect(table.getAttribute('tabindex')).toBe('0');
 expect(screen.getByRole('button',{name:'Open report'}).closest('td')).toBe(table.querySelector('tbody td'));
 fireEvent.click(screen.getByRole('button',{name:'Open report'}));expect(onOpenRun).toHaveBeenLastCalledWith('saved');
});

it('normalizes detailed profile defaults without falsely changing saved contracts',()=>{
 expect(researchProfileSnapshot({...defaultProfile,execution_minutes:1})).toEqual(defaultProfile);
 expect(researchProfileSnapshot({...defaultProfile,execution_minutes:240}).execution_minutes).toBe(240);
});

it('later-period setup uses independent dates and only freezes the saved candidate',async()=>{
 const report={id:'saved',status:'completed',active_id:null,snapshot:{inputs,end:3600,rows:[{name:'Original candidate',kind:'graph',profile:defaultProfile,dataset:{id:'data'}}]},rows:[{ordinal:0,status:'completed',run_id:'original',metrics:{net_pnl:'4'}}]};
 vi.mocked(api).mockImplementation(async(command)=>{
  if(command==='library_batch_history')return {rows:[{id:'saved',status:'completed',created_at:'Saved'}],next:null};
  if(command==='library_batch_status')return report;
  if(command==='research_evidence_preview')return {groups:[],message:'No recorded overlap',limitation:'History incomplete'};
  if(command==='library_validation_freeze')return {batch_id:'later'};
  return {};
 });
 render(<LibraryResearch view="saved" selections={selections} datasets={[{...datasets[0],id:'later-data',range:[3600,10800]}]} profile={{...defaultProfile,capital:'9999'}} onProfile={vi.fn()} onActive={vi.fn()} onReport={vi.fn()} onOpenRun={vi.fn()}/>);
 await screen.findByRole('option',{name:/Saved/});
 fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'saved'}});
 fireEvent.click(await screen.findByText('Verify on a later period',{selector:'summary'}));
 fireEvent.click(screen.getByRole('button',{name:'Set up later-period test'}));
 expect(screen.queryByRole('button',{name:'Review test'})).toBeNull();
 expect(screen.queryByRole('spinbutton',{name:'Research capital'})).toBeNull();
 fireEvent.change(screen.getByLabelText('Later-period history'),{target:{value:'later-data'}});
 fireEvent.change(screen.getByLabelText('Later evaluation start (UTC)'),{target:{value:'1970-01-01T02:00'}});
 fireEvent.click(screen.getByRole('button',{name:'Freeze later-period candidate'}));
 fireEvent.click(await screen.findByRole('button',{name:'Confirm candidate freeze'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('library_validation_freeze',{batch_id:'saved',ordinal:0,dataset_id:'later-data',start:7200,end:10800,spot_dataset_id:null}));
 expect(api).not.toHaveBeenCalledWith('library_batch_start',expect.anything());
 expect(report.snapshot.rows[0].profile.capital).toBe(defaultProfile.capital);
});

it('reserves warmup, waits for preparation, and accepts repeated history selection requests',async()=>{
 let resolveWarmup!:(value:any)=>void;
 vi.mocked(api).mockImplementation(async(command:string)=>{
  if(command==='library_warmup')return new Promise(resolve=>{resolveWarmup=resolve;});
  if(command==='library_batch_history')return {rows:[],next:null};
  return {};
 });
 const props={selections,datasets:[...datasets,{...datasets[0],id:'second'}],profile:defaultProfile,onActive:vi.fn(),onReport:vi.fn(),onOpenRun:vi.fn(),preferredDataset:{id:'data',request:1}};
 const {rerender}=render(<LibraryResearch {...props}/>);
 fireEvent.click(screen.getByRole('button',{name:'Edit test setup'}));
 await screen.findByText('Preparing warmup and instrument settings…');
 expect((screen.getByRole('button',{name:'Review test'}) as HTMLButtonElement).disabled).toBe(true);
 resolveWarmup({start:600,end:3600,available:true});
 await waitFor(()=>expect((screen.getByLabelText('Evaluation start (UTC)') as HTMLInputElement).value).toBe('1970-01-01T00:10'));
 fireEvent.change(screen.getByLabelText('Batch dataset'),{target:{value:'second'}});
 rerender(<LibraryResearch {...props} preferredDataset={{id:'data',request:2}}/>);
 await waitFor(()=>expect((screen.getByLabelText('Batch dataset') as HTMLSelectElement).value).toBe('data'));
});

it('keeps failed rows visible and sorts only inside matching cohorts, with undefined win rates last',()=>{
 const spec=(capital:string)=>({profile:{...defaultProfile,capital},dataset:{id:'data'}});
 const report={snapshot:{rows:[spec('1000'),spec('1000'),spec('2000'),spec('1000')]},rows:[
  {ordinal:0,status:'completed',metrics:{win_rate:null}},{ordinal:1,status:'completed',metrics:{win_rate:.5}},
  {ordinal:2,status:'completed',metrics:{win_rate:1}},{ordinal:3,status:'failed',metrics:null}]};
 expect(sortedLibraryRows(report,'win_rate').map(r=>r.ordinal)).toEqual([1,0,3,2]);
 expect(canonical({b:1,a:2})).toBe(canonical({a:2,b:1}));
});

it('cancels active work and exposes pending-only resume without hiding failed rows',async()=>{
 let active=true;
 vi.mocked(api).mockImplementation(async(command)=>{
  if(command==='library_batch_history')return {rows:[{id:'batch',status:'running',created_at:'2026-01-01'}],next:null};
  if(command==='library_batch_status')return {id:'batch',status:active?'running':'cancelled',active_id:active?'batch':null,
   snapshot:{inputs,rows:[{kind:'graph',name:'Failed candidate',profile:defaultProfile,dataset:{id:'data'}}]},rows:[{ordinal:0,status:'pending',metrics:null}]};
  if(command==='library_batch_cancel'){active=false;return {};}
  return {};
 });
 render(<LibraryResearch selections={selections} datasets={datasets} profile={defaultProfile} onActive={vi.fn()} onReport={vi.fn()} onOpenRun={vi.fn()}/>);
 await screen.findByRole('option',{name:/2026-01-01/});fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'batch'}});
 fireEvent.click(screen.getByRole('button',{name:'Edit test setup'}));
 fireEvent.click(await screen.findByRole('button',{name:'Cancel remaining tests'}));
 fireEvent.click(screen.getByRole('button',{name:'Back to strategies'}));
 fireEvent.click(await screen.findByRole('button',{name:'Resume pending rows with frozen inputs'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('library_batch_resume',{batch_id:'batch'}));
 await screen.findByRole('option',{name:/2026-01-01 · Cancelled/});
});


it('freezes a saved candidate separately and never ranks or attaches holdout metrics to selection cards',async()=>{
 const onReport=vi.fn();
 const base={id:'selection',status:'completed',active_id:null,snapshot:{inputs,start:600,end:3600,rows:[{name:'RSI',kind:'graph',profile:defaultProfile,dataset:{id:'data'}}]},rows:[{ordinal:0,status:'completed',run_id:'run',metrics:{net_pnl:'2'}}]};
 const frozen={...base,id:'holdout',status:'frozen',snapshot:{...base.snapshot,phase:'out_of_sample',start:7200,end:10800,validation:{selection_range:[600,3600],selection_attempted_variants:3,holdout_attempt:2,source_version_date:'2026-09-18',warning:'Repeated holdout is not independent evidence.'}},rows:[{ordinal:0,status:'pending',metrics:null}]};
 vi.mocked(api).mockImplementation(async(command,params:any)=>{
  if(command==='library_batch_history')return {rows:[{id:'selection',status:'completed',created_at:'Selection'}],next:null};
  if(command==='library_batch_status')return params.batch_id==='holdout'?frozen:base;
  if(command==='research_evidence_preview')return {groups:[],message:'No recorded overlap',limitation:'History incomplete'};
  if(command==='library_validation_freeze')return {batch_id:'holdout'};
  return {};
 });
 render(<LibraryResearch selections={selections} datasets={datasets} profile={defaultProfile} onActive={vi.fn()} onReport={onReport} onOpenRun={vi.fn()}/>);
 await screen.findByRole('option',{name:/Selection/});fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'selection'}});
 fireEvent.click(screen.getByRole('button',{name:'Edit test setup'}));
 fireEvent.change(screen.getByLabelText('Batch dataset'),{target:{value:'data'}});
 fireEvent.change(screen.getByLabelText('Evaluation start (UTC)'),{target:{value:'1970-01-01T02:00'}});
 fireEvent.change(screen.getByLabelText('Evaluation end, exclusive (UTC)'),{target:{value:'1970-01-01T03:00'}});
 fireEvent.click(screen.getByRole('button',{name:'Back to strategies'}));
 fireEvent.click(await screen.findByRole('button',{name:'Freeze later-period candidate'}));
 fireEvent.click(await screen.findByRole('button',{name:'Confirm candidate freeze'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('library_validation_freeze',{batch_id:'selection',ordinal:0,dataset_id:'data',start:7200,end:10800,spot_dataset_id:null}));
 expect(await screen.findByText(/Later-period verification — excluded/)).toBeTruthy();
 expect((screen.getByLabelText('Library sort') as HTMLSelectElement).disabled).toBe(true);
 await waitFor(()=>expect(onReport).toHaveBeenLastCalledWith(null,true,'holdout'));
 fireEvent.click(screen.getByRole('button',{name:'Run frozen later-period verification'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('library_validation_start',{batch_id:'holdout'}));
 expect(sortedLibraryRows({...frozen,rows:[{ordinal:1,metrics:{net_pnl:1}},{ordinal:0,metrics:{net_pnl:10}}]},'net_pnl').map(r=>r.ordinal)).toEqual([1,0]);
});


it('filters family/timeframe/review/state and sorts measured baseline deltas without converting failures to zero',()=>{
 const catalog=[{id:'a',family:'momentum',availability:'verified'},{id:'b',family:'trend',availability:'preview'}];
 const report={snapshot:{rows:[{kind:'graph',selection:{entry_id:'a'},profile:defaultProfile,dataset:{id:'same'}},{kind:'graph',selection:{entry_id:'b'},profile:defaultProfile,dataset:{id:'same'}},{kind:'benchmark',profile:defaultProfile,dataset:{id:'same'}}]},rows:[{ordinal:0,status:'completed',metrics:{period_return:.1}},{ordinal:1,status:'failed',metrics:null},{ordinal:2,status:'completed',metrics:{period_return:.2}}]};
 expect(filterLibraryRows(report,catalog,{family:'momentum',review:'verified',status:'completed',minutes:String(defaultProfile.primary_minutes)}).map(r=>r.ordinal)).toEqual([0,2]);
 expect(filterLibraryRows(report,catalog,{status:'failed'}).map(r=>r.ordinal)).toEqual([1,2]);
 expect(sortedLibraryRows(report,'delta_hold').map(r=>r.ordinal)).toEqual([0,1,2]);
});

it('keeps a newly chosen resolution and reserves warmup on repeated history use',async()=>{
 vi.mocked(api).mockImplementation(async(command)=>command==='library_batch_history'?{rows:[],next:null}:command==='library_warmup'?{start:144000,end:288000,available:true}:{});
 const all=[{...datasets[0],id:'hour',interval_seconds:3600,range:[0,288000]},{...datasets[0],id:'four-hour',interval_seconds:14400,range:[0,288000]}];
 const props={selections:[{...selections[0],minutes:1440}],datasets:all,profile:{...defaultProfile,execution_minutes:60},onActive:vi.fn(),onReport:vi.fn(),onOpenRun:vi.fn()};
 const {rerender}=render(<LibraryResearch {...props} preferredDataset={{id:'hour',request:1}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Edit test setup'}));
 await waitFor(()=>expect((screen.getByLabelText('Evaluation start (UTC)') as HTMLInputElement).value).toBe('1970-01-02T16:00'));
 rerender(<LibraryResearch {...props} profile={{...props.profile,execution_minutes:240}} preferredDataset={{id:'four-hour',request:2}}/>);
 await waitFor(()=>expect((screen.getByLabelText('Batch dataset') as HTMLSelectElement).value).toBe('four-hour'));
 await waitFor(()=>expect((screen.getByLabelText('Evaluation start (UTC)') as HTMLInputElement).value).toBe('1970-01-02T16:00'));
 rerender(<LibraryResearch {...props} profile={{...props.profile,execution_minutes:240}} preferredDataset={{id:'four-hour',request:3}}/>);
 await waitFor(()=>expect((screen.getByLabelText('Evaluation start (UTC)') as HTMLInputElement).value).toBe('1970-01-02T16:00'));
 expect(api).toHaveBeenLastCalledWith('library_warmup',{selections:props.selections,dataset_id:'four-hour'});
});


it('sorts both directions within matching models while losses and unavailable results remain visible',()=>{
 const spec=(version:number)=>({profile:{...defaultProfile,version},dataset:{id:'same'}});
 const report={snapshot:{rows:[spec(1),spec(1),spec(1),spec(2)]},rows:[{ordinal:0,metrics:{net_pnl:-5}},{ordinal:1,metrics:{net_pnl:2}},{ordinal:2,metrics:null},{ordinal:3,metrics:{net_pnl:100}}]};
 expect(sortedLibraryRows(report,'net_pnl','desc').map(r=>r.ordinal)).toEqual([1,0,2,3]);
 expect(sortedLibraryRows(report,'net_pnl','asc').map(r=>r.ordinal)).toEqual([0,1,2,3]);
 expect(report.rows.map(r=>r.ordinal)).toEqual([0,1,2,3]);
});


it.each([false,true])('suspends hidden completed batches but retains active polling (active=%s)',async(running)=>{
 vi.mocked(api).mockClear();
 let active=running;
 const report=()=>({id:'retained',status:active?'running':'completed',active_id:active?'retained':null,snapshot:{inputs,rows:[]},rows:[]});
 vi.mocked(api).mockImplementation(async(command)=>command==='library_batch_history'?{rows:[{id:'retained',status:'completed',created_at:'Retained'}],next:null}:command==='library_batch_status'?report():{});
 const props={selections,datasets,profile:defaultProfile,onActive:vi.fn(),onReport:vi.fn(),onOpenRun:vi.fn()};
 const {rerender}=render(<LibraryResearch {...props}/>);
 await screen.findByRole('option',{name:/Retained/});
 fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'retained'}});
 await waitFor(()=>expect(props.onActive).toHaveBeenCalledWith(running?'retained':null));
 rerender(<LibraryResearch {...props} suspendSetup/>);
 const calls=()=>vi.mocked(api).mock.calls.filter(([command])=>command==='library_batch_status').length;
 const hiddenCount=calls();
 await new Promise(resolve=>setTimeout(resolve,780));
 if(running){
  expect(calls()).toBeGreaterThan(hiddenCount);
  active=false;
  await waitFor(()=>expect(props.onActive).toHaveBeenLastCalledWith(null),{timeout:1200});
  const completedCount=calls();
  await new Promise(resolve=>setTimeout(resolve,780));
  expect(calls()).toBe(completedCount);
 }else expect(calls()).toBe(hiddenCount);
 expect(vi.mocked(api).mock.calls.some(([command])=>/start|cancel|resume/.test(command))).toBe(false);
});

it('blocks review on missing metadata and early warmup instead of starting an invalid test',async()=>{
 vi.mocked(api).mockImplementation(async(command)=>{
  if(command==='library_batch_history')return {rows:[],next:null};
  if(command==='dataset_profile')throw Error('Instrument metadata is missing. Prepare history again.');
  if(command==='library_warmup')return {start:600,end:3600,available:true};
  return {};
 });
 render(<LibraryResearch selections={selections} datasets={datasets} profile={defaultProfile} onProfile={vi.fn()} onActive={vi.fn()} onReport={vi.fn()} onOpenRun={vi.fn()}/>);
 fireEvent.click(screen.getByRole('button',{name:'Edit test setup'}));
 fireEvent.change(screen.getByLabelText('Batch dataset'),{target:{value:'data'}});
 await screen.findByText('Instrument metadata is missing. Prepare history again.');
 fireEvent.change(screen.getByLabelText('Evaluation start (UTC)'),{target:{value:'1970-01-01T00:01'}});
 expect(screen.getByText(/Not enough preceding warmup/)).toBeTruthy();
 expect((screen.getByRole('button',{name:'Review test'}) as HTMLButtonElement).disabled).toBe(true);
 expect(api).not.toHaveBeenCalledWith('library_batch_preview',expect.anything());
});

it('returns prepared history to the later-period candidate without changing ordinary setup',async()=>{
 const frozenInputs={...inputs,profile:defaultProfile};
 const report={id:'saved',status:'completed',active_id:null,snapshot:{inputs:frozenInputs,end:3600,rows:[{name:'Candidate',kind:'graph',profile:defaultProfile,dataset:{id:'data'}}]},rows:[{ordinal:0,status:'completed',run_id:'run',metrics:{net_pnl:'1'}}]};
 vi.mocked(api).mockImplementation(async command=>command==='library_batch_history'?{rows:[{id:'saved',status:'completed',created_at:'Saved'}],next:null}:command==='library_batch_status'?report:{});
 const onHistory=vi.fn(),props={view:'saved' as const,selections,datasets:[...datasets,{...datasets[0],id:'later',range:[3600,10800]}],profile:defaultProfile,onHistory,onActive:vi.fn(),onReport:vi.fn(),onOpenRun:vi.fn()};
 const {rerender}=render(<LibraryResearch {...props}/>);
 await screen.findByRole('option',{name:/Saved/});fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'saved'}});
 fireEvent.click(await screen.findByText('Verify on a later period',{selector:'summary'}));fireEvent.click(screen.getByRole('button',{name:'Set up later-period test'}));
 fireEvent.click(screen.getByRole('button',{name:'Prepare more market data'}));expect(onHistory).toHaveBeenCalledWith('later',defaultProfile);
 rerender(<LibraryResearch {...props} preferredDataset={{id:'later',request:1,target:'later'}}/>);
 await waitFor(()=>expect((screen.getByLabelText('Later-period history') as HTMLSelectElement).value).toBe('later'));
 expect((screen.getByLabelText('Later evaluation start (UTC)') as HTMLInputElement).value).toBe('1970-01-01T01:00');
 expect(screen.queryByRole('dialog')).toBeNull();
 expect(api).not.toHaveBeenCalledWith('library_validation_freeze',expect.anything());
});

it('loads an older comparison page and opens its frozen report without execution',async()=>{
 const initial=Array.from({length:50},(_,i)=>({id:`new-${i}`,status:'completed',created_at:`2026-${i}`}));
 const report={id:'old',status:'completed',active_id:null,snapshot:{inputs,rows:[]},rows:[]};
 vi.mocked(api).mockImplementation(async(command,params:any)=>command==='library_batch_history'?(params.before?{rows:[{id:'old',status:'completed',created_at:'Older fixture'}],next:null}:{rows:initial,next:{id:'new-49',created_at:'2026-49'}}):command==='library_batch_status'?report:{});
 render(<LibraryResearch view="saved" selections={selections} datasets={datasets} profile={defaultProfile} onActive={vi.fn()} onReport={vi.fn()} onOpenRun={vi.fn()}/>);
 fireEvent.click(await screen.findByRole('button',{name:'Load older comparisons'}));
 await screen.findByRole('option',{name:/Older fixture/});
 expect(api).toHaveBeenCalledWith('library_batch_history',{before:{id:'new-49',created_at:'2026-49'}});
 fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'old'}});
 await waitFor(()=>expect(api).toHaveBeenCalledWith('library_batch_status',{batch_id:'old'}));
 expect(screen.queryByRole('button',{name:'Load older comparisons'})).toBeNull();
 expect(vi.mocked(api).mock.calls.some(([c])=>/start|prepare|warmup|preview/.test(c))).toBe(false);
});

it('retains baseline deltas between strategy model 2 and passive model 1',()=>{
 const report={snapshot:{rows:[{kind:'graph',profile:{...defaultProfile,version:2},dataset:{id:'same'}},{kind:'graph',profile:{...defaultProfile,version:2},dataset:{id:'same'}},{kind:'benchmark',profile:{...defaultProfile,version:1},dataset:{id:'same'}}]},rows:[{ordinal:0,metrics:{period_return:'.1'}},{ordinal:1,metrics:{period_return:'.2'}},{ordinal:2,metrics:{period_return:'.05'}}]};
 // Passive model 1 is intentionally separate from graph model 2; both remain visible.
 expect(sortedLibraryRows(report,'delta_hold').filter(r=>r.ordinal!==2).map(r=>r.ordinal)).toEqual([1,0]);
});

it('retains continuation when the byte-bound first history page has fewer than 50 rows',async()=>{
 vi.mocked(api).mockImplementation(async(command,params:any)=>command==='library_batch_history'?{rows:params.before?[{id:'older',created_at:'2025-01-01',status:'completed'}]:[{id:'first',created_at:'2026-01-01',status:'completed'}],next:params.before?null:{id:'first',created_at:'2026-01-01'}}:{});
 render(<LibraryResearch view="saved" selections={selections} datasets={datasets} profile={defaultProfile} onActive={vi.fn()} onReport={vi.fn()} onOpenRun={vi.fn()}/>);
 fireEvent.click(await screen.findByRole('button',{name:'Load older comparisons'}));
 await screen.findByRole('option',{name:/2025-01-01/});
 expect(api).toHaveBeenCalledWith('library_batch_history',{before:{id:'first',created_at:'2026-01-01'}});
 expect(screen.queryByRole('button',{name:'Load older comparisons'})).toBeNull();
});

it('shows exact small declared costs in review and saved settings without changing the request',async()=>{
 const profile={...defaultProfile,fee_rate:'0.00001',slippage:'0.00002',tier_assumption:'Invented synthetic limits; not exchange metadata'};
 const report={id:'small-cost',status:'completed',active_id:null,snapshot:{inputs:{...inputs,profile},start:600,end:3600,rows:[]},rows:[]};
 vi.mocked(api).mockImplementation(async(command)=>{
  if(command==='library_batch_history')return {rows:[{id:'small-cost',created_at:'Small cost fixture',status:'completed'}],next:null};
  if(command==='library_batch_status')return report;
  if(command==='library_batch_preview')return {rows:[],modeled_minutes:1,contract_sha256:'fixture'};
  return {};
 });
 render(<LibraryResearch selections={selections} datasets={datasets} profile={profile} onActive={vi.fn()} onReport={vi.fn()} onOpenRun={vi.fn()}/>);
 await screen.findByRole('option',{name:/Small cost fixture/});
 fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'small-cost'}});
 expect(await screen.findByText(/Source.*Fee 0.001% \(fraction 0.00001\).*Slippage 0.002% \(fraction 0.00002\)/)).toBeTruthy();
 expect(screen.getByText(/Instrument assumptions: Invented synthetic limits/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Edit test setup'}));
 fireEvent.change(screen.getByLabelText('Batch dataset'),{target:{value:'data'}});
 await waitFor(()=>expect((screen.getByRole('button',{name:'Review test'}) as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(screen.getByRole('button',{name:'Review test'}));
 const reviewed=await screen.findByRole('region',{name:'Reviewed test settings'});
 expect(reviewed.textContent).toContain('Fee 0.001% (fraction 0.00001) per fill');
 expect(reviewed.textContent).toContain('slippage 0.002% (fraction 0.00002)');
 expect(api).toHaveBeenCalledWith('library_batch_preview',expect.objectContaining({profile:expect.objectContaining({fee_rate:'0.00001',slippage:'0.00002'})}));
});

it('uses percentage boundaries, keeps context and baselines, and never mixes cohorts',()=>{
 const specs=[defaultProfile,defaultProfile,defaultProfile,{...defaultProfile,version:3},defaultProfile].map((profile,i)=>({kind:i===4?'benchmark':'graph',profile,dataset:{id:'same'}}));
 const rows=[{ordinal:0,status:'completed',metrics:{max_drawdown:'.10',completed_positions:5,period_return:'-.02'}},{ordinal:1,status:'completed',metrics:{max_drawdown:'.11',completed_positions:6,period_return:'.05'}},{ordinal:2,status:'failed',metrics:null},{ordinal:3,status:'completed',metrics:{max_drawdown:null,completed_positions:0,period_return:null}},{ordinal:4,status:'completed',metrics:{max_drawdown:'.8',completed_positions:1,period_return:'-.5'}}];
 const report={snapshot:{rows:specs},rows};
 expect(filterLibraryRows({...report,rows:[{...rows[0],metrics:{max_drawdown:'.07'}}]},[],{maxDrawdown:'7'})).toHaveLength(1);
 expect(filterLibraryRows(report,[],{maxDrawdown:'10',minTrades:'5',minReturn:'-2'}).map(r=>r.ordinal)).toEqual([0,2,3,4]);
 expect(filterLibraryRows(report,[],{maxDrawdown:'0'}).map(r=>r.ordinal)).toEqual([2,3,4]);
 expect(filterLibraryRows(report,[],{maxDrawdown:''})).toHaveLength(5);
 expect(filterLibraryRows(report,[],{minTrades:'1.2'})).toHaveLength(5);
 expect(filterLibraryRows(report,[],{minReturn:'NaN'})).toHaveLength(5);
 expect(sortedLibraryRows(report,'period_return').map(r=>r.ordinal)).toEqual([1,0,4,2,3]);
 expect(sortedLibraryRows({...report,snapshot:{...report.snapshot,phase:'out_of_sample'}},'period_return')).toEqual(rows);
});

it('searches the complete catalog and pages within the submitted query while keeping an outside selection',async()=>{
 const report={id:'selected',status:'completed',active_id:null,metadata:{name:'Chosen',notes:'',revision:1},snapshot:{inputs,rows:[]},rows:[]};
 vi.mocked(api).mockImplementation(async(command,params:any)=>{
  if(command==='library_batch_status')return report;
  if(command==='library_batch_history')return params.query?{rows:[{id:params.before?'oldest':'match',name:params.before?'Old match':'New match',status:'completed',created_at:'2026-01-01'}],next:params.before?null:{id:'server-cursor',created_at:'2025-01-01'}}:{rows:[{id:'selected',name:'Chosen',status:'completed',created_at:'2026-01-02'}],next:null};
  return {};
 });
 render(<LibraryResearch view="saved" selections={[]} datasets={[]} profile={defaultProfile} onActive={vi.fn()} onReport={vi.fn()} onOpenRun={vi.fn()}/>);
 await screen.findByRole('option',{name:/Chosen/});fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'selected'}});
 fireEvent.click(await screen.findByRole('button',{name:'Edit details'}));
 await screen.findByLabelText('Comparison name');
 fireEvent.click(screen.getByText(/^Search saved comparisons · /,{selector:'summary'}));
 fireEvent.change(screen.getByLabelText('Search all saved comparisons'),{target:{value:'needle%_'}});
 fireEvent.click(screen.getByRole('button',{name:'Search saved comparisons'}));
 await screen.findByRole('option',{name:/New match/});
 expect(screen.getByRole('option',{name:/selected outside search page/})).toBeTruthy();
 expect(screen.getByText('How filters and comparison groups work').closest('details')?.open).toBe(false);
 expect(screen.getByText('Thresholds: this comparison only. Baselines stay visible; N/A rows are context, not matches.')).toBeTruthy();
 fireEvent.click(screen.getByText('Load older comparisons'));
 await screen.findByRole('option',{name:/Old match/});
 expect(api).toHaveBeenCalledWith('library_batch_history',{before:{id:'server-cursor',created_at:'2025-01-01'},query:'needle%_'});
 expect((screen.getByLabelText('Comparison name') as HTMLInputElement).value).toBe('Chosen');
});

it('does not claim no search matches after a failed catalog request',async()=>{
 vi.mocked(api).mockImplementation(async command=>{if(command==='library_batch_history')throw Error('Catalog unavailable');return {};});
 render(<LibraryResearch view="saved" selections={[]} datasets={[]} profile={defaultProfile} onActive={vi.fn()} onReport={vi.fn()} onOpenRun={vi.fn()}/>);
 await screen.findByText(/Catalog unavailable/);
 expect(screen.queryByText('No saved comparisons match this search.')).toBeNull();
});

it('labels same-day history choices with source, short identity and precise UTC range',()=>{
 const a={id:'abcdef012345',symbol:'BTCUSDT',market:'spot',source:'Synthetic shared',range:[0,2880]};
 const b={...a,id:'12345678abcd',source:'Unknown provenance'};
 expect(historyLabel(a)).toContain('Synthetic shared · abcdef01');
 expect(historyLabel(a)).toContain('1970-01-01T00:00 — 1970-01-01T00:48 UTC');
 expect(historyLabel(a)).not.toBe(historyLabel(b));
});
