import {afterEach,beforeEach,it,expect,vi} from 'vitest';
import {act,render,screen,fireEvent,waitFor} from '@testing-library/react';
import LibraryResearch from './LibraryResearch';
import {defaultProfile} from './model';
import {api} from './api';
import {finishDisplayWrites} from './DisplayedEvidence';
vi.mock('./api',()=>({api:vi.fn()}));
const profile={...defaultProfile,tier_assumption:'Synthetic limits; not exchange metadata'};
const inputs={profile,dataset_id:'source',start:600,end:3600,interval:'weekly',selections:[]};
const report={id:'saved',metadata:{name:'Retained comparison',notes:'',revision:1},observation:{id:'note',revision:2},status:'completed_with_errors',active_id:null,error:'A saved execution warning',snapshot:{inputs,start:600,end:3600,rows:[{name:'Losing candidate',kind:'graph',profile,dataset:{id:'source'}},{name:'Unavailable candidate',kind:'graph',profile,dataset:{id:'source'}},{name:'Buy & Hold',kind:'benchmark',profile,dataset:{id:'source'}}]},rows:[{ordinal:0,status:'completed',run_id:'loss',metrics:{net_pnl:'-2',period_return:'-.02',completed_positions:0}},{ordinal:1,status:'failed',metrics:null},{ordinal:2,status:'completed',run_id:'passive',metrics:{net_pnl:'-5',period_return:'-.05'}}]};
const props={view:'saved' as const,selections:[],datasets:[{id:'source',market:'spot',symbol:'BTCUSDT',range:[0,3600]}],profile:defaultProfile,onActive:vi.fn(),onReport:vi.fn(),onOpenRun:vi.fn(),onObservation:vi.fn(),preferredDataset:{id:'source',request:1}};
beforeEach(()=>{vi.mocked(api).mockReset().mockImplementation(async(command)=>command==='library_batch_history'?{rows:[{id:'saved',created_at:'Fixture',status:'completed_with_errors'}],next:null}:command==='library_batch_status'?report:{});});
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});
async function open(){const result=render(<LibraryResearch {...props}/>);await screen.findByRole('option',{name:/Fixture/});fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'saved'}});await screen.findByText('Losing candidate');return result;}
it('keeps frozen context, warnings, counts, sorting and linked return outside optional disclosures',async()=>{
 await open();
 for(const text of [/^Search saved comparisons · /,'Detailed saved assumptions','Filter results · 0 active'])expect(screen.getByText(text,{selector:'summary'}).closest('details')?.open).toBe(false);
 expect(screen.getByRole('region',{name:'Saved comparison settings'}).textContent).toContain('spot');
 for(const element of [screen.getByText(/Instrument assumptions: Synthetic/),screen.getByText(/Saved settings differ/),screen.getByText('A saved execution warning'),screen.getByText(/Thresholds: this comparison only/),screen.getByLabelText('Library sort')])expect(element.closest('details')).toBeNull();
 expect(screen.getByText(/2 completed.*1 failed/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Return to linked observation'}));expect(props.onObservation).toHaveBeenCalledWith('note',2);
 const summary=screen.getByText('Detailed saved assumptions',{selector:'summary'});summary.focus();expect(document.activeElement).toBe(summary);fireEvent.click(summary);expect(summary.closest('details')?.open).toBe(true);fireEvent.click(summary);expect(summary.closest('details')?.open).toBe(false);
 expect(vi.mocked(api).mock.calls.some(([c])=>/start|resume|save_metadata|research_displayed/.test(c))).toBe(false);
});
it('retains invalid and active filter indications collapsed; clear resets only viewing filters',async()=>{
 const {rerender}=await open();
 fireEvent.change(screen.getByLabelText('Library sort'),{target:{value:'period_return'}});
 fireEvent.change(screen.getByLabelText('Library sort direction'),{target:{value:'asc'}});
 const filters=screen.getByText('Filter results · 0 active',{selector:'summary'});fireEvent.click(filters);
 fireEvent.change(screen.getByLabelText('Library filter Compatibility / result state'),{target:{value:'completed'}});
 fireEvent.change(screen.getByLabelText('Minimum completed positions'),{target:{value:'1.5'}});
 fireEvent.click(filters);
 expect(filters.closest('details')?.open).toBe(false);expect(filters.textContent).toContain('2 active · invalid numeric input');
 const error=screen.getByText(/Numeric thresholds are not applied until corrected/);expect(error.closest('details')).toBeNull();
 expect(screen.getByText('-2.0000 / -2.00%')).toBeTruthy();expect(screen.getByText('Passive reference · thresholds not applied')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Clear filters'}));
 expect(filters.textContent).toBe('Filter results · 0 active');expect(screen.queryByText(/Numeric thresholds are not applied/)).toBeNull();
 expect((screen.getByLabelText('Library sort') as HTMLSelectElement).value).toBe('period_return');expect((screen.getByLabelText('Library sort direction') as HTMLSelectElement).value).toBe('asc');expect((screen.getByLabelText('Saved library batches') as HTMLSelectElement).value).toBe('saved');
 expect(screen.getByText('Unavailable candidate')).toBeTruthy();
 // Opening the retained ordinary draft confirms the reset did not change source.
 rerender(<LibraryResearch {...props} view="catalog"/>);
 expect((screen.getByLabelText('Batch dataset') as HTMLSelectElement).value).toBe('source');
 expect(JSON.stringify(report.snapshot.inputs)).toBe(JSON.stringify(inputs));
});
it('disclosure toggles do not record exposure; only displayed numeric cells of the selected table do',async()=>{
 const observers:{target:HTMLElement|null;callback:(entries:any[])=>void}[]=[];let frames:(()=>void)[]=[];
 vi.stubGlobal('IntersectionObserver',class {entry:any;constructor(callback:any){this.entry={callback,target:null};observers.push(this.entry);}observe(target:HTMLElement){this.entry.target=target;}disconnect(){this.entry.target=null;}});
 vi.stubGlobal('requestAnimationFrame',(f:()=>void)=>{frames.push(f);return frames.length;});vi.stubGlobal('cancelAnimationFrame',()=>{});
 vi.spyOn(HTMLElement.prototype,'getClientRects').mockReturnValue([{width:100,height:100}] as any);
 const {container}=await open();
 fireEvent.click(screen.getByText('Detailed saved assumptions',{selector:'summary'}));fireEvent.click(screen.getByText('Filter results · 0 active',{selector:'summary'}));
 const flush=()=>{const next=frames;frames=[];next.forEach(f=>f());};act(flush);
 const writes=()=>vi.mocked(api).mock.calls.filter(([c])=>c==='research_displayed');expect(writes()).toHaveLength(0);
 expect(observers.every(o=>!o.target||o.target.matches('[data-metric]'))).toBe(true);
 const metric=container.querySelector('[data-metric]') as HTMLElement;
 await act(async()=>{for(const o of observers)if(o.target===metric)o.callback([{target:metric,isIntersecting:true,intersectionRect:{width:100,height:100}}]);flush();await finishDisplayWrites();});
 await waitFor(()=>expect(writes()).toHaveLength(1));expect(writes()[0][1]).toMatchObject({reference:{surface:'comparison_metrics',batch_id:'saved'},viewport:null});
});
