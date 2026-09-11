import { describe,it,expect } from 'vitest';
import { canConnect,exampleGraph } from './model';
describe('graph connections',()=>{
  it('rejects numerical signals and cycles while accepting shared boolean outputs',()=>{
    const graph=exampleGraph();
    expect(canConnect(graph,'close','value','out:entry_long','signal')).toBe(false);
    expect(canConnect(graph,'above','value','out:exit_short','signal')).toBe(true);
    expect(canConnect(graph,'above','value','mean','source')).toBe(false);
    graph.nodes.push({id:'second',type:'ema',inputs:{source:'mean.value'},params:{period:5}});
    expect(canConnect(graph,'second','value','mean','source')).toBe(false);
    expect(canConnect(graph,'close','value','second','source')).toBe(true);
  });
});
