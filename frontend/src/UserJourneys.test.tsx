import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,within} from '@testing-library/react';
import App from './App';
import {api} from './api';
import {defaultProfile,exampleGraph} from './model';

vi.mock('./GraphEditor',()=>({default:()=> <div>Graph workspace</div>}));
vi.mock('./api',()=>({isDesktop:()=>true,api:vi.fn()}));
vi.mock('@tauri-apps/api/window',()=>({getCurrentWindow:()=>({onCloseRequested:async()=>()=>{}})}));
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn()}));
vi.mock('@tauri-apps/api/app',()=>({getVersion:async()=> '0.6.0-dev'}));

const entry={id:'trend',version:1,name:'Test trend',family:'trend',kind:'Adapted',source_url:'https://example.org/review',license:'Apache-2.0',markets:['spot'],directions:['long'],source_default_minutes:1440,author_recommended_minutes:null,local_default_minutes:1440,timeframes:[60,240,1440],timeframe_evidence:'Synthetic test catalog',adaptation:'Synthetic fixture',review:'Independent fixture',compatibility:'Closed bars',verification:'Test fixture',parameters:{}};
const data={id:'hourly',source:'Synthetic',market:'spot',symbol:'BTCUSDT',interval_seconds:3600,range:[0,31536000],coverage:{trade:{count:8760,complete:true,gaps:[]}}};
const rows=['Daily trend','Hourly trend','Four-hour trend','Buy & Hold','DCA'].map((name,ordinal)=>({name,kind:ordinal<3?'graph':'benchmark',profile:{...defaultProfile,capital:'1000',execution_minutes:60,primary_minutes:[1440,60,240,60,60][ordinal]},dataset:{id:data.id}}));

it('guides first-time testing through history, exact timeframe review, navigation and cancellation',async()=>{
 let prepared=false,cancelled=false;
 const report=()=>({id:'new',status:cancelled?'cancelled':'running',active_id:cancelled?null:'new',snapshot:{inputs:{},rows},rows:rows.map((_,ordinal)=>({ordinal,status:ordinal===0?'completed':'pending',run_id:ordinal===0?'daily-run':null,metrics:ordinal===0?{net_pnl:'10',period_return:'.01'}:null}))});
 vi.mocked(api).mockImplementation(async(command,p:any)=>{
  if(command==='library_catalog')return [entry];
  if(command==='list_datasets')return prepared?[data]:[];
  if(command==='library_batches')return [];
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
 fireEvent.click(screen.getByRole('button',{name:'Market data'}));
 fireEvent.click(screen.getByRole('button',{name:'Saved tests'}));
 fireEvent.click(await screen.findByRole('button',{name:'Cancel remaining tests'}));
 expect(await screen.findByText(/cancelled · 1\/5 completed/)).toBeTruthy();
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
  if(command==='library_batches')return [{id:'saved',status:'completed',created_at:'Saved fixture'}];
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
 fireEvent.change(screen.getByLabelText('Research capital'),{target:{value:'2000'}});
 fireEvent.click(screen.getByRole('button',{name:'Saved tests'}));
 expect(screen.getByText('25.0000 / 2.50%')).toBeTruthy();
 expect(report.snapshot.rows[0].profile.capital).toBe('1000');
 expect(vi.mocked(api).mock.calls.some(([c])=>/prepare|start|warmup|preview/.test(c))).toBe(false);
});

it('customizes an independent draft and preserves the card selection when returning',async()=>{
 vi.mocked(api).mockImplementation(async(command)=>{
  if(command==='library_catalog')return [entry,{...entry,id:'second',name:'Second idea'}];
  if(command==='library_batches'||command.startsWith('list_'))return [];
  if(command==='run_history')return {rows:[],next:null};
  if(command==='library_copy')return {strategy_id:'independent'};
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
 await screen.findByText('Graph workspace');
 expect((screen.getByLabelText('Strategy name') as HTMLInputElement).value).toBe('Independent draft');
 fireEvent.click(screen.getByRole('button',{name:'Strategy library'}));
 expect((screen.getByLabelText('Include Test trend') as HTMLInputElement).checked).toBe(true);
 expect(api).toHaveBeenCalledWith('get_strategy',{strategy_id:'independent'});
 expect(vi.mocked(api).mock.calls.some(([c])=>['trust_native','start_run','library_batch_start'].includes(c))).toBe(false);
});
