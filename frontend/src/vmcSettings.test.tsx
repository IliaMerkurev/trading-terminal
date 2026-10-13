import {expect,it,vi} from 'vitest';
import {fireEvent,render,screen} from '@testing-library/react';
import ChartIndicators,{defaults,emptySettings,parameterOrder,validateIndicators,type ChartIndicator} from './ChartIndicators';
import {vmcDefaults,validateVmcParams} from './vmcSettings';
import {indicatorCatalog} from './indicatorCatalog';
import {installIndicatorSeries,updateIndicatorSeries} from './chartIndicatorSeries';
import {indicatorWindow} from './chartWindow';
const item=(type:'vmc_cipher_a'|'vmc_cipher_b'|'vmc_swing',id=type):ChartIndicator=>({id,type,params:{...defaults[type]},visible:true,color:'#7eabff'});
it('registers all 33 types with native boolean/source fields and exact canonical parameter order',()=>{
 expect(indicatorCatalog).toHaveLength(33);
 for(const kind of Object.keys(vmcDefaults) as (keyof typeof vmcDefaults)[]) {
  expect(parameterOrder[kind]).toEqual(Object.keys(vmcDefaults[kind]));
  expect(validateIndicators([item(kind)])).toBe('');
 }
 expect(defaults.vmc_cipher_b).toMatchObject({average:12,source:'hlc3',flow_offset:2.5,wt_regular:true,wt_secondary:true,wt_hidden:false,stoch_log:true});
 expect(defaults.vmc_cipher_a).toMatchObject({average:13,ema1:5,ema2:11,ema3:15,ema4:18,ema5:21,ema6:24,ema7:28,ema8:34});
 expect(defaults.vmc_swing).toEqual({source:'close',period:20,multiplier:3.5});
});
it('accepts signed fractions, rejects wrong types, invalid keys, inverted thresholds and nonfinite values even when hidden',()=>{
 const good={...defaults.vmc_cipher_b,oversold:-55.25,flow_offset:-1.5};
 expect(validateVmcParams('vmc_cipher_b',good)).toBe('');
 for (const bad of [{stoch_log:1},{source:'volume'},{channel:2.5},{channel:true},{flow_offset:Infinity},{flow_offset:NaN},{overbought:-100},{wt_secondary_top:-50},{rsi_div_top:29},{unexpected:1}]) expect(validateVmcParams('vmc_cipher_b',{...good,...bad} as any)).not.toBe('');
 expect(validateVmcParams('vmc_swing',{...defaults.vmc_swing,multiplier:0})).not.toBe('');
 expect(validateIndicators([{...item('vmc_cipher_b'),visible:false,params:{...good,channel:0}}])).not.toBe('');
 expect(validateIndicators(Array.from({length:40},(_,i)=>item('vmc_cipher_a',String(i) as any)))).toBe('');
});
it('searches VMC, edits grouped switches/signed fractions/sources and applies atomically',()=>{
 const apply=vi.fn();render(<ChartIndicators settings={emptySettings} onApply={apply} busy={false} error=""/>);
 fireEvent.click(screen.getByRole('button',{name:'Indicators (0)'}));
 fireEvent.change(screen.getByLabelText('Search indicators'),{target:{value:'VMC Cipher B'}});
 fireEvent.click(screen.getByRole('button',{name:'Add VMC B'}));
 fireEvent.change(screen.getByLabelText('1 VMC B oversold'),{target:{value:'-61.5'}});
 fireEvent.click(screen.getByLabelText('1 VMC B stoch_log'));
 fireEvent.change(screen.getByLabelText('1 VMC B source'),{target:{value:'ohlc4'}});
 fireEvent.click(screen.getByRole('button',{name:'Apply indicators'}));
 expect(apply.mock.calls[0][0][0].params).toMatchObject({oversold:-61.5,stoch_log:false,source:'ohlc4'});
 expect(screen.getByText(/VMC flow is a candle-body proxy/)).toBeTruthy();
});
it('renders signed waves on a normal auxiliary pane, eight price EMAs and Swing bands without changing primary scale',()=>{
 const primary={mode:1,autoScale:false,scaleMargins:{top:.1,bottom:.15}},restore=vi.fn();
 const chart={priceScale:()=>({options:()=>primary,applyOptions:restore}),panes:()=>[],addSeries:vi.fn((kind,options,pane)=>({kind,options,pane,setData:vi.fn(),createPriceLine:vi.fn(),priceScale:()=>({applyOptions:vi.fn()})}))};
 const recorded={moveToPane:vi.fn()};
 const owned=installIndicatorSeries(chart,recorded,[item('vmc_cipher_b'),item('vmc_cipher_a'),item('vmc_swing'),{...item('vmc_cipher_b','hidden' as any),visible:false}],true);
 expect(owned).toHaveLength(18);expect(recorded.moveToPane).toHaveBeenLastCalledWith(2);
 expect(owned.filter(x=>x.kind==='vmc_cipher_b').every(x=>x.series.pane===1 && !x.series.options.autoscaleInfoProvider)).toBe(true);
 expect(owned.filter(x=>x.kind!=='vmc_cipher_b').every(x=>x.series.pane===0)).toBe(true);
 expect(restore).toHaveBeenCalledWith(primary);
 const result={times:[60,120,240],columns:{vmc_cipher_b:{wt1:[-20,30,40],flow:[-4,2,3]},vmc_swing:{filter:[10,11,12]},vmc_cipher_a:{ema1:[10,11,12]}},regimes:{vmc_swing:[-1,1,0],vmc_cipher_a:[1,-1,1]}};
 updateIndicatorSeries(owned,result,1);
 expect(owned.find(x=>x.port==='wt1')!.series.setData.mock.calls[0][0][1].topLineColor).toBe('transparent');
 expect(owned.find(x=>x.port==='flow')!.series.setData.mock.calls[0][0][0].color).toBe('#e78389');
 expect(owned.find(x=>x.port==='ema1')!.series.setData.mock.calls[0][0][1].color).toBe('transparent');
 const clipped=indicatorWindow(result,[{time:180,open:10,high:12,low:9,close:11,volume:1}],1);
 expect(clipped.regimes).toEqual({vmc_swing:[0],vmc_cipher_a:[1]});
});

it('uses readable VMC short labels instead of internal identifiers',async()=>{
 const {indicatorShortLabel}=await import('./indicatorCatalog');
 expect(indicatorShortLabel('vmc_cipher_b')).toBe('VMC B');
 expect(indicatorShortLabel('vmc_cipher_a')).toBe('VMC A');
 expect(indicatorShortLabel('vmc_swing')).toBe('Swing');
});
