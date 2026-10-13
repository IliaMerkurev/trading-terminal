import {it, expect, vi, beforeEach} from 'vitest';
import {render, screen, fireEvent, waitFor, act} from '@testing-library/react';
import ChartIndicators, {emptySettings, defaults, type ChartIndicator} from './ChartIndicators';
import IndicatorPresets, {type IndicatorPreset} from './IndicatorPresets';
const mock = vi.hoisted(() => ({api: vi.fn()}));
vi.mock('./api', () => ({api: mock.api}));
const namespace = {source:'bybit', market:'spot', symbol:'BTCUSDT'};
const volume: ChartIndicator = {id:'volume-preserved', type:'volume', params:{}, color:'#abcdef', visible:false, placement:'pane'};
const vmc: ChartIndicator = {id:'vmc-preserved',type:'vmc_cipher_b',params:{...defaults.vmc_cipher_b}, color:'#abcdef',visible:true};
const preset: IndicatorPreset = {id:'p1',name:'Research',revision:7,deleted:false,instance_count:2,content:{version:1,instances:[volume,vmc],extensions:{}}};
const deferred = () => {let resolve!:(value:any)=>void; const promise = new Promise<any>(r => {resolve=r;}); return {resolve,promise};};
beforeEach(() => {
 mock.api.mockReset();
 mock.api.mockImplementation(async(command:string) => command==='chart_preset_list' ? {version:1,presets:[preset]} : command==='chart_preset_get' ? preset : {...preset,revision:8});
});
async function openAndSelect() {
 fireEvent.click(screen.getByRole('button',{name:'Named presets'}));
 await waitFor(() => expect((screen.getByLabelText('Named indicator preset') as HTMLSelectElement).disabled).toBe(false));
 fireEvent.change(screen.getByLabelText('Named indicator preset'), {target:{value:'p1'}});
 await screen.findByRole('region', {name:'Preset preview'});
}
it('previews without mutation, explicitly stages an exact replacement, and requires final revision-guarded Apply',async()=>{
 const apply=vi.fn();
 render(<ChartIndicators namespace={namespace} settings={{...emptySettings,revision:11}} busy={false} error="" onApply={apply}/>);
 await openAndSelect(); expect(apply).not.toHaveBeenCalled();
 expect(screen.getByRole('button',{name:'Indicators (0)'})).toBeTruthy();
 expect(mock.api).toHaveBeenCalledWith('chart_preset_get',{preset_id:'p1',revision:7});
 fireEvent.click(screen.getByRole('button',{name:'Stage preset'}));
 expect(screen.getByText(/Staged preset: Research/)).toBeTruthy(); expect(apply).not.toHaveBeenCalled();
 expect((screen.getByRole('button',{name:'Save current as preset'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 expect(apply).toHaveBeenCalledExactlyOnceWith(preset.content.instances,11);
 expect(mock.api.mock.calls.some(call => call[0]==='chart_indicator_save')).toBe(false);
});
it('saves the applied set from the exact namespace/revision and trims names without submitting draft instances',async()=>{
 render(<IndicatorPresets namespace={{...namespace,source:'okx'}} revision={13} dirty={false} busy={false} onStage={vi.fn()}/>);
 await openAndSelect();
 fireEvent.change(screen.getByLabelText('Preset name'),{target:{value:'  Another  '}});
 fireEvent.click(screen.getByRole('button',{name:'Save current as preset'}));
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('chart_preset_save_current',{source:'okx',market:'spot',symbol:'BTCUSDT',revision:13,name:'Another'}));
});
it('keeps dirty edits and their original revision across settings refresh, blocks stage/save, and supports explicit Cancel',async()=>{
 const apply=vi.fn(), original={...emptySettings,revision:3,instances:[volume]};
 const {rerender}=render(<ChartIndicators namespace={namespace} settings={original} busy={false} error="" onApply={apply}/>);
 await openAndSelect();
 fireEvent.click(screen.getByRole('button',{name:'Indicators (1)'}));fireEvent.click(screen.getByRole('button',{name:'Add EMA'}));
 rerender(<ChartIndicators namespace={namespace} settings={{...emptySettings,revision:5,instances:[vmc]}} busy={false} error="" onApply={apply}/>);
 expect((screen.getByRole('button',{name:'Stage preset'}) as HTMLButtonElement).disabled).toBe(true);
 expect((screen.getByRole('button',{name:'Save current as preset'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 expect(apply.mock.calls[0][0][0]).toEqual(volume); expect(apply.mock.calls[0][0]).toHaveLength(2); expect(apply.mock.calls[0][1]).toBe(3);
 fireEvent.click(screen.getByRole('button',{name:'Cancel edits'}));
 expect((screen.getByRole('button',{name:'Stage preset'}) as HTMLButtonElement).disabled).toBe(false);
});
it('stages an empty preset as pending replacement and retains it across unrelated settings refresh',async()=>{
 const empty={...preset,instance_count:0,content:{...preset.content,instances:[]}};
 mock.api.mockImplementation(async(command:string)=>command==='chart_preset_list'?{version:1,presets:[empty]}:empty);
 const apply=vi.fn();const settings={...emptySettings,revision:3};
 const {rerender}=render(<ChartIndicators namespace={namespace} settings={settings} busy={false} error="" onApply={apply}/>);
 await openAndSelect();fireEvent.click(screen.getByRole('button',{name:'Stage preset'}));
 rerender(<ChartIndicators namespace={namespace} settings={{...settings}} busy={false} error="" onApply={apply}/>);
 expect(screen.getByText(/Staged preset: Research/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));expect(apply).toHaveBeenCalledWith([],3);
});
it('rejects unsupported extension staging but allows exact revision-bound duplication',async()=>{
 mock.api.mockImplementation(async(command:string)=>command==='chart_preset_list'?{version:1,presets:[preset]}:{...preset,content:{...preset.content,extensions:{presentation:{future:true}}}});
 render(<IndicatorPresets namespace={namespace} revision={2} dirty={false} busy={false} onStage={vi.fn()}/>);
 await openAndSelect();expect((screen.getByRole('button',{name:'Stage preset'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.change(screen.getByLabelText('Preset name'),{target:{value:'Copy'}});
 fireEvent.click(screen.getByRole('button',{name:'Duplicate preset / Save as'}));
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('chart_preset_duplicate',{preset_id:'p1',revision:7,name:'Copy'}));
});
it.each(['Rename preset','Move preset to Trash'])('uses selected revision for %s without applying chart settings',async(label)=>{
 render(<IndicatorPresets namespace={namespace} revision={2} dirty={false} busy={false} onStage={vi.fn()}/>);
 await openAndSelect();fireEvent.change(screen.getByLabelText('Preset name'),{target:{value:'Renamed'}});fireEvent.click(screen.getByRole('button',{name:label}));
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith(label==='Rename preset'?'chart_preset_rename':'chart_preset_trash',{preset_id:'p1',revision:7,...(label==='Rename preset'?{name:'Renamed'}:{})}));
});
it('restores durable trash and does not allow staging a deleted preset',async()=>{
 mock.api.mockImplementation(async(command:string)=>command==='chart_preset_list'?{version:1,presets:[{...preset,deleted:true}]}:{...preset,deleted:true});
 render(<IndicatorPresets namespace={namespace} revision={2} dirty={false} busy={false} onStage={vi.fn()}/>);
 await openAndSelect();fireEvent.change(screen.getByLabelText('Preset library view'),{target:{value:'trash'}});
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('chart_preset_list',{trashed:true},expect.anything()));
 await waitFor(()=>expect((screen.getByLabelText('Named indicator preset') as HTMLSelectElement).disabled).toBe(false));
 fireEvent.change(screen.getByLabelText('Named indicator preset'),{target:{value:'p1'}});await screen.findByRole('region',{name:'Preset preview'});
 expect((screen.getByRole('button',{name:'Stage preset'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Restore preset'}));await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('chart_preset_restore',{preset_id:'p1',revision:7}));
});
it('keeps uncertain save visible, blocks retries, and uses explicit Refresh to reconcile the library',async()=>{
 mock.api.mockImplementation(async(command:string)=>{if(command==='chart_preset_list')return {version:1,presets:[preset]};if(command==='chart_preset_get')return preset;throw new Error('Lost response');});
 render(<IndicatorPresets namespace={namespace} revision={2} dirty={false} busy={false} onStage={vi.fn()}/>);
 await openAndSelect();fireEvent.click(screen.getByRole('button',{name:'Save current as preset'}));
 expect((await screen.findByRole('alert')).textContent).toContain('may have completed');
 expect((screen.getByRole('button',{name:'Save current as preset'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Named presets'}));expect(screen.getByRole('alert').textContent).toContain('Lost response');
 fireEvent.click(screen.getByRole('button',{name:'Named presets'}));
 await waitFor(()=>expect((screen.getByRole('button',{name:'Refresh library'}) as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(screen.getByRole('button',{name:'Refresh library'}));
 await waitFor(()=>expect(screen.queryByRole('alert')).toBeNull());
 expect(mock.api.mock.calls.filter(call=>call[0]==='chart_preset_save_current')).toHaveLength(1);
});
it('surfaces revision conflicts without retry and Refresh reads authoritative revisions',async()=>{
 mock.api.mockImplementation(async(command:string)=>{if(command==='chart_preset_list')return {version:1,presets:[preset]};if(command==='chart_preset_get')return preset;throw Object.assign(new Error('Preset revision conflict'),{definiteRejection:true});});
 render(<IndicatorPresets namespace={namespace} revision={2} dirty={false} busy={false} onStage={vi.fn()}/>);
 await openAndSelect();fireEvent.click(screen.getByRole('button',{name:'Move preset to Trash'}));
 expect((await screen.findByRole('alert')).textContent).toContain('revision conflict');
 fireEvent.click(screen.getByRole('button',{name:'Refresh library'}));await waitFor(()=>expect(screen.queryByRole('alert')).toBeNull());
 expect(mock.api.mock.calls.filter(call=>call[0]==='chart_preset_trash')).toHaveLength(1);
});
it.each(['read','mutation'])('ignores late %s results after a namespace switch',async(kind)=>{
 const pending=deferred();
 mock.api.mockImplementation(async(command:string)=>{if(command==='chart_preset_list')return {version:1,presets:[preset]};if(command==='chart_preset_get')return kind==='read'?pending.promise:preset;return pending.promise;});
 const renderEditor=(source:string)=><ChartIndicators key={source} namespace={{...namespace,source}} settings={emptySettings} busy={false} error="" onApply={vi.fn()}/>;
 const {rerender}=render(renderEditor('bybit'));
 fireEvent.click(screen.getByRole('button',{name:'Named presets'}));await waitFor(()=>expect((screen.getByLabelText('Named indicator preset') as HTMLSelectElement).disabled).toBe(false));
 fireEvent.change(screen.getByLabelText('Named indicator preset'),{target:{value:'p1'}});
 if(kind==='mutation'){await screen.findByRole('region',{name:'Preset preview'});fireEvent.click(screen.getByRole('button',{name:'Save current as preset'}));}
 rerender(renderEditor('okx'));
 await act(async()=>pending.resolve(preset));
 expect(screen.queryByRole('region',{name:'Preset preview'})).toBeNull();expect(screen.queryByText(/Saved library change/)).toBeNull();
 expect(screen.getByRole('button',{name:'Indicators (0)'})).toBeTruthy();
});

it('recognizes canonical-key acknowledgements and clears pending preset only after successful Apply',async()=>{
 const apply=vi.fn(), settings={...emptySettings,revision:1};
 const {rerender}=render(<ChartIndicators namespace={namespace} settings={settings} busy={false} error="" onApply={apply}/>);
 await openAndSelect();fireEvent.click(screen.getByRole('button',{name:'Stage preset'}));
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 const canonical=JSON.parse(JSON.stringify(preset.content.instances,(_key,value)=>value&&typeof value==='object'&&!Array.isArray(value)?Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b))):value));
 rerender(<ChartIndicators namespace={namespace} settings={{...settings,revision:2,instances:canonical}} busy={false} error="" onApply={apply}/>);
 expect(screen.queryByText(/Staged preset: Research/)).toBeNull();
 expect((screen.getByRole('button',{name:'Save current as preset'}) as HTMLButtonElement).disabled).toBe(false);
});
