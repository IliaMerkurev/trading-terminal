import { describe,it,expect,vi } from 'vitest';
import { render,screen,fireEvent,waitFor } from '@testing-library/react';
import App from './App';
import { api } from './api';
import {invoke} from '@tauri-apps/api/core';
const windowMock=vi.hoisted(()=>({close:null as null|((event:{preventDefault:()=>void})=>void)}));
vi.mock('./GraphEditor',()=>({default:()=> <div>Graph workspace</div>}));
vi.mock('./api',()=>({isDesktop:()=>true,api:vi.fn(async(command:string)=>command==='run_history'?{rows:[],next:null}:command.startsWith('list_')?[]:{strategy_id:'saved'})}));
vi.mock('@tauri-apps/api/window',()=>({getCurrentWindow:()=>({onCloseRequested:async(fn:any)=>{windowMock.close=fn;return ()=>{windowMock.close=null;};}})}));
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn(async()=>{})}));
vi.mock('@tauri-apps/api/app',()=>({getVersion:vi.fn(async()=>'0.3.0-dev')}));
describe('research workspace',()=>{
  it('captures physical undo before a canvas handler can stop propagation',async()=>{
    render(<App/>);const canvas=await screen.findByText('Graph workspace');
    fireEvent.click(screen.getByText('Add node',{selector:'button'}));
    expect((screen.getByText('Undo',{selector:'button'}) as HTMLButtonElement).disabled).toBe(false);
    canvas.addEventListener('keydown',event=>event.stopPropagation());
    fireEvent.keyDown(canvas,{key:'я',code:'KeyZ',ctrlKey:true});
    expect((screen.getByText('Undo',{selector:'button'}) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.keyDown(canvas,{key:'н',code:'KeyY',ctrlKey:true});
    expect((screen.getByText('Undo',{selector:'button'}) as HTMLButtonElement).disabled).toBe(false);
  });
  it('saves a graph snapshot and exposes all required tabs',async()=>{
    render(<App/>);
    await screen.findByText('Graph workspace');
    await screen.findByText('RESEARCH 0.3-dev');
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
      if(command==='run_history')return {rows:[],next:null};
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


it('loads Results beyond 100 saved runs, preserves rows on error, and retries without duplicates',async()=>{
 const rows=Array.from({length:125},(_,i)=>({id:String(125-i).padStart(32,'0'),created_at:'2026-01-01T00:00:00+00:00',status:'completed',summary:{profile:{symbol:'BTCUSDT',evaluation:'closed'},metrics:{net_pnl:0}}}));
 let failed=false;
 vi.mocked(api).mockImplementation(async(command:string,p:any)=>{
  if(command==='run_history'){
   const offset=p.before?rows.findIndex(r=>r.id===p.before.id)+1:0;
   if(offset===50&&!failed){failed=true;throw new Error('Synthetic history failure');}
   const page=rows.slice(offset,offset+50),last=page.at(-1);
   return {rows:offset===50?[rows[49],...page]:page,next:offset+50<rows.length?{id:last!.id,created_at:last!.created_at}:null};
  }
  if(command.startsWith('list_'))return [];
  return {};
 });
 const {container}=render(<App/>);
 fireEvent.click(screen.getByText('Results',{selector:'button'}));
 await waitFor(()=>expect(container.querySelectorAll('.run-list button')).toHaveLength(50));
 fireEvent.click(screen.getByRole('button',{name:'Load older runs'}));
 await screen.findByText(/Synthetic history failure/);
 expect(container.querySelectorAll('.run-list button')).toHaveLength(50);
 fireEvent.click(screen.getByRole('button',{name:'Retry run history'}));
 await waitFor(()=>expect(container.querySelectorAll('.run-list button')).toHaveLength(100));
 fireEvent.click(screen.getByRole('button',{name:'Load older runs'}));
 await waitFor(()=>expect(container.querySelectorAll('.run-list button')).toHaveLength(125));
 expect(screen.getByText('End of saved run history.')).toBeTruthy();
 expect(screen.queryByRole('button',{name:'Load older runs'})).toBeNull();
});

it('distinguishes initial Results loading from an empty history',async()=>{
 let finish!:(value:any)=>void;
 vi.mocked(api).mockImplementation(async(command:string)=>command==='run_history'?new Promise(resolve=>{finish=resolve;}):[]);
 render(<App/>);fireEvent.click(screen.getByText('Results',{selector:'button'}));
 expect(screen.getByText('Loading run history…')).toBeTruthy();
 expect(screen.queryByText('No saved runs.')).toBeNull();
 finish({rows:[],next:null});
 expect(await screen.findByText('No saved runs.')).toBeTruthy();
 expect(screen.queryByText('End of saved run history.')).toBeNull();
});
