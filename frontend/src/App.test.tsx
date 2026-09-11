import { describe,it,expect,vi } from 'vitest';
import { render,screen,fireEvent,waitFor } from '@testing-library/react';
import App from './App';
import { api } from './api';
import {invoke} from '@tauri-apps/api/core';
const windowMock=vi.hoisted(()=>({close:null as null|((event:{preventDefault:()=>void})=>void)}));
vi.mock('./GraphEditor',()=>({default:()=> <div>Graph workspace</div>}));
vi.mock('./api',()=>({isDesktop:()=>true,api:vi.fn(async(command:string)=>command.startsWith('list_')?[]:{strategy_id:'saved'})}));
vi.mock('@tauri-apps/api/window',()=>({getCurrentWindow:()=>({onCloseRequested:async(fn:any)=>{windowMock.close=fn;return ()=>{windowMock.close=null;};}})}));
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn(async()=>{})}));
describe('research workspace',()=>{
  it('saves a graph snapshot and exposes all required tabs',async()=>{
    render(<App/>);
    await screen.findByText('Graph workspace');
    fireEvent.change(screen.getByLabelText('Strategy name'),{target:{value:'Causal trend'}});
    fireEvent.click(screen.getByText('Save',{selector:'button'}));
    await waitFor(()=>expect(api).toHaveBeenCalledWith('save_graph',expect.objectContaining({name:'Causal trend',graph:expect.objectContaining({version:1})})));
    expect(screen.getByText('Backtest',{selector:'button'})).toBeTruthy();
    expect(screen.getByText('Results',{selector:'button'})).toBeTruthy();
  });
  it('does not grant native execution consent on selection or save',async()=>{
    vi.mocked(api).mockClear();render(<App/>);
    fireEvent.click(screen.getByText('＋ Native Python'));
    expect(screen.getByLabelText('Python source preview')).toBeTruthy();
    fireEvent.click(screen.getByText('Save',{selector:'button'}));
    await waitFor(()=>expect(api).toHaveBeenCalledWith('save_native',expect.anything()));
    expect(vi.mocked(api).mock.calls.some(([c])=>c==='trust_native'||c==='start_run')).toBe(false);
  });
  it('keeps an active run on return and cancels it before desktop exit',async()=>{
    vi.mocked(api).mockImplementation(async(command:string)=>{
      if(command==='list_datasets')return [{id:'dataset',source:'Synthetic fixture',market:'spot',symbol:'BTCUSDT',range:[0,3600],coverage:{trade:{count:60,complete:true}}}];
      if(command.startsWith('list_'))return [];
      if(command==='start_run')return {run_id:'active'};
      if(command==='run_status')return {id:'active',status:'running',progress:{fraction:.2}};
      return {};
    });
    render(<App/>);
    fireEvent.click(screen.getByText('Backtest',{selector:'button'}));
    await waitFor(()=>expect(screen.getByLabelText('Prepared dataset').querySelectorAll('option').length).toBe(2));
    fireEvent.change(screen.getByLabelText('Prepared dataset'),{target:{value:'dataset'}});
    fireEvent.click(screen.getByText('Run immutable snapshot'));
    await screen.findByText('Cancel run',{selector:'button'});
    const preventDefault=vi.fn();windowMock.close!({preventDefault});
    await screen.findByRole('dialog');
    fireEvent.click(screen.getByText('Return to application'));
    expect(api).not.toHaveBeenCalledWith('cancel_run',expect.anything());
    expect(invoke).not.toHaveBeenCalled();
    windowMock.close!({preventDefault});
    fireEvent.click(await screen.findByText('Cancel run and exit'));
    await waitFor(()=>expect(invoke).toHaveBeenCalledWith('close_application'));
    expect(api).toHaveBeenCalledWith('cancel_run',{run_id:'active'});
    const cancelCall=vi.mocked(api).mock.calls.findIndex(([c])=>c==='cancel_run');
    expect(vi.mocked(api).mock.invocationCallOrder[cancelCall]).toBeLessThan(vi.mocked(invoke).mock.invocationCallOrder[0]);
    expect(preventDefault).toHaveBeenCalledTimes(2);
  });
});
