import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import LibraryResearch,{filterLibraryRows,libraryFilterSummary,sortedLibraryRows} from './LibraryResearch';
import {defaultProfile} from './model';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
const catalog=[{id:'a',family:'trend',availability:'verified'},{id:'b',family:'momentum',availability:'research'}];
function fixture(){
 const specs=[
  ['Zero','graph','a',60],['Loss','graph','b',240],['Missing','graph','a',60],
  ['Failed','graph','a',60],['Pending','graph','a',60],['Buy & Hold','benchmark','',60],['DCA','benchmark','',60],
 ].map(([name,kind,id,minutes])=>({name,kind,selection:{entry_id:id},profile:{...defaultProfile,primary_minutes:minutes},dataset:{id:'source'}}));
 return {id:'saved',status:'completed_with_errors',active_id:null,snapshot:{inputs:{profile:defaultProfile,selections:[],interval:'weekly'},rows:specs},rows:[
  {ordinal:0,status:'completed',metrics:{period_return:'0',max_drawdown:'0',completed_positions:0}},
  {ordinal:1,status:'completed',metrics:{period_return:'-.02',max_drawdown:'.1',completed_positions:5}},
  {ordinal:2,status:'completed',metrics:{period_return:null,max_drawdown:'.5',completed_positions:0}},
  {ordinal:3,status:'failed',metrics:null},{ordinal:4,status:'pending',metrics:null},
  {ordinal:5,status:'completed',metrics:{period_return:'.8'}},{ordinal:6,status:'unavailable',metrics:null},
 ]};
}
function summary(report:any,filters:Record<string,string>){return libraryFilterSummary(report,filterLibraryRows(report,catalog,filters),filters);}
it('counts finite zero and negative threshold boundaries independently of baseline returns',()=>{
 const report=fixture();
 expect(summary(report,{minReturn:'-2',maxDrawdown:'10',minTrades:'0'})).toBe('2 strategy rows match numeric thresholds · 3 context-only strategy rows · 2 passive reference rows. Context-only rows lack required metrics or are unfinished; they are not numeric matches.');
 expect(summary(report,{minReturn:'0'})).toContain('1 strategy rows match numeric thresholds · 3 context-only strategy rows · 2 passive reference rows.');
 expect(summary(report,{maxDrawdown:'0',minTrades:'0'})).toContain('1 strategy rows match numeric thresholds · 2 context-only strategy rows');
 expect(JSON.stringify(report)).toBe(JSON.stringify(fixture()));
});
it('explains zero matches while baselines and N/A context remain visible',()=>{
 const report=fixture(),filters={minReturn:'99'};
 expect(filterLibraryRows(report,catalog,filters).map(r=>r.ordinal)).toEqual([2,3,4,5,6]);
 expect(summary(report,filters)).toBe('0 strategy rows match numeric thresholds · 3 context-only strategy rows · 2 passive reference rows. No strategy rows match the numeric thresholds within the current category filters. Context-only rows lack required metrics or are unfinished; they are not numeric matches.');
});
it.each([null,undefined,'',NaN,Infinity,'not-a-number'])('counts unavailable metric %s as context, never a match',(metric)=>{
 const report=fixture();report.rows[0].metrics!.period_return=metric as any;
 expect(summary(report,{minReturn:'0'})).toContain('0 strategy rows match numeric thresholds · 4 context-only strategy rows');
});
it('uses only displayed strategy rows after combined family, timeframe, state and review filters',()=>{
 const report=fixture(),filters={family:'trend',minutes:'60',status:'completed',review:'verified',minReturn:'0'};
 expect(filterLibraryRows(report,catalog,filters).map(r=>r.ordinal)).toEqual([0,2,5,6]);
 expect(summary(report,filters)).toContain('1 strategy rows match numeric thresholds · 1 context-only strategy rows · 2 passive reference rows');
 expect(summary(report,{...filters,review:'research'})).toContain('0 strategy rows match numeric thresholds · 0 context-only strategy rows · 2 passive reference rows');
 expect(summary(report,{status:'failed',minReturn:'0'})).toContain('0 strategy rows match numeric thresholds · 1 context-only strategy rows');
});
it('describes rows as shown rather than numeric matches when thresholds are blank or invalid',()=>{
 const report=fixture();
 expect(summary(report,{})).toBe('5 strategy rows shown · 2 passive reference rows.');
 expect(summary(report,{minReturn:'  '})).toBe(summary(report,{}));
 const invalidFilters:Record<string,string>[]=[{minTrades:'1.5'},{maxDrawdown:'-1'},{minReturn:'NaN'}];
 for(const invalid of invalidFilters)expect(summary(report,{...invalid,minTrades:invalid.minTrades??'99'})).toBe('5 strategy rows shown · 2 passive reference rows.');
 expect(summary(report,{status:'failed',minTrades:'1.5'})).toBe('1 strategy rows shown · 2 passive reference rows.');
 expect(summary(report,{family:'absent'})).toBe('0 strategy rows shown · 2 passive reference rows. No strategy rows match the current category filters.');
});
it('keeps frozen holdout order with the same counts under either sort direction',()=>{
 const report={...fixture(),snapshot:{...fixture().snapshot,phase:'out_of_sample'}};
 const filters={minReturn:'99'},filtered=filterLibraryRows(report,catalog,filters);
 for(const direction of ['asc','desc'] as const){
  const displayed=sortedLibraryRows(report,'period_return',direction).filter(r=>filtered.includes(r));
  expect(displayed.map(r=>r.ordinal)).toEqual([2,3,4,5,6]);
  expect(libraryFilterSummary(report,displayed,filters)).toBe(summary(report,filters));
 }
});
it('announces the table summary outside collapsed filters and clears viewing thresholds without actions',async()=>{
 const report=fixture();
 vi.mocked(api).mockReset().mockImplementation(async command=>command==='library_batch_history'?{rows:[{id:'saved',created_at:'Fixture',status:'completed'}],next:null}:command==='library_batch_status'?report:{});
 render(<LibraryResearch view="saved" selections={[]} datasets={[]} profile={defaultProfile} catalog={catalog} onActive={vi.fn()} onReport={vi.fn()} onOpenRun={vi.fn()}/>);
 await screen.findByRole('option',{name:/Fixture/});fireEvent.change(screen.getByLabelText('Saved library batches'),{target:{value:'saved'}});
 const text=await screen.findByText('5 strategy rows shown · 2 passive reference rows.');
 expect(text.getAttribute('role')).toBe('status');expect(text.getAttribute('aria-atomic')).toBe('true');expect(text.closest('details')).toBeNull();
 expect(screen.getByRole('region',{name:'Saved comparison results'}).getAttribute('aria-describedby')?.split(' ')).toContain(text.id);
 fireEvent.click(screen.getByText('Filter results · 0 active',{selector:'summary'}));
 fireEvent.change(screen.getByLabelText('Minimum period return (%)'),{target:{value:'99'}});
 expect(text.textContent).toBe(summary(report,{minReturn:'99'}));
 expect(screen.queryByText('Zero',{exact:true})).toBeNull();expect(screen.getByText('Buy & Hold',{exact:true})).toBeTruthy();
 fireEvent.change(screen.getByLabelText('Minimum completed positions'),{target:{value:'1.5'}});
 expect(text.textContent).toBe('5 strategy rows shown · 2 passive reference rows.');
 expect(screen.getByRole('alert').textContent).toBe('Enter a valid minimum completed positions (whole number). Numeric thresholds are not applied until corrected.');
 expect(screen.getByText('Zero',{exact:true})).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Clear filters'}));
 expect(text.textContent).toBe('5 strategy rows shown · 2 passive reference rows.');expect(screen.queryByRole('alert')).toBeNull();
 expect(vi.mocked(api).mock.calls.every(([command])=>['library_batch_history','library_batch_status'].includes(command))).toBe(true);
});
