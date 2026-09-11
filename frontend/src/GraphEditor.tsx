import { useEffect, useMemo, useState } from 'react';
import { ReactFlow, Background, Controls, Handle, Position, type ReactFlowInstance, type Connection, type NodeProps, type Node, type Edge, type NodeChange } from '@xyflow/react';
import NodeMenu from './NodeMenu';
import {duplicateNodes,isTextEditing} from './editor';
import '@xyflow/react/dist/style.css';
import { catalog, labels, outputNames, canConnect, type Graph, type Layout, type NodeKind, type OutputName } from './model';

type FlowData = { label:string; kind:NodeKind|'output'; params:Record<string,number|string> };
function StrategyNode({data,selected}:NodeProps<Node<FlowData>>) {
  const inputs = data.kind==='output' ? {signal:'boolean'} : catalog[data.kind].inputs;
  const outputs = data.kind==='output' ? {} : catalog[data.kind].outputs;
  const ports = Math.max(Object.keys(inputs).length,Object.keys(outputs).length,1);
  return <div className={`strategy-node ${data.kind==='output'?'output-node':''} ${selected?'selected':''}`} style={{minHeight:60+ports*22}}>
    <strong>{data.label}</strong><small>{Object.entries(data.params).map(([k,v])=>`${k}: ${v}`).join(' · ') || (data.kind==='output'?'Signal output':'Logic')}</small>
    {Object.keys(inputs).map((port,i)=><div className="port-label input" style={{top:60+i*22}} key={port}><Handle type="target" position={Position.Left} id={port} style={{top:7}}/>{port}</div>)}
    {Object.keys(outputs).map((port,i)=><div className="port-label output" style={{top:60+i*22}} key={port}>{port}<Handle type="source" position={Position.Right} id={port} style={{top:7}}/></div>)}
  </div>;
}
const nodeTypes={strategy:StrategyNode};
export default function GraphEditor({graph,layout,onChange,onSelect,onCreate,selected,locate,onBegin,onEnd}:{graph:Graph;layout:Layout;onChange:(g:Graph,l:Layout)=>void;onSelect:(id:string|null)=>void;onCreate:(kind:NodeKind,position:{x:number;y:number})=>void;selected:string|null;locate:{id:string;request:number}|null;onBegin:()=>void;onEnd:()=>void}) {
  const [selectedNodes,setSelectedNodes]=useState<string[]>([]);
  const [selectedEdges,setSelectedEdges]=useState<string[]>([]);
  const [flow,setFlow]=useState<ReactFlowInstance<Node<FlowData>>|null>(null);
  const [menu,setMenu]=useState<{screen:{x:number;y:number};graph:{x:number;y:number}}|null>(null);
  useEffect(()=>{if(selected)setSelectedNodes(ids=>ids.includes(selected)?ids:[selected]);},[selected]);
  useEffect(()=>{if(locate&&flow){setSelectedNodes([locate.id]);flow.fitView({nodes:[{id:locate.id}],duration:200,maxZoom:1.2});}},[locate,flow]);
  function duplicate(){if(graph.nodes.length+selectedNodes.filter(id=>!id.startsWith('out:')).length>128)return;const result=duplicateNodes(graph,layout,selectedNodes);if(!result.selected.length)return;onChange(result.graph,result.layout);setSelectedNodes(result.selected);onSelect(result.selected[0]);}
  useEffect(()=>{const shortcut=(event:KeyboardEvent)=>{if(!menu&&!isTextEditing(event.target)&&(event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='d'){event.preventDefault();duplicate();}};document.addEventListener('keydown',shortcut);return()=>document.removeEventListener('keydown',shortcut);});
  const nodes=useMemo<Node<FlowData>[]>(()=>[
    ...graph.nodes.map((n,i)=>({id:n.id,type:'strategy',data:{label:labels[n.type],kind:n.type,params:n.params},position:layout[n.id]??{x:60+(i%3)*260,y:70+Math.floor(i/3)*180}})),
    ...outputNames.map((name,i)=>({id:`out:${name}`,type:'strategy',deletable:false,data:{label:labels[name],kind:'output' as const,params:{}},position:layout[`out:${name}`]??{x:920,y:30+i*135}})),
  ],[graph,layout]);
  const edges=useMemo<Edge[]>(()=>{
    const result:Edge[]=[];
    for (const n of graph.nodes) for (const [port,ref] of Object.entries(n.inputs)) {
      const [source,sourceHandle]=ref.split('.');
      if (source&&sourceHandle) result.push({id:`${n.id}:${port}`,source,sourceHandle,target:n.id,targetHandle:port});
    }
    for (const [output,ref] of Object.entries(graph.outputs)) if(ref) {
      const [source,sourceHandle]=ref.split('.');result.push({id:`out:${output}`,source,sourceHandle,target:`out:${output}`,targetHandle:'signal'});
    }
    return result;
  },[graph]);
  function connect(c:Connection) {
    if(!c.sourceHandle||!c.targetHandle||!canConnect(graph,c.source,c.sourceHandle,c.target,c.targetHandle)) return;
    const next=structuredClone(graph),ref=`${c.source}.${c.sourceHandle}`;
    if(c.target.startsWith('out:')) next.outputs[c.target.slice(4) as OutputName]=ref;
    else next.nodes.find(n=>n.id===c.target)!.inputs[c.targetHandle]=ref;
    onChange(next,layout);
  }
  function changeNodes(changes:NodeChange[]) {
    let next=graph;const positions={...layout};
    for(const c of changes) {
      if(c.type==='select') setSelectedNodes(ids=>c.selected?[...new Set([...ids,c.id])]:ids.filter(id=>id!==c.id));
      if(c.type==='position'&&c.position) positions[c.id]=c.position;
      if(c.type==='remove'&&!c.id.startsWith('out:')) {
        next=structuredClone(next);next.nodes=next.nodes.filter(n=>n.id!==c.id);
        for(const n of next.nodes) for(const p of Object.keys(n.inputs)) if(n.inputs[p].startsWith(c.id+'.')) n.inputs[p]='';
        for(const p of outputNames) if(next.outputs[p]?.startsWith(c.id+'.')) next.outputs[p]=null;
        delete positions[c.id];
      }
    }
    if(changes.some(c=>c.type==='position'||c.type==='remove')) onChange(next,positions);
  }
  function removeEdges(removed:Edge[]) {
    const next=structuredClone(graph);
    for(const e of removed) {
      if(e.target.startsWith('out:')) next.outputs[e.target.slice(4) as OutputName]=null;
      else if(e.targetHandle) next.nodes.find(n=>n.id===e.target)!.inputs[e.targetHandle]='';
    }
    onChange(next,layout);
  }
  return <><ReactFlow onInit={setFlow} nodes={nodes.map(n=>({...n,selected:selectedNodes.includes(n.id)}))} edges={edges.map(e=>({...e,selected:selectedEdges.includes(e.id)}))} nodeTypes={nodeTypes} onConnect={connect} onNodesChange={changeNodes} onEdgesDelete={removeEdges}
    onNodeDragStart={onBegin} onNodeDragStop={onEnd} onBeforeDelete={async()=>{onBegin();return true;}} onDelete={onEnd}
    onPaneContextMenu={event=>{event.preventDefault();if(flow){const screen={x:event.clientX,y:event.clientY};setMenu({screen,graph:flow.screenToFlowPosition(screen)});}}}
    onEdgesChange={changes=>changes.forEach(c=>{if(c.type==='select')setSelectedEdges(ids=>c.selected?[...new Set([...ids,c.id])]:ids.filter(id=>id!==c.id));})}
    onNodeClick={(_,n)=>onSelect(n.id.startsWith('out:')?null:n.id)} onPaneClick={()=>onSelect(null)}
    isValidConnection={c=>!!c.source&&!!c.target&&!!c.sourceHandle&&!!c.targetHandle&&canConnect(graph,c.source,c.sourceHandle,c.target,c.targetHandle)}
    fitView minZoom={0.25} maxZoom={2} colorMode="dark" proOptions={{hideAttribution:false}}><Background gap={24}/><Controls/><div className="duplicate-tool"><button disabled={!selectedNodes.some(id=>!id.startsWith('out:'))} onClick={duplicate}>Duplicate selection</button></div></ReactFlow>{menu&&<NodeMenu at={menu.screen} onClose={()=>setMenu(null)} onChoose={kind=>{onCreate(kind,menu.graph);setMenu(null);}}/>}</>;
}
