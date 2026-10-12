import {it,expect,vi} from 'vitest';
import {legacyPaneLayout,reconcilePaneLayout,validatePaneLayout,visiblePanes,unsupportedPaneExtensions} from './chartPanes';
import {installIndicatorSeries} from './chartIndicatorSeries';
const row=(id:string,type:string,visible=true):any=>({id,type,visible,color:'#123abc',params:{period:14}});
const makeLayout=()=>({version:1 as const,price_weight:400,recorded_weight:155,panes:[{id:'momentum',weight:111,instance_ids:['m']},{id:'bounded',weight:222,instance_ids:['s','r']},{id:'distance',weight:333,instance_ids:['a']}]});
it('preserves identity, membership and weights across every visible subset and edit reconciliation without mutating input',()=>{
 const rows=[row('r','rsi'),row('s','stochastic'),row('a','atr'),row('m','macd'),row('v','volume')];
 const original=makeLayout();const before=JSON.stringify(original);
 for(let mask=0;mask<16;mask++){
  const changed=rows.map((r,i)=>({...r,visible:!!(mask&(1<<i))}));
  expect(validatePaneLayout(original,changed)).toBe('');
  expect(reconcilePaneLayout(original,changed)).toEqual(original);
  expect(visiblePanes(changed,original).map(p=>p.id)).toEqual(original.panes.filter(p=>p.instance_ids.some(id=>changed.some(r=>r.id===id&&r.visible))).map(p=>p.id));
 }
 const changed=reconcilePaneLayout(original,[...rows.filter(r=>r.id!=='s'),row('r2','rsi')]);
 expect(changed.panes[1].instance_ids).toEqual(['r','r2']);
 expect(JSON.stringify(original)).toBe(before);
});
it('rejects unsupported, incomplete and incompatible definitions without discarding other preset extensions',()=>{
 const rows=[row('r','rsi'),row('s','stochastic'),row('a','atr'),row('m','macd')];
 for(const value of [true,false,NaN,Infinity,-Infinity,0,-1,10000.01,'300',null])expect(validatePaneLayout({...makeLayout(),price_weight:value},rows)).not.toBe('');
 const value=makeLayout();value.panes[1].instance_ids.push('m');expect(validatePaneLayout(value,rows)).not.toBe('');
 const content={version:1,instances:rows,extensions:{pane_layout:makeLayout(),future:{v:2}}};
 const before=JSON.stringify(content);expect(unsupportedPaneExtensions(content)).toBe(true);expect(JSON.stringify(content)).toBe(before);
 expect(unsupportedPaneExtensions({version:1,instances:rows,extensions:{}})).toBe(false);
});
it('renders chosen physical order independently of instance order, hidden first pane and recorded visibility',()=>{
 const all=[row('r','rsi'),row('s','stochastic'),row('a','atr'),row('m','macd'),row('v','volume')];
 for(const visibleRecorded of [false,true])for(const hideFirst of [false,true])for(const reverse of [false,true]){
  const rows=(reverse?[...all].reverse():all).map(r=>({...r,visible:r.id==='m'?!hideFirst:true}));
  const panes:any[]=[{setStretchFactor:vi.fn()}];const assignments:any[]=[];
  const primary={options:()=>({mode:1,autoScale:false,scaleMargins:{top:.1,bottom:.2}}),applyOptions:vi.fn()};
  const scale={applyOptions:vi.fn()};
  const chart:any={panes:()=>panes,priceScale:()=>primary,addSeries:(_kind:any,options:any,index:number)=>{
   expect(index).toBeLessThanOrEqual(panes.length);if(index===panes.length)panes.push({setStretchFactor:vi.fn()});
   const series={priceScale:()=>scale,createPriceLine:vi.fn(),index,options};assignments.push(series);return series;
  }};
  const recorded={moveToPane:(index:number)=>{expect(index).toBe(visibleRecorded?panes.length:0);if(index===panes.length)panes.push({setStretchFactor:vi.fn()});},priceScale:()=>scale};
  const owned=installIndicatorSeries(chart,recorded,rows as any,visibleRecorded,makeLayout());
  const target=hideFirst?1:2;
  expect(owned.filter(r=>['r','s'].includes(r.id)).every(r=>r.series.index===target)).toBe(true);
  expect(owned.find(r=>r.id==='a')?.series.index).toBe(target+1);
  expect(owned.find(r=>r.id==='v')?.series.options.priceScaleId).toBe('volume-v');
  expect(panes.map(p=>p.setStretchFactor.mock.calls.at(-1)[0])).toEqual([400,...(hideFirst?[]:[111]),222,333,...(visibleRecorded?[155]:[])]);
  expect(primary.applyOptions.mock.calls.every(([v])=>v.mode===1&&v.autoScale===false)).toBe(true);
 }
});
