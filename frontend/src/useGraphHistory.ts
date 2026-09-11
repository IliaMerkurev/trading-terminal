import {useRef,useState} from 'react';
import type {Graph,Layout} from './model';
export type EditorSnapshot={graph:Graph;layout:Layout};
export class GraphHistory {
  past:EditorSnapshot[]=[];future:EditorSnapshot[]=[];group:EditorSnapshot|null=null;
  constructor(public current:EditorSnapshot,readonly limit=100){}
  begin(){this.group??=structuredClone(this.current);}
  end(){const before=this.group;this.group=null;if(before&&JSON.stringify(before)!==JSON.stringify(this.current)){this.past.push(before);this.past=this.past.slice(-this.limit);this.future=[];}}
  change(next:EditorSnapshot){if(JSON.stringify(next)===JSON.stringify(this.current))return;if(!this.group){this.past.push(structuredClone(this.current));this.past=this.past.slice(-this.limit);this.future=[];}this.current=structuredClone(next);}
  undo(){this.end();const previous=this.past.pop();if(previous){this.future.push(this.current);this.current=previous;}}
  redo(){this.end();const next=this.future.pop();if(next){this.past.push(this.current);this.current=next;}}
  reset(next:EditorSnapshot){this.current=structuredClone(next);this.past=[];this.future=[];this.group=null;}
}
export function useGraphHistory(initial:()=>EditorSnapshot){
  const ref=useRef<GraphHistory|null>(null);ref.current??=new GraphHistory(initial());const history=ref.current;
  const [,render]=useState(0);const update=(fn:()=>void)=>{fn();render(n=>n+1);};
  return {graph:history.current.graph,layout:history.current.layout,canUndo:!!history.past.length,canRedo:!!history.future.length,
    change:(graph:Graph,layout:Layout)=>update(()=>history.change({graph,layout})),reset:(graph:Graph,layout:Layout)=>update(()=>history.reset({graph,layout})),
    begin:()=>history.begin(),end:()=>update(()=>history.end()),undo:()=>update(()=>history.undo()),redo:()=>update(()=>history.redo())};
}
