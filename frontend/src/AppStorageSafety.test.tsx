import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import App from './App';
import {api} from './api';
import {invoke} from '@tauri-apps/api/core';
import {storageFailureReleased} from './storageSafety';
const windowMock=vi.hoisted(()=>({close:null as null|((event:{preventDefault:()=>void})=>void)}));
vi.mock('./GraphEditor',()=>({default:()=> <div>Graph workspace</div>}));
vi.mock('./api',()=>({isDesktop:()=>true,transportCapabilities:()=>({mode:'desktop',localService:true,nativeWindow:true,openExportsFolder:true,downloadArchives:false,stopService:false}),productVersion:async()=>'0.6.0-dev',downloadArchive:vi.fn(),api:vi.fn()}));
vi.mock('@tauri-apps/api/window',()=>({getCurrentWindow:()=>({onCloseRequested:async(fn:any)=>{windowMock.close=fn;return ()=>{windowMock.close=null;};}})}));
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn(async()=>{})}));
vi.mock('@tauri-apps/api/app',()=>({getVersion:async()=> '0.6.0-dev'}));
afterEach(()=>{cleanup();vi.clearAllMocks();});
const failure={id:'faulted',kind:'run',durable:false as const,message:'Calculations blocked by storage finalization failure. Restart after checking storage.'};
const stopped={storage_failure:failure,active:null,reservation:null};
const base=(command:string)=>{
  if(command==='run_history'||command==='library_batch_history')return {rows:[],next:null};
  if(command==='list_datasets')return [{id:'dataset',source:'Synthetic',market:'spot',symbol:'BTCUSDT',range:[0,3600],coverage:{trade:{count:60,complete:true}}}];
  if(command.startsWith('list_')||command==='library_catalog'||command==='library_batches')return [];
  return {};
};

it('closes a faulted standalone run without cancelling stale durable running state',async()=>{
  let fault=false;
  vi.mocked(api).mockImplementation(async command=>{
    if(command==='scheduler_status')return fault?stopped:{storage_failure:null,active:null,reservation:null};
    if(command==='start_run')return {run_id:'faulted'};
    if(command==='run_status')return {id:'faulted',status:'running'};
    if(command==='cancel_run')throw Error('That run is not active');
    return base(command);
  });
  render(<App/>);
  fireEvent.click(screen.getByRole('button',{name:'Custom backtest'}));
  await waitFor(()=>expect(screen.getByLabelText('Prepared dataset').querySelectorAll('option')).toHaveLength(2));
  fireEvent.change(screen.getByLabelText('Prepared dataset'),{target:{value:'dataset'}});
  fireEvent.click(screen.getByText('Run immutable snapshot'));
  await screen.findByText('Cancel run',{selector:'button'});
  fault=true;windowMock.close!({preventDefault:vi.fn()});
  await waitFor(()=>expect(invoke).toHaveBeenCalledWith('close_application'));
  expect(api).not.toHaveBeenCalledWith('cancel_run',expect.anything());
  expect(screen.queryByRole('dialog')).toBeNull();
});

it('closes a replay that fails after the close prompt without issuing obsolete cancellation',async()=>{
  let fault=false;
  vi.mocked(api).mockImplementation(async command=>{
    if(command==='scheduler_status')return fault?stopped:{storage_failure:null,active:{id:'replay',kind:'replay'},reservation:null};
    if(command==='replay_status')return {id:'replay',status:'running',worker_active:!fault};
    if(command==='replay_cancel')throw Error('That replay is not active');
    return base(command);
  });
  render(<App/>);await waitFor(()=>expect(windowMock.close).not.toBeNull());
  windowMock.close!({preventDefault:vi.fn()});
  await screen.findByRole('dialog');
  fault=true;fireEvent.click(screen.getByText('Cancel run and exit'));
  await waitFor(()=>expect(invoke).toHaveBeenCalledWith('close_application'));
  expect(api).not.toHaveBeenCalledWith('replay_cancel',expect.anything());
});

it('still prompts and cancels an active download after calculation storage failure',async()=>{
  vi.mocked(api).mockImplementation(async command=>{
    if(command==='scheduler_status')return stopped;
    if(command==='download_start'||command==='download_status')return {status:'running'};
    if(command==='download_cancel')return {status:'cancel_requested'};
    return base(command);
  });
  render(<App/>);fireEvent.click(screen.getByRole('button',{name:'Custom backtest'}));
  fireEvent.click(screen.getByText('Download selected market / instrument'));
  await screen.findByText('Cancel download',{selector:'button'});
  windowMock.close!({preventDefault:vi.fn()});
  await screen.findByRole('dialog');
  expect(invoke).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText('Cancel run and exit'));
  await waitFor(()=>expect(invoke).toHaveBeenCalledWith('close_application'));
  expect(api).toHaveBeenCalledWith('download_cancel');
  const index=vi.mocked(api).mock.calls.findIndex(([command])=>command==='download_cancel');
  expect(vi.mocked(api).mock.invocationCallOrder[index]).toBeLessThan(vi.mocked(invoke).mock.invocationCallOrder[0]);
});

it('never equates an existing worker or scheduler reservation with a released failure',()=>{
  expect(storageFailureReleased(stopped)).toBe(true);
  expect(storageFailureReleased({...stopped,active:{id:'worker',kind:'run'}})).toBe(false);
  expect(storageFailureReleased({...stopped,reservation:'batch'})).toBe(false);
  expect(storageFailureReleased({...stopped,storage_failure:null})).toBe(false);
  expect(storageFailureReleased({storage_failure:failure} as any)).toBe(false);
});
