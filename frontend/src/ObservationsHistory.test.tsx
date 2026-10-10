import {act,fireEvent,render,screen,within} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import Observations from './Observations';
import {api} from './api';

vi.mock('./api',()=>({api:vi.fn()}));
vi.mock('./ObservationChart',()=>({default:()=> <div>Verified observation chart</div>}));
const source={id:'synthetic-history',source:'Synthetic fixture',market:'spot',symbol:'BTCUSDT',range:[0,3600],interval_seconds:60,classification:'synthetic'};
const note={id:'saved-note',revision:1,latest_revision:1,source,start:600,end:1200,hypothesis:'Saved hypothesis',falsification:'Saved falsification',source_error:null,links:[]};
const cursor={id:note.id,created_at:'2026-10-10T00:00:00Z'};
const page={source,start:0,end:3600,candles:[],missing:[]};
const props={datasets:[source],onTest:vi.fn(),onBatch:vi.fn()};
function deferred(){let resolve!:(value:any)=>void,reject!:(reason:Error)=>void;const promise=new Promise<any>((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};}
function setup(history:(params:any)=>any){
 vi.mocked(api).mockReset();props.onTest.mockClear();props.onBatch.mockClear();
 vi.mocked(api).mockImplementation(async(command,p:any)=>{
  if(command==='observation_history')return history(p);
  if(command==='observation_get')return note;
  if(command==='local_history_window')return {...page,start:p.start,end:p.end};
  if(command==='observation_save')return {...note,revision:2,latest_revision:2,hypothesis:p.hypothesis,falsification:p.falsification};
  throw Error(`Unexpected command: ${command}`);
 });
}
const calls=(command:string)=>vi.mocked(api).mock.calls.filter(([c])=>c===command);
const list=()=>within(screen.getByRole('complementary'));
const input=(label:string)=>(screen.getByLabelText(label) as HTMLInputElement|HTMLTextAreaElement).value;

it('distinguishes a pending or failed initial list from empty history and retries only the read',async()=>{
 const initial=deferred(),retry=deferred();let reads=0;
 setup(()=>++reads===1?initial.promise:retry.promise);
 render(<Observations {...props}/>);
 expect(list().getByRole('status').textContent).toBe('Loading saved observations…');
 expect(list().queryByText('No saved observations yet.')).toBeNull();
 await act(async()=>initial.reject(Error('Temporary list failure')));
 expect(list().getByRole('alert').textContent).toContain('Could not load saved observations: Temporary list failure');
 expect(list().queryByText('No saved observations yet.')).toBeNull();
 fireEvent.change(screen.getByLabelText('Observation history'),{target:{value:source.id}});
 await screen.findByText('Verified observation chart');
 expect(list().getByRole('alert').textContent).toContain('Temporary list failure');
 const button=list().getByRole('button',{name:'Retry saved observations'});
 button.focus();expect(document.activeElement).toBe(button);
 act(()=>{fireEvent.click(button);fireEvent.click(button);});
 expect(calls('observation_history')).toEqual([['observation_history',{before:null}],['observation_history',{before:null}]]);
 expect(list().getByRole('status').textContent).toBe('Loading saved observations…');
 expect(list().queryByText('No saved observations yet.')).toBeNull();
 await act(async()=>retry.resolve({rows:[note],next:null}));
 fireEvent.click(list().getByRole('button',{name:/Saved hypothesis/}));
 await screen.findByRole('heading',{name:'Observation · revision 1'});
 expect(input('Observation history')).toBe(source.id);
 expect(input('Observation start (UTC)')).toBe('1970-01-01T00:10');
 expect(input('Observation end, exclusive (UTC)')).toBe('1970-01-01T00:20');
 expect(input('Observation hypothesis')).toBe(note.hypothesis);
 expect(list().queryByRole('alert')).toBeNull();
 expect(vi.mocked(api).mock.calls.every(([c])=>['observation_history','observation_get','local_history_window'].includes(c))).toBe(true);
 expect(props.onTest).not.toHaveBeenCalled();
});

it('confirms empty history only after a successful empty response',async()=>{
 const read=deferred();setup(()=>read.promise);render(<Observations {...props}/>);
 expect(list().queryByText('No saved observations yet.')).toBeNull();
 await act(async()=>read.resolve({rows:[],next:null}));
 expect(list().getByText('No saved observations yet.')).toBeTruthy();
 expect(list().queryByRole('status')).toBeNull();expect(list().queryByRole('alert')).toBeNull();
});

it('retains loaded notes, exact dirty revision and cursor on failed pagination, then deduplicates the explicit retry',async()=>{
 const older=deferred(),failedRetry=deferred(),retry=deferred();let reads=0;
 setup(()=>++reads===1?{rows:[note],next:cursor}:reads===2?older.promise:reads===3?failedRetry.promise:retry.promise);
 render(<Observations {...props}/>);
 fireEvent.click(await list().findByRole('button',{name:/Saved hypothesis/}));
 await screen.findByText('Verified observation chart');
 const button=list().getByRole('button',{name:'Older observations'});
 act(()=>{fireEvent.click(button);fireEvent.click(button);});
 expect((button as HTMLButtonElement).disabled).toBe(true);
 expect(calls('observation_history')).toHaveLength(2);
 fireEvent.change(screen.getByLabelText('Observation hypothesis'),{target:{value:'Keep my edited hypothesis'}});
 fireEvent.change(screen.getByLabelText('Observation falsification'),{target:{value:'Keep my edited falsification'}});
 await act(async()=>older.reject(Error('Older page failed')));
 expect(list().getByRole('button',{name:/Saved hypothesis/})).toBeTruthy();
 expect(list().queryByText('No saved observations yet.')).toBeNull();
 const retryButton=list().getByRole('button',{name:'Retry saved observations'});
 expect((retryButton as HTMLButtonElement).disabled).toBe(false);
 act(()=>{fireEvent.click(retryButton);fireEvent.click(retryButton);});
 expect(calls('observation_history').map(([,p])=>p)).toEqual([{before:null},{before:cursor},{before:cursor}]);
 await act(async()=>failedRetry.reject(Error('Retry still unavailable')));
 expect(list().getByRole('alert').textContent).toContain('Retry still unavailable');
 expect(list().getByRole('button',{name:/Saved hypothesis/})).toBeTruthy();
 expect(input('Observation hypothesis')).toBe('Keep my edited hypothesis');
 fireEvent.click(list().getByRole('button',{name:'Retry saved observations'}));
 expect(calls('observation_history').map(([,p])=>p)).toEqual([{before:null},{before:cursor},{before:cursor},{before:cursor}]);
 await act(async()=>retry.resolve({rows:[note,{...note,id:'older-note',hypothesis:'Older hypothesis'}],next:null}));
 expect(list().getAllByRole('button',{name:/Saved hypothesis/})).toHaveLength(1);
 expect(list().getByRole('button',{name:/Older hypothesis/})).toBeTruthy();
 expect(list().queryByRole('button',{name:'Older observations'})).toBeNull();
 expect(screen.getByRole('heading',{name:'Observation · revision 1'})).toBeTruthy();
 expect(input('Observation hypothesis')).toBe('Keep my edited hypothesis');
 expect(input('Observation falsification')).toBe('Keep my edited falsification');
 expect(input('Observation history')).toBe(source.id);
 expect(input('Observation start (UTC)')).toBe('1970-01-01T00:10');
 expect(input('Observation end, exclusive (UTC)')).toBe('1970-01-01T00:20');
 expect(calls('observation_get')).toHaveLength(1);
 expect(calls('local_history_window')).toHaveLength(1);
 expect(calls('observation_save')).toHaveLength(0);
});

it('separates a saved revision from its failed list refresh and never retries the write',async()=>{
 const refresh=deferred(),retry=deferred();let reads=0;
 setup(()=>++reads===1?{rows:[note],next:cursor}:reads===2?refresh.promise:retry.promise);
 render(<Observations {...props} request={{id:note.id,revision:1,request:1}}/>);
 await screen.findByText('Verified observation chart');
 fireEvent.change(screen.getByLabelText('Observation hypothesis'),{target:{value:'Explicitly saved revision'}});
 fireEvent.click(screen.getByRole('button',{name:'Save note revision'}));
 await screen.findByRole('heading',{name:'Observation · revision 2'});
 await act(async()=>refresh.reject(Error('List refresh unavailable')));
 expect(list().getByRole('alert').textContent).toContain('Note saved. Could not refresh saved observations: List refresh unavailable');
 expect(list().getByRole('button',{name:/Saved hypothesis/})).toBeTruthy();
 expect((screen.getByRole('button',{name:'Save note revision'}) as HTMLButtonElement).disabled).toBe(true);
 expect((screen.getByRole('button',{name:'Test observation in Lab'}) as HTMLButtonElement).disabled).toBe(false);
 fireEvent.change(screen.getByLabelText('Observation hypothesis'),{target:{value:'Further unsaved change'}});
 fireEvent.click(list().getByRole('button',{name:'Retry saved observations'}));
 await act(async()=>retry.resolve({rows:[{...note,revision:2,hypothesis:'Explicitly saved revision'}],next:null}));
 expect(list().queryByRole('alert')).toBeNull();
 expect(list().getByRole('button',{name:/Explicitly saved revision/})).toBeTruthy();
 expect(screen.getByRole('heading',{name:'Observation · revision 2'})).toBeTruthy();
 expect(input('Observation hypothesis')).toBe('Further unsaved change');
 expect(input('Observation falsification')).toBe(note.falsification);
 expect(input('Observation start (UTC)')).toBe('1970-01-01T00:10');
 expect(input('Observation end, exclusive (UTC)')).toBe('1970-01-01T00:20');
 expect(calls('observation_save')).toHaveLength(1);
 expect(calls('observation_save')[0][1]).toEqual({observation_id:note.id,expected_revision:1,dataset_id:source.id,start:600,end:1200,hypothesis:'Explicitly saved revision',falsification:note.falsification});
 expect(calls('observation_history').map(([,p])=>p)).toEqual([{before:null},{before:null},{before:null}]);
 expect(props.onTest).not.toHaveBeenCalled();
});

it.each(['resolve','reject'] as const)('ignores a stale older-page %s after the explicit save refresh',async(outcome)=>{
 const older=deferred();let reads=0;
 setup(()=>++reads===1?{rows:[note],next:cursor}:reads===2?older.promise:{rows:[{...note,revision:2,hypothesis:'New saved revision'}],next:null});
 render(<Observations {...props} request={{id:note.id,revision:1,request:1}}/>);
 await screen.findByText('Verified observation chart');
 fireEvent.click(list().getByRole('button',{name:'Older observations'}));
 fireEvent.change(screen.getByLabelText('Observation hypothesis'),{target:{value:'New saved revision'}});
 fireEvent.click(screen.getByRole('button',{name:'Save note revision'}));
 await list().findByRole('button',{name:/New saved revision/});
 await act(async()=>{if(outcome==='resolve')older.resolve({rows:[note,{...note,id:'stale-note',hypothesis:'Stale page'}],next:cursor});else older.reject(Error('Stale page failure'));});
 expect(list().getByRole('button',{name:/New saved revision/})).toBeTruthy();
 expect(list().queryByRole('button',{name:/Saved hypothesis|Stale page|Older observations/})).toBeNull();
 expect(list().queryByRole('alert')).toBeNull();
 expect(screen.getByRole('heading',{name:'Observation · revision 2'})).toBeTruthy();
 expect(calls('observation_history')).toHaveLength(3);
 expect(calls('observation_save')).toHaveLength(1);
});
