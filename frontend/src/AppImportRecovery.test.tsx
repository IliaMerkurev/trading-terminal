import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,cleanup,waitFor,act} from '@testing-library/react';
import App from './App';
import {api} from './api';
import {defaultProfile} from './model';
vi.mock('./RunChart',()=>({default:()=> <div>Saved chart fixture</div>}));
vi.mock('./GraphEditor',()=>({default:()=> <div>Graph workspace</div>}));
vi.mock('./api',()=>({isDesktop:()=>true,transportCapabilities:()=>({mode:'desktop',localService:true,nativeWindow:true,openExportsFolder:true,downloadArchives:false,stopService:false}),productVersion:async()=>'0.6.0-dev',downloadArchive:vi.fn(),api:vi.fn()}));
vi.mock('@tauri-apps/api/window',()=>({getCurrentWindow:()=>({onCloseRequested:async()=>()=>{}})}));
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn()}));
afterEach(()=>{cleanup();vi.resetAllMocks();});
it.each(['list_strategies','run_history','get_strategy'])('propagates the narrow import %s error without changing global action or persistence',async failed=>{
 let committed=false;
 vi.mocked(api).mockImplementation(async command=>{
  if(committed&&command===failed)throw Error(`Failed ${failed}`);
  if(command==='archive_begin')return {operation_id:'a'.repeat(32),upload_id:'a'.repeat(32),chunk_bytes:10};
  if(command==='archive_import_start'||command==='archive_import_status'){committed=true;return {operation_id:'a'.repeat(32),phase:'terminal',outcome:'completed',content_identity:'bound',artifact_verification:'not_checked',inspection_state:'available',items:[{kind:'strategy',destination_id:'saved'}]};}
  if(command==='run_history'||command==='library_batch_history')return {rows:[],next:null};
  if(command.startsWith('list_')||command==='library_catalog')return [];
  return {};
 });
 render(<App/>);fireEvent.click(screen.getByRole('button',{name:'Saved tests'}));fireEvent.click(screen.getByRole('button',{name:'Individual run reports'}));
 fireEvent.click(screen.getByText('Project archive'));
 fireEvent.change(screen.getByLabelText('Import project archive'),{target:{files:[{size:1,slice:()=>({arrayBuffer:async()=>new Uint8Array([80]).buffer})}]}});
 expect(await screen.findByText(new RegExp(`refreshing or opening the strategy failed: Error: Failed ${failed}`))).toBeTruthy();
 expect(screen.getByRole('heading',{name:'Import completed'})).toBeTruthy();
 expect(vi.mocked(api).mock.calls.filter(([c])=>c==='archive_import_start')).toHaveLength(1);
 expect(vi.mocked(api).mock.calls.some(([c])=>['archive_cancel','archive_import_cancel','trust_native','start_run'].includes(c))).toBe(false);
});


it('does not replace editor changes when a late import strategy read returns after navigation',async()=>{
 let resolve!:(value:any)=>void;
 vi.mocked(api).mockImplementation(async command=>{
  if(command==='archive_begin')return {operation_id:'a'.repeat(32),upload_id:'a'.repeat(32),chunk_bytes:10};
  if(command==='archive_import_start'||command==='archive_import_status')return {operation_id:'a'.repeat(32),phase:'terminal',outcome:'completed',inspection_state:'available',items:[{kind:'strategy',destination_id:'saved'}]};
  if(command==='get_strategy')return new Promise(r=>{resolve=r;});
  if(command==='run_history'||command==='library_batch_history')return {rows:[],next:null};
  if(command.startsWith('list_')||command==='library_catalog')return [];
  return {};
 });
 render(<App/>);fireEvent.click(screen.getByRole('button',{name:'Saved tests'}));fireEvent.click(screen.getByRole('button',{name:'Individual run reports'}));
 fireEvent.change(screen.getByLabelText('Import project archive'),{target:{files:[{size:1,slice:()=>({arrayBuffer:async()=>new Uint8Array([80]).buffer})}]}});
 await waitFor(()=>expect(api).toHaveBeenCalledWith('get_strategy',{strategy_id:'saved'}));
 fireEvent.click(screen.getByRole('button',{name:'Strategy editor'}));
 const input=screen.getByLabelText('Strategy name');fireEvent.change(input,{target:{value:'New editor draft'}});
 await act(async()=>resolve({name:'Late imported strategy',kind:'graph',document:{graph:{nodes:[],edges:[]},layout:{}}}));
 expect((screen.getByLabelText('Strategy name') as HTMLInputElement).value).toBe('New editor draft');
 expect(vi.mocked(api).mock.calls.filter(([c])=>c==='archive_import_start')).toHaveLength(1);
 expect(vi.mocked(api).mock.calls.some(([c])=>c==='archive_import_cancel')).toBe(false);
});


it('keeps imported provenance visible beside a directly opened saved report in normal mode',async()=>{
 const op='a'.repeat(32);
 vi.mocked(api).mockImplementation(async command=>{
  if(command==='archive_import_list')return {rows:[{operation_id:op,created_at:'2026-10-10',phase:'terminal',outcome:'partial',archive_sha256:'hash'}],next:null};
  if(command==='archive_import_status')return {operation_id:op,phase:'terminal',outcome:'partial',content_identity:'bound',artifact_verification:'not_checked',inspection_state:'available',items:[{kind:'run',ordinal:0,destination_id:'saved-run',source_run_id:'source',publication_state:'published',current_status:'completed'}]};
  if(command==='run_status')return {id:'saved-run',created_at:'2026-10-10',status:'completed',summary:{origin:'imported',profile:defaultProfile,metrics:{net_pnl:'0',max_drawdown:'0',trade_count:0,win_rate:null,fees:'0',funding:'0'}}};
  if(command==='result_page')return {rows:[],total:0,next:null};
  if(command==='run_history'||command==='library_batch_history')return {rows:[],next:null};
  if(command.startsWith('list_')||command==='library_catalog')return [];
  return {};
 });
 render(<App/>);fireEvent.click(screen.getByRole('button',{name:'Saved tests'}));fireEvent.click(screen.getByRole('button',{name:'Individual run reports'}));fireEvent.click(screen.getByText('Project archive'));
 fireEvent.click(screen.getByRole('button',{name:'Recent imports'}));fireEvent.click(await screen.findByRole('button',{name:`Inspect import ${op}`}));fireEvent.click(await screen.findByRole('button',{name:'Open report 1'}));
 expect(await screen.findByText('Imported report: saved archive values, not locally verified calculations. Raw candle history is omitted. Artifact files have not been verified.')).toBeTruthy();
 expect(screen.getByRole('heading',{name:'Import partial'})).toBeTruthy();
 expect(vi.mocked(api).mock.calls.some(([c])=>['archive_begin','archive_import_start','trust_native','start_run'].includes(c))).toBe(false);
});
