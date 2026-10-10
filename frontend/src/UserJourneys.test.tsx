import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,within} from '@testing-library/react';
import App from './App';
import {api} from './api';
import {defaultProfile,exampleGraph} from './model';

vi.mock('./ObservationChart',()=>({default:()=> <div>Local observation chart</div>}));
vi.mock('./GraphEditor',()=>({default:()=> <div>Graph workspace</div>}));
vi.mock('./api',()=>({isDesktop:()=>true,transportCapabilities:()=>({mode:'desktop',localService:true,nativeWindow:true,openExportsFolder:true,downloadArchives:false,stopService:false}),productVersion:async()=>(await import('@tauri-apps/api/app')).getVersion(),downloadArchive:vi.fn(),api:vi.fn()}));
vi.mock('@tauri-apps/api/window',()=>({getCurrentWindow:()=>({onCloseRequested:async()=>()=>{}})}));
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn()}));
vi.mock('@tauri-apps/api/app',()=>({getVersion:async()=> '0.6.0-dev'}));

const entry={id:'trend',version:1,name:'Test trend',family:'trend',kind:'Adapted',source_url:'https://example.org/review',license:'Apache-2.0',markets:['spot'],directions:['long'],source_default_minutes:1440,author_recommended_minutes:null,local_default_minutes:1440,timeframes:[60,240,1440],timeframe_evidence:'Synthetic test catalog',adaptation:'Synthetic fixture',review:'Independent fixture',compatibility:'Closed bars',verification:'Test fixture',parameters:{}};
const data={id:'hourly',source:'Synthetic',market:'spot',symbol:'BTCUSDT',interval_seconds:3600,range:[0,31536000],coverage:{trade:{count:8760,complete:true,gaps:[]}}};
const rows=['Daily trend','Hourly trend','Four-hour trend','Buy & Hold','DCA'].map((name,ordinal)=>({name,kind:ordinal<3?'graph':'benchmark',profile:{...defaultProfile,capital:'1000',execution_minutes:60,primary_minutes:[1440,60,240,60,60][ordinal]},dataset:{id:data.id}}));

it('keeps card result ordering, edited inputs and selection through Saved tests and Lab return',async()=>{
 const catalog=[{...entry,name:'Zulu trend',parameters:{period:{type:'integer',default:14,min:2,max:100}}},{...entry,id:'alpha',name:'Alpha trend',parameters:{period:{type:'integer',default:14,min:2,max:100}}}];
 const specs=catalog.map(item=>({name:item.name,kind:'graph',profile:{...defaultProfile,execution_minutes:60,primary_minutes:240},dataset:{id:data.id},selection:{entry_id:item.id,version:1,minutes:240,parameters:{period:14}}}));
 const report={id:'ordered',status:'completed',active_id:null,metadata:{name:'October check',notes:'',revision:0},snapshot:{start:86400,end:172800,inputs:{},rows:specs},rows:specs.map((_,ordinal)=>({ordinal,status:'completed',run_id:`run-${ordinal}`,metrics:{net_pnl:ordinal===0?'-20':'0',period_return:ordinal===0?'-.02':'0',max_drawdown:'.02',completed_positions:ordinal===0?1:0}}))};
 vi.mocked(api).mockReset().mockImplementation(async command=>command==='library_catalog'?catalog:command==='library_batch_history'?{rows:[{id:'ordered',status:'completed',created_at:'Saved card fixture'}],next:null}:command==='library_batch_status'?report:command==='run_history'?{rows:[],next:null}:command.startsWith('list_')?[]:{});
 render(<App/>);
 const card=await screen.findByRole('article',{name:'Zulu trend'});
 fireEvent.change(within(card).getByLabelText('Zulu trend period'),{target:{value:'7'}});
 fireEvent.change(within(card).getByLabelText('Zulu trend timeframe'),{target:{value:'60'}});
 fireEvent.click(within(card).getByLabelText('Zulu trend compare 4h'));fireEvent.click(within(card).getByLabelText('Include Zulu trend'));
 fireEvent.click(screen.getByRole('button',{name:'Choose saved comparison'}));
 await screen.findByRole('option',{name:/Saved card fixture/});fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'ordered'}});
 await screen.findByText('-20.0000 / -2.00%');fireEvent.click(screen.getByRole('button',{name:'New test'}));
 fireEvent.change(screen.getByLabelText('Order cards'),{target:{value:'period_return'}});
 fireEvent.change(screen.getByLabelText('Card order direction'),{target:{value:'asc'}});
 expect(screen.getAllByRole('article').map(item=>item.getAttribute('aria-label'))).toEqual(['Zulu trend','Alpha trend']);
 fireEvent.click(screen.getByRole('button',{name:'Saved tests'}));fireEvent.click(screen.getByRole('button',{name:'Lab'}));
 expect((screen.getByLabelText('Order cards') as HTMLSelectElement).value).toBe('period_return');
 expect((screen.getByLabelText('Card order direction') as HTMLSelectElement).value).toBe('asc');
 expect(screen.getByRole('article',{name:'Zulu trend'})).toBe(card);
 expect((within(card).getByLabelText('Zulu trend period') as HTMLInputElement).value).toBe('7');
 expect((within(card).getByLabelText('Zulu trend timeframe') as HTMLSelectElement).value).toBe('60');
 expect(within(card).getByLabelText('Zulu trend compare 4h').getAttribute('aria-pressed')).toBe('true');
 expect((within(card).getByLabelText('Include Zulu trend') as HTMLInputElement).checked).toBe(true);
 const trigger=within(card).getByRole('button',{name:'Test this strategy'});trigger.focus();fireEvent.click(trigger);
 fireEvent(screen.getByRole('dialog'),new Event('cancel',{bubbles:false,cancelable:true}));expect(document.activeElement).toBe(trigger);
 expect(vi.mocked(api).mock.calls.some(([command])=>/preview|start|trust|library_copy/.test(command))).toBe(false);
});

