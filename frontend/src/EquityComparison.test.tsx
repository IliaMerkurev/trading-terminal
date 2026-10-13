import {beforeEach,it,expect,vi} from 'vitest';
import {act,render,screen,fireEvent,within,waitFor} from '@testing-library/react';
import LibraryResearch from './LibraryResearch';
import {defaultProfile} from './model';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
const profile={...defaultProfile,primary_minutes:240,capital:'1000'};
const specs=[240,1440].map((minutes,ordinal)=>({name:'Repeated strategy',kind:'graph',profile:{...profile,primary_minutes:minutes},dataset:{id:'source'},selection:{entry_id:'template',version:2,minutes,parameters:{period:ordinal?40:20}}}));
const makeReport=(id='saved')=>({id,metadata:{name:`Comparison ${id}`},status:'completed',active_id:null,snapshot:{inputs:{profile,selections:[]},start:600,end:3600,rows:structuredClone(specs)},rows:specs.map((_,ordinal)=>({ordinal,status:'completed',run_id:`${id}-run-${ordinal}`,metrics:{net_pnl:'-2',period_return:'-.002',completed_positions:0}}))});
const props={view:'saved' as const,selections:[],datasets:[],profile:defaultProfile,onActive:vi.fn(),onReport:vi.fn(),onOpenRun:vi.fn()};
const deferred=()=>{let resolve!:(v:any)=>void,reject!:(v:any)=>void;const promise=new Promise<any>((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const curve=(name='Chosen curve')=>({start:600,end:3600,capital:'1000',curves:[{name,status:'completed',run_id:'saved-run-0',points:[{time_ns:600e9,equity:'1000'},{time_ns:3600e9,equity:'998'}]},{name:'Buy & Hold',status:'incompatible',run_id:null,points:[]}],note:'Up to 400 sampled observations per curve; metrics use every recorded point. Passive spot alternatives are not leverage/risk equivalent.'});
let read:(params:any)=>Promise<any>;
let reports:Record<string,ReturnType<typeof makeReport>>;
beforeEach(()=>{reports={saved:makeReport(),other:makeReport('other')};read=async()=>curve();vi.mocked(api).mockReset().mockImplementation(async(command,params:any)=>{
 if(command==='library_batch_history')return {rows:[{id:'saved',created_at:'First',status:'completed'},{id:'other',created_at:'Second',status:'completed'}],next:null};
 if(command==='library_batch_status')return reports[params.batch_id];
 if(command==='library_batch_equity')return read(params);
 return {};
});});
async function open(){const result=render(<LibraryResearch {...props}/>);await screen.findByRole('option',{name:/First/});fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'saved'}});await screen.findAllByRole('button',{name:'Compare equity'});return result;}
const calls=(command:string)=>vi.mocked(api).mock.calls.filter(([c])=>c===command);
const panel=()=>screen.getByRole('region',{name:'Equity comparison'});
it('opens a focused named inspector with frozen variant identity and retained curve limitations',async()=>{
 const original=JSON.stringify(reports.saved);const {rerender}=await open();const before=calls('library_batch_history').length;
 fireEvent.click(screen.getAllByRole('button',{name:'Compare equity'})[0]);
 expect(document.activeElement).toBe(within(panel()).getByRole('heading',{name:'Equity comparison'}));
 expect(panel().textContent).toContain('4h · Comparison group 1');expect(panel().textContent).toContain('Saved capital 1000 USDT');
 fireEvent.click(within(panel()).getByText('Saved variant and identifiers'));expect(within(panel()).getByText('20')).toBeTruthy();expect(panel().textContent).toContain('Run ID: saved-run-0');
 expect(await within(panel()).findByText('Buy & Hold: incompatible · N/A')).toBeTruthy();expect(panel().textContent).toContain('400 sampled observations');expect(panel().textContent).toContain('not leverage/risk equivalent');
 const focus=screen.getByLabelText('Library sort');focus.focus();rerender(<LibraryResearch {...props} profile={{...defaultProfile,capital:'9000'}}/>);
 expect(panel().textContent).toContain('Saved capital 1000 USDT');expect(document.activeElement).toBe(focus);expect(calls('library_batch_history')).toHaveLength(before);
 expect(calls('library_batch_equity')[0][1]).toEqual({batch_id:'saved',ordinal:0});
 expect(calls('research_displayed')).toHaveLength(0);expect(vi.mocked(api).mock.calls.some(([c])=>/start|resume|freeze|save/.test(c))).toBe(false);expect(JSON.stringify(reports.saved)).toBe(original);
});
it('replaces the old curve with a different variant loading state and ignores its late response',async()=>{
 const first=deferred(),second=deferred();read=p=>p.ordinal===0?first.promise:second.promise;
 await open();fireEvent.click(screen.getAllByRole('button',{name:'Compare equity'})[0]);fireEvent.click(screen.getAllByRole('button',{name:'Compare equity'})[1]);
 expect(panel().textContent).toContain('1d · Comparison group 1');expect(panel().textContent).toContain('Loading saved equity');expect(panel().textContent).toContain('Run ID: saved-run-1');
 await act(async()=>first.resolve(curve('Late first')));expect(screen.queryByText('Late first: completed')).toBeNull();
 await act(async()=>second.resolve(curve('Current second')));expect(within(panel()).getByText('Current second: completed')).toBeTruthy();
 fireEvent.click(screen.getAllByRole('button',{name:'Compare equity'})[0]);expect(screen.queryByText('Current second: completed')).toBeNull();
});
it('keeps equity failure local and retries only the exact read without refreshing history',async()=>{
 read=async()=>{throw Error('Read unavailable');};await open();const history=calls('library_batch_history').length;
 fireEvent.click(screen.getAllByRole('button',{name:'Compare equity'})[1]);expect((await within(panel()).findByRole('alert')).textContent).toContain('Read unavailable');
 expect((screen.getByLabelText('Saved library batches') as HTMLSelectElement).disabled).toBe(false);expect((screen.getByLabelText('Library sort') as HTMLSelectElement).disabled).toBe(false);
 const retry=deferred();read=()=>retry.promise;const retryButton=within(panel()).getByRole('button',{name:'Retry equity read'});retryButton.focus();fireEvent.click(retryButton);expect(document.activeElement).toBe(within(panel()).getByRole('heading',{name:'Equity comparison'}));await act(async()=>retry.resolve(curve('Retry result')));expect(await within(panel()).findByText('Retry result: completed')).toBeTruthy();
 expect(calls('library_batch_equity').map(call=>call[1])).toEqual([{batch_id:'saved',ordinal:1},{batch_id:'saved',ordinal:1}]);expect(calls('library_batch_history')).toHaveLength(history);
});
it('close returns to its trigger, invalidates pending success and supports explicit reopening',async()=>{
 const pending=deferred();read=()=>pending.promise;await open();const trigger=screen.getAllByRole('button',{name:'Compare equity'})[0];trigger.focus();fireEvent.click(trigger);
 fireEvent.click(within(panel()).getByRole('button',{name:'Back to result'}));expect(document.activeElement).toBe(trigger);expect(screen.queryByRole('region',{name:'Equity comparison'})).toBeNull();
 await act(async()=>pending.resolve(curve('Closed result')));expect(screen.queryByText('Closed result: completed')).toBeNull();
 read=async()=>curve('Reopened');fireEvent.click(trigger);expect(await within(panel()).findByText('Reopened: completed')).toBeTruthy();expect(calls('library_batch_equity')).toHaveLength(2);
});
it('close falls back to the table when filtering removes the original trigger',async()=>{
 await open();fireEvent.click(screen.getAllByRole('button',{name:'Compare equity'})[0]);await within(panel()).findByRole('img');
 fireEvent.change(screen.getByLabelText('Library filter Timeframe'),{target:{value:'1440'}});
 fireEvent.click(within(panel()).getByRole('button',{name:'Back to result'}));expect(document.activeElement).toBe(screen.getByRole('region',{name:'Saved comparison results'}));expect((screen.getByLabelText('Library filter Timeframe') as HTMLSelectElement).value).toBe('1440');
});
it('batch changes invalidate late errors without replacing the current comparison or stealing focus',async()=>{
 const pending=deferred();read=()=>pending.promise;await open();fireEvent.click(screen.getAllByRole('button',{name:'Compare equity'})[0]);
 const select=screen.getByLabelText('Saved library batches');select.focus();fireEvent.change(select,{target:{value:'other'}});await waitFor(()=>expect(screen.queryByRole('region',{name:'Equity comparison'})).toBeNull());
 await act(async()=>pending.reject(Error('Old batch error')));expect(screen.queryByText(/Old batch error/)).toBeNull();expect(document.activeElement).toBe(select);
});
it('route suspension discards pending inspection and return never starts another read',async()=>{
 const pending=deferred();read=()=>pending.promise;const {rerender}=await open();fireEvent.click(screen.getAllByRole('button',{name:'Compare equity'})[0]);
 rerender(<LibraryResearch {...props} suspendSetup/>);expect(screen.queryByRole('region',{name:'Equity comparison'})).toBeNull();await act(async()=>pending.resolve(curve('Hidden result')));
 rerender(<LibraryResearch {...props}/>);expect(screen.queryByRole('region',{name:'Equity comparison'})).toBeNull();expect(calls('library_batch_equity')).toHaveLength(1);
});
it('Lab navigation and unmount discard late responses without a new automatic read',async()=>{
 const pending=deferred();read=()=>pending.promise;const {rerender,unmount}=await open();fireEvent.click(screen.getAllByRole('button',{name:'Compare equity'})[0]);rerender(<LibraryResearch {...props} view="catalog"/>);
 await act(async()=>pending.reject(Error('Hidden failure')));rerender(<LibraryResearch {...props}/>);expect(screen.queryByRole('region',{name:'Equity comparison'})).toBeNull();expect(screen.queryByText(/Hidden failure/)).toBeNull();
 const next=deferred();read=()=>next.promise;fireEvent.click(screen.getAllByRole('button',{name:'Compare equity'})[0]);unmount();await act(async()=>next.resolve(curve('Unmounted')));expect(calls('library_batch_equity')).toHaveLength(2);
});

