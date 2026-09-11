export type NodeKind = 'price' | 'constant' | 'sma' | 'ema' | 'rsi' | 'bb' | 'macd' | 'atr' | 'compare' | 'cross_above' | 'cross_below' | 'and' | 'or' | 'not';
export interface IRNode { id: string; type: NodeKind; inputs: Record<string,string>; params: Record<string,number|string> }
export const outputNames = ['entry_long','exit_long','entry_short','exit_short'] as const;
export type OutputName = typeof outputNames[number];
export interface Graph { version: 1; nodes: IRNode[]; outputs: Record<OutputName,string|null> }
export type Layout = Record<string,{x:number;y:number}>;
export type Profile = Record<string,string|number>;
export const labels: Record<string,string> = { price:'OHLCV', constant:'Value', sma:'SMA', ema:'EMA', rsi:'RSI', bb:'Bollinger Bands', macd:'MACD', atr:'ATR', compare:'Compare', cross_above:'Cross Above', cross_below:'Cross Below', and:'AND', or:'OR', not:'NOT', entry_long:'Entry Long',exit_long:'Exit Long',entry_short:'Entry Short',exit_short:'Exit Short' };
const numericSource = {source:'number'};
export const catalog: Record<NodeKind,{inputs:Record<string,string>;outputs:Record<string,string>;params:Record<string,string|number>}> = {
  price:{inputs:{},outputs:{value:'number'},params:{field:'close'}},
  constant:{inputs:{},outputs:{value:'number'},params:{value:100}},
  sma:{inputs:numericSource,outputs:{value:'number'},params:{period:20}},
  ema:{inputs:numericSource,outputs:{value:'number'},params:{period:20}},
  rsi:{inputs:numericSource,outputs:{value:'number'},params:{period:14}},
  bb:{inputs:numericSource,outputs:{upper:'number',middle:'number',lower:'number'},params:{period:20,deviations:2}},
  macd:{inputs:numericSource,outputs:{macd:'number',signal:'number',histogram:'number'},params:{fast:12,slow:26,signal:9}},
  atr:{inputs:{},outputs:{value:'number'},params:{period:14}},
  compare:{inputs:{left:'number',right:'number'},outputs:{value:'boolean'},params:{operator:'>'}},
  cross_above:{inputs:{left:'number',right:'number'},outputs:{value:'boolean'},params:{}},
  cross_below:{inputs:{left:'number',right:'number'},outputs:{value:'boolean'},params:{}},
  and:{inputs:{left:'boolean',right:'boolean'},outputs:{value:'boolean'},params:{}},
  or:{inputs:{left:'boolean',right:'boolean'},outputs:{value:'boolean'},params:{}},
  not:{inputs:{source:'boolean'},outputs:{value:'boolean'},params:{}},
};
export const defaultProfile: Profile = {
  market:'spot',symbol:'BTCUSDT',capital:'1000',leverage:'1',sizing:'fixed',allocation:'100',fee_rate:'0.001',slippage:'0',
  stop_loss:'0',take_profit:'0',tick_size:'0.01',quantity_step:'0.001',min_quantity:'0.001',max_quantity:'1000000000',
  min_notional:'1',max_notional:'1000000',maintenance_rate:'0.005',primary_minutes:60,evaluation:'closed',path:'OLHC',
  funding_mode:'history',mark_mode:'history',gap_policy:'reject',tier_assumption:'Manual constant tier; historical risk tiers are not known',version:2,
};
export function exampleGraph(): Graph {
  return {version:1,nodes:[
    {id:'close',type:'price',inputs:{},params:{field:'close'}},
    {id:'mean',type:'sma',inputs:{source:'close.value'},params:{period:2}},
    {id:'above',type:'compare',inputs:{left:'close.value',right:'mean.value'},params:{operator:'>'}},
    {id:'below',type:'compare',inputs:{left:'close.value',right:'mean.value'},params:{operator:'<'}},
  ],outputs:{entry_long:'above.value',exit_long:'below.value',entry_short:null,exit_short:null}};
}
export function canConnect(graph:Graph,source:string,sourcePort:string,target:string,targetPort:string):boolean {
  const from = graph.nodes.find(n=>n.id===source);
  if (!from || source===target) return false;
  const sourceType = catalog[from.type].outputs[sourcePort];
  if (target.startsWith('out:')) return outputNames.includes(target.slice(4) as OutputName) && sourceType==='boolean';
  const to = graph.nodes.find(n=>n.id===target);
  if (!to || !sourceType || catalog[to.type].inputs[targetPort]!==sourceType) return false;
  // Edges are source -> target. A path target -> source would create a cycle.
  const visit = (id:string,seen:Set<string>):boolean => {
    if (id===source) return true;
    if (seen.has(id)) return false;
    seen.add(id);
    return graph.nodes.filter(n=>Object.values(n.inputs).some(ref=>ref.startsWith(id+'.'))).some(n=>visit(n.id,seen));
  };
  return !visit(target,new Set());
}
