import {it,expect} from 'vitest';
import {chartPoints} from './RunChart';
it('plots stored availability values without recomputing an indicator from candles',()=>{
  const data={series:{candles:[{time:0,open:100,high:110,low:90,close:105}],indicators:[{time:60,values:{'mean.value':73.125}},{time:120,values:{'mean.value':null}}],equity:[{time_ns:20e9,equity:'998'},{time_ns:40e9,equity:'1003'}]}};
  const points=chartPoints(data,'mean.value');
  expect(points.candles[0].time).toBe(60);
  expect(points.indicator).toEqual([{time:60,value:73.125}]);
  expect(points.equity).toEqual([{time:60,value:1003}]);
});
it('labels daily source candles at close and retains recorded indicator values',()=>{
 const points=chartPoints({interval_seconds:86400,series:{candles:[{time:0,open:10,high:12,low:9,close:11}],indicators:[{time:86400,values:{channel:9.75}}],equity:[{time_ns:28800e9,equity:'995'},{time_ns:86399999999999,equity:'1002'}]}},'channel');
 expect(points.candles[0].time).toBe(86400);
 expect(points.indicator).toEqual([{time:86400,value:9.75}]);
 expect(points.equity).toEqual([{time:86400,value:1002}]);
});
