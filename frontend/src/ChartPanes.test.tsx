import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import ChartIndicators,{defaults,emptySettings,type ChartIndicator} from './ChartIndicators';
import {IndicatorDraftProvider} from './IndicatorDrafts';
import {legacyPaneLayout,reconcilePaneLayout,validatePaneLayout,visiblePanes,type PaneLayout} from './chartPanes';
import {installIndicatorSeries} from './chartIndicatorSeries';
import IndicatorPresets from './IndicatorPresets';
const mock=vi.hoisted(()=>({api:vi.fn()}));
vi.mock('./api',()=>({api:mock.api}));
const item=(type:ChartIndicator['type'],id:string=type)=>({id,type,params:{...defaults[type]},color:'#abcdef',visible:true} as ChartIndicator);
const items=[item('rsi'),item('stochastic'),item('macd'),item('momentum'),item('atr'),item('stddev'),item('vmc_cipher_b'),item('ema'),item('volume')];
const layout=():PaneLayout=>({version:1,price_weight:400,recorded_weight:150,panes:[{id:'b',weight:240,instance_ids:['vmc_cipher_b']},{id:'difference',weight:130,instance_ids:['macd','momentum']},{id:'bounded',weight:160,instance_ids:['rsi','stochastic']},{id:'distance',weight:120,instance_ids:['atr','stddev']}]});
beforeEach(()=>{mock.api.mockReset();localStorage.clear();});

