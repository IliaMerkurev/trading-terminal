import {it,expect} from 'vitest';
import {chartPriceData} from './chartPriceData';
import {indicatorWindow} from './chartWindow';
const rows=[{time:0,open:100,high:110,low:90,close:108,volume:1},{time:60,open:108,high:120,low:105,close:115,volume:2}];
it('never substitutes raw prices for missing HA and uses backend UTC interval-end prices without recurrence',()=>{
 const result={price_style:'heikin_ashi',price_candles:[{time:60,open:104,high:110,low:90,close:102,status:'confirmed'},{time:120,status:'unavailable'}]};
 expect(chartPriceData(rows,1,'heikin_ashi',result)).toEqual([{time:60,open:104,high:110,low:90,close:102},{time:120}]);
 expect(chartPriceData(rows,1,'heikin_ashi',null)).toEqual([{time:60},{time:120}]);
 expect(chartPriceData(rows,60,'heikin_ashi',result)).toEqual([{time:3600},{time:3660}]);
 expect(chartPriceData(rows,1,'line',result)).toEqual([{time:60},{time:120}]);
 expect(chartPriceData(rows,1,'candles',result)).toEqual(rows.map(row=>({...row,time:row.time+60})));
 expect(rows[0].close).toBe(108);
});
it('filters additive price candles independently of indicator times on Return and rollover',()=>{
 const result={times:[60,120,180],columns:{x:{value:[1,2,3]}},price_style:'heikin_ashi',price_candles:[{time:60,close:1},{time:120,close:2},{time:999999,close:3}]};
 expect(indicatorWindow(result,rows.slice(1),1)).toMatchObject({times:[120],columns:{x:{value:[2]}},price_candles:[{time:120,close:2}]});
 expect(indicatorWindow(result,[{...rows[0],time:6000}],1)).toMatchObject({times:[],price_candles:[]});
});
