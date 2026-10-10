import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup,act,within} from '@testing-library/react';
import ProjectTransfer from './ProjectTransfer';
import {api} from './api';
import type {ImportReceipt} from './ImportReceipts';
vi.mock('./api',()=>({transportCapabilities:()=>({localService:true,openExportsFolder:false,downloadArchives:true}),api:vi.fn(),downloadArchive:vi.fn()}));
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn()}));
afterEach(()=>{cleanup();vi.resetAllMocks();});
const op='a'.repeat(32),other='b'.repeat(32);
const receipt=(id=op,outcome='completed'):ImportReceipt=>({operation_id:id,phase:'terminal',outcome,termination_reason:'finished',content_identity:'bound',artifact_verification:'not_checked',inspection_state:'available',items:[
  {kind:'run',ordinal:0,destination_id:'run-one',source_run_id:'old-one',publication_state:'published',current_status:'completed'},
  {kind:'run',ordinal:1,destination_id:'run-two',source_run_id:'old-two',publication_state:outcome==='partial'?'reserved':'published',current_status:outcome==='partial'?'interrupted':'completed'},
  {kind:'strategy',ordinal:0,destination_id:'strategy',source_run_id:null,publication_state:outcome==='partial'?'reserved':'published',current_status:outcome==='partial'?'missing':'available'}]});
const file={size:1,slice:()=>({arrayBuffer:async()=>new Uint8Array([80]).buffer})};
function mount(props:any={}){return render(<ProjectTransfer strategy={()=>({})} profile={{}} runIds={[]} onImported={async()=>{}} {...props}/>);}
function upload(){fireEvent.change(screen.getByLabelText('Import project archive'),{target:{files:[file]}});}
function transport(command:string){if(command==='archive_begin')return {operation_id:op,upload_id:op,chunk_bytes:3};if(command==='archive_append')return {offset:1};}
const mutations=()=>vi.mocked(api).mock.calls.filter(([command])=>['archive_begin','archive_append','archive_import_start','archive_cancel','archive_import_cancel','trust_native','start_run','save_graph','save_native'].includes(command));

