import {beforeEach,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import ProjectExport from './ProjectExport';
import {api,downloadArchive} from './api';
vi.mock('./api',()=>({transportCapabilities:()=>({localService:true,downloadArchives:true}),api:vi.fn(),downloadArchive:vi.fn()}));
const id='a'.repeat(32),running={export_id:id,status:'running',phase:'compress_validate',descriptor:null,error:null};
const completed={...running,status:'completed',phase:'terminal',descriptor:{export_id:id,filename:id+'.ttproject.zip',bytes:3,note:'Saved locally'}};
const mount=(strategy=()=>({name:'Frozen'}))=>render(<ProjectExport strategy={strategy} profile={{capital:'1000'}} runIds={['run']} disabled={false}/>);
beforeEach(()=>{vi.resetAllMocks();vi.mocked(downloadArchive).mockResolvedValue();});
it('inspects a lost start response without creating another operation',async()=>{
 let ready=false;vi.mocked(api).mockImplementation(async(command,params)=>{if(command==='archive_export_start'){ready=true;throw Error('Lost reply');}if(command==='archive_export_status')return ready?{...completed,export_id:params?.export_id}:running;return [];});
 mount();fireEvent.click(screen.getByText('Export project archive'));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('archive_export_start',expect.objectContaining({request_id:expect.stringMatching(/^[a-f0-9]{32}$/)})));
 await waitFor(()=>expect(downloadArchive).toHaveBeenCalledOnce());
 expect(vi.mocked(api).mock.calls.filter(([command])=>command==='archive_export_start')).toHaveLength(1);
});
it('retries the exact frozen request after uncertain start and refuses implicit new inputs',async()=>{
 let calls=0;vi.mocked(api).mockImplementation(async command=>{if(command==='archive_export_start'){calls++;throw Error('Lost reply');}throw Error('Status unavailable');});
 let name='first';mount(()=>({name}));fireEvent.click(screen.getByText('Export project archive'));
 fireEvent.click(await screen.findByText('Retry exact export start'));name='changed';
 await waitFor(()=>expect(calls).toBe(2));const starts=vi.mocked(api).mock.calls.filter(([c])=>c==='archive_export_start');expect(starts[0][1]).toEqual(starts[1][1]);expect(starts[1][1]?.strategy).toEqual({name:'first'});
});
it('shows draft preparation errors without sending a start',async()=>{
 mount(()=>{throw Error('Invalid native document');});fireEvent.click(screen.getByText('Export project archive'));
 expect((await screen.findByRole('alert')).textContent).toContain('Invalid native document');expect(api).not.toHaveBeenCalled();
});
it('reconciles terminal cancellation and ignores a late acknowledgement',async()=>{
 let terminal=false,ack!:(value:any)=>void;vi.mocked(api).mockImplementation(async(command,params)=>command==='archive_export_cancel'?new Promise(resolve=>{ack=resolve;}):{...running,export_id:params?.export_id??params?.request_id,status:terminal?'cancelled':'running',phase:terminal?'terminal':'compress_validate'});
 mount();fireEvent.click(screen.getByText('Export project archive'));fireEvent.click(await screen.findByText('Cancel export'));
 terminal=true;await screen.findByText('Export cancelled. No downloadable archive was published.');ack({status:'cancel_requested'});
 await waitFor(()=>expect(screen.queryByText(/Waiting for the export worker/)).toBeNull());expect(downloadArchive).not.toHaveBeenCalled();
});
it('does not download when an obsolete or unmounted start completes',async()=>{
 let resolve!:(value:any)=>void;vi.mocked(api).mockImplementation(async command=>command==='archive_export_start'?new Promise(r=>{resolve=r;}):new Promise(()=>{}));
 const view=mount();fireEvent.click(screen.getByText('Export project archive'));await waitFor(()=>expect(resolve).toBeTypeOf('function'));
 view.unmount();resolve(completed);await new Promise(r=>setTimeout(r,10));expect(downloadArchive).not.toHaveBeenCalled();
});
it('stopping transfer invalidates its generation without cancelling completed export',async()=>{
 let current!:()=>boolean;vi.mocked(downloadArchive).mockImplementation(async(_d,guard)=>{current=guard!;await new Promise(()=>{});});
 vi.mocked(api).mockImplementation(async(_command,params)=>({...completed,export_id:params?.request_id??params?.export_id}));
 mount();fireEvent.click(screen.getByText('Export project archive'));fireEvent.click(await screen.findByText('Stop archive download'));
 expect(current()).toBe(false);expect(vi.mocked(api).mock.calls.some(([c])=>c==='archive_export_cancel')).toBe(false);
 expect(screen.getByText('Transfer stopped. The completed export is retained.')).toBeTruthy();
});
it('recent export inspection is read only and never auto-downloads',async()=>{
 vi.mocked(api).mockImplementation(async command=>command==='archive_export_list'?[completed]:completed);mount();fireEvent.click(screen.getByText('Recent exports'));fireEvent.click(await screen.findByText(`${id} · completed`));
 await screen.findByText('Download verified archive');expect(downloadArchive).not.toHaveBeenCalled();expect(vi.mocked(api).mock.calls.map(([c])=>c)).toEqual(['archive_export_list','archive_export_status']);
});
