import {it,expect,vi,beforeEach} from 'vitest';
const {readFileSync}=await vi.importActual<{readFileSync(path:string,encoding:'utf8'):string}>('node:fs');
const marketStyles=readFileSync('frontend/src/market-workspace.css','utf8');
import {render,screen,fireEvent,waitFor,renderHook,act} from '@testing-library/react';
import ChartIndicators,{emptySettings,defaults,indicatorName,type ChartIndicator} from './ChartIndicators';
import {installIndicatorSeries,updateIndicatorSeries} from './chartIndicatorSeries';
import {useChartIndicators} from './useChartIndicators';
import {favoritesKey,parseIndicatorFavorites,indicatorCatalog} from './indicatorCatalog';
const mock=vi.hoisted(()=>({api:vi.fn()}));
vi.mock('./api',()=>({api:mock.api}));
const primaryScale = () => ({options: () => ({scaleMargins: {top: 0.2, bottom: 0.1}}), applyOptions: vi.fn()});
const item=(type:ChartIndicator['type'],id:string=type):ChartIndicator=>({id,type,params:{...defaults[type]},color:'#7eabff',visible:true,...(type==='volume'?{placement:'pane' as const}:{})});
beforeEach(()=>{mock.api.mockReset();localStorage.clear();});

it('adds duplicate EMA instances and applies parameters, visibility and removal atomically',()=>{
 const apply=vi.fn();render(<ChartIndicators settings={emptySettings} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Indicators (0)'}));
 fireEvent.click(screen.getByRole('button',{name:'Add EMA'}));fireEvent.click(screen.getByRole('button',{name:'Add EMA'}));
 fireEvent.change(screen.getByLabelText('Selected indicator instance'),{target:{value:(screen.getByLabelText('Selected indicator instance') as HTMLSelectElement).options[0].value}});
 const first=screen.getByLabelText('1 EMA period');
 fireEvent.change(first,{target:{value:'0'}});fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));expect(apply).not.toHaveBeenCalled();
 expect(screen.getByRole('alert').textContent).toContain('whole numbers');
 fireEvent.change(first,{target:{value:'9'}});fireEvent.change(screen.getByLabelText('Selected indicator instance'),{target:{value:(screen.getByLabelText('Selected indicator instance') as HTMLSelectElement).options[1].value}});fireEvent.click(screen.getByLabelText('2 EMA visible'));
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 expect(apply.mock.calls[0][0]).toHaveLength(2);expect(apply.mock.calls[0][0][0].params.period).toBe(9);expect(apply.mock.calls[0][0][1].visible).toBe(false);
 expect(apply.mock.calls[0][0][0].id).not.toBe(apply.mock.calls[0][0][1].id);
 fireEvent.change(screen.getByLabelText('Selected indicator instance'),{target:{value:(screen.getByLabelText('Selected indicator instance') as HTMLSelectElement).options[0].value}});
 fireEvent.click(screen.getByRole('button',{name:'Remove 1 EMA'}));fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));expect(apply.mock.calls[1][0]).toHaveLength(1);
});

it('separates price, RSI fixed scale, MACD, volume and recorded IR panes; removes no unrelated series',()=>{
 const added:any[]=[];const chart={priceScale:primaryScale,addSeries:vi.fn((kind,options,pane)=>{const s={kind,options,pane,setData:vi.fn(),createPriceLine:vi.fn(),priceScale:()=>({applyOptions:vi.fn()})};added.push(s);return s;}),panes:()=>[]};const recorded={moveToPane:vi.fn()};
 const items=[item('ema'),item('ema','second'),item('sma'),item('bb'),item('rsi'),item('macd'),item('volume')];
 const owned=installIndicatorSeries(chart,recorded,items,true);
 expect(owned).toHaveLength(11);expect(added.filter(s=>s.pane===0)).toHaveLength(6);
 const rsi=owned.find(s=>s.kind==='rsi')!.series;expect(rsi.pane).toBe(1);expect(rsi.options.autoscaleInfoProvider().priceRange).toEqual({minValue:0,maxValue:100});expect(rsi.createPriceLine.mock.calls.map((c:any[])=>c[0].price)).toEqual([30,70]);
 expect(added.filter(s=>s.pane===2)).toHaveLength(3);expect(added.filter(s=>s.pane===3)).toHaveLength(1);expect(recorded.moveToPane).toHaveBeenLastCalledWith(4);
 updateIndicatorSeries(owned,{times:[60,120],columns:{ema:{value:[null,12.5]}},directions:[1,-1]});expect(owned[0].series.setData).toHaveBeenCalledWith([{time:60},{time:120,value:12.5}]);
 installIndicatorSeries(chart,recorded,[item('volume')],true);expect(recorded.moveToPane).toHaveBeenLastCalledWith(2);
});

it('ignores stale settings and calculations after source/timeframe switches and retains loaded saved configuration',async()=>{
 let resolveOld:(value:any)=>void=()=>{};let resolveCalculation:(value:any)=>void=()=>{};
 const doc={...emptySettings,revision:1,instances:[item('ema')]};let reads=0;
 mock.api.mockImplementation((command:string,p:any)=>{
  if(command==='chart_indicator_settings')return p.market==='spot'?new Promise(resolve=>{resolveOld=resolve;}):Promise.resolve(doc);
  if(command==='chart_indicator_read'){reads++;return reads===1?new Promise(resolve=>{resolveCalculation=resolve;}):Promise.resolve({status:'ready',times:[3600],columns:{ema:{value:[42]}}});}
 });
 const rows={current:[{time:0,open:10,high:12,low:9,close:11,volume:1}]};
 const {result,rerender,unmount}=renderHook(({market,minutes})=>useChartIndicators(market,'BTCUSDT',minutes,true,rows),{initialProps:{market:'spot',minutes:1}});
 rerender({market:'linear',minutes:1});await waitFor(()=>expect(result.current.loaded).toBe(true));
 await act(async()=>{resolveOld({...emptySettings,instances:[item('volume')]});});expect(result.current.settings.instances[0].type).toBe('ema');
 rerender({market:'linear',minutes:60});await waitFor(()=>expect(result.current.result?.times).toEqual([3600]));
 await act(async()=>{resolveCalculation({status:'ready',times:[60],columns:{ema:{value:[999]}}});});expect(result.current.result?.times).toEqual([3600]);
 expect(mock.api.mock.calls.every(c=>['chart_indicator_settings','chart_indicator_read'].includes(c[0]))).toBe(true);unmount();
});

