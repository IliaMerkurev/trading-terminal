import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import App from './App';
import {api,stopLocalService} from './api';
import {invoke} from '@tauri-apps/api/core';
import {getCurrentWindow} from '@tauri-apps/api/window';

vi.mock('./GraphEditor',()=>({default:()=> <div>Graph workspace</div>}));
vi.mock('./StrategyLibrary',()=>({default:()=> <div>Strategy library content</div>}));
vi.mock('./Experiments',()=>({default:()=> <div>Experiment content</div>}));
vi.mock('./RunLogs',()=>({default:()=>null}));
vi.mock('./api',()=>({
  transportCapabilities:()=>({mode:'browser',localService:true,nativeWindow:false,openExportsFolder:false,downloadArchives:true,stopService:true}),
  productVersion:async()=>'0.6.0-dev',api:vi.fn(),stopLocalService:vi.fn(),downloadArchive:vi.fn(),
}));
vi.mock('@tauri-apps/api/window',()=>({getCurrentWindow:vi.fn()}));
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn()}));
const base=async(command:string):Promise<any>=>{
  if(command==='run_history')return {rows:[],next:null};
  if(command==='library_batch_history')return {rows:[],next:null};
  if(command.startsWith('list_')||command==='library_batches')return [];
  if(command==='download_status')return {status:'idle'};
  if(command==='platform_capabilities')return {platform:'linux',native_execution:{available:false,reason:'Unavailable on Linux'}};
  return {};
};
beforeEach(()=>{vi.clearAllMocks();vi.mocked(api).mockImplementation(base);vi.mocked(stopLocalService).mockResolvedValue();});
afterEach(()=>vi.restoreAllMocks());

it('loads a real browser workspace with service version and enables saving without native window calls',async()=>{
  render(<App/>);
  expect(await screen.findByText('Local workspace · 0.6-dev')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Strategy editor'}));
  expect((screen.getByRole('button',{name:'Save'}) as HTMLButtonElement).disabled).toBe(false);
  fireEvent.click(screen.getByRole('button',{name:'Save'}));
  await waitFor(()=>expect(api).toHaveBeenCalledWith('save_graph',expect.anything()));
  expect(getCurrentWindow).not.toHaveBeenCalled();expect(invoke).not.toHaveBeenCalled();
  expect(screen.queryByText(/Browser layout preview/)).toBeNull();
});

it('restores an active run and history download after page reload without starting them again',async()=>{
  vi.mocked(api).mockImplementation(async(command)=>{
    if(command==='list_runs')return [{id:'existing-run',status:'running'}];
    if(command==='run_status')return {id:'existing-run',status:'running',progress:{fraction:.2}};
    if(command==='download_status')return {status:'running',stage:'trade'};
    return base(command);
  });
  render(<App/>);
  fireEvent.click(await screen.findByRole('button',{name:'Test running'}));
  expect(await screen.findByRole('button',{name:'Cancel run'})).toBeTruthy();
  expect(await screen.findByRole('button',{name:'Cancel download'})).toBeTruthy();
  expect(vi.mocked(api).mock.calls.some(([command])=>command==='start_run'||command==='download_start')).toBe(false);
  const leave=new Event('beforeunload',{cancelable:true});window.dispatchEvent(leave);expect(leave.defaultPrevented).toBe(true);
  expect(vi.mocked(api).mock.calls.some(([command])=>command==='cancel_run'||command==='download_cancel')).toBe(false);
});

it('shows the stopped state only after confirmed shutdown succeeds',async()=>{
  vi.spyOn(window,'confirm').mockReturnValue(true);render(<App/>);
  fireEvent.click(screen.getByRole('button',{name:'Stop local service'}));
  expect(await screen.findByRole('heading',{name:'Local service stopped'})).toBeTruthy();
  expect(stopLocalService).toHaveBeenCalledOnce();expect(invoke).not.toHaveBeenCalled();
  expect(screen.queryByRole('button',{name:'Stop local service'})).toBeNull();
});