it('inspects a discarded finish response without cancel, repeat finish, or another upload',async()=>{
 const imported=vi.fn();vi.mocked(api).mockImplementation(async command=>{if(command==='archive_import_start')throw Error('Lost response');if(command==='archive_import_status')return receipt();return transport(command);});
 mount({onImported:imported});upload();await screen.findByText(/start response is uncertain/);
 expect(screen.getByText(`Current operation: ${op}`)).toBeTruthy();
 const writes=mutations().length;fireEvent.click(screen.getByRole('button',{name:/this import/}));
 expect(await screen.findByRole('heading',{name:'Import completed'})).toBeTruthy();
 expect(screen.getByText('Saved receipt confirms completed. Inspection did not retry the import.')).toBeTruthy();
 expect(screen.queryByText(/start response is uncertain/)).toBeNull();expect(screen.queryByText('Error: Lost response')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Refresh this import'}));await waitFor(()=>expect(vi.mocked(api).mock.calls.filter(([c])=>c==='archive_import_status').length).toBeGreaterThanOrEqual(2));
 expect(mutations()).toHaveLength(writes);expect(imported).not.toHaveBeenCalled();
 expect(vi.mocked(api).mock.calls.filter(([c])=>c==='archive_import_start')).toHaveLength(1);
 expect(screen.getByText(/Artifact verification: not checked/)).toBeTruthy();
});

it('recovers after reload through recent receipts and opens only a published member explicitly',async()=>{
 const open=vi.fn(async()=>{}),strategy=vi.fn(async()=>{});
 vi.mocked(api).mockImplementation(async command=>command==='archive_import_list'?{rows:[{operation_id:op,created_at:'2026-10-10T00:00:00Z',phase:'terminal',outcome:'partial',archive_sha256:'f'.repeat(64)}],next:null}:receipt(op,'partial'));
 mount({onOpenReport:open,onOpenStrategy:strategy});fireEvent.click(screen.getByRole('button',{name:'Recent imports'}));
 expect(await screen.findByText(/2026-10-10 00:00:00 UTC/)).toBeTruthy();
 fireEvent.click(await screen.findByRole('button',{name:`Inspect import ${op}`}));
 await screen.findByRole('heading',{name:'Import partial'});expect(screen.queryByRole('button',{name:'Open report 2'})).toBeNull();expect(screen.queryByRole('button',{name:'Open saved strategy'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Open report 1'}));await waitFor(()=>expect(open).toHaveBeenCalledWith('run-one',expect.any(Function)));
 expect(mutations()).toHaveLength(0);expect(strategy).not.toHaveBeenCalled();
});

it('ignores a late receipt lookup after a different operation is selected',async()=>{
 let resolve!:(value:any)=>void;const old=new Promise(r=>{resolve=r;});
 vi.mocked(api).mockImplementation(async(command,p)=>command==='archive_import_list'?{rows:[op,other].map(operation_id=>({operation_id,created_at:'2026-10-10',phase:'terminal',outcome:'completed',archive_sha256:'hash'})),next:null}:p?.operation_id===op?old:receipt(other,'partial'));
 mount();fireEvent.click(screen.getByRole('button',{name:'Recent imports'}));fireEvent.click(await screen.findByRole('button',{name:`Inspect import ${op}`}));
 fireEvent.click(screen.getByRole('button',{name:`Inspect import ${other}`}));await screen.findByRole('heading',{name:'Import partial'});
 await act(async()=>resolve(receipt()));
 expect(within(screen.getByRole('region',{name:'Import receipt'})).getByText(`Operation ${other}`)).toBeTruthy();
 expect(screen.queryByRole('heading',{name:'Import completed'})).toBeNull();expect(mutations()).toHaveLength(0);
});

it('keeps completion visible when the import callback or explicit strategy opening fails',async()=>{
 vi.mocked(api).mockImplementation(async command=>['archive_import_start','archive_import_status'].includes(command)?receipt():transport(command));
 mount({onImported:async()=>{throw Error('refresh unavailable');},onOpenStrategy:async()=>{throw Error('strategy read unavailable');}});upload();
 expect(await screen.findByText(/refreshing or opening the strategy failed/)).toBeTruthy();expect(screen.getByRole('heading',{name:'Import completed'})).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Open saved strategy'}));await screen.findByText(/Could not open the saved strategy/);
 expect(screen.getByRole('heading',{name:'Import completed'})).toBeTruthy();expect(mutations().map(([c])=>c)).toEqual(['archive_begin','archive_append','archive_import_start']);
});

it('shows unavailable status and unknown metadata without claiming an empty successful import',async()=>{
 vi.mocked(api).mockImplementation(async command=>command==='archive_import_list'?{rows:[{operation_id:op,created_at:'2026-10-10',phase:'terminal',outcome:'unknown',archive_sha256:null}],next:null}:Promise.reject(Error('storage unavailable')));
 mount();fireEvent.click(screen.getByRole('button',{name:'Recent imports'}));fireEvent.click(await screen.findByRole('button',{name:`Inspect import ${op}`}));
 await screen.findByText(/Inspection unavailable. Outcome remains unknown/);expect(screen.queryByRole('heading',{name:'Import completed'})).toBeNull();expect(mutations()).toHaveLength(0);
});

it('cancels only the exact receiving upload after an append error',async()=>{
 vi.mocked(api).mockImplementation(async command=>{if(command==='archive_append')throw Error('append response lost');return transport(command);});
 mount();upload();await waitFor(()=>expect(api).toHaveBeenCalledWith('archive_import_cancel',{operation_id:op}));
 expect(mutations().map(([c])=>c)).toEqual(['archive_begin','archive_append','archive_import_cancel']);
});

it('keeps status and cancellation usable while start acknowledgement is pending',async()=>{
 let finish!:(value:any)=>void;vi.mocked(api).mockImplementation(async command=>command==='archive_import_start'?new Promise(resolve=>{finish=resolve;}):command==='archive_import_status'?{...receipt(),phase:'validating',outcome:null,items:[]}:transport(command));
 mount();upload();await screen.findByText(/Starting background import/);
 expect(screen.queryByRole('button',{name:'Cancel upload'})).toBeNull();expect((screen.getByRole('button',{name:/this import/}) as HTMLButtonElement).disabled).toBe(false);expect(screen.getByRole('button',{name:'Cancel import'})).toBeTruthy();
 await act(async()=>finish(receipt()));expect(mutations()).toHaveLength(3);
});


it('does not reopen or cancel after an unmounted final request completes',async()=>{
 let resolve!:(value:any)=>void;const imported=vi.fn();
 vi.mocked(api).mockImplementation(async command=>command==='archive_import_start'?new Promise(r=>{resolve=r;}):transport(command));
 const view=mount({onImported:imported});upload();await screen.findByText(/Starting background import/);view.unmount();
 await act(async()=>resolve({receipt:receipt(),strategy_id:'strategy',note:'Import completed.'}));
 expect(imported).not.toHaveBeenCalled();expect(mutations().map(([c])=>c)).toEqual(['archive_begin','archive_append','archive_import_start']);
});

it('targets cancellation and never sends finish when unmounted during upload',async()=>{
 let resolve!:(value:any)=>void;
 vi.mocked(api).mockImplementation(async command=>command==='archive_append'?new Promise(r=>{resolve=r;}):transport(command));
 const view=mount();upload();await waitFor(()=>expect(api).toHaveBeenCalledWith('archive_append',expect.anything()));view.unmount();
 await act(async()=>resolve({offset:1}));
 expect(mutations().map(([c])=>c)).toEqual(['archive_begin','archive_append','archive_import_cancel']);
 expect(api).toHaveBeenCalledWith('archive_import_cancel',{operation_id:op});
});


it('releases stale opening state when selecting another receipt and rejects the old callback',async()=>{
 let resolve!:()=>void;let applied=false;
 const open=vi.fn(async(_id:string,isCurrent:()=>boolean)=>{await new Promise<void>(r=>{resolve=r;});if(isCurrent())applied=true;});
 vi.mocked(api).mockImplementation(async(command,p)=>command==='archive_import_list'?{rows:[op,other].map(operation_id=>({operation_id,created_at:'2026-10-10',phase:'terminal',outcome:'completed',archive_sha256:'hash'})),next:null}:receipt(String(p?.operation_id)));
 mount({onOpenStrategy:open});fireEvent.click(screen.getByRole('button',{name:'Recent imports'}));fireEvent.click(await screen.findByRole('button',{name:`Inspect import ${op}`}));
 fireEvent.click(await screen.findByRole('button',{name:'Open saved strategy'}));expect((screen.getByLabelText('Import project archive') as HTMLInputElement).disabled).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:`Inspect import ${other}`}));await screen.findByText(`Operation ${other}`);
 expect((screen.getByRole('button',{name:'Open saved strategy'}) as HTMLButtonElement).disabled).toBe(false);
 expect((screen.getByLabelText('Import project archive') as HTMLInputElement).disabled).toBe(false);
 await act(async()=>resolve());expect(applied).toBe(false);expect(screen.queryByRole('alert')).toBeNull();
});


it('does not apply a delayed old cancellation message to a newly selected receipt',async()=>{
 let append!:(value:any)=>void,cancel!:(value:any)=>void;
 vi.mocked(api).mockImplementation(async(command,p)=>{
  if(command==='archive_append')return new Promise(r=>{append=r;});
  if(command==='archive_import_cancel')return new Promise(r=>{cancel=r;});
  if(command==='archive_import_list')return {rows:[{operation_id:other,created_at:'2026-10-10',phase:'terminal',outcome:'completed',archive_sha256:'hash'}],next:null};
  if(command==='archive_import_status')return receipt(other);
  return transport(command);
 });
 mount();upload();await waitFor(()=>expect(api).toHaveBeenCalledWith('archive_append',expect.anything()));
 fireEvent.click(screen.getByRole('button',{name:'Cancel upload'}));await act(async()=>append({offset:1}));
 fireEvent.click(screen.getByRole('button',{name:'Recent imports'}));fireEvent.click(await screen.findByRole('button',{name:`Inspect import ${other}`}));await screen.findByText(`Operation ${other}`);
 await act(async()=>cancel({status:'cancelled',operation_id:op}));
 expect(screen.queryByText(/Upload cancelled/)).toBeNull();expect(screen.getByRole('heading',{name:'Import completed'})).toBeTruthy();
});

it('explicitly continues one revision with a stable attempt key and cancels that exact attempt',async()=>{
 let started=false;const key='c'.repeat(32);
 const partial={...receipt(op,'partial'),revision:4,execution:{state:'terminal',phase:'terminal',attempt_key:key,staged_rows:4,total_rows:8,termination_reason:'process_restart'}};
 const running={...partial,outcome:null,phase:'publishing',revision:5,execution:{...partial.execution,state:'running',phase:'verifying'}};
 vi.mocked(api).mockImplementation(async(command,p)=>{
  if(command==='archive_import_list')return {rows:[{operation_id:op,created_at:'2026-10-10',outcome:'partial',archive_sha256:'hash'}],next:null};
  if(command==='archive_import_status')return started?running:partial;
  if(command==='archive_import_resume'){started=true;running.execution.attempt_key=String(p?.attempt_key);return running;}
  if(command==='archive_import_cancel')return {status:'cancel_requested',operation_id:op};
  return {};
 });
 mount();fireEvent.click(screen.getByRole('button',{name:'Recent imports'}));fireEvent.click(await screen.findByRole('button',{name:`Inspect import ${op}`}));
 fireEvent.click(await screen.findByRole('button',{name:'Continue this import with retained progress'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('archive_import_resume',{operation_id:op,expected_revision:4,attempt_key:expect.stringMatching(/^[a-f0-9]{32}$/)}));
 fireEvent.click(await screen.findByRole('button',{name:'Cancel import'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('archive_import_cancel',{operation_id:op,attempt_key:running.execution.attempt_key}));
 expect(await screen.findByText(/Cancellation requested. Waiting for the worker to stop/)).toBeTruthy();
 expect(vi.mocked(api).mock.calls.filter(([c])=>c==='archive_import_resume')).toHaveLength(1);
 expect(vi.mocked(api).mock.calls.some(([c])=>['archive_begin','archive_finish','start_run','trust_native'].includes(c))).toBe(false);
});

it('keeps recovery-upload cancellation visible and releases busy state after abort',async()=>{
 let append!:(value:any)=>void;
 vi.mocked(api).mockImplementation(async command=>{
  if(command==='archive_import_list')return {rows:[{operation_id:op,created_at:'2026-10-10',outcome:'partial',archive_sha256:'hash'}],next:null};
  if(command==='archive_import_status')return receipt(op,'partial');
  if(command==='archive_recovery_begin')return {upload_id:'recovery',chunk_bytes:3};
  if(command==='archive_append')return new Promise(r=>{append=r;});
  if(command==='archive_recovery_cancel')return {status:'cancelled'};
  return {};
 });
 mount();fireEvent.click(screen.getByRole('button',{name:'Recent imports'}));fireEvent.click(await screen.findByRole('button',{name:`Inspect import ${op}`}));
 fireEvent.change(await screen.findByLabelText('Recovery archive'),{target:{files:[{...file,size:4}]}});
 await waitFor(()=>expect(api).toHaveBeenCalledWith('archive_append',expect.objectContaining({upload_id:'recovery'})));
 expect((screen.getByRole('button',{name:'Refresh this import'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.click(await screen.findByRole('button',{name:'Cancel recovery upload'}));
 await act(async()=>append({offset:1}));
 await waitFor(()=>expect((screen.getByRole('button',{name:'Refresh this import'}) as HTMLButtonElement).disabled).toBe(false));
 expect(api).toHaveBeenCalledWith('archive_recovery_cancel',{upload_id:'recovery'});
 expect(vi.mocked(api).mock.calls.some(([c])=>['archive_import_resume','archive_import_cancel','archive_recovery_finish'].includes(c))).toBe(false);
});


it.each(['continuation','new import'])('clears a historical partial notice before %s acknowledgement',async action=>{
 let acknowledge!:(value:any)=>void,active=false;
 const partial={...receipt(op,'partial'),revision:1,execution:{state:'terminal',phase:'terminal',attempt_key:'c'.repeat(32),staged_rows:4,total_rows:8,termination_reason:'process_restart'}};
 const running={...partial,outcome:null,phase:'publishing',execution:{...partial.execution,state:'running',phase:'verifying'}};
 vi.mocked(api).mockImplementation(async command=>{
  if(command==='archive_import_list')return {rows:[{operation_id:op,created_at:'2026-10-10',outcome:'partial',archive_sha256:'hash'}],next:null};
  if(command==='archive_import_status')return active?running:partial;
  if(command==='archive_import_resume'||command==='archive_import_start'){active=true;return new Promise(r=>{acknowledge=r;});}
  return transport(command);
 });
 mount();fireEvent.click(screen.getByRole('button',{name:'Recent imports'}));fireEvent.click(await screen.findByRole('button',{name:`Inspect import ${op}`}));
 expect(await screen.findByText('Saved receipt confirms partial. Inspection did not retry the import.')).toBeTruthy();
 if(action==='continuation')fireEvent.click(screen.getByRole('button',{name:'Continue this import with retained progress'}));else upload();
 await waitFor(()=>expect(acknowledge).toBeDefined());
 expect(screen.queryByText('Saved receipt confirms partial. Inspection did not retry the import.')).toBeNull();
 expect(screen.getByRole('status').textContent).toContain(action==='continuation'?'Continuation requested':'Starting background import');
 await act(async()=>acknowledge(running));
 expect(screen.queryByText('Saved receipt confirms partial. Inspection did not retry the import.')).toBeNull();
});


it('updates only the matching recent row when continuation polling completes',async()=>{
 let active=false,complete!:(value:any)=>void;
 const partial={...receipt(op,'partial'),revision:1,execution:{state:'terminal',phase:'terminal',attempt_key:'c'.repeat(32),staged_rows:4,total_rows:8,termination_reason:'process_restart'}};
 const running={...partial,outcome:null,phase:'publishing',execution:{...partial.execution,state:'running',phase:'verifying'}};
 const cursor={created_at:'2026-10-09',operation_id:other};
 vi.mocked(api).mockImplementation(async command=>{
  if(command==='archive_import_list')return {rows:[op,other].map(operation_id=>({operation_id,created_at:'2026-10-10',phase:'terminal',outcome:'partial',archive_sha256:'hash'})),next:cursor};
  if(command==='archive_import_status')return active?new Promise(r=>{complete=r;}):partial;
  if(command==='archive_import_resume'){active=true;return running;}
  return {};
 });
 mount();fireEvent.click(screen.getByRole('button',{name:'Recent imports'}));fireEvent.click(await screen.findByRole('button',{name:`Inspect import ${op}`}));
 fireEvent.click(await screen.findByRole('button',{name:'Continue this import with retained progress'}));
 await waitFor(()=>expect(screen.getByRole('button',{name:`Inspect import ${op}`}).textContent).toContain('publishing'));
 await waitFor(()=>expect(complete).toBeDefined());
 await act(async()=>complete({...receipt(),revision:2,execution:{...partial.execution,state:'terminal',phase:'terminal',staged_rows:8}}));
 expect(await screen.findByRole('heading',{name:'Import completed'})).toBeTruthy();
 expect(screen.getByRole('button',{name:`Inspect import ${op}`}).textContent).toContain('completed');
 expect(screen.getByRole('button',{name:`Inspect import ${other}`}).textContent).toContain('partial');
 expect(screen.getByRole('button',{name:'Older imports'})).toBeTruthy();
 expect(vi.mocked(api).mock.calls.filter(([c])=>c==='archive_import_list')).toHaveLength(1);
});
