import {it,expect,vi,beforeEach} from 'vitest';
const {readFileSync}=await vi.importActual<{readFileSync(path:string,encoding:'utf8'):string}>('node:fs');
const marketStyles=readFileSync('frontend/src/market-workspace.css','utf8');
import {render,screen,fireEvent,waitFor,renderHook,act} from '@testing-library/react';
import ChartIndicators,{emptySettings,defaults,indicatorName,type ChartIndicator} from './ChartIndicators';
import {installIndicatorSeries,updateIndicatorSeries} from './chartIndicatorSeries';
import {useChartIndicators} from './useChartIndicators';
const mock=vi.hoisted(()=>({api:vi.fn()}));
vi.mock('./api',()=>({api:mock.api}));
const primaryScale = () => ({options: () => ({scaleMargins: {top: 0.2, bottom: 0.1}}), applyOptions: vi.fn()});
const item=(type:ChartIndicator['type'],id:string=type):ChartIndicator=>({id,type,params:{...defaults[type]},color:'#7eabff',visible:true,...(type==='volume'?{placement:'pane' as const}:{})});
beforeEach(()=>{mock.api.mockReset();});

it('adds duplicate EMA instances and applies parameters, visibility and removal atomically',()=>{
 const apply=vi.fn();render(<ChartIndicators settings={emptySettings} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Indicators (0)'}));
 fireEvent.click(screen.getByRole('button',{name:'Add indicator'}));fireEvent.click(screen.getByRole('button',{name:'Add indicator'}));
 const first=screen.getByLabelText('1 EMA period');
 fireEvent.change(first,{target:{value:'0'}});fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));expect(apply).not.toHaveBeenCalled();
 expect(screen.getByRole('alert').textContent).toContain('whole numbers');
 fireEvent.change(first,{target:{value:'9'}});fireEvent.click(screen.getByLabelText('2 EMA visible'));
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 expect(apply.mock.calls[0][0]).toHaveLength(2);expect(apply.mock.calls[0][0][0].params.period).toBe(9);expect(apply.mock.calls[0][0][1].visible).toBe(false);
 expect(apply.mock.calls[0][0][0].id).not.toBe(apply.mock.calls[0][0][1].id);
 fireEvent.click(screen.getByRole('button',{name:'Remove 1 EMA'}));fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));expect(apply.mock.calls[1][0]).toHaveLength(1);
});

it('separates price, RSI fixed scale, MACD, volume and recorded IR panes; removes no unrelated series',()=>{
 const added:any[]=[];const chart={priceScale:primaryScale,addSeries:vi.fn((kind,options,pane)=>{const s={kind,options,pane,setData:vi.fn(),createPriceLine:vi.fn(),priceScale:()=>({applyOptions:vi.fn()})};added.push(s);return s;}),panes:()=>[]};const recorded={moveToPane:vi.fn()};
 const items=[item('ema'),item('ema','second'),item('sma'),item('bb'),item('rsi'),item('macd'),item('volume')];
 const owned=installIndicatorSeries(chart,recorded,items,true);
 expect(owned).toHaveLength(11);expect(added.filter(s=>s.pane===0)).toHaveLength(6);
 const rsi=added.find(s=>s.options.title.startsWith('RSI'));expect(rsi.pane).toBe(1);expect(rsi.options.autoscaleInfoProvider().priceRange).toEqual({minValue:0,maxValue:100});expect(rsi.createPriceLine.mock.calls.map((c:any[])=>c[0].price)).toEqual([30,70]);
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
 fireEvent.click(screen.getByRole('button',{name:'Save fixture'}));expect((await screen.findByRole('alert')).textContent).toContain('Settings not saved');
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
  '1 BB period','1 BB deviations','2 MACD fast','2 MACD slow','2 MACD signal']);
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
 expect(added.filter(series => series.options.title.startsWith('RSI')).map(series => series.pane)).toEqual([1, 1]);
 expect(scales.get(1)!.options().scaleMargins).toEqual({top: 0, bottom: 0});
 for (const index of [0, 2, 3, 4]) expect(scales.get(index)!.options().scaleMargins).toEqual(normalMargins);
 expect(defaults).toEqual(normalMargins);
 // MarketChart removes owned panes before rebuilding. Re-added RSI gets the
 // new pane's API; earlier and later non-RSI scales retain ordinary padding.
 for (const index of [1, 2, 3, 4]) scales.delete(index);
 installIndicatorSeries(chart, null, [item('volume'), item('rsi', 'readded'), item('macd')], false);
 expect(scales.get(2)!.options().scaleMargins).toEqual({top: 0, bottom: 0});
 for (const index of [0, 1, 3]) expect(scales.get(index)!.options().scaleMargins).toEqual(normalMargins);
 expect(added.find(series => series.options.title.startsWith('RSI'))!.options.autoscaleInfoProvider()).toEqual({priceRange: {minValue: 0, maxValue: 100}});
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
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('chart_indicator_read',expect.objectContaining({source:'okx'})));
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
 for(const kind of ['atr','stochastic','obv']){fireEvent.change(screen.getByLabelText('Add indicator type'),{target:{value:kind}});fireEvent.click(screen.getByRole('button',{name:'Add indicator'}));}
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
