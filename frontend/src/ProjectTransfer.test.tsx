import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import ProjectTransfer from './ProjectTransfer';
import {api} from './api';
vi.mock('./api',()=>({isDesktop:()=>true,api:vi.fn()}));
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn()}));
it('transfers selected file bytes in exact bounded order and opens only the validated import',async()=>{
  const imported=vi.fn(async()=>{});
  vi.mocked(api).mockImplementation(async(command)=>{
    if(command==='archive_begin')return {upload_id:'transfer',chunk_bytes:3};
    if(command==='archive_finish')return {strategy_id:'validated',note:'Imported report; no Python executed'};
    return {offset:3};
  });
  render(<ProjectTransfer strategy={()=>({})} profile={{}} runIds={[]} onImported={imported}/>);
  fireEvent.click(screen.getByText('Project archive'));
  const bytes=new Uint8Array([80,75,3,4,5,6,7]);
  const selectedFile={size:bytes.length,slice:(start:number,end:number)=>({arrayBuffer:async()=>bytes.slice(start,end).buffer})};
  fireEvent.change(screen.getByLabelText('Import project archive'),{target:{files:[selectedFile]}});
  await waitFor(()=>expect(imported).toHaveBeenCalledWith(expect.objectContaining({strategy_id:'validated'})));
  const calls=vi.mocked(api).mock.calls;
  expect(calls.map(([command])=>command)).toEqual(['archive_begin','archive_append','archive_append','archive_append','archive_finish']);
  const chunks=calls.filter(([c])=>c==='archive_append').map(([,p])=>p!);
  expect(chunks.map(p=>p.offset)).toEqual([0,3,6]);
  expect(chunks.map(p=>atob(p.data as string)).join('')).toBe(String.fromCharCode(...bytes));
  expect(calls.some(([c])=>c==='trust_native'||c==='start_run')).toBe(false);
});
