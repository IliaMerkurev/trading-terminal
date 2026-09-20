import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import LibraryResearch,{sortedLibraryRows,canonical,filterLibraryRows} from './LibraryResearch';
import {defaultProfile} from './model';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
const selections=[{entry_id:'rsi-threshold',version:1,minutes:1,parameters:{period:2}}];
const datasets=[{id:'data',market:'spot',symbol:'BTCUSDT',source:'Synthetic',range:[0,3600]}];
const inputs={selections,dataset_id:'data',profile:defaultProfile,start:600,end:3600,interval:'weekly',spot_dataset_id:null};

it('freezes preview, invalidates changed inputs and preserves an explicit saved result contract',async()=>{
 const onActive=vi.fn(),onReport=vi.fn(),onOpenRun=vi.fn();
 const report={id:'batch',status:'completed',active_id:null,snapshot:{inputs,rows:[{name:'RSI',kind:'graph',profile:defaultProfile,dataset:{id:'data'},selection:selections[0]}]},rows:[{ordinal:0,status:'completed',run_id:'saved',metrics:{net_pnl:'-2',period_return:'-.002',final_equity:'998',max_drawdown:'.01',completed_positions:0,win_rate:null,fees:'2',funding:'0',annualized_geometric_return:null}}]};
 vi.mocked(api).mockImplementation(async(command)=>{
  if(command==='library_batches')return [{id:'batch',status:'completed',created_at:'2026-01-01'}];
  if(command==='library_batch_preview')return {contract_sha256:'frozen',modeled_minutes:100,rows:[{name:'RSI',kind:'graph',error:null}]};
  if(command==='library_batch_start')return {batch_id:'batch'};
  if(command==='library_batch_status')return report;
  return {};
 });
 const props={selections,datasets,profile:defaultProfile,onActive,onReport,onOpenRun};
 const {rerender}=render(<LibraryResearch {...props}/>);
 fireEvent.change(screen.getByLabelText('Batch dataset'),{target:{value:'data'}});
 fireEvent.change(screen.getByLabelText('Evaluation start (UTC)'),{target:{value:'1970-01-01T00:10'}});
 fireEvent.click(screen.getByRole('button',{name:'Preview batch'}));
 fireEvent.click(await screen.findByRole('button',{name:'Start frozen batch'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('library_batch_start',{...inputs,expected_contract:'frozen'}));
 expect(await screen.findByText(/Matches current inputs/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Open report'}));expect(onOpenRun).toHaveBeenCalledWith('saved');
 expect(screen.getAllByText(/N\/A/).length).toBeGreaterThan(0);
 rerender(<LibraryResearch {...props} profile={{...defaultProfile,capital:'2000'}}/>);
 expect(await screen.findByText(/Prior run — inputs changed/)).toBeTruthy();
 expect(screen.queryByRole('button',{name:'Start frozen batch'})).toBeNull();
 expect(report.rows[0].metrics.final_equity).toBe('998');
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
  if(command==='library_batches')return [{id:'batch',status:'running',created_at:'2026-01-01'}];
  if(command==='library_batch_status')return {id:'batch',status:active?'running':'cancelled',active_id:active?'batch':null,
   snapshot:{inputs,rows:[{kind:'graph',name:'Failed candidate',profile:defaultProfile,dataset:{id:'data'}}]},rows:[{ordinal:0,status:'pending',metrics:null}]};
  if(command==='library_batch_cancel'){active=false;return {};}
  return {};
 });
 render(<LibraryResearch selections={selections} datasets={datasets} profile={defaultProfile} onActive={vi.fn()} onReport={vi.fn()} onOpenRun={vi.fn()}/>);
 await screen.findByRole('option',{name:/2026-01-01/});fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'batch'}});
 fireEvent.click(await screen.findByRole('button',{name:'Cancel batch'}));
 fireEvent.click(await screen.findByRole('button',{name:'Resume pending rows with frozen inputs'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('library_batch_resume',{batch_id:'batch'}));
 await screen.findByRole('option',{name:/2026-01-01 · cancelled/});
});


it('freezes a saved candidate separately and never ranks or attaches holdout metrics to selection cards',async()=>{
 const onReport=vi.fn();
 const base={id:'selection',status:'completed',active_id:null,snapshot:{inputs,start:600,end:3600,rows:[{name:'RSI',kind:'graph',profile:defaultProfile,dataset:{id:'data'}}]},rows:[{ordinal:0,status:'completed',run_id:'run',metrics:{net_pnl:'2'}}]};
 const frozen={...base,id:'holdout',status:'frozen',snapshot:{...base.snapshot,phase:'out_of_sample',start:7200,end:10800,validation:{selection_range:[600,3600],selection_attempted_variants:3,holdout_attempt:2,source_version_date:'2026-09-18',warning:'Repeated holdout is not independent evidence.'}},rows:[{ordinal:0,status:'pending',metrics:null}]};
 vi.mocked(api).mockImplementation(async(command,params:any)=>{
  if(command==='library_batches')return [{id:'selection',status:'completed',created_at:'Selection'}];
  if(command==='library_batch_status')return params.batch_id==='holdout'?frozen:base;
  if(command==='library_validation_freeze')return {batch_id:'holdout'};
  return {};
 });
 render(<LibraryResearch selections={selections} datasets={datasets} profile={defaultProfile} onActive={vi.fn()} onReport={onReport} onOpenRun={vi.fn()}/>);
 await screen.findByRole('option',{name:/Selection/});fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'selection'}});
 fireEvent.change(screen.getByLabelText('Batch dataset'),{target:{value:'data'}});
 fireEvent.change(screen.getByLabelText('Evaluation start (UTC)'),{target:{value:'1970-01-01T02:00'}});
 fireEvent.change(screen.getByLabelText('Evaluation end, exclusive (UTC)'),{target:{value:'1970-01-01T03:00'}});
 fireEvent.click(await screen.findByRole('button',{name:'Freeze later-period candidate'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('library_validation_freeze',{batch_id:'selection',ordinal:0,dataset_id:'data',start:7200,end:10800,spot_dataset_id:null}));
 expect(await screen.findByText(/Later-period verification — excluded/)).toBeTruthy();
 expect((screen.getByLabelText('Library sort') as HTMLSelectElement).disabled).toBe(true);
 await waitFor(()=>expect(onReport).toHaveBeenLastCalledWith(null,true));
 fireEvent.click(screen.getByRole('button',{name:'Run frozen later-period verification'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('library_validation_start',{batch_id:'holdout'}));
 expect(sortedLibraryRows({...frozen,rows:[{ordinal:1,metrics:{net_pnl:1}},{ordinal:0,metrics:{net_pnl:10}}]},'net_pnl').map(r=>r.ordinal)).toEqual([1,0]);
});


it('filters family/timeframe/review/state and sorts measured baseline deltas without converting failures to zero',()=>{
 const catalog=[{id:'a',family:'momentum',availability:'verified'},{id:'b',family:'trend',availability:'preview'}];
 const report={snapshot:{rows:[{kind:'graph',selection:{entry_id:'a'},profile:defaultProfile,dataset:{id:'same'}},{kind:'graph',selection:{entry_id:'b'},profile:defaultProfile,dataset:{id:'same'}},{kind:'benchmark',profile:defaultProfile,dataset:{id:'same'}}]},rows:[{ordinal:0,status:'completed',metrics:{period_return:.1}},{ordinal:1,status:'failed',metrics:null},{ordinal:2,status:'completed',metrics:{period_return:.2}}]};
 expect(filterLibraryRows(report,catalog,{family:'momentum',review:'verified',status:'completed',minutes:String(defaultProfile.primary_minutes)}).map(r=>r.ordinal)).toEqual([0]);
 expect(filterLibraryRows(report,catalog,{status:'failed'}).map(r=>r.ordinal)).toEqual([1]);
 expect(sortedLibraryRows(report,'delta_hold').map(r=>r.ordinal)).toEqual([0,1,2]);
});