it('shows resolved frozen defaults rather than empty overrides or the current catalog',async()=>{
 const spec=reports.saved.snapshot.rows[0] as any;spec.selection.parameters={};spec.contract={parameters:{fast:10,slow:20}};
 const {rerender}=await open();fireEvent.click(screen.getAllByRole('button',{name:'Compare equity'})[0]);await within(panel()).findByRole('img');
 fireEvent.click(within(panel()).getByText('Saved variant and identifiers'));
 expect(panel().textContent).toContain('Resolved parameters from the saved contract');expect(within(panel()).getByText('10')).toBeTruthy();expect(within(panel()).getByText('20')).toBeTruthy();
 rerender(<LibraryResearch {...props} catalog={[{id:'template',family:'trend',availability:'verified',parameters:{fast:{default:999},slow:{default:888}}}]}/>);
 expect(within(panel()).getByText('10')).toBeTruthy();expect(within(panel()).getByText('20')).toBeTruthy();expect(panel().textContent).not.toContain('999');
 // The captured contract remains immutable even if a later source object changes.
 spec.contract.parameters.fast=777;rerender(<LibraryResearch {...props}/>);expect(within(panel()).getByText('10')).toBeTruthy();expect(panel().textContent).not.toContain('777');
});
it('labels selection-only legacy parameters explicitly rather than inventing resolved defaults',async()=>{
 await open();fireEvent.click(screen.getAllByRole('button',{name:'Compare equity'})[0]);
 expect(panel().textContent).toContain('Saved selection overrides only; resolved parameters unavailable.');expect(within(panel()).getByText('20')).toBeTruthy();
});
