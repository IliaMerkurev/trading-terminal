import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import Observations from './Observations';
import {api} from './api';
import {navigationUTC} from './observationNavigation';

const charts=vi.hoisted(()=>[] as any[]);
vi.mock('./api',()=>({api:vi.fn()}));
vi.mock('./ObservationChart',()=>({default:(p:any)=>{charts.push(p);return <div data-testid="boundary-chart">Verified chart</div>;}}));
const S=1704067200,H=3600;
const source={id:'source',source:'Synthetic boundary workflow',market:'spot',symbol:'BTCUSDT',range:[S,S+900*H],interval_seconds:H,classification:'synthetic',content_sha256:'content-a'};
const note={id:'note',revision:2,latest_revision:2,source,start:S+10*H,end:S+20*H,hypothesis:'Original hypothesis',falsification:'Original falsification',source_error:null,links:[]};
const props={datasets:[source],onTest:vi.fn(),onBatch:vi.fn()};
const input=(name:string)=>screen.getByLabelText(name) as HTMLInputElement;
const start=()=>input('Observation start (UTC)'),end=()=>input('Observation end, exclusive (UTC)');
const chart=()=>charts.at(-1);
const boundary=(edge='start',opening=S+12*H,closing=S+13*H,p=chart())=>act(()=>p.onUseBoundary({edge,opening,closing,identity:p.boundaryIdentity}));
const page=(p:any)=>({source,start:p.start,end:p.end,candles:[],missing:[],display_reference:{surface:'observation_chart',page_id:String(p.start)}});
const calls=(name:string)=>vi.mocked(api).mock.calls.filter(([c])=>c===name);
function mock(read:(p:any)=>any=page,get:any=note){vi.mocked(api).mockImplementation(async(c,p:any)=>{
 if(c==='observation_history')return {rows:[note],next:null};
 if(c==='observation_get')return get;
 if(c==='local_history_window')return read(p);
 if(c==='observation_save')return {...note,revision:p.expected_revision+1,latest_revision:p.expected_revision+1,start:p.start,end:p.end,hypothesis:p.hypothesis,falsification:p.falsification};
 throw Error(`Unexpected command ${c}`);
});}
async function ready(){await screen.findByTestId('boundary-chart');}
function deferred(){let resolve!:(v:any)=>void,reject!:(e:Error)=>void;const promise=new Promise<any>((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};}
beforeEach(()=>{charts.length=0;vi.mocked(api).mockReset();props.onTest.mockClear();props.onBatch.mockClear();});

it('sets only explicitly chosen UTC endpoints, preserves text and browsing, and saves/hands off only on explicit actions',async()=>{
 mock();render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await ready();
 fireEvent.change(input('Observation hypothesis'),{target:{value:'Keep this draft'}});fireEvent.change(input('Observation falsification'),{target:{value:'Keep falsification'}});
 fireEvent.change(input('Go to UTC date'),{target:{value:'Not submitted'}});
 boundary();expect(start().value).toBe(navigationUTC(S+12*H));expect(end().value).toBe(navigationUTC(source.range[1]));
 boundary('end',S+15*H,S+16*H);expect(end().value).toBe(navigationUTC(S+16*H));
 expect(input('Go to UTC date').value).toBe('Not submitted');expect(input('Observation hypothesis').value).toBe('Keep this draft');expect(input('Observation falsification').value).toBe('Keep falsification');
 expect(calls('observation_save')).toHaveLength(0);expect(props.onTest).not.toHaveBeenCalled();expect(calls('local_history_window')).toHaveLength(1);
 fireEvent.click(screen.getByRole('button',{name:'Save observation'}));await screen.findByRole('heading',{name:'Observation · revision 1'});
 expect(api).toHaveBeenCalledWith('observation_save',expect.objectContaining({observation_id:null,expected_revision:0,dataset_id:'source',start:S+12*H,end:S+16*H,hypothesis:'Keep this draft',falsification:'Keep falsification'}),expect.objectContaining({onRequest:expect.any(Function),onPhase:expect.any(Function)}));
 fireEvent.click(screen.getByRole('button',{name:'Test observation in Lab'}));expect(props.onTest).toHaveBeenCalledWith({id:'note',revision:1,source,start:S+12*H,end:S+16*H});
 expect(calls('library_batch_start')).toHaveLength(0);
});
it('retains a reversed range unchanged until the other endpoint is explicitly corrected',async()=>{
 mock();render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await ready();fireEvent.change(input('Observation hypothesis'),{target:{value:'Draft'}});
 boundary('end',S+9*H,S+10*H);boundary('start',S+12*H,S+13*H);
 expect(start().value).toBe(navigationUTC(S+12*H));expect(end().value).toBe(navigationUTC(S+10*H));expect(screen.getByText(/observation end must be after/)).toBeTruthy();expect((screen.getByRole('button',{name:'Save observation'}) as HTMLButtonElement).disabled).toBe(true);
 boundary('end',S+15*H,S+16*H);expect(start().value).toBe(navigationUTC(S+12*H));expect((screen.getByRole('button',{name:'Save observation'}) as HTMLButtonElement).disabled).toBe(false);
});
it('rejects stale display and source callbacks and malformed/unbounded endpoints',async()=>{
 mock();const view=render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await ready();const old=chart();
 fireEvent.change(screen.getByLabelText('Saved-history display interval'),{target:{value:'14400'}});boundary('start',S+12*H,S+16*H,old);expect(start().value).toBe(navigationUTC(S));
 for(const [edge,a,b] of [['bad',S+H,S+2*H],['start',S+1,S+H],['end',S,S+901*H],['start',S+H,S],['start',NaN,S+H]] as const)boundary(edge,a,b);
 expect(start().value).toBe(navigationUTC(S));expect(end().value).toBe(navigationUTC(source.range[1]));
 const before=chart();view.rerender(<Observations {...props} datasets={[{...source,content_sha256:'changed'}]} request={{dataset:source.id,request:1}}/>);
 boundary('start',S+12*H,S+16*H,before);expect(start().value).toBe(navigationUTC(S));expect(screen.queryByTestId('boundary-chart')).toBeNull();
});
it('blocks old-page callbacks during navigation, failure and retry, even when the same page returns',async()=>{
 const pending=deferred();let reads=0;mock(p=>++reads===2?pending.promise:page(p));render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await ready();const old=chart();
 fireEvent.click(screen.getByRole('button',{name:'Latest saved page'}));boundary('start',S+12*H,S+13*H,old);expect(start().value).toBe(navigationUTC(S));
 await act(async()=>pending.reject(Error('Controlled read failure')));boundary('start',S+12*H,S+13*H,old);expect(start().value).toBe(navigationUTC(S));
 fireEvent.click(screen.getByRole('button',{name:'Retry reading'}));await ready();boundary('start',S+12*H,S+13*H,old);expect(start().value).toBe(navigationUTC(S));
 fireEvent.click(screen.getByRole('button',{name:'First saved page'}));await waitFor(()=>expect(chart().start).toBe(S));boundary('start',S+12*H,S+13*H,old);expect(start().value).toBe(navigationUTC(S));boundary();expect(start().value).toBe(navigationUTC(S+12*H));
});
it.each([2,1])('protects saved revision %s and requires explicit New observation before editing its period',async revision=>{
 mock(undefined,{...note,revision});render(<Observations {...props} request={{id:'note',revision,request:1}}/>);await ready();
 expect(chart().boundaryDisabledReason).toContain('Saved observation dates are fixed');boundary('end',S+15*H,S+16*H);expect(end().value).toBe(navigationUTC(note.end));
 fireEvent.click(screen.getByRole('button',{name:'New observation'}));boundary('end',S+15*H,S+16*H);expect(end().value).toBe(navigationUTC(S+16*H));expect(calls('observation_save')).toHaveLength(0);
});
it('blocks stale callbacks while a save is pending and after it becomes an immutable saved note',async()=>{
 mock();const previous=vi.mocked(api).getMockImplementation()!,pending=deferred();vi.mocked(api).mockImplementation((c,p)=>c==='observation_save'?pending.promise:previous(c,p));
 render(<Observations {...props} request={{dataset:source.id,request:1}}/>);await ready();fireEvent.change(input('Observation hypothesis'),{target:{value:'Saving draft'}});const old=chart();
 fireEvent.click(screen.getByRole('button',{name:'Save observation'}));boundary('start',S+12*H,S+13*H,old);expect(start().value).toBe(navigationUTC(S));
 await act(async()=>pending.resolve({...note,start:S,end:source.range[1],hypothesis:'Saving draft'}));boundary('start',S+12*H,S+13*H,old);expect(start().value).toBe(navigationUTC(S));expect(calls('observation_save')).toHaveLength(1);
});