it('guides first-time testing through history, exact timeframe review, navigation and cancellation',async()=>{
 let prepared=false,cancelled=false;
 const report=()=>({id:'new',status:cancelled?'cancelled':'running',active_id:cancelled?null:'new',snapshot:{inputs:{},rows},rows:rows.map((_,ordinal)=>({ordinal,status:ordinal===0?'completed':'pending',run_id:ordinal===0?'daily-run':null,metrics:ordinal===0?{net_pnl:'10',period_return:'.01'}:null}))});
 vi.mocked(api).mockImplementation(async(command,p:any)=>{
  if(command==='library_catalog')return [entry];
  if(command==='list_datasets')return prepared?[data]:[];
  if(command==='library_batch_history')return {rows:[],next:null};
  if(command==='run_history')return {rows:[],next:null};
  if(command.startsWith('list_'))return [];
  if(command==='history_prepare')return {status:'running'};
  if(command==='download_status'){prepared=true;return {status:'completed',dataset_id:data.id};}
  if(command==='dataset_profile')return {};
  if(command==='library_warmup')return {start:86400,end:31536000,available:true};
  if(command==='library_batch_preview')return {contract_sha256:'reviewed-contract',modeled_minutes:9000,rows:rows.map(r=>({...r,error:null}))};
  if(command==='library_batch_start')return {batch_id:'new'};
  if(command==='library_batch_status')return report();
  if(command==='library_batch_cancel'){cancelled=true;return {};}
  throw Error(`Unexpected command: ${command} ${JSON.stringify(p)}`);
 });
 render(<App/>);
 expect(screen.queryByRole('button',{name:'Pro'})).toBeNull();
 expect(screen.queryByRole('button',{name:'Research'})).toBeNull();
 await screen.findByRole('button',{name:'Test this strategy'});
 fireEvent.click(screen.getByRole('button',{name:'Test trend compare 1h'}));
 fireEvent.click(screen.getByRole('button',{name:'Test trend compare 4h'}));
 fireEvent.click(screen.getByRole('button',{name:'Test this strategy'}));
 expect(screen.getByRole('dialog',{name:'Set up backtest'})).toBeTruthy();
 expect(document.activeElement?.id).toBe('test-setup');
 fireEvent.change(screen.getByLabelText('Research capital'),{target:{value:'1000'}});
 fireEvent.click(screen.getByRole('button',{name:'Prepare market data'}));
 expect((screen.getByLabelText('History resolution') as HTMLSelectElement).value).toBe('60');
 fireEvent.click(screen.getByRole('button',{name:'Prepare / reuse history'}));
 fireEvent.click(await screen.findByRole('button',{name:'Continue with this history'}));
 expect(await screen.findByRole('dialog',{name:'Set up backtest'})).toBeTruthy();
 await waitFor(()=>expect((screen.getByLabelText('Batch dataset') as HTMLSelectElement).value).toBe('hourly'));
 await waitFor(()=>expect((screen.getByRole('button',{name:'Review test'}) as HTMLButtonElement).disabled).toBe(false));
 expect((screen.getByLabelText('Evaluation start (UTC)') as HTMLInputElement).value).toBe('1970-01-02T00:00');
 fireEvent.click(screen.getByRole('button',{name:'Review test'}));
 fireEvent.click(await screen.findByRole('button',{name:'Start 5 tests'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('library_batch_start',expect.objectContaining({expected_contract:'reviewed-contract',dataset_id:'hourly',start:86400,end:31536000,profile:expect.objectContaining({capital:'1000',execution_minutes:60}),selections:[60,240,1440].map(minutes=>({entry_id:'trend',version:1,minutes,parameters:{}}))})));
 expect(await screen.findByRole('heading',{name:'Saved tests'})).toBeTruthy();
 expect(screen.queryByRole('dialog',{name:'Set up backtest'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Data'}));
 fireEvent.click(screen.getByRole('button',{name:'Saved tests'}));
 fireEvent.click(await screen.findByRole('button',{name:'Cancel remaining tests'}));
 expect(await screen.findByText(/Cancelled · 1 completed · 0 unavailable · 0 failed · 4 pending/)).toBeTruthy();
 expect(screen.getByRole('button',{name:'Open report'})).toBeTruthy();
 expect(api).not.toHaveBeenCalledWith('library_batch_resume',expect.anything());
 expect(vi.mocked(api).mock.calls.filter(([c])=>c==='history_prepare')).toHaveLength(1);
 expect(vi.mocked(api).mock.calls.some(([c])=>['library_copy','get_strategy','trust_native','start_run'].includes(c))).toBe(false);
});

it('reopens saved gains, losses and no-trade results without setup or execution',async()=>{
 const report={id:'saved',status:'completed',active_id:null,snapshot:{inputs:{},rows:rows.slice(0,3)},rows:[
  {ordinal:0,status:'completed',run_id:'gain',metrics:{net_pnl:'25',period_return:'.025',completed_positions:2,win_rate:'.5'}},
  {ordinal:1,status:'completed',run_id:'loss',metrics:{net_pnl:'-12',period_return:'-.012',completed_positions:1,win_rate:'0'}},
  {ordinal:2,status:'completed',run_id:'none',metrics:{net_pnl:'0',period_return:'0',completed_positions:0,win_rate:null}}
 ]};
 vi.mocked(api).mockImplementation(async(command)=>{
  if(command==='library_catalog')return [entry];
  if(command==='library_batch_history')return {rows:[{id:'saved',status:'completed',created_at:'Saved fixture'}],next:null};
  if(command==='library_batch_status')return report;
  if(command==='run_history')return {rows:[],next:null};
  if(command.startsWith('list_'))return [];
  throw Error(`Unexpected execution: ${command}`);
 });
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Saved tests'}));
 await screen.findByRole('option',{name:/Saved fixture/});
 fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'saved'}});
 expect(await screen.findByText('25.0000 / 2.50%')).toBeTruthy();
 expect(screen.getByText('-12.0000 / -1.20%')).toBeTruthy();
 expect(screen.getByText('0 / N/A')).toBeTruthy();
 expect(screen.queryByRole('region',{name:'Test setup'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'New test'}));
 fireEvent.click(screen.getByRole('button',{name:'Edit test setup'}));
 fireEvent.change(screen.getByLabelText('Research capital'),{target:{value:'2000'}});
 fireEvent.click(screen.getByRole('button',{name:'Back to strategies'}));
 fireEvent.click(screen.getByRole('button',{name:'Saved tests'}));
 expect(screen.getByText('25.0000 / 2.50%')).toBeTruthy();
 expect(report.snapshot.rows[0].profile.capital).toBe('1000');
 expect(vi.mocked(api).mock.calls.some(([c])=>/prepare|start|warmup|preview/.test(c))).toBe(false);
});

it('customizes an independent draft and preserves the card selection when returning',async()=>{
 vi.mocked(api).mockImplementation(async(command)=>{
  if(command==='library_catalog')return [entry,{...entry,id:'second',name:'Second idea'}];
  if(command==='library_batch_history')return {rows:[],next:null};
  if(command==='library_batches'||command.startsWith('list_'))return [];
  if(command==='run_history')return {rows:[],next:null};
  if(command==='library_copy'||command==='save_graph')return {strategy_id:'independent'};
  if(command==='get_strategy')return {name:'Independent draft',kind:'graph',document:{graph:exampleGraph(),layout:{}}};
  throw Error(`Unexpected execution: ${command}`);
 });
 render(<App/>);
 const first=await screen.findByRole('article',{name:'Test trend'}),second=screen.getByRole('article',{name:'Second idea'});
 fireEvent.click(within(second).getByLabelText('Include Second idea'));
 fireEvent.click(within(first).getByRole('button',{name:'Test this strategy'}));
 expect((within(second).getByLabelText('Include Second idea') as HTMLInputElement).checked).toBe(false);
 expect((within(first).getByLabelText('Include Test trend') as HTMLInputElement).checked).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Back to strategies'}));
 fireEvent.click(within(first).getByRole('button',{name:'Customize strategy'}));
 expect(screen.getByRole('dialog',{name:'Choose copy settings'})).toBeTruthy();
 expect(screen.getByText('Source / execution resolution')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Use Lab test settings'}));
 await screen.findByText('Graph workspace');
 expect((screen.getByLabelText('Strategy name') as HTMLInputElement).value).toBe('Independent draft');
 fireEvent.click(screen.getByRole('button',{name:'Lab'}));
 expect((screen.getByLabelText('Include Test trend') as HTMLInputElement).checked).toBe(true);
 expect(api).toHaveBeenCalledWith('get_strategy',{strategy_id:'independent'});
 expect(api).toHaveBeenCalledWith('library_copy',expect.objectContaining({profile:expect.objectContaining({execution_minutes:60,sizing:'percent',allocation:'95',slippage:'0.0005'})}));
 expect(vi.mocked(api).mock.calls.some(([c])=>['trust_native','start_run','library_batch_start'].includes(c))).toBe(false);
});

it('uses Data from the custom backtest without replacing the Lab selection',async()=>{
 const minuteData={...data,id:'minute',interval_seconds:60};
 vi.mocked(api).mockImplementation(async(command)=>command==='library_catalog'?[entry]:command==='list_datasets'?[minuteData]:command==='run_history'?{rows:[],next:null}:command==='library_batch_history'?{rows:[],next:null}:command==='library_batches'||command.startsWith('list_')?[]:{});
 render(<App/>);await screen.findByRole('button',{name:'Test this strategy'});
 fireEvent.click(screen.getByLabelText('Include Test trend'));
 fireEvent.click(screen.getByRole('button',{name:'Custom backtest'}));
 fireEvent.click(screen.getByRole('button',{name:'Data'}));
 expect(screen.getByRole('button',{name:'Back to custom backtest'})).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Use this history'}));
 expect((screen.getByLabelText('Prepared dataset') as HTMLSelectElement).value).toBe('minute');
 fireEvent.click(screen.getByRole('button',{name:'Lab'}));
 expect((screen.getByLabelText('Include Test trend') as HTMLInputElement).checked).toBe(true);
 expect(vi.mocked(api).mock.calls.some(([c])=>/start|prepare|preview/.test(c))).toBe(false);
});

it('can cancel copy settings or explicitly keep the editor profile',async()=>{
 vi.mocked(api).mockImplementation(async(command)=>{
  if(command==='library_catalog')return [entry];
  if(command==='library_batch_history')return {rows:[],next:null};
  if(command==='library_batches'||command.startsWith('list_'))return [];
  if(command==='run_history')return {rows:[],next:null};
  if(command==='library_copy'||command==='save_graph')return {strategy_id:'copy'};
  if(command==='get_strategy')return {name:'Copy',kind:'graph',profile:{...defaultProfile,capital:'123'},document:{graph:exampleGraph(),layout:{}}};
  return {};
 });
 render(<App/>);fireEvent.click(await screen.findByRole('button',{name:'Customize strategy'}));
 fireEvent.click(screen.getByRole('button',{name:'Cancel copy'}));
 expect(api).not.toHaveBeenCalledWith('library_copy',expect.anything());
 fireEvent.click(screen.getByRole('button',{name:'Customize strategy'}));fireEvent.click(screen.getByRole('button',{name:'Keep current editor settings'}));
 await screen.findByText('Graph workspace');
 expect(api).toHaveBeenCalledWith('library_copy',expect.objectContaining({profile:expect.objectContaining({capital:'1000',sizing:'fixed',allocation:'100',slippage:'0',primary_minutes:1440})}));
 expect(vi.mocked(api).mock.calls.some(([c])=>/start|trust/.test(c))).toBe(false);
});

it('opens ordinary Lab setup from Saved tests Data without inventing a later-period candidate',async()=>{
 vi.mocked(api).mockImplementation(async command=>command==='library_catalog'?[entry]:command==='list_datasets'?[data]:['run_history','library_batch_history'].includes(command)?{rows:[],next:null}:command.startsWith('list_')?[]:{});
 render(<App/>);await screen.findByRole('button',{name:'Test this strategy'});
 fireEvent.click(screen.getByRole('button',{name:'Saved tests'}));fireEvent.click(screen.getByRole('button',{name:'Data'}));
 expect(screen.getByRole('button',{name:'Back to saved tests'})).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Use this history'}));
 expect(await screen.findByRole('dialog',{name:'Set up backtest'})).toBeTruthy();
 expect((screen.getByLabelText('Batch dataset') as HTMLSelectElement).value).toBe('hourly');
 expect(screen.queryByRole('region',{name:'Later-period setup'})).toBeNull();
 expect(vi.mocked(api).mock.calls.some(([command])=>command==='library_validation_freeze')).toBe(false);
});

vi.mock('./RunChart',()=>({default:({runId}:{runId:string})=><div aria-label="Saved report chart">{runId}</div>}));
it('opens a comparison report before collapsed history and returns to the same filtered comparison',async()=>{
 const run={id:'saved-loss',created_at:'2026-01-01T00:00:00Z',status:'completed',summary:{profile:defaultProfile,metrics:{net_pnl:'-12',max_drawdown:'.02',trade_count:1,win_rate:0,fees:'2',funding:'0'}}};
 const history=Array.from({length:17},(_,i)=>({...run,id:i===0?run.id:`older-${i}`,created_at:new Date(Date.parse(run.created_at)-i*86400000).toISOString()}));
 const report={id:'saved',status:'completed',active_id:null,snapshot:{inputs:{},rows:[rows[1]]},rows:[{ordinal:0,status:'completed',run_id:run.id,metrics:{net_pnl:'-12',period_return:'-.012',completed_positions:1,win_rate:0}}]};
 vi.mocked(api).mockImplementation(async(command)=>{
  if(command==='library_catalog')return [{...entry,availability:'verified'}];
  if(command==='library_batch_history')return {rows:[{id:'saved',status:'completed',created_at:'Saved fixture'}],next:null};
  if(command==='library_batch_status')return report;
  if(command==='run_history')return {rows:history,next:null};
  if(command==='run_status'){const {created_at,...status}=run;return status;}
  if(command==='result_page')return {rows:[],total:0,next:null};
  if(command.startsWith('list_'))return [];
  throw Error(`Unneeded detail: ${command}`);
 });
 const {container}=render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Saved tests'}));
 await screen.findByRole('option',{name:/Saved fixture/});
 fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'saved'}});
 await screen.findByText('-12.0000 / -1.20%');
 fireEvent.click(screen.getByText('Filter results · 0 active',{selector:'summary'}));
 fireEvent.change(screen.getByLabelText('Library filter Compatibility / result state'),{target:{value:'completed'}});
 fireEvent.click(screen.getByRole('button',{name:'Open report'}));
 expect(await screen.findByRole('heading',{name:'Saved report · BTCUSDT'})).toBeTruthy();
 const selector=container.querySelector('.saved-run-history') as HTMLDetailsElement;
 expect(selector.open).toBe(false);
 expect(container.querySelector('.selected-report-heading p')!.textContent).toContain(new Date(run.created_at).toLocaleString());
 expect(screen.queryByText(/Invalid Date/)).toBeNull();
 expect(screen.getByLabelText('Saved report chart').textContent).toBe('saved-loss');
 expect(screen.getByText('-12.00 USDT',{selector:'.metrics strong'})).toBeTruthy();
 expect(container.querySelector('.selected-report-heading')!.compareDocumentPosition(container.querySelector('.comparison')!)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
 fireEvent.click(screen.getByText('Run history · 17 loaded',{selector:'summary'}));
 expect(selector.open).toBe(true);
 expect(selector.querySelectorAll('.run-list button')).toHaveLength(17);
 fireEvent.click(selector.querySelectorAll('.run-list button')[1]);
 expect((container.querySelector('.saved-run-history') as HTMLDetailsElement).open).toBe(false);
 expect(screen.getByLabelText('Saved report chart').textContent).toBe('older-1');
 fireEvent.click(screen.getByRole('button',{name:'Back to saved tests'}));
 expect((screen.getByLabelText('Saved library batches') as HTMLSelectElement).value).toBe('saved');
 expect((screen.getByLabelText('Library filter Compatibility / result state') as HTMLSelectElement).value).toBe('completed');
 expect(screen.getByText('-12.0000 / -1.20%')).toBeTruthy();
 expect(vi.mocked(api).mock.calls.some(([c])=>/prepare|start|warmup|preview|resume/.test(c))).toBe(false);
});


it('opens local observation directly from Data without mounting live market or executing a strategy',async()=>{
 vi.mocked(api).mockImplementation(async(command,p:any)=>{
  if(command==='library_catalog')return [entry];
  if(command==='list_datasets')return [data];
  if(command==='library_batch_history'||command==='run_history'||command==='observation_history')return {rows:[],next:null};
  if(command==='local_history_window')return {source:{...data,classification:'synthetic'},start:p.start,end:p.end,candles:[],missing:[]};
  if(command.startsWith('list_'))return [];
  return {};
 });
 render(<App/>);
 fireEvent.click(screen.getByRole('button',{name:'Data'}));
 fireEvent.click(await screen.findByRole('button',{name:'Observe this history'}));
 const localChart=await screen.findByText('Local observation chart');
 expect(localChart).toBeTruthy();
 // The existing workspace host bounds .content's overflow scroller. A plain
 // wrapper grows beyond the fixed-height app and makes the form unreachable.
 const scrollSurface=localChart.closest('.content');
 expect(scrollSurface?.parentElement?.classList.contains('experiment-host')).toBe(true);
 expect(scrollSurface?.parentElement?.classList.contains('observation-host')).toBe(true);
 expect(screen.getByRole('button',{name:'Saved history · local'}).getAttribute('aria-pressed')).toBe('true');
 expect(vi.mocked(api).mock.calls.some(([c])=>['market_open','market_chart','live_status','start_run','library_batch_start','history_prepare'].includes(c))).toBe(false);
});

it('keeps manual observation identity and selected tests through closed setup and ordinary navigation',async()=>{
 const observation={id:'manual-observation',revision:2,latest_revision:3,source:{...data,classification:'synthetic'},start:90000,end:176400,hypothesis:'Saved historical hypothesis',falsification:'Lower close',source_error:null,links:[]};
 vi.mocked(api).mockClear();
 vi.mocked(api).mockImplementation(async(command,p:any)=>{
  if(command==='library_catalog')return [entry];
  if(command==='list_datasets')return [data];
  if(command==='library_batch_history'||command==='run_history')return {rows:[],next:null};
  if(command==='observation_history')return {rows:[observation],next:null};
  if(command==='observation_get')return observation;
  if(command==='local_history_window')return {source:observation.source,start:p.start,end:p.end,candles:[],missing:[]};
  if(command==='library_warmup')return {start:3600,end:31536000,available:true};
  if(command==='dataset_profile')return {};
  if(command.startsWith('list_'))return [];
  throw Error(`Unexpected command: ${command}`);
 });
 render(<App/>);
 fireEvent.click(await screen.findByLabelText('Include Test trend'));
 fireEvent.change(screen.getByLabelText('Test trend timeframe'),{target:{value:'60'}});
 fireEvent.click(screen.getByLabelText('Test trend compare 4h'));
 fireEvent.click(screen.getByRole('button',{name:'Data'}));
 fireEvent.click(await screen.findByRole('button',{name:'Observe this history'}));
 fireEvent.click(await screen.findByRole('button',{name:/Saved historical hypothesis/}));
 await screen.findByRole('heading',{name:'Observation · revision 2'});
 await waitFor(()=>expect((screen.getByRole('button',{name:'Test observation in Lab'}) as HTMLButtonElement).disabled).toBe(false));
 fireEvent.change(screen.getByLabelText('Saved-history display interval'),{target:{value:'14400'}});
 fireEvent.click(screen.getByRole('button',{name:'Test observation in Lab'}));
 await screen.findByRole('dialog');
 fireEvent.click(screen.getByRole('button',{name:'Back to strategies'}));
 expect(screen.queryByRole('dialog')).toBeNull();
 expect((screen.getByLabelText('Include Test trend') as HTMLInputElement).checked).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Data'}));
 fireEvent.click(screen.getByRole('button',{name:'Lab'}));
 const attachment=screen.getByRole('region',{name:'Attached observation for draft test'});
 expect(within(attachment).getByText('Observation manual-o · revision 2')).toBeTruthy();
 expect((screen.getByLabelText('Include Test trend') as HTMLInputElement).checked).toBe(true);
 fireEvent.click(within(attachment).getByRole('button',{name:'Return to observation'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('observation_get',{observation_id:'manual-observation',revision:2}));
 expect(await screen.findByRole('heading',{name:'Observation · revision 2'})).toBeTruthy();
 await waitFor(()=>expect((screen.getByLabelText('Saved-history display interval') as HTMLSelectElement).value).toBe('14400'));
 expect((screen.getByLabelText('Observation start (UTC)') as HTMLInputElement).value).toBe('1970-01-02T01:00');
 fireEvent.click(screen.getByRole('button',{name:'Lab'}));
 expect(screen.getByRole('region',{name:'Attached observation for draft test'})).toBeTruthy();
 expect((screen.getByLabelText('Include Test trend') as HTMLInputElement).checked).toBe(true);
 expect((screen.getByLabelText('Test trend timeframe') as HTMLSelectElement).value).toBe('60');
 expect(screen.getByLabelText('Test trend compare 4h').getAttribute('aria-pressed')).toBe('true');
 fireEvent.click(screen.getByRole('button',{name:'Edit test setup'}));
 expect((screen.getByLabelText('Evaluation start (UTC)') as HTMLInputElement).value).toBe('1970-01-02T01:00');
 expect((screen.getByLabelText('Evaluation end, exclusive (UTC)') as HTMLInputElement).value).toBe('1970-01-03T01:00');
 expect((screen.getByLabelText('Batch dataset') as HTMLSelectElement).value).toBe('hourly');
 expect((screen.getByLabelText('Evaluation start (UTC)') as HTMLInputElement).disabled).toBe(true);
 expect(vi.mocked(api).mock.calls.some(([c])=>/save|start|preview|resume|prepare|market_open/.test(c))).toBe(false);
});

it('recovers saved observations after tab changes without replacing the unsaved period, notes or Lab selection',async()=>{
 let reads=0;
 const observation={id:'recovered-note',revision:3,latest_revision:3,source:{...data,classification:'synthetic'},start:86400,end:172800,hypothesis:'Recovered saved hypothesis',falsification:'',source_error:null,links:[]};
 vi.mocked(api).mockClear();
 vi.mocked(api).mockImplementation(async(command,p:any)=>{
  if(command==='library_catalog')return [entry];
  if(command==='list_datasets')return [data];
  if(command==='library_batch_history'||command==='run_history')return {rows:[],next:null};
  if(command==='observation_history'){if(++reads===1)throw Error('Temporary observation read failure');return {rows:[observation],next:null};}
  if(command==='observation_get')return observation;
  if(command==='local_history_window')return {source:observation.source,start:p.start,end:p.end,candles:[],missing:[]};
  if(command.startsWith('list_'))return [];
  throw Error(`Unexpected command: ${command}`);
 });
 render(<App/>);
 fireEvent.click(await screen.findByLabelText('Include Test trend'));
 fireEvent.click(screen.getByRole('button',{name:'Data'}));
 fireEvent.click(await screen.findByRole('button',{name:'Observe this history'}));
 await screen.findByText(/Could not load saved observations: Temporary observation read failure/);
 fireEvent.change(screen.getByLabelText('Observation start (UTC)'),{target:{value:'1970-01-02T00:00'}});
 fireEvent.change(screen.getByLabelText('Observation end, exclusive (UTC)'),{target:{value:'1970-01-03T00:00'}});
 fireEvent.change(screen.getByLabelText('Observation hypothesis'),{target:{value:'Unsaved hypothesis'}});
 fireEvent.change(screen.getByLabelText('Observation falsification'),{target:{value:'Unsaved falsification'}});
 fireEvent.change(screen.getByLabelText('Saved-history display interval'),{target:{value:'14400'}});
 fireEvent.change(screen.getByLabelText('Go to UTC date'),{target:{value:'1970-01-10T01:00'}});
 fireEvent.submit(screen.getByLabelText('Go to UTC date').closest('form')!);
 await waitFor(()=>expect(vi.mocked(api).mock.calls.filter(([c])=>c==='local_history_window')).toHaveLength(2));
 await screen.findByLabelText('Saved-history display interval');
 fireEvent.change(screen.getByLabelText('Go to UTC date'),{target:{value:'Pending invalid browse draft'}});
 fireEvent.click(screen.getByRole('button',{name:'Lab'}));
 expect((screen.getByLabelText('Include Test trend') as HTMLInputElement).checked).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Market'}));
 expect(reads).toBe(1);
 fireEvent.click(screen.getByRole('button',{name:'Retry saved observations'}));
 const recovered=await screen.findByRole('button',{name:/Recovered saved hypothesis/});
 expect((recovered as HTMLButtonElement).disabled).toBe(true);
 expect((screen.getByLabelText('Observation history') as HTMLSelectElement).value).toBe(data.id);
 expect((screen.getByLabelText('Observation start (UTC)') as HTMLInputElement).value).toBe('1970-01-02T00:00');
 expect((screen.getByLabelText('Observation end, exclusive (UTC)') as HTMLInputElement).value).toBe('1970-01-03T00:00');
 expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).value).toBe('Unsaved hypothesis');
 expect((screen.getByLabelText('Observation falsification') as HTMLTextAreaElement).value).toBe('Unsaved falsification');
 expect(screen.getByRole('heading',{name:'New observation'})).toBeTruthy();
 expect((screen.getByLabelText('Go to UTC date') as HTMLInputElement).value).toBe('Pending invalid browse draft');
 expect((screen.getByLabelText('Saved-history display interval') as HTMLSelectElement).value).toBe('14400');
 expect(api).toHaveBeenCalledWith('local_history_window',{dataset_id:data.id,start:781200,end:2581200});
 expect(vi.mocked(api).mock.calls.filter(([c])=>c==='local_history_window')).toHaveLength(2);
 expect(vi.mocked(api).mock.calls.filter(([c])=>c==='observation_get')).toHaveLength(0);
 fireEvent.click(screen.getByRole('button',{name:'Discard note edits'}));
 fireEvent.click(recovered);
 await screen.findByRole('heading',{name:'Observation · revision 3'});
 fireEvent.click(screen.getByRole('button',{name:'Lab'}));
 expect((screen.getByLabelText('Include Test trend') as HTMLInputElement).checked).toBe(true);
 expect(reads).toBe(2);
 expect(vi.mocked(api).mock.calls.some(([c])=>/save|start|preview|resume|prepare|market_open/.test(c))).toBe(false);
});
