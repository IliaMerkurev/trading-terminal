import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import App from './App';
import {api} from './api';

const fixture=vi.hoisted(()=>({observation:null as any}));
vi.mock('./GraphEditor',()=>({default:()=>null}));
vi.mock('./Experiments',()=>({default:()=>null}));
vi.mock('./Live',()=>({default:()=>null}));
// Exercise the actual App callback and actual Lab request assembly, without chart I/O.
vi.mock('./Observations',()=>({default:({onTest}:any)=><button onClick={()=>onTest(fixture.observation)}>Test saved observation in Lab</button>}));
vi.mock('./api',()=>({transportCapabilities:()=>({mode:'browser',localService:true,nativeWindow:false,openExportsFolder:false,downloadArchives:true,stopService:true}),
 productVersion:async()=>'0.6.0-dev',api:vi.fn(),stopLocalService:vi.fn(),downloadArchive:vi.fn()}));
vi.mock('@tauri-apps/api/window',()=>({getCurrentWindow:vi.fn()}));
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn()}));

it.each([15,60,240,1440])('submits compatible shared profile after a %im observation transfer without a resolution toggle',async minutes=>{
 const day=86400,start=200*day,end=204*day;
 const source={id:'synthetic-source',source:'Synthetic/local daily-rule fixture',market:'spot',symbol:'BTCUSDT',interval_seconds:minutes*60,range:[0,207*day],coverage:{trade:{complete:true,count:207*1440/minutes}}};
 fixture.observation={id:'saved-note',revision:3,source,start,end};
 const entry={id:'double-seven-reversion',version:1,name:"Double 7's daily reversion",family:'mean_reversion',kind:'Adapted',source_url:'https://example.org/rules',license:'MIT',markets:['spot'],directions:['long'],source_default_minutes:1440,author_recommended_minutes:null,local_default_minutes:1440,timeframes:[1440],parameters:{},adaptation:'Synthetic fixture',review:'Independent rules',compatibility:'Daily',verification:'Synthetic only'};
 vi.mocked(api).mockReset().mockImplementation(async(command,p:any)=>{
  if(command==='list_datasets')return [source];
  if(command==='library_catalog')return [entry];
  if(command==='library_batch_history'||command==='run_history')return {rows:[],next:null};
  if(command.startsWith('list_'))return [];
  if(command==='download_status')return {status:'idle'};
  if(command==='library_warmup')return {start,end,available:true};
  if(command==='dataset_profile')return {tick_size:'.5',quantity_step:'.1',min_quantity:'.1'};
  if(command==='library_batch_preview'){
   // Same critical backend Profile divisibility gate; never silently fix the request in this stub.
   if(p.profile.primary_minutes%p.profile.execution_minutes)throw Error('Strategy timeframe must be a multiple of execution resolution');
   return {contract_sha256:'a'.repeat(64),rows:[{kind:'graph',name:'Ready daily candidate',error:null}]};
  }
  return {};
 });
 render(<App/>);await screen.findByRole('article',{name:entry.name});
 fireEvent.click(screen.getByRole('button',{name:'Edit test setup'}));
 fireEvent.change(screen.getByLabelText('Research capital'),{target:{value:'1250'}});
 fireEvent.click(screen.getByText('Costs, sizing & execution assumptions',{selector:'summary'}));
 fireEvent.change(screen.getByLabelText('Research allocation'),{target:{value:'10'}});
 fireEvent.change(screen.getByLabelText('Adverse slippage'),{target:{value:'1'}});
 fireEvent.click(screen.getByRole('button',{name:'Back to strategies'}));
 fireEvent.click(screen.getByRole('button',{name:'Market'}));
 fireEvent.click(screen.getByRole('button',{name:'Saved history · local'}));
 fireEvent.click(screen.getByRole('button',{name:'Test saved observation in Lab'}));
 await screen.findByRole('region',{name:'Observation test context'});
 expect((screen.getByLabelText('Research resolution') as HTMLSelectElement).value).toBe(String(minutes));
 fireEvent.click(screen.getByRole('button',{name:'Back to strategies'}));
 fireEvent.click(screen.getByRole('button',{name:'Test this strategy'}));
 await waitFor(()=>expect((screen.getByRole('button',{name:'Review test'}) as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(screen.getByRole('button',{name:'Review test'}));
 await screen.findByText(/Ready daily candidate/);
 expect(api).toHaveBeenCalledWith('library_batch_preview',expect.objectContaining({dataset_id:source.id,start,end,
  selections:[{entry_id:entry.id,version:1,minutes:1440,parameters:{}}],
  profile:expect.objectContaining({primary_minutes:minutes<=60?60:minutes,execution_minutes:minutes,capital:'1250',sizing:'percent',allocation:'10',slippage:'0.01',tick_size:'.5',quantity_step:'.1'})}));
 expect(screen.queryByText('Strategy timeframe must be a multiple of execution resolution')).toBeNull();
 expect(vi.mocked(api).mock.calls.some(([command])=>/start|trust|save_graph|download_start/.test(command))).toBe(false);
});
