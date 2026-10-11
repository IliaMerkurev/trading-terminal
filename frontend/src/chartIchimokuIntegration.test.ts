import {it,expect} from 'vitest';
import {acceptedIchimoku,retainIchimokuRawAnchor} from './chartIchimokuIntegration';
import {defaults,type ChartIndicator} from './ChartIndicators';
const item:ChartIndicator={id:'cloud',type:'ichimoku',params:{...defaults.ichimoku,displacement:1},color:'#123456',visible:true};
const rows=[0,60].map(time=>({time,open:1,high:2,low:0,close:1,volume:1}));
const context={source:'bybit',market:'spot',symbol:'BTCUSDT',minutes:1,revision:7};
function result(){return {status:'ready',origin:{generation:3,time:0},projections:{version:1,contract:'ichimoku-raw-ordinal-v1',raw_times:[60,120],horizon:120,context:{source:'bybit',market:'spot',symbol:'BTCUSDT',minutes:1,start:0,end:60,settings_revision:7,generation:3,origin:0},instances:{cloud:{displacement:1,source_logical:[0,1],computed_at:[60,120],segment:[0,0],senkou_a:[1,2],senkou_b:[0,1],chikou:[null,2],senkou_plotted_at:[120,180],chikou_plotted_at:[null,60],senkou_estimated:[false,true]}}}};}
it('accepts only the exact source/window/revision/origin/generation projection context',()=>{
 expect(acceptedIchimoku(result(),item,rows,context).senkou_a).toHaveLength(2);
 for(const key of ['source','market','symbol','minutes','start','end','settings_revision','generation','origin']){
  const value=result();(value.projections.context as any)[key]='stale';expect(acceptedIchimoku(value,item,rows,context).senkou_a).toHaveLength(0);
 }
 const value=result();value.projections.horizon=180;expect(acceptedIchimoku(value,item,rows,context).senkou_a).toHaveLength(0);
 expect(acceptedIchimoku(result(),{...item,visible:false},rows,context).senkou_a).toHaveLength(0);
 expect(acceptedIchimoku(result(),item,rows.slice(1),context).senkou_a).toHaveLength(0);
});
it('only constrains right-side projection-only pan, retaining width and the final raw candle',()=>{
 expect(retainIchimokuRawAnchor({from:310,to:350},300,true)).toEqual({from:298.5,to:338.5});
 for(const enabled of [true,false])expect(retainIchimokuRawAnchor({from:250,to:350},300,enabled)).toEqual({from:250,to:350});
 expect(retainIchimokuRawAnchor({from:310,to:350},300,false)).toEqual({from:310,to:350});
});
