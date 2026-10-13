import {it, expect, vi, beforeEach} from 'vitest';
import {render, screen, fireEvent, waitFor, act} from '@testing-library/react';
import LiveTerminal from './LiveTerminal';
import ChartIndicators, {emptySettings, type IndicatorSettings, type ChartIndicator} from './ChartIndicators';
import {useChartIndicators} from './useChartIndicators';
import {defaultProfile} from './model';
const mock=vi.hoisted(()=>({api:vi.fn()}));
vi.mock('./api',()=>({api:mock.api}));
// Keep the actual LiveTerminal provider/key boundary and actual editor/save hook;
// the chart canvas and market calculation are outside this lifecycle contract.
vi.mock('./LiveChart',()=>({default:({source,market,symbol}:any)=>{
 const state=useChartIndicators(market,symbol,1,false,{current:[]},source);
 return <ChartIndicators namespace={{source,market,symbol}} settings={state.settings} busy={!state.loaded||state.saving} error={state.error} onApply={state.apply}/>;
}}));
const row:ChartIndicator={id:'ema-fixture',type:'ema',params:{period:20},visible:true,color:'#abcdef'};
const preset={id:'preset-fixture',name:'Retained research',revision:4,deleted:false,instance_count:1,content:{version:1,instances:[row],extensions:{}}};
let settings:Record<string,IndicatorSettings>;
const key=(p:any)=>JSON.stringify([p.source??'bybit',p.market,p.symbol]);
const profile={...defaultProfile,market:'spot',symbol:'BTCUSDT'};
const firstKey=key(profile);
const deferred=()=>{let resolve!:(x:any)=>void; const promise=new Promise<any>(r=>{resolve=r;});return {resolve,promise};};
beforeEach(()=>{
 settings={[firstKey]:{...emptySettings,revision:6}};
 mock.api.mockReset();mock.api.mockImplementation(async(command:string,p:any)=>{
  if(command==='market_preferences')return {source:'bybit'};
  if(command==='live_status')return {active:false,market:{active:false}};
  if(command==='chart_indicator_settings')return settings[key(p)]??emptySettings;
  if(command==='chart_indicator_save'){
   const current=settings[key(p)]??emptySettings;
   if(current.revision!==p.revision)throw Object.assign(new Error('Settings revision conflict'),{definiteRejection:true});
   return settings[key(p)]={...current,revision:current.revision+1,instances:p.instances};
  }
  if(command==='chart_preset_list')return {version:1,presets:[preset]};
  if(command==='chart_preset_get')return preset;
  return {...preset,revision:5};
 });
});
const terminal=(p=profile,visible=true)=><LiveTerminal strategyId={null} profile={p} visible={visible}/>;
async function ready(){await waitFor(()=>expect(mock.api.mock.calls.some(c=>c[0]==='chart_indicator_settings')).toBe(true));}
async function stage(){
 fireEvent.click(screen.getByRole('button',{name:'Named presets'}));
 await waitFor(()=>expect((screen.getByLabelText('Named indicator preset') as HTMLSelectElement).disabled).toBe(false));
 fireEvent.change(screen.getByLabelText('Named indicator preset'),{target:{value:preset.id}});
 await screen.findByRole('region',{name:'Preset preview'});fireEvent.click(screen.getByRole('button',{name:'Stage preset'}));
}
async function switchSource(source:string){
 fireEvent.change(screen.getByLabelText('Market data source'),{target:{value:source}});
 await waitFor(()=>expect(mock.api.mock.calls.some(c=>c[0]==='chart_indicator_settings'&&(c[1].source??'bybit')===source)).toBe(true));
 await act(async()=>{});
}
it('retains an edited staged preset across source remounts and blocks stale revision Apply visibly',async()=>{
 render(terminal());await ready();await stage();
 fireEvent.change(screen.getByLabelText('1 EMA period'),{target:{value:'37'}});
 await switchSource('okx');expect(screen.queryByText(/Staged preset:/)).toBeNull();
 settings[firstKey]={...emptySettings,revision:9};
 await switchSource('bybit');
 expect(screen.getByText(/Staged preset: Retained research/)).toBeTruthy();
 expect((screen.getByLabelText('1 EMA period') as HTMLInputElement).value).toBe('37');
 expect(screen.getByText(/Pending edits are retained for this source/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('chart_indicator_save',expect.objectContaining({market:'spot',symbol:'BTCUSDT',revision:6,instances:[{...row,params:{period:37}}]})));
 expect((await screen.findByRole('alert')).textContent).toContain('revision conflict');
 expect(screen.getByText(/Staged preset: Retained research/)).toBeTruthy();
});
it('retains collapsed ordinary edits by source and clears them after explicit Cancel',async()=>{
 render(terminal());await ready();fireEvent.click(screen.getByRole('button',{name:'Indicators (0)'}));
 fireEvent.click(screen.getByRole('button',{name:'Add EMA'}));fireEvent.change(screen.getByLabelText('1 EMA period'),{target:{value:'41'}});
 fireEvent.click(screen.getByRole('button',{name:'Close indicator settings'}));
 await switchSource('okx');expect(screen.queryByText(/Unapplied edits retained/)).toBeNull();
 await switchSource('bybit');expect(screen.getByText(/Unapplied edits retained/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Indicators (0)'}));expect((screen.getByLabelText('1 EMA period') as HTMLInputElement).value).toBe('41');
 fireEvent.click(screen.getByRole('button',{name:'Cancel edits'}));
 await switchSource('okx');await switchSource('bybit');expect(screen.queryByText(/Pending edits are retained/)).toBeNull();
});
it('isolates symbol and market draft namespaces and keeps edits when Market is hidden',async()=>{
 const {rerender}=render(terminal());await ready();await stage();
 const other={...profile,symbol:'ETHUSDT'};
 rerender(terminal(other));await act(async()=>{});expect(screen.queryByText(/Staged preset:/)).toBeNull();
 rerender(terminal({...profile,market:'linear'}));await act(async()=>{});expect(screen.queryByText(/Staged preset:/)).toBeNull();
 rerender(terminal(profile,false));await act(async()=>{});expect(screen.getByText(/Staged preset: Retained research/)).toBeTruthy();
 rerender(terminal());await act(async()=>{});expect(screen.getByText(/Staged preset: Retained research/)).toBeTruthy();
});
it('clears retained pending preset after acknowledged Apply and restores only the applied chart',async()=>{
 render(terminal());await ready();await stage();fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 await waitFor(()=>expect(screen.queryByText(/Staged preset:/)).toBeNull());
 await switchSource('okx');await switchSource('bybit');
 expect(screen.queryByText(/Pending edits are retained/)).toBeNull();expect(screen.getByRole('button',{name:'Indicators (1)'})).toBeTruthy();
});
it('rejects a late library mutation response after switching source while retaining the original draft',async()=>{
 const late=deferred(),previous=mock.api.getMockImplementation()!;
 mock.api.mockImplementation((command:string,...args:any[])=>command==='chart_preset_rename'?late.promise:previous(command,...args));
 render(terminal());await ready();await stage();
 fireEvent.change(screen.getByLabelText('Preset name'),{target:{value:'Renamed later'}});
 fireEvent.click(screen.getByRole('button',{name:'Rename preset'}));
 await switchSource('okx');await act(async()=>late.resolve({...preset,name:'Renamed later',revision:5}));
 expect(screen.queryByText(/Saved library change/)).toBeNull();expect(screen.queryByText(/Staged preset:/)).toBeNull();
 await switchSource('bybit');expect(screen.getByText(/Staged preset: Retained research/)).toBeTruthy();
 expect(screen.queryByText(/Saved library change/)).toBeNull();
});
it('uses authoritative reload to reconcile a late Apply without leaking its result to another source',async()=>{
 const late=deferred(),previous=mock.api.getMockImplementation()!;
 mock.api.mockImplementation((command:string,...args:any[])=>command==='chart_indicator_save'?late.promise:previous(command,...args));
 render(terminal());await ready();await stage();fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 await switchSource('okx');settings[firstKey]={...emptySettings,revision:7,instances:[row]};
 await act(async()=>late.resolve(settings[firstKey]));expect(screen.getByRole('button',{name:'Indicators (0)'})).toBeTruthy();
 await switchSource('bybit');expect(screen.queryByText(/Staged preset:/)).toBeNull();expect(screen.getByRole('button',{name:'Indicators (1)'})).toBeTruthy();
});
it('never retains drafts across a new terminal/workspace owner mount',async()=>{
 const first=render(terminal());await ready();await stage();first.unmount();
 render(terminal());await ready();expect(screen.queryByText(/Staged preset:/)).toBeNull();expect(screen.queryByText(/Pending edits are retained/)).toBeNull();
});

it('retains an uncertain empty replacement through transient empty settings until authoritative reload',async()=>{
 settings[firstKey]={...emptySettings,revision:6,instances:[row]};
 const reload=deferred(),previous=mock.api.getMockImplementation()!;let loads=0;
 mock.api.mockImplementation((command:string,p:any,...args:any[])=>{
  if(command==='chart_preset_get')return Promise.resolve({...preset,instance_count:0,content:{...preset.content,instances:[]}});
  if(command==='chart_indicator_save')return Promise.reject(new Error('Lost acknowledgement'));
  if(command==='chart_indicator_settings'&&key(p)===firstKey&&++loads>1)return reload.promise;
  return previous(command,p,...args);
 });
 render(terminal());await ready();await stage();fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 expect((await screen.findByRole('alert')).textContent).toContain('could not be confirmed');
 await switchSource('okx');await switchSource('bybit');
 expect(screen.getByText(/Staged preset: Retained research/)).toBeTruthy();
 expect(screen.getByRole('button',{name:'Saving…'}).hasAttribute('disabled')).toBe(true);
 await act(async()=>reload.resolve(settings[firstKey]));
 expect(screen.getByText(/Staged preset: Retained research/)).toBeTruthy();
 expect(screen.getByLabelText('Selected indicator instance').textContent).toContain('No instances yet');
 expect((screen.getByRole('button',{name:'Apply indicators'}) as HTMLButtonElement).disabled).toBe(false);
 expect(mock.api.mock.calls.filter(c=>c[0]==='chart_indicator_save')).toHaveLength(1);
});
