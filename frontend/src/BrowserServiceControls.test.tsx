import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import BrowserServiceControls from './BrowserServiceControls';
import {api,stopLocalService} from './api';
vi.mock('./api',()=>({api:vi.fn(),stopLocalService:vi.fn()}));
beforeEach(()=>{
  vi.clearAllMocks();vi.mocked(api).mockImplementation(async command=>['list_runs','list_experiments','library_batches'].includes(command)?[]:{status:'idle'});
  vi.mocked(stopLocalService).mockResolvedValue();
});
afterEach(()=>vi.restoreAllMocks());
const leave=()=>{const event=new Event('beforeunload',{cancelable:true});window.dispatchEvent(event);return event;};

it('warns for active work without cancelling or stopping when leaving, and removes the listener on cleanup',async()=>{
  const {rerender,unmount}=render(<BrowserServiceControls active onStopped={()=>{}}/>);
  await waitFor(()=>expect(api).toHaveBeenCalledWith('live_status'));
  expect(screen.getByText(/closing this tab keeps work running/)).toBeTruthy();
  expect(leave().defaultPrevented).toBe(true);
  expect(stopLocalService).not.toHaveBeenCalled();expect(vi.mocked(api).mock.calls.some(([command])=>/cancel|close|pause|start/.test(command))).toBe(false);
  rerender(<BrowserServiceControls active={false} onStopped={()=>{}}/>);
  await waitFor(()=>expect(leave().defaultPrevented).toBe(false));
  unmount();expect(leave().defaultPrevented).toBe(false);
});

it('detects work from another tab or a previous page load',async()=>{
  vi.mocked(api).mockImplementation(async command=>command==='library_batches'?[{status:'running'}]:['list_runs','list_experiments'].includes(command)?[]:{status:'idle'});
  render(<BrowserServiceControls active={false} onStopped={()=>{}}/>);
  await waitFor(()=>expect(api).toHaveBeenCalledWith('library_batches'));
  expect(leave().defaultPrevented).toBe(true);expect(stopLocalService).not.toHaveBeenCalled();
});

it('requires confirmation and sends a single stop while shutdown is pending',async()=>{
  const confirm=vi.spyOn(window,'confirm').mockReturnValue(false),stopped=vi.fn();
  let finish!:()=>void;vi.mocked(stopLocalService).mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  render(<BrowserServiceControls active={false} onStopped={stopped}/>);
  fireEvent.click(screen.getByRole('button',{name:'Stop local service'}));expect(stopLocalService).not.toHaveBeenCalled();
  confirm.mockReturnValue(true);fireEvent.click(screen.getByRole('button',{name:'Stop local service'}));
  expect(confirm).toHaveBeenLastCalledWith(expect.stringContaining('cancels active tests'));
  fireEvent.click(screen.getByRole('button',{name:'Stopping local service…'}));expect(stopLocalService).toHaveBeenCalledOnce();
  finish();await waitFor(()=>expect(stopped).toHaveBeenCalledOnce());
});

it('reports uncertain shutdown and does not retry it automatically',async()=>{
  vi.spyOn(window,'confirm').mockReturnValue(true);vi.mocked(stopLocalService).mockRejectedValue(new Error('Connection lost'));
  const stopped=vi.fn();render(<BrowserServiceControls active={false} onStopped={stopped}/>);
  fireEvent.click(screen.getByRole('button',{name:'Stop local service'}));
  expect(await screen.findByRole('alert')).toHaveProperty('textContent',expect.stringContaining('Could not confirm shutdown'));
  expect(stopLocalService).toHaveBeenCalledOnce();expect(stopped).not.toHaveBeenCalled();
});


it.each(['archive:','export:'])('warns for a %s reservation discovered after reload without cancelling it',async(prefix)=>{
 vi.mocked(api).mockImplementation(async command=>command==='scheduler_status'?{reservation:prefix+'operation'}:['list_runs','list_experiments','library_batches'].includes(command)?[]:{status:'idle'});
 render(<BrowserServiceControls active={false} onStopped={()=>{}}/>);
 await waitFor(()=>expect(api).toHaveBeenCalledWith('scheduler_status'));
 expect(leave().defaultPrevented).toBe(true);expect(stopLocalService).not.toHaveBeenCalled();
 expect(vi.mocked(api).mock.calls.some(([command])=>['archive_import_cancel','archive_export_cancel'].includes(command))).toBe(false);
});

it('warns before stopping a pending verified chart or note-save reader',async()=>{
 vi.mocked(api).mockImplementation(async command=>command==='scheduler_status'?{verified_reads:[{request_id:'read',kind:'save',status:'running'}]}:['list_runs','list_experiments','library_batches'].includes(command)?[]:{status:'idle'});
 const confirm=vi.spyOn(window,'confirm').mockReturnValue(false);
 render(<BrowserServiceControls active={false} onStopped={()=>{}}/>);
 await waitFor(()=>expect(api).toHaveBeenCalledWith('scheduler_status'));
 expect(leave().defaultPrevented).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Stop local service'}));
 expect(confirm).toHaveBeenCalledWith(expect.stringContaining('pending verified reads and note saves'));expect(stopLocalService).not.toHaveBeenCalled();
});
