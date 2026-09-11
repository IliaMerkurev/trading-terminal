import { describe,it,expect,vi } from 'vitest';
import { render,screen,fireEvent,waitFor } from '@testing-library/react';
import App from './App';
import { api } from './api';
vi.mock('./GraphEditor',()=>({default:()=> <div>Graph workspace</div>}));
vi.mock('./api',()=>({isDesktop:()=>true,api:vi.fn(async(command:string)=>command.startsWith('list_')?[]:{strategy_id:'saved'})}));
vi.mock('@tauri-apps/api/window',()=>({getCurrentWindow:()=>({onCloseRequested:async()=>()=>{}})}));
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
});