it('validates exact compatible membership, versions and uncapped pane counts',()=>{
 expect(validatePaneLayout(layout(),items)).toBe('');
 for(const value of [{...layout(),version:2},{...layout(),price_weight:NaN},{...layout(),recorded_weight:0},{...layout(),panes:[]},{...layout(),panes:[{id:'mix',weight:1,instance_ids:['rsi','macd','vmc_cipher_b']}]}]) expect(validatePaneLayout(value,items)).toContain('Invalid');
 for(const pair of [['macd','atr'],['momentum','stddev'],['vmc_cipher_b','rsi'],['vmc_cipher_b','macd']]) {
  const subset=items.filter(item=>pair.includes(item.id));
  expect(validatePaneLayout({...layout(),panes:[{id:'mixed',weight:130,instance_ids:pair}]},subset)).toContain('Invalid');
 }
 const many=Array.from({length:400},(_,i)=>item('rsi',`r${i}`));
 expect(validatePaneLayout({...layout(),panes:many.map(row=>({id:`p${row.id}`,weight:130,instance_ids:[row.id]}))},many)).toBe('');
});
it('keeps legacy grouping separate and retains custom order and weight when hidden',()=>{
 expect(legacyPaneLayout(items).panes.map(p=>p.instance_ids)).toEqual([['rsi'],['stochastic'],['macd'],['momentum'],['atr'],['stddev'],['vmc_cipher_b']]);
 const hidden=items.map(row=>row.id==='vmc_cipher_b'?{...row,visible:false}:row);
 expect(reconcilePaneLayout(layout(),hidden)).toEqual(layout());
 expect(visiblePanes(hidden,layout()).map(p=>p.id)).toEqual(['difference','bounded','distance']);
 expect(visiblePanes(items,layout())[0]).toEqual({id:'b',weight:240,instance_ids:['vmc_cipher_b']});
 const overlay=items.map(row=>row.type==='volume'?{...row,placement:'pane' as const}:row);
 const changed=reconcilePaneLayout(layout(),overlay);expect(changed.panes.at(-1)?.instance_ids).toEqual(['volume']);
 expect(reconcilePaneLayout(changed,items)).toEqual(layout());
});
it('creates actual-series requests in physical pane order with seven B ports, linear extras and separate recorded last',()=>{
 const panes:any[]=[{setStretchFactor:vi.fn()}], scales=new Map<number,any>();
 const primary={options:()=>({mode:1,autoScale:false,scaleMargins:{top:.2,bottom:.1}}),applyOptions:vi.fn()};
 scales.set(0,primary);
 const chart={priceScale:()=>primary,panes:()=>panes,addSeries:vi.fn((_kind:any,options:any,index:number)=>{
  // Reject holes as a real chart can: model order alone is not enough.
  expect(index).toBeLessThanOrEqual(panes.length);
  if(index===panes.length){panes.push({setStretchFactor:vi.fn()});scales.set(index,{applyOptions:vi.fn()});}
  return {options,index,priceScale:()=>options.priceScaleId?{applyOptions:vi.fn()}:scales.get(index),createPriceLine:vi.fn()};
 })};
 const recorded={moveToPane:vi.fn((index:number)=>{expect(index).toBe(panes.length);panes.push({setStretchFactor:vi.fn()});}),priceScale:()=>({applyOptions:vi.fn()})};
 const owned=installIndicatorSeries(chart,recorded,items,true,layout());
 expect(owned.filter(row=>row.kind==='vmc_cipher_b').map(row=>row.series.index)).toEqual(Array(7).fill(1));
 expect(owned.filter(row=>['macd','momentum'].includes(row.kind)).every(row=>row.series.index===2)).toBe(true);
 expect(owned.filter(row=>['rsi','stochastic'].includes(row.kind)).every(row=>row.series.index===3)).toBe(true);
 expect(owned.filter(row=>['atr','stddev'].includes(row.kind)).every(row=>row.series.index===4)).toBe(true);
 expect(recorded.moveToPane).toHaveBeenCalledWith(5);
 expect(panes.map(pane=>pane.setStretchFactor.mock.calls.at(-1)[0])).toEqual([400,240,130,160,120,150]);
 expect([...scales.entries()].filter(([i])=>i>0).every(([,scale])=>scale.applyOptions.mock.calls.every(([value]:any)=>value.mode===0&&value.autoScale===true))).toBe(true);
 expect(primary.applyOptions.mock.calls.every(([value])=>value.mode===1&&value.autoScale===false)).toBe(true);
 expect(owned.find(row=>row.kind==='volume')?.series.options.priceScaleId).toBe('volume-volume');
 expect(owned.filter(row=>row.kind==='vmc_cipher_b').every(row=>!row.series.options.autoscaleInfoProvider)).toBe(true);
});
const open=()=>{fireEvent.click(screen.getByRole('button',{name:/^Indicators \(/}));fireEvent.click(screen.getByRole('button',{name:'Pane layout'}));};
it('applies or cancels layout and indicator edits atomically at the original revision',()=>{
 const apply=vi.fn(),settings={...emptySettings,revision:3,instances:items,pane_layout:layout()};
 const {rerender}=render(<ChartIndicators settings={settings} onApply={apply} busy={false} error=""/>);open();
 fireEvent.change(screen.getByLabelText('Price pane weight'),{target:{value:'500'}});
 fireEvent.change(screen.getByLabelText('1 RSI period'),{target:{value:'12'}});
 fireEvent.click(screen.getByRole('button',{name:'Move pane 1 down'}));
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 expect(apply).toHaveBeenCalledWith(expect.arrayContaining([expect.objectContaining({id:'rsi',params:{period:12}})]),3,expect.objectContaining({price_weight:500,panes:[layout().panes[1],layout().panes[0],...layout().panes.slice(2)]}));
 rerender(<ChartIndicators settings={{...settings,revision:5}} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));expect(apply.mock.calls.at(-1)?.[1]).toBe(3);
 fireEvent.click(screen.getByRole('button',{name:'Cancel edits'}));open();expect((screen.getByLabelText('Price pane weight') as HTMLInputElement).value).toBe('400');
 expect((screen.getByLabelText('1 RSI period') as HTMLInputElement).value).toBe('14');
});
it('retains a layout-only draft across namespace remount without advancing its revision',()=>{
 const apply=vi.fn(),settings={...emptySettings,revision:3,instances:items,pane_layout:layout()};
 const view=(source:string,revision=3)=><IndicatorDraftProvider><ChartIndicators key={source} namespace={{source,market:'spot',symbol:'BTCUSDT'}} settings={{...settings,revision}} onApply={apply} busy={false} error=""/></IndicatorDraftProvider>;
 const {rerender}=render(view('bybit'));open();fireEvent.change(screen.getByLabelText('Pane 1 weight'),{target:{value:'300'}});
 rerender(view('okx'));expect(screen.queryByText(/Pending edits/)).toBeNull();
 rerender(view('bybit',8));fireEvent.click(screen.getByRole('button',{name:'Pane layout'}));expect((screen.getByLabelText('Pane 1 weight') as HTMLInputElement).value).toBe('300');
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));expect(apply.mock.calls[0][1]).toBe(3);expect(apply.mock.calls[0][2].panes[0].weight).toBe(300);
});
it('offers compatible grouping only and keeps hidden pane edits without reserving visible space',()=>{
 const apply=vi.fn(),settings={...emptySettings,instances:items};render(<ChartIndicators settings={settings} onApply={apply} busy={false} error=""/>);open();
 const rsi=screen.getByLabelText('Pane for 1 RSI') as HTMLSelectElement;
 expect([...rsi.options].map(option=>option.textContent).join(' ')).toContain('STOCH');
 expect([...rsi.options].map(option=>option.textContent).join(' ')).not.toContain('MACD');
 fireEvent.change(rsi,{target:{value:'legacy_stochastic'}});
 fireEvent.click(screen.getByRole('button',{name:'Hide pane 1'}));
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 expect(apply.mock.calls[0][2].panes[0].instance_ids).toEqual(['stochastic','rsi']);
 expect(apply.mock.calls[0][0].filter((row:ChartIndicator)=>['rsi','stochastic'].includes(row.type)).every((row:ChartIndicator)=>!row.visible)).toBe(true);
});
it.each([false,true])('stages supported layout extension or legacy preset explicitly, custom=%s',async(custom)=>{
 const preset={id:'preset',name:'Panes',revision:1,deleted:false,instance_count:items.length,content:{version:1,instances:items,extensions:custom?{pane_layout:layout()}:{}}};
 mock.api.mockImplementation(async(command:string)=>command==='chart_preset_list'?{version:1,presets:[preset]}:preset);
 const apply=vi.fn();render(<ChartIndicators namespace={{source:'bybit',market:'spot',symbol:'BTCUSDT'}} settings={{...emptySettings,revision:2,instances:items,pane_layout:{...layout(),price_weight:999}}} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Named presets'}));await waitFor(()=>expect((screen.getByLabelText('Named indicator preset') as HTMLSelectElement).disabled).toBe(false));
 fireEvent.change(screen.getByLabelText('Named indicator preset'),{target:{value:'preset'}});await screen.findByRole('region',{name:'Preset preview'});
 fireEvent.click(screen.getByRole('button',{name:'Stage preset'}));expect(apply).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));expect(apply).toHaveBeenCalledWith(items,2,custom?layout():null);
});
it.each([{pane_layout:{...layout(),version:2}},{pane_layout:{...layout(),panes:[]}},{unknown:{version:1}}])('refuses invalid or unsupported preset extension before Stage',async(extensions)=>{
 const preset={id:'p',name:'Future',revision:1,deleted:false,instance_count:items.length,content:{version:1,instances:items,extensions}};
 mock.api.mockImplementation(async(command:string)=>command==='chart_preset_list'?{version:1,presets:[preset]}:preset);
 render(<IndicatorPresets namespace={{source:'bybit',market:'spot',symbol:'BTCUSDT'}} revision={0} busy={false} dirty={false} onStage={vi.fn()}/>);
 fireEvent.click(screen.getByRole('button',{name:'Named presets'}));await waitFor(()=>expect((screen.getByLabelText('Named indicator preset') as HTMLSelectElement).disabled).toBe(false));fireEvent.change(screen.getByLabelText('Named indicator preset'),{target:{value:'p'}});
 await screen.findByRole('alert');expect((screen.getByRole('button',{name:'Stage preset'}) as HTMLButtonElement).disabled).toBe(true);
});
