import {describe,it,expect} from 'vitest';
import {createNode,deleteNodes,duplicateNodes,graphProblems,searchNodes,shortcutKey} from './editor';
import {exampleGraph,catalog} from './model';
import {GraphHistory} from './useGraphHistory';
describe('graph editing contracts',()=>{
 it('recognizes physical shortcuts under non-Latin layouts',()=>{expect(shortcutKey({key:'я',code:'KeyZ'})).toBe('z');expect(shortcutKey({key:'н',code:'KeyY'})).toBe('y');expect(shortcutKey({key:'в',code:'KeyD'})).toBe('d');});
 it('deletes multiple nodes and connections in one reversible transaction, preserving outputs',()=>{
  const graph=exampleGraph(),layout={close:{x:10,y:20},above:{x:50,y:60},'out:entry_long':{x:90,y:80}};
  const h=new GraphHistory({graph,layout});const result=deleteNodes(graph,layout,['close','above','out:entry_long'])!;
  h.change(result);expect(h.past).toHaveLength(1);expect(result.graph.nodes.map(n=>n.id)).toEqual(['mean','below']);
  expect(result.graph.nodes[0].inputs.source).toBe('');expect(result.graph.nodes[1].inputs.left).toBe('');expect(result.graph.outputs.entry_long).toBeNull();
  expect(result.layout).toEqual({'out:entry_long':{x:90,y:80}});expect(graph.nodes).toHaveLength(4);
  h.undo();expect(h.current).toEqual({graph,layout});h.redo();expect(h.current).toEqual(result);
  expect(deleteNodes(graph,layout,['out:entry_long'])).toBeNull();
 });
 it('searches full names and abbreviations without fixed outputs',()=>{expect(searchNodes(' exponential moving ')).toEqual(['ema']);expect(searchNodes('rSi')).toEqual(['rsi']);expect(searchNodes('Entry Long')).toEqual([]);expect(searchNodes('')).toHaveLength(19);});
 it('creates the five read-only position sources without writable inputs',()=>{const names=searchNodes('read-only');expect(names).toEqual(['position_side','position_size','position_avg_entry','position_unrealized_pnl_pct','bars_since_entry']);for(const kind of names){const n=createNode(kind);expect(n.inputs).toEqual({});expect(n.params).toEqual({});expect(catalog[kind].outputs).toEqual({value:'number'});}expect(searchNodes('weighted average')).toEqual(['position_avg_entry']);});
 it('creates independent defaults and remaps only internal duplicate edges',()=>{const a=createNode('ema'),b=createNode('ema');a.params.period=3;expect(b.params.period).toBe(20);expect(a.id).not.toBe(b.id);const graph=exampleGraph();const copy=duplicateNodes(graph,{close:{x:10,y:20}},['close','mean','out:entry_long']);expect(copy.selected).toHaveLength(2);expect(copy.graph.nodes[5].inputs.source).toBe(copy.selected[0]+'.value');expect(copy.graph.outputs).toEqual(graph.outputs);expect(graph.nodes).toHaveLength(4);expect(copy.layout[copy.selected[0]]).toEqual({x:50,y:60});});
 it('groups an entire drag, bounds undo and invalidates redo after editing',()=>{const h=new GraphHistory({graph:exampleGraph(),layout:{}},2);h.begin();for(let x=1;x<=10;x++)h.change({graph:h.current.graph,layout:{close:{x,y:0}}});h.end();expect(h.past).toHaveLength(1);h.undo();expect(h.current.layout).toEqual({});h.redo();expect(h.current.layout.close.x).toBe(10);h.undo();h.change({graph:h.current.graph,layout:{close:{x:22,y:0}}});expect(h.future).toHaveLength(0);h.change({graph:h.current.graph,layout:{}});h.change({graph:h.current.graph,layout:{close:{x:1,y:1}}});expect(h.past).toHaveLength(2);h.reset({graph:exampleGraph(),layout:{}});expect(h.past).toHaveLength(0);});
 it('locates disconnected inputs and invalid parameters without changing drafts',()=>{const g=exampleGraph();g.nodes[1].inputs.source='';g.nodes[1].params.period=0;const problems=graphProblems(g);expect(problems).toEqual(expect.arrayContaining([expect.objectContaining({node:'mean',field:'source'}),expect.objectContaining({node:'mean',field:'period'})]));expect(g.nodes[1].inputs.source).toBe('');});
});
