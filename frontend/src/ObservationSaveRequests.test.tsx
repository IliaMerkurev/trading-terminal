import {beforeEach,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,act} from '@testing-library/react';
import Observations from './Observations';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
vi.mock('./ObservationChart',()=>({default:()=> <div>Verified chart</div>}));
const source={id:'source',source:'Synthetic note request',market:'spot',symbol:'BTCUSDT',range:[0,3600],interval_seconds:60,classification:'synthetic'};
const note={id:'note',revision:1,latest_revision:1,source,start:600,end:1200,hypothesis:'Original note',falsification:'',source_error:null,links:[]};
const props={datasets:[source],onTest:vi.fn(),onBatch:vi.fn()};
let save:(p:any,o:any)=>Promise<any>;
beforeEach(()=>{
 vi.clearAllMocks();save=async()=>note;
 vi.mocked(api).mockImplementation(async(c,p:any,o:any)=>{
  if(c==='observation_save_history')return [];
  if(c==='observation_history')return {rows:[note],next:null};
  if(c==='observation_get')return note;
  if(c==='local_history_window')return {source,start:p.start,end:p.end,candles:[],missing:[]};
  if(c==='observation_save'){o.onRequest('a'.repeat(32));return save(p,o);}
  if(c==='chart_read_status')return {request_id:'a'.repeat(32),status:'completed',result:{...note,revision:2,latest_revision:2,hypothesis:'Saved wording'}};
  return {};
 });
});
async function edit(){
 fireEvent.click(await screen.findByRole('button',{name:/Original note/}));await screen.findByText('Verified chart');
 fireEvent.change(screen.getByLabelText('Observation hypothesis'),{target:{value:'Saved wording'}});
 fireEvent.click(screen.getByRole('button',{name:'Save note revision'}));
}
it('unlocks a definitively rejected start while preserving exact draft and source binding',async()=>{
 save=async()=>{throw Object.assign(new Error('Note rejected'),{saveOutcome:'not_started'});};
 render(<Observations {...props}/>);await edit();await screen.findByText(/Note rejected/);
 expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).disabled).toBe(false);
 expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).value).toBe('Saved wording');
 expect(screen.queryByRole('button',{name:'Inspect note save'})).toBeNull();
 expect(api).toHaveBeenCalledWith('observation_save',expect.objectContaining({expected_source:source,start:600,end:1200,expected_revision:1}),expect.any(Object));
});
it('keeps a lost-acknowledgement save inspectable without automatically creating a second save',async()=>{
 save=async()=>{throw Object.assign(new Error('Lost save acknowledgement'),{saveOutcome:'unknown'});};
 render(<Observations {...props}/>);await edit();await screen.findByText(/Lost save acknowledgement/);
 expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).disabled).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Inspect note save'}));
 await waitFor(()=>expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).disabled).toBe(false));
 expect(vi.mocked(api).mock.calls.filter(([c])=>c==='observation_save')).toHaveLength(1);
 expect(screen.getByText('Observation · revision 2')).toBeTruthy();
});
it('ignores the original save promise after inspection settles it and the user edits again',async()=>{
 let resolve:(v:any)=>void=()=>{};save=async()=>new Promise(r=>{resolve=r;});
 render(<Observations {...props}/>);await edit();
 fireEvent.click(screen.getByRole('button',{name:'Inspect note save'}));
 await waitFor(()=>expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).disabled).toBe(false));
 fireEvent.change(screen.getByLabelText('Observation hypothesis'),{target:{value:'New draft after inspection'}});
 await act(async()=>{resolve({...note,revision:2,hypothesis:'Late old response'});});
 expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).value).toBe('New draft after inspection');
});
it('discovers durable completed/interrupted save identities after reopening without another save',async()=>{
 const previous=vi.mocked(api).getMockImplementation()!;
 vi.mocked(api).mockImplementation(async(c,p,o)=>c==='observation_save_history'?[{request_id:'receipt-committed',status:'completed',observation_id:'note',revision:1},{request_id:'receipt-interrupted',status:'interrupted',error:'No automatic retry'}]:previous(c,p,o));
 render(<Observations {...props}/>);
 expect(await screen.findByText(/receipt-interrupted/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Open saved revision 1'}));await screen.findByText('Verified chart');
 expect(api).toHaveBeenCalledWith('observation_get',{observation_id:'note',revision:1});
 expect(vi.mocked(api).mock.calls.some(([c])=>c==='observation_save')).toBe(false);
});
it('does not discard a dirty draft when opening a completed receipt',async()=>{
 const previous=vi.mocked(api).getMockImplementation()!;
 vi.mocked(api).mockImplementation(async(c,p,o)=>c==='observation_save_history'?[{request_id:'receipt',status:'completed',observation_id:'note',revision:1}]:previous(c,p,o));
 render(<Observations {...props}/>);
 fireEvent.click(await screen.findByRole('button',{name:/Original note/}));await screen.findByText('Verified chart');
 fireEvent.change(screen.getByLabelText('Observation hypothesis'),{target:{value:'Unsaved important wording'}});
 const button=screen.getByRole('button',{name:'Open saved revision 1'});expect((button as HTMLButtonElement).disabled).toBe(true);fireEvent.click(button);
 expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).value).toBe('Unsaved important wording');
});
it('shows intentional note cancellation as a neutral outcome and retains its draft',async()=>{
 save=async()=>{throw Object.assign(new Error('Note was not saved.'),{saveOutcome:'cancelled'});};
 render(<Observations {...props}/>);await edit();
 expect(await screen.findByText('Note save cancelled. Your draft is retained.')).toBeTruthy();
 expect(screen.queryByRole('alert')).toBeNull();
 expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).value).toBe('Saved wording');
 expect((screen.getByLabelText('Observation hypothesis') as HTMLTextAreaElement).disabled).toBe(false);
});