it('storage failures are nonfatal and valid Apply preserves old state until save succeeds',async()=>{
 const doc={...emptySettings,revision:1,instances:[item('ema')]};
 mock.api.mockImplementation(async(command:string)=>{if(command==='chart_indicator_settings')return doc;throw new Error('Storage denied');});
 const rows={current:[]};
 function Harness(){const state=useChartIndicators('spot','BTCUSDT',1,true,rows);return <><button disabled={!state.loaded||state.saving} onClick={()=>{void state.apply([item('rsi')]);}}>Save fixture</button><span>{state.settings.instances[0]?.type}</span>{state.error&&<p role="alert">{state.error}</p>}</>;}
 render(<Harness/>);await waitFor(()=>expect((screen.getByRole('button',{name:'Save fixture'}) as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(screen.getByRole('button',{name:'Save fixture'}));expect((await screen.findByRole('alert')).textContent).toContain('Settings save could not be confirmed');
 expect(screen.getByText('ema')).toBeTruthy();expect(screen.queryByText('rsi')).toBeNull();expect((screen.getByRole('button',{name:'Save fixture'}) as HTMLButtonElement).disabled).toBe(false);
});


it('names persisted BB and MACD with semantic order after canonical key sorting',()=>{
 const bb={...item('bb'),params:JSON.parse('{"deviations":2,"period":20}')};
 const macd={...item('macd'),params:JSON.parse('{"fast":12,"signal":9,"slow":26}')};
 expect(indicatorName(bb)).toBe('Bollinger Bands (20, 2)');
 expect(indicatorName(macd)).toBe('MACD (12, 26, 9)');
 const {rerender}=render(<ChartIndicators settings={{...emptySettings,instances:[bb,macd]}} onApply={vi.fn()} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Indicators (2)'}));
 expect(screen.getAllByRole('spinbutton').map(input=>input.getAttribute('aria-label'))).toEqual([
  '1 BB period','1 BB deviations']);
 fireEvent.change(screen.getByLabelText('Selected indicator instance'),{target:{value:'macd'}});
 expect(screen.getAllByRole('spinbutton').map(input=>input.getAttribute('aria-label'))).toEqual(['2 MACD fast','2 MACD slow','2 MACD signal']);
 rerender(<ChartIndicators settings={{...emptySettings,revision:2,instances:[bb,macd]}} onApply={vi.fn()} busy={false} error=""/>);
 expect((screen.getByLabelText('2 MACD slow') as HTMLInputElement).value).toBe('26');
});


it('keeps chart controls and natural-height panes inside a visible workspace scroll owner',()=>{
 const style=document.createElement('style');
 style.textContent=marketStyles;
 document.head.append(style);
 const host=document.createElement('div');
 host.className='market-host';
 host.innerHTML='<section class="live-terminal"><div class="terminal-market"><section class="live-chart"><div class="chart-plot"></div></section></div></section>';
 document.body.append(host);
 try {
  const workspace=getComputedStyle(host.querySelector('.live-terminal')!);
  const market=getComputedStyle(host.querySelector('.terminal-market')!);
  const chart=getComputedStyle(host.querySelector('.live-chart')!);
  const plot=getComputedStyle(host.querySelector('.chart-plot')!);
  expect(workspace.overflowY).toBe('auto');
  expect(market.overflow).toBe('visible');
  expect(chart.height).toBe('auto');
  expect(chart.width).toBe('100%');
  expect(chart.boxSizing).toBe('border-box');
  expect(chart.alignSelf).toBe('stretch');
  expect(plot.minHeight).toBe('320px');
 } finally {
  host.remove();
  style.remove();
 }
});


it('assigns persistent relative pane weights without sequential pixel redistribution',()=>{
 const panes=Array.from({length:4},()=>({setStretchFactor:vi.fn(),setHeight:vi.fn()}));
 const series=()=>({setData:vi.fn(),createPriceLine:vi.fn(),priceScale:()=>({applyOptions:vi.fn()})});
 const chart={priceScale:primaryScale,addSeries:vi.fn(series),panes:()=>panes};
 installIndicatorSeries(chart,{moveToPane:vi.fn()},[item('rsi'),item('macd'),item('volume')],false);
 expect(panes.map(pane=>pane.setStretchFactor.mock.calls[0][0])).toEqual([320,130,130,130]);
 expect(panes.every(pane=>pane.setHeight.mock.calls.length===0)).toBe(true);
 // A different pane set gets the same relative policy, independent of its
 // previous pixel heights or the order of ResizeObserver notifications.
 const resized=[panes[0],panes[3]];
 installIndicatorSeries({...chart,panes:()=>resized},{moveToPane:vi.fn()},[item('volume')],false);
 expect(resized.map(pane=>pane.setStretchFactor.mock.calls.at(-1)![0])).toEqual([320,130]);
});

it('keeps a chosen color through Apply, canonical reopen and series creation',()=>{
 const apply=vi.fn();
 const original={...emptySettings,instances:[item('ema')]};
 const {rerender}=render(<ChartIndicators settings={original} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Indicators (1)'}));
 fireEvent.change(screen.getByLabelText('1 EMA color'),{target:{value:'#ff8800'}});
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 const applied=apply.mock.calls[0][0] as ChartIndicator[];
 expect(applied[0].color).toBe('#ff8800');
 const reopened=JSON.parse(JSON.stringify({...original,revision:1,instances:applied}));
 rerender(<ChartIndicators settings={reopened} onApply={apply} busy={false} error=""/>);
 expect((screen.getByLabelText('1 EMA color') as HTMLInputElement).value).toBe('#ff8800');
 const addSeries=vi.fn((_kind:any,_options:any)=>({setData:vi.fn(),createPriceLine:vi.fn()}));
 installIndicatorSeries({addSeries,panes:()=>[]},{moveToPane:vi.fn()},reopened.instances,false);
 expect(addSeries.mock.calls[0][1].color).toBe('#ff8800');
});


it('isolates RSI padding from shared-scale defaults and rebuilt non-RSI panes', () => {
 const normalMargins = {top: 0.2, bottom: 0.1};
 let defaults = {...normalMargins};
 const makeScale = () => {
  let margins = {...defaults};
  return {
   options: () => ({scaleMargins: {...margins}}),
   applyOptions: vi.fn((options: {scaleMargins: typeof normalMargins}) => {
    margins = {...options.scaleMargins};
    // Installed v5.2 right-scale updates also change future pane defaults.
    defaults = {...margins};
   }),
  };
 };
 const scales = new Map([[0, makeScale()]]);
 const added: {options: any; pane: number}[] = [];
 const chart = {
  priceScale: vi.fn((_id: string, pane: number) => scales.get(pane)),
  addSeries: vi.fn((_kind: any, options: any, pane: number) => {
   if (!scales.has(pane)) scales.set(pane, makeScale());
   added.push({options, pane});
   return {priceScale: () => scales.get(pane), createPriceLine: vi.fn()};
  }),
  panes: () => [],
 };
 const instances = [item('ema'), item('rsi'), item('rsi', 'second-rsi'), item('macd'), item('volume')];
 const recorded = {moveToPane: vi.fn((pane: number) => scales.set(pane, makeScale()))};
 installIndicatorSeries(chart, recorded, instances, true);
 expect(added.filter(series => series.options.autoscaleInfoProvider).map(series => series.pane)).toEqual([1, 1]);
 expect(scales.get(1)!.options().scaleMargins).toEqual({top: 0, bottom: 0});
 for (const index of [0, 2, 3, 4]) expect(scales.get(index)!.options().scaleMargins).toEqual(normalMargins);
 expect(defaults).toEqual(normalMargins);
 // MarketChart removes owned panes before rebuilding. Re-added RSI gets the
 // new pane's API; earlier and later non-RSI scales retain ordinary padding.
 for (const index of [1, 2, 3, 4]) scales.delete(index);
 installIndicatorSeries(chart, null, [item('volume'), item('rsi', 'readded'), item('macd')], false);
 expect(scales.get(2)!.options().scaleMargins).toEqual({top: 0, bottom: 0});
 for (const index of [0, 1, 3]) expect(scales.get(index)!.options().scaleMargins).toEqual(normalMargins);
 expect(added.find(series => series.options.autoscaleInfoProvider)!.options.autoscaleInfoProvider()).toEqual({priceRange: {minValue: 0, maxValue: 100}});
 expect(defaults).toEqual(normalMargins);
});

it('rejects delayed settings, calculation and save replies from the previous exchange',async()=>{
 let oldSettings:(v:any)=>void=()=>{},oldRead:(v:any)=>void=()=>{},oldSave:(v:any)=>void=()=>{};let bybitLoads=0;
 const doc=(type:ChartIndicator['type'])=>({...emptySettings,revision:1,instances:[item(type)]});
 mock.api.mockImplementation((command:string,p:any)=>{
  if(command==='chart_indicator_settings'){
   if(p.source==='okx')return Promise.resolve(doc('ema'));
   return ++bybitLoads===1?new Promise(resolve=>{oldSettings=resolve;}):Promise.resolve(doc('volume'));
  }
  if(command==='chart_indicator_read')return p.source==='okx'?new Promise(resolve=>{oldRead=resolve;}):Promise.resolve({status:'ready',times:[60],columns:{volume:{value:[10]}}});
  if(command==='chart_indicator_save')return new Promise(resolve=>{oldSave=resolve;});
 });
 const rows={current:[{time:0,open:10,high:12,low:9,close:11,volume:10}]};
 const {result,rerender}=renderHook(({source})=>useChartIndicators('spot','BTCUSDT',1,true,rows,source),{initialProps:{source:'bybit'}});
 rerender({source:'okx'});
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('chart_indicator_read',expect.objectContaining({source:'okx'}),expect.objectContaining({signal:expect.any(AbortSignal)})));
 let save:Promise<void>;act(()=>{save=result.current.apply([item('rsi')]);});
 expect(result.current.saving).toBe(true);
 rerender({source:'bybit'});
 await waitFor(()=>expect(result.current.result?.columns.volume.value).toEqual([10]));
 await act(async()=>{oldSettings(doc('bb'));oldRead({status:'ready',times:[60],columns:{ema:{value:[999]}}});oldSave(doc('rsi'));await save;});
 expect(result.current.settings.instances[0].type).toBe('volume');
 expect(result.current.result.columns.volume.value).toEqual([10]);expect(result.current.saving).toBe(false);
});


it('defaults volume to a hidden independent overlay scale and preserves explicit pane instances',()=>{
 const scales:any[]=[];const added:any[]=[];const chart={priceScale:primaryScale,addSeries:vi.fn((_kind,options,pane)=>{const scale={applyOptions:vi.fn()};scales.push(scale);added.push({options,pane});return {priceScale:()=>scale};}),panes:()=>[]};
 const overlay={...item('volume'),placement:undefined};
 const second={...item('volume','second'),placement:'overlay' as const};
 installIndicatorSeries(chart,null,[overlay,second,item('volume','pane'),{...item('volume','hidden'),visible:false}],false);
 expect(added.map(s=>s.pane)).toEqual([0,0,1]);
 expect(added[0].options.priceScaleId).toBe('volume-volume');expect(added[1].options.priceScaleId).toBe('volume-second');
 expect(added[2].options.priceScaleId).toBeUndefined();
 expect(scales[0].applyOptions).toHaveBeenCalledWith({mode:0,autoScale:true,visible:false,scaleMargins:{top:0.8,bottom:0}});
 expect(added[0].options.lastValueVisible).toBe(false);
});

it('keeps logarithmic/manual price choices out of newly created auxiliary scales',()=>{
 let defaults={mode:1,autoScale:false,scaleMargins:{top:0.3,bottom:0.1}};
 const scales:any[]=[];
 const primary={options:()=>({...defaults}),applyOptions:vi.fn(options=>{defaults={...defaults,...options};})};
 const chart={priceScale:()=>primary,panes:()=>[],addSeries:vi.fn(()=>{const scale={options:{...defaults},applyOptions:vi.fn((options:any)=>{scale.options={...scale.options,...options};defaults={...defaults,...options};})};scales.push(scale);return {priceScale:()=>scale,createPriceLine:vi.fn()};})};
 installIndicatorSeries(chart,null,[item('rsi'),item('macd'),item('volume')],false);
 expect(scales.every(scale=>scale.options.mode===0&&scale.options.autoScale===true)).toBe(true);
 expect(primary.options().mode).toBe(1);expect(primary.options().autoScale).toBe(false);
});

it('adds ATR, Stochastic and OBV with bounded parameters and preserves old instances',()=>{
 const apply=vi.fn();render(<ChartIndicators settings={{...emptySettings,instances:[item('ema')]}} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Indicators (1)'}));
 for(const kind of ['atr','stochastic','obv']){fireEvent.click(screen.getByRole('button',{name:`Add ${kind.toUpperCase()}`}));}
 fireEvent.change(screen.getByLabelText('Selected indicator instance'),{target:{value:(screen.getByLabelText('Selected indicator instance') as HTMLSelectElement).options[2].value}});
 fireEvent.change(screen.getByLabelText('3 STOCHASTIC smooth'),{target:{value:'0'}});
 expect((screen.getByRole('button',{name:'Apply indicators'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.change(screen.getByLabelText('3 STOCHASTIC smooth'),{target:{value:'2'}});fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 expect(apply.mock.calls[0][0].map((i:ChartIndicator)=>i.type)).toEqual(['ema','atr','stochastic','obv']);
 expect(apply.mock.calls[0][0][0]).toEqual(item('ema'));expect(indicatorName(item('atr'))).toContain('Wilder, SMA seed');
});

it('keeps ATR, Stochastic and negative OBV in normal auxiliary panes under log price',()=>{
 const added:any[]=[];const primary={options:()=>({mode:1,autoScale:false,scaleMargins:{top:.2,bottom:.1}}),applyOptions:vi.fn()};
 const chart={priceScale:()=>primary,addSeries:vi.fn((kind,options,pane)=>{const scale={applyOptions:vi.fn()};const s={options,pane,setData:vi.fn(),createPriceLine:vi.fn(),priceScale:()=>scale};added.push(s);return s;}),panes:()=>[]};
 const owned=installIndicatorSeries(chart,null,[item('atr'),item('stochastic'),item('obv')],false);
 expect(added.map(s=>s.pane)).toEqual([1,2,2,3]);expect(owned.map(s=>s.port)).toEqual(['value','k','d','value']);
 expect(added.every(s=>s.priceScale().applyOptions.mock.calls[0][0].mode===0)).toBe(true);
 expect(added[1].options.autoscaleInfoProvider().priceRange).toEqual({minValue:0,maxValue:100});
 expect(added[1].createPriceLine.mock.calls.map((c:any[])=>c[0].price)).toEqual([20,80]);
 updateIndicatorSeries(owned,{times:[60,120],columns:{obv:{value:[0,-20]}},directions:[1,-1]});
 expect(added[3].setData).toHaveBeenCalledWith([{time:60,value:0},{time:120,value:-20}]);
 expect(primary.applyOptions.mock.calls.at(-1)?.[0].mode).toBe(1);
});

it('exposes semantic parameters and source units outside the plot while keeping axis values compact',()=>{
 const instances=[item('atr'),item('stochastic'),item('obv')];
 render(<ChartIndicators settings={{...emptySettings,instances}} onApply={vi.fn()} busy={false} error="" volumeUnit="OKX contracts"/>);
 const legend=screen.getByRole('list',{name:'Chart indicator legend'});
 expect(legend.textContent).toContain('period 14 · smooth 3 · signal 3');
 fireEvent.click(screen.getByText('Indicator units and seed notes'));
 expect(screen.getByText(/ATR: price units/).textContent).toContain('initialization differs from graph/recorded IR');
 expect(screen.getByText(/ATR: price units/).textContent).toContain('OKX contracts');
 const added:any[]=[];const chart={priceScale:primaryScale,panes:()=>[],addSeries:vi.fn((_kind,options)=>{added.push(options);return {priceScale:()=>({applyOptions:vi.fn()}),createPriceLine:vi.fn()};})};
 installIndicatorSeries(chart,null,instances,false);
 expect(added.every(options=>options.title===''&&options.lastValueVisible===true)).toBe(true);
});

it('retains unsaved edits across collapse and targeted settings, guards quick actions, and cancels explicitly',()=>{
 const apply=vi.fn(),settings={...emptySettings,instances:[item('ema'),item('bb')]};
 render(<ChartIndicators settings={settings} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Settings for 1 EMA'}));
 expect(document.activeElement?.tagName).toBe('FIELDSET');
 fireEvent.change(screen.getByLabelText('1 EMA period'),{target:{value:'37'}});
 fireEvent.click(screen.getByRole('button',{name:'Close indicator settings'}));
 expect(screen.getByText(/Unapplied edits retained/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Hide 1 EMA'}));expect(apply).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Settings for 2 BB'}));
 expect(document.activeElement?.textContent).toContain('Bollinger Bands');
 expect(screen.queryByLabelText('1 EMA period')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Close indicator settings'}));
 expect(document.activeElement).toBe(screen.getByRole('button',{name:'Settings for 2 BB'}));
 fireEvent.click(screen.getByRole('button',{name:'Settings for 1 EMA'}));
 expect((screen.getByLabelText('1 EMA period') as HTMLInputElement).value).toBe('37');
 fireEvent.click(screen.getByRole('button',{name:'Cancel edits'}));
 fireEvent.click(screen.getByRole('button',{name:'Settings for 1 EMA'}));
 expect((screen.getByLabelText('1 EMA period') as HTMLInputElement).value).toBe('20');
 fireEvent.click(screen.getByRole('button',{name:'Cancel edits'}));
 fireEvent.click(screen.getByRole('button',{name:'Hide 1 EMA'}));
 expect(apply).toHaveBeenCalledExactlyOnceWith([{...settings.instances[0],visible:false},settings.instances[1]]);
});

it('keeps legend visibility truthful and disabled until asynchronous save settles',async()=>{
 let rejectSave:(reason:Error)=>void=()=>{};
 mock.api.mockImplementation((command:string)=>command==='chart_indicator_settings'?Promise.resolve({...emptySettings,instances:[item('ema')]}):command==='chart_indicator_save'?new Promise((_resolve,reject)=>{rejectSave=reject;}):Promise.resolve({}));
 const rows={current:[]};function Harness(){const state=useChartIndicators('spot','BTCUSDT',1,true,rows);return <ChartIndicators settings={state.settings} onApply={state.apply} busy={!state.loaded||state.saving} error={state.error}/>;}
 render(<Harness/>);await waitFor(()=>expect((screen.getByRole('button',{name:'Hide 1 EMA'}) as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(screen.getByRole('button',{name:'Hide 1 EMA'}));
 expect((screen.getByRole('button',{name:'Hide 1 EMA'}) as HTMLButtonElement).disabled).toBe(true);
 expect((screen.getByRole('button',{name:'Settings for 1 EMA'}) as HTMLButtonElement).disabled).toBe(true);
 expect((screen.getByRole('button',{name:'Indicators (1)'}) as HTMLButtonElement).disabled).toBe(false);
 fireEvent.click(screen.getByRole('button',{name:'Hide 1 EMA'}));
 expect(mock.api.mock.calls.filter(call=>call[0]==='chart_indicator_save')).toHaveLength(1);
 await act(async()=>rejectSave(new Error('Save denied')));
 expect(screen.getByRole('button',{name:'Hide 1 EMA'}).getAttribute('aria-pressed')).toBe('true');
 fireEvent.click(screen.getByRole('button',{name:'Indicators (1)'}));
 expect(screen.getByRole('alert').textContent).toContain('Settings save could not be confirmed');
});

it('offers only implemented kinds with search, categories and persistent type-only favorites',()=>{
 const apply=vi.fn();const view=render(<ChartIndicators settings={emptySettings} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Indicators (0)'}));
 expect(document.activeElement).toBe(screen.getByLabelText('Search indicators'));
 expect(screen.getAllByRole('button',{name:/^Add /})).toHaveLength(9);
 expect(indicatorCatalog.map(entry=>entry.kind).sort()).toEqual(Object.keys(defaults).sort());
 fireEvent.change(screen.getByLabelText('Search indicators'),{target:{value:'bollinger'}});
 expect(screen.getByRole('button',{name:'Add BB'})).toBeTruthy();expect(screen.queryByRole('button',{name:'Add EMA'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Favorite BB'}));
 expect(JSON.parse(localStorage.getItem(favoritesKey)!)).toEqual(['bb']);expect(apply).not.toHaveBeenCalled();
 fireEvent.change(screen.getByLabelText('Search indicators'),{target:{value:''}});
 fireEvent.change(screen.getByLabelText('Indicator category'),{target:{value:'Momentum'}});
 expect(screen.getAllByRole('button',{name:/^Add /}).map(button=>button.getAttribute('aria-label'))).toEqual(['Add RSI','Add MACD','Add STOCHASTIC','Add ROC','Add MOMENTUM','Add CCI','Add WILLIAMSR','Add STOCHRSI']);
 fireEvent.change(screen.getByLabelText('Indicator category'),{target:{value:'Favorites'}});
 expect(screen.getAllByRole('button',{name:/^Add /})).toHaveLength(1);
 view.unmount();render(<ChartIndicators settings={emptySettings} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Indicators (0)'}));
 expect(screen.getByRole('button',{name:'Favorite BB'}).getAttribute('aria-pressed')).toBe('true');
 fireEvent.change(screen.getByLabelText('Search indicators'),{target:{value:'unsupported'}});
 expect(screen.getByRole('status').textContent).toContain('No indicators match');
});

it('bounds favorites to recognized identifiers and falls back safely on malformed or unavailable storage',()=>{
 for(const value of ['{','{}','null','"ema"','x'.repeat(4097),JSON.stringify(Array(65).fill('ema'))])expect(parseIndicatorFavorites(value)).toEqual([]);
 expect(parseIndicatorFavorites('["ema","ema","unknown",{"params":99},"volume"]')).toEqual(['ema','volume']);
 const read=vi.spyOn(Storage.prototype,'getItem').mockImplementation(()=>{throw new Error('Denied');});
 const write=vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('Denied');});
 try {
  render(<ChartIndicators settings={emptySettings} onApply={vi.fn()} busy={false} error=""/>);
  fireEvent.click(screen.getByRole('button',{name:'Indicators (0)'}));fireEvent.click(screen.getByRole('button',{name:'Favorite EMA'}));
  expect(screen.getByRole('button',{name:'Favorite EMA'}).getAttribute('aria-pressed')).toBe('true');
  expect(screen.getByRole('status').textContent).toContain('this session only');
 } finally {read.mockRestore();write.mockRestore();}
});

it('allows additional hidden instances and validates the entire draft behind a single editor',()=>{
 const settings={...emptySettings,instances:Array.from({length:8},(_,index)=>({...item('ema',String(index)),visible:false}))};
 const apply=vi.fn();render(<ChartIndicators settings={settings} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Indicators (8)'}));
 expect(screen.getAllByRole('group')).toHaveLength(1);
 expect(screen.getAllByRole('button',{name:/^Add /}).every(button=>(button as HTMLButtonElement).disabled)).toBe(false);
 fireEvent.change(screen.getByLabelText('1 EMA period'),{target:{value:'0'}});
 fireEvent.change(screen.getByLabelText('Selected indicator instance'),{target:{value:'7'}});
 expect(screen.queryByLabelText('1 EMA period')).toBeNull();expect(screen.getByLabelText('8 EMA period')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));expect(apply).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Remove 8 EMA'}));
 expect((screen.getByRole('button',{name:'Add EMA'}) as HTMLButtonElement).disabled).toBe(false);
 expect(screen.getByRole('alert').textContent).toContain('whole numbers');
});

it('retains a failed draft across safe dismissal and Escape without focus mode, and accepts canonical revisions',()=>{
 const settings={...emptySettings,revision:4,instances:[item('ema')]};const apply=vi.fn();
 const view=render(<ChartIndicators settings={settings} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Settings for 1 EMA'}));
 fireEvent.change(screen.getByLabelText('1 EMA period'),{target:{value:'31'}});
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 const saved=apply.mock.calls[0][0];
 view.rerender(<ChartIndicators settings={settings} onApply={apply} busy={true} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Close indicator settings'}));
 expect(screen.getByText(/Unapplied edits retained/)).toBeTruthy();
 view.rerender(<ChartIndicators settings={settings} onApply={apply} busy={false} error="Settings not saved. Revision conflict."/>);
 fireEvent.click(screen.getByRole('button',{name:'Indicators (1)'}));
 expect((screen.getByLabelText('1 EMA period') as HTMLInputElement).value).toBe('31');
 expect(screen.getByRole('alert').textContent).toContain('Revision conflict');
 fireEvent.keyDown(screen.getByLabelText('1 EMA period'),{key:'Escape'});expect(screen.getByLabelText('1 EMA period')).toBeTruthy();
 fireEvent.keyDown(screen.getByRole('button',{name:'Apply indicators'}),{key:'Escape'});
 expect(document.activeElement).toBe(screen.getByRole('button',{name:'Indicators (1)'}));
 fireEvent.click(screen.getByRole('button',{name:'Indicators (1)'}));
 view.rerender(<ChartIndicators settings={{...settings,revision:5,instances:saved}} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Close indicator settings'}));expect(screen.queryByText(/Unapplied edits retained/)).toBeNull();
});

it('keeps repeated native instance selection focused and opens legend settings without the catalog',()=>{
 const settings={...emptySettings,instances:[item('volume'),item('ema'),item('rsi')]};
 render(<ChartIndicators settings={settings} onApply={vi.fn()} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Settings for 3 RSI'}));
 expect(screen.queryByLabelText('Indicator catalog')).toBeNull();
 expect(document.activeElement?.tagName).toBe('FIELDSET');
 fireEvent.change(screen.getByLabelText('3 RSI period'),{target:{value:'21'}});
 const selector=screen.getByLabelText('Selected indicator instance');selector.focus();
 fireEvent.change(selector,{target:{value:'ema'}});expect(document.activeElement).toBe(selector);
 fireEvent.change(selector,{target:{value:'volume'}});expect(document.activeElement).toBe(selector);
 expect(screen.getByLabelText('1 VOLUME placement')).toBeTruthy();
 fireEvent.change(selector,{target:{value:'rsi'}});expect((screen.getByLabelText('3 RSI period') as HTMLInputElement).value).toBe('21');
 fireEvent.click(screen.getByRole('button',{name:'Browse indicators'}));
 expect(screen.getByLabelText('Indicator catalog')).toBeTruthy();expect(document.activeElement).toBe(screen.getByLabelText('Search indicators'));
 fireEvent.click(screen.getByRole('button',{name:'Settings for 2 EMA'}));expect(screen.queryByLabelText('Indicator catalog')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Indicators (3)'}));expect(screen.getByLabelText('Indicator catalog')).toBeTruthy();
 expect(document.activeElement).toBe(screen.getByLabelText('Search indicators'));
});

it('restores an enabled toolbar initiator when saving disables the legend and permits read-only reopening',()=>{
 const settings={...emptySettings,instances:[item('ema')]};const apply=vi.fn();
 const view=render(<ChartIndicators settings={settings} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Settings for 1 EMA'}));
 fireEvent.change(screen.getByLabelText('1 EMA period'),{target:{value:'30'}});
 view.rerender(<ChartIndicators settings={settings} onApply={apply} busy={true} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Close indicator settings'}));
 const toggle=screen.getByRole('button',{name:'Indicators (1)'});
 expect(document.activeElement).toBe(toggle);expect((toggle as HTMLButtonElement).disabled).toBe(false);
 fireEvent.click(toggle);expect((screen.getByLabelText('1 EMA period') as HTMLInputElement).value).toBe('30');
 expect((screen.getByRole('button',{name:'Add EMA'}) as HTMLButtonElement).disabled).toBe(true);
 expect((screen.getByRole('button',{name:'Saving…'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Add EMA'}));expect(apply).not.toHaveBeenCalled();
});

it('exposes exactly 30 validated types with bounded pages and resets pagination on filtering',()=>{
 expect(indicatorCatalog).toHaveLength(30);
 expect(new Set(indicatorCatalog.map(entry=>entry.kind)).size).toBe(30);
 render(<ChartIndicators settings={emptySettings} onApply={vi.fn()} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Indicators (0)'}));
 expect(screen.getAllByRole('button',{name:/^Add /})).toHaveLength(9);
 fireEvent.click(screen.getByRole('button',{name:'Next indicators'}));
 expect(screen.getByRole('button',{name:'Add KELTNER'})).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Next indicators'}));
 expect(screen.getAllByRole('button',{name:/^Add /})).toHaveLength(9);
 fireEvent.click(screen.getByRole('button',{name:'Next indicators'}));
 expect(screen.getAllByRole('button',{name:/^Add /})).toHaveLength(3);
 fireEvent.change(screen.getByLabelText('Search indicators'),{target:{value:'keltner'}});
 fireEvent.click(screen.getByRole('button',{name:'Add KELTNER'}));
 expect(screen.getAllByRole('spinbutton').map(input=>input.getAttribute('aria-label'))).toEqual(['1 KELTNER period','1 KELTNER atr_period','1 KELTNER multiplier']);
 fireEvent.change(screen.getByLabelText('1 KELTNER multiplier'),{target:{value:'0'}});
 expect(screen.getByRole('alert').textContent).toContain('Keltner multiplier');
 fireEvent.change(screen.getByLabelText('1 KELTNER multiplier'),{target:{value:'2.5'}});
 expect(screen.queryByRole('alert')).toBeNull();
 fireEvent.change(screen.getByLabelText('Search indicators'),{target:{value:''}});
 expect(screen.getByRole('button',{name:'Add SMA'})).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Next indicators'}));
 fireEvent.change(screen.getByLabelText('Indicator category'),{target:{value:'Trend'}});
 expect(screen.getByRole('button',{name:'Add SMA'})).toBeTruthy();
 expect(screen.getAllByRole('button',{name:/^Add /})).toHaveLength(9);
});

it('places all twelve new formulas on their intended panes with exact ports and bounded percent axes',()=>{
 const chart={priceScale:primaryScale,addSeries:vi.fn((kind,options,pane)=>({kind,options,pane,setData:vi.fn(),createPriceLine:vi.fn(),priceScale:()=>({applyOptions:vi.fn()})})),panes:()=>[]};
 const kinds=indicatorCatalog.slice(9,21).map(entry=>entry.kind);
 const owned=installIndicatorSeries(chart,null,kinds.map(kind=>item(kind)),false);
 expect(owned).toHaveLength(16);
 for(const kind of ['wma','rma','vwma','donchian','keltner'])expect(owned.filter(row=>row.kind===kind).every(row=>row.series.pane===0)).toBe(true);
 for(const kind of ['donchian','keltner'])expect(owned.filter(row=>row.kind===kind).map(row=>row.port)).toEqual(['upper','middle','lower']);
 const separate=owned.filter(row=>!['wma','rma','vwma','donchian','keltner'].includes(row.kind));
 expect(new Set(separate.map(row=>row.series.pane)).size).toBe(7);
 expect(separate.every(row=>row.series.pane>0)).toBe(true);
 expect(owned.find(row=>row.kind==='williamsr')!.series.options.autoscaleInfoProvider().priceRange).toEqual({minValue:-100,maxValue:0});
 expect(owned.find(row=>row.kind==='roc')!.series.options.priceFormat.type).toBe('percent');
 expect(owned.find(row=>row.kind==='cmf')!.series.options.priceFormat.precision).toBe(4);
 expect(owned.find(row=>row.kind==='mfi')!.series.options.autoscaleInfoProvider().priceRange).toEqual({minValue:0,maxValue:100});
});

it('uses the existing indicator poll for HA without instances and rejects obsolete style responses',async()=>{
 let finish:(value:any)=>void=()=>{};
 mock.api.mockImplementation((command:string,p:any)=>command==='chart_indicator_settings'?Promise.resolve(emptySettings):new Promise(resolve=>{finish=resolve;}));
 const rows={current:[{time:0,open:10,high:12,low:9,close:11,volume:1}]};
 const {result,rerender,unmount}=renderHook(({style}:{style:'candles'|'heikin_ashi'|'line'})=>useChartIndicators('spot','BTCUSDT',1,true,rows,'bybit',0,style),{initialProps:{style:'heikin_ashi'}});
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('chart_indicator_read',expect.objectContaining({price_style:'heikin_ashi',revision:0}),expect.objectContaining({signal:expect.any(AbortSignal)})));
 rerender({style:'line'});
 await act(async()=>finish({status:'ready',price_style:'heikin_ashi',price_candles:[{time:60,close:999}]}));
 expect(result.current.result).toBeNull();
 expect(mock.api.mock.calls.filter(call=>call[0]==='chart_indicator_read')).toHaveLength(1);
 rerender({style:'heikin_ashi'});
 await waitFor(()=>expect(mock.api.mock.calls.filter(call=>call[0]==='chart_indicator_read')).toHaveLength(2));
 await act(async()=>finish({status:'ready',price_style:'heikin_ashi',price_candles:[{time:60,close:10}]}));
 expect(result.current.result.price_candles[0].close).toBe(10);
 unmount();
});

it('edits VWAP using UTC session names and aligned candle-open timestamps without saving a partial draft',()=>{
 const apply=vi.fn();render(<ChartIndicators minutes={60} settings={{...emptySettings,instances:[item('vwap')]}} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Settings for 1 VWAP'}));
 expect(screen.queryByLabelText('1 VWAP mode')).toBeNull();
 expect(screen.getByText(/UTC candle-open time/)).toBeTruthy();
 fireEvent.change(screen.getByLabelText('1 VWAP session'),{target:{value:'1'}});
 fireEvent.change(screen.getByLabelText('1 VWAP anchor UTC'),{target:{value:'2026-10-11T12:01:00'}});
 expect(screen.getByRole('alert').textContent).toContain('native 60-minute candle open');
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));expect(apply).not.toHaveBeenCalled();
 fireEvent.change(screen.getByLabelText('1 VWAP anchor UTC'),{target:{value:'2026-10-11T12:00:00'}});
 fireEvent.click(screen.getByRole('button',{name:'Close indicator settings'}));
 fireEvent.click(screen.getByRole('button',{name:'Settings for 1 VWAP'}));
 expect((screen.getByLabelText('1 VWAP anchor UTC') as HTMLInputElement).value).toBe('2026-10-11T12:00');
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 expect(apply.mock.calls[0][0][0].params).toEqual({mode:1,anchor:Date.parse('2026-10-11T12:00:00Z')/1000});
 expect(indicatorName(apply.mock.calls[0][0][0])).toContain('2026-10-11 12:00:00 UTC');
 fireEvent.change(screen.getByLabelText('1 VWAP session'),{target:{value:'0'}});
 expect(screen.queryByLabelText('1 VWAP anchor UTC')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));expect(apply.mock.calls[1][0][0].params).toEqual({mode:0,anchor:0});
});

it('validates SAR acceleration ordering and preserves fractional values',()=>{
 const apply=vi.fn();render(<ChartIndicators settings={{...emptySettings,instances:[item('sar')]}} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Settings for 1 SAR'}));
 fireEvent.change(screen.getByLabelText('1 SAR step'),{target:{value:'0.3'}});
 expect(screen.getByRole('alert').textContent).toContain('step ≤ max');
 fireEvent.change(screen.getByLabelText('1 SAR max'),{target:{value:'0.4'}});
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));expect(apply.mock.calls[0][0][0].params).toEqual({step:0.3,max:0.4});
});

it('installs advanced exact ports, readout-only direction, unbounded %B and SAR dots on raw price coordinates',()=>{
 const chart={priceScale:primaryScale,addSeries:vi.fn((kind,options,pane)=>({kind,options,pane,setData:vi.fn(),createPriceLine:vi.fn(),priceScale:()=>({applyOptions:vi.fn()})})),panes:()=>[]};
 const kinds=indicatorCatalog.slice(21,29).map(entry=>entry.kind);
 const owned=installIndicatorSeries(chart,null,kinds.map(kind=>item(kind)),false);
 expect(owned).toHaveLength(12);
 expect(owned.filter(row=>row.kind==='supertrend').map(row=>row.port)).toEqual(['up','down']);
 expect(owned.filter(row=>row.kind==='dmi').map(row=>row.port)).toEqual(['plus_di','minus_di','adx']);
 expect(owned.filter(row=>row.kind==='stochrsi').map(row=>row.port)).toEqual(['k','d']);
 for(const kind of ['supertrend','hma','vwap','sar'])expect(owned.filter(row=>row.kind===kind).every(row=>row.series.pane===0)).toBe(true);
 for(const kind of ['dmi','stochrsi','bbpercentb','bbwidth'])expect(owned.filter(row=>row.kind===kind).every(row=>row.series.pane>0)).toBe(true);
 const sar=owned.find(row=>row.kind==='sar')!;expect(sar.series.options).toMatchObject({lineVisible:false,pointMarkersVisible:true});
 expect(owned.find(row=>row.kind==='bbpercentb')!.series.options.autoscaleInfoProvider).toBeUndefined();
 updateIndicatorSeries(owned,{times:[60,120,180],columns:{supertrend:{up:[10,null,11],down:[null,12,null],direction:[1,-1,1]},sar:{value:[null,9,10]}}});
 expect(owned.find(row=>row.kind==='supertrend'&&row.port==='up')!.series.setData).toHaveBeenCalledWith([{time:60,value:10,color:'transparent'},{time:120},{time:180,value:11,color:'#7eabff'}]);
 expect(sar.series.setData).toHaveBeenCalledWith([{time:60},{time:120,value:9},{time:180,value:10}]);
});

it('keeps native UTC picker editing independent from numeric draft and accepts input events before blur',()=>{
 const apply=vi.fn();render(<ChartIndicators minutes={60} settings={{...emptySettings,instances:[{...item('vwap'),params:{mode:1,anchor:0}}]}} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Settings for 1 VWAP'}));
 const picker=screen.getByLabelText('1 VWAP anchor UTC') as HTMLInputElement;
 fireEvent.input(picker,{target:{value:''}});expect(screen.getByRole('alert')).toBeTruthy();
 expect(screen.getByLabelText('1 VWAP anchor UTC')).toBe(picker);
 fireEvent.input(picker,{target:{value:'2010-01-01T00:01:00'}});expect(screen.getByRole('alert').textContent).toContain('align exactly');
 fireEvent.input(picker,{target:{value:'2010-01-01T00:00:00'}});
 fireEvent.change(picker,{target:{value:'2010-01-01T00:00:00'}});fireEvent.blur(picker);
 expect(picker.value).toBe('2010-01-01T00:00');expect(screen.queryByRole('alert')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Close indicator settings'}));
 fireEvent.click(screen.getByRole('button',{name:'Settings for 1 VWAP'}));
 expect((screen.getByLabelText('1 VWAP anchor UTC') as HTMLInputElement).value).toBe('2010-01-01T00:00');
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 expect(apply.mock.calls[0][0][0].params.anchor).toBe(Date.parse('2010-01-01T00:00:00Z')/1000);
});

it('adds the 129th instance, preserves search and atomically applies every instance',()=>{
 const settings={...emptySettings,instances:Array.from({length:128},(_,index)=>({...item('ema','i'+index),visible:false}))};
 const apply=vi.fn();render(<ChartIndicators settings={settings} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Indicators (128)'}));
 const search=screen.getByLabelText('Search indicators');fireEvent.change(search,{target:{value:'ema'}});
 fireEvent.click(screen.getByRole('button',{name:'Add EMA'}));
 expect((search as HTMLInputElement).value).toBe('ema');
 expect(screen.getByLabelText('129 EMA period')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 expect(apply.mock.calls[0][0]).toHaveLength(129);
 expect(apply.mock.calls[0][0].filter((entry:any)=>entry.visible)).toHaveLength(1);
});
