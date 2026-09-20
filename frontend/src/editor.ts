import {catalog,labels,outputNames,type Graph,type Layout,type NodeKind} from './model';
export const fullNames:Record<NodeKind,string>={roc:'Rate of Change (fraction)',multiply:'Multiply two numeric values',price:'Open High Low Close Volume',constant:'Numeric Constant',sma:'Simple Moving Average',ema:'Exponential Moving Average',rsi:'Relative Strength Index',bb:'Bollinger Bands',macd:'Moving Average Convergence Divergence',atr:'Average True Range',compare:'Compare',cross_above:'Cross Above',cross_below:'Cross Below',and:'Boolean AND',or:'Boolean OR',not:'Boolean NOT',position_side:'Read-only side: short -1, flat 0, long 1',position_size:'Read-only remaining position quantity',position_avg_entry:'Read-only weighted average entry price',position_unrealized_pnl_pct:'Read-only unleveraged last-price change from entry',bars_since_entry:'Read-only elapsed strategy bars since first entry'};
export const groups:Record<NodeKind,string>={roc:'Indicators',multiply:'Math',price:'Sources',constant:'Sources',sma:'Indicators',ema:'Indicators',rsi:'Indicators',bb:'Indicators',macd:'Indicators',atr:'Indicators',compare:'Conditions',cross_above:'Conditions',cross_below:'Conditions',and:'Logic',or:'Logic',not:'Logic',position_side:'Position',position_size:'Position',position_avg_entry:'Position',position_unrealized_pnl_pct:'Position',bars_since_entry:'Position'};
export function searchNodes(query:string){const q=query.trim().toLowerCase();return (Object.keys(catalog) as NodeKind[]).filter(k=>`${k} ${labels[k]} ${fullNames[k]}`.toLowerCase().includes(q));}
export function createNode(kind:NodeKind){return {id:`${kind}_${crypto.randomUUID().replaceAll('-','')}`,type:kind,inputs:Object.fromEntries(Object.keys(catalog[kind].inputs).map(p=>[p,''])),params:structuredClone(catalog[kind].params)};}
export function duplicateNodes(graph:Graph,layout:Layout,selected:string[]){
  const next=structuredClone(graph),positions=structuredClone(layout),copies=graph.nodes.filter(n=>selected.includes(n.id));
  const ids=new Map(copies.map(n=>[n.id,createNode(n.type).id]));
  for(const node of copies){const copy=structuredClone(node);copy.id=ids.get(node.id)!;for(const [port,ref] of Object.entries(copy.inputs)){const [id,p]=ref.split('.');if(ids.has(id))copy.inputs[port]=`${ids.get(id)}.${p}`;}next.nodes.push(copy);const index=graph.nodes.findIndex(n=>n.id===node.id);const pos=layout[node.id]??{x:60+(index%3)*260,y:70+Math.floor(index/3)*180};positions[copy.id]={x:pos.x+40,y:pos.y+40};}
  return {graph:next,layout:positions,selected:[...ids.values()]};
}
/** One atomic edit for keyboard and context-menu deletion. Fixed outputs are not IR nodes. */
export function deleteNodes(graph:Graph,layout:Layout,selected:string[]){
  const removed=new Set(graph.nodes.filter(n=>selected.includes(n.id)).map(n=>n.id));
  if(!removed.size)return null;
  const next=structuredClone(graph),positions=structuredClone(layout);
  next.nodes=next.nodes.filter(n=>!removed.has(n.id));
  for(const n of next.nodes)for(const [port,ref] of Object.entries(n.inputs))if(removed.has(ref.split('.')[0]))n.inputs[port]='';
  for(const output of outputNames)if(removed.has(next.outputs[output]?.split('.')[0]??''))next.outputs[output]=null;
  for(const id of removed)delete positions[id];
  return {graph:next,layout:positions};
}
export type GraphProblem={node:string;field:string;message:string};
export function graphProblems(graph:Graph):GraphProblem[]{
  const problems:GraphProblem[]=[];const add=(node:string,field:string,message:string)=>problems.push({node,field,message});
  if(!graph.nodes.length||graph.nodes.length>128)add('','','Use 1–128 nodes');
  const nodes=new Map(graph.nodes.map(n=>[n.id,n]));
  const refCheck=(id:string,port:string,ref:string|null,expected:string)=>{const [source,output]=ref?.split('.')??[];const n=nodes.get(source);if(!n||catalog[n.type]?.outputs[output]!==expected)add(id,port,`Connect ${port} to a ${expected} output`);};
  for(const n of graph.nodes){
    for(const [p,type] of Object.entries(catalog[n.type].inputs))refCheck(n.id,p,n.inputs[p],type);
    for(const [p,v] of Object.entries(n.params)){
      if(['period','fast','slow','signal'].includes(p)&&(!Number.isInteger(v)||Number(v)<1||Number(v)>10000))add(n.id,p,'Period must be an integer from 1 to 10000');
      if(p==='value'&&!Number.isFinite(v))add(n.id,p,'Value must be finite');
      if(p==='deviations'&&(!Number.isFinite(v)||Number(v)<=0||Number(v)>10))add(n.id,p,'Deviations must be in (0, 10]');
    }
    if(n.type==='macd'&&Number(n.params.fast)>=Number(n.params.slow))add(n.id,'fast','MACD fast period must be below slow');
  }
  for(const output of outputNames)if(graph.outputs[output])refCheck(`out:${output}`,'signal',graph.outputs[output],'boolean');
  const visiting=new Set<string>(),done=new Set<string>();
  function visit(id:string){if(visiting.has(id)){add(id,'inputs','Remove the cyclic connection');return;}if(done.has(id))return;visiting.add(id);for(const ref of Object.values(nodes.get(id)?.inputs??{})){const from=ref.split('.')[0];if(nodes.has(from))visit(from);}visiting.delete(id);done.add(id);}
  graph.nodes.forEach(n=>visit(n.id));return problems;
}
export function isTextEditing(target:EventTarget|null){return target instanceof HTMLElement&&!!target.closest('input,textarea,select,[contenteditable="true"],[role="textbox"]');}
export function shortcutKey(event:Pick<KeyboardEvent,'key'|'code'>){return /^Key[A-Z]$/.test(event.code)?event.code.slice(3).toLowerCase():event.key.toLowerCase();}
