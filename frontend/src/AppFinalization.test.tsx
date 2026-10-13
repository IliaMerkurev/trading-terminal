import {afterEach,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,cleanup,waitFor} from '@testing-library/react';
import App from './App';
import {api} from './api';
import {defaultProfile} from './model';
vi.mock('./GraphEditor',()=>({default:()=> <div>Graph workspace</div>}));
vi.mock('./RunChart',()=>({default:()=> <div>Saved chart fixture</div>}));
vi.mock('./RunSnapshot',()=>({default:()=> <div>Saved snapshot fixture</div>}));
vi.mock('./RunLogs',()=>({default:()=> <div>Saved logs fixture</div>}));
vi.mock('./api',()=>({transportCapabilities:()=>({mode:'desktop',localService:true,nativeWindow:true,openExportsFolder:true,downloadArchives:false,stopService:false}),productVersion:async()=>'0.6.0-dev',downloadArchive:vi.fn(),api:vi.fn()}));
vi.mock('@tauri-apps/api/window',()=>({getCurrentWindow:()=>({onCloseRequested:async()=>()=>{}})}));
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn()}));
afterEach(()=>{cleanup();vi.resetAllMocks();});
function fixture(status:string){
 const row={id:'local-run',created_at:'2026-10-11T00:00:00Z',status,summary:status==='completed'?{origin:'local',profile:defaultProfile,metrics:{net_pnl:'0',max_drawdown:'0',trade_count:0,win_rate:null,fees:'0',funding:'0'}}:null};
 vi.mocked(api).mockImplementation(async command=>{
  if(command==='run_history')return {rows:[row],next:null};
  if(command==='run_status')return {...row,worker_active:status!=='completed',finalization:status==='running'?null:{phase:'artifact',staged_rows:0,total_rows:1202,staged_bytes:0}};
  if(command==='result_page')return {rows:[],total:0,next:null};
  if(command==='library_batch_history')return {rows:[],next:null};
  if(command.startsWith('list_')||command==='library_catalog'||command==='library_batches')return [];
  return {};
 });
 return row;
}
async function history(){
 const rendered=render(<App/>);fireEvent.click(screen.getByRole('button',{name:'Saved tests'}));fireEvent.click(screen.getByRole('button',{name:'Individual run reports'}));
 await waitFor(()=>expect(rendered.container.querySelectorAll('.run-list button')).toHaveLength(1));
 return rendered.container.querySelector('.run-list button')!;
}
it.each(['running','finalizing','cancel_requested'])('opens active %s history at its Backtest status',async status=>{
 fixture(status);const row=await history();
 expect(row.querySelector('span')?.textContent).toBe(status);fireEvent.click(row);
 expect(screen.getByRole('heading',{name:'Prepare a reproducible run'})).toBeTruthy();
 await waitFor(()=>expect(api).toHaveBeenCalledWith('run_status',{run_id:'local-run'}));
 expect(screen.queryByRole('heading',{name:/Saved report/})).toBeNull();
 if(status==='finalizing'){
  const copy=await screen.findByText(/Finalizing result · artifact/);
  expect(copy.closest('.run-status')?.querySelector('p small')).toBeTruthy();
 }
});
it('continues opening a completed history item as a saved report',async()=>{
 fixture('completed');const row=await history();
 expect(row.querySelector('strong')?.textContent).toBe('BTCUSDT');fireEvent.click(row);
 expect(screen.getByRole('heading',{name:'Saved report · BTCUSDT'})).toBeTruthy();
 expect(screen.queryByRole('heading',{name:'Prepare a reproducible run'})).toBeNull();
 expect(vi.mocked(api).mock.calls.some(([command])=>command==='start_run')).toBe(false);
});
