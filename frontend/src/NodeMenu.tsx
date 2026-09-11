import {useEffect,useLayoutEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {fullNames,groups,searchNodes} from './editor';
import {labels,type NodeKind} from './model';
export default function NodeMenu({at,onChoose,onClose}:{at:{x:number;y:number};onChoose:(kind:NodeKind)=>void;onClose:()=>void}){
  const ref=useRef<HTMLDivElement>(null),input=useRef<HTMLInputElement>(null),chosen=useRef(false);
  const [query,setQuery]=useState(''),[active,setActive]=useState(0),[position,setPosition]=useState(at);const items=searchNodes(query);
  useLayoutEffect(()=>{const rect=ref.current!.getBoundingClientRect();setPosition({x:Math.max(8,Math.min(at.x,window.innerWidth-rect.width-8)),y:Math.max(8,Math.min(at.y,window.innerHeight-rect.height-8))});input.current?.focus();},[at]);
  useEffect(()=>{const close=(event:PointerEvent)=>{if(!ref.current?.contains(event.target as Node))onClose();};const resize=()=>onClose();document.addEventListener('pointerdown',close);window.addEventListener('resize',resize);return()=>{document.removeEventListener('pointerdown',close);window.removeEventListener('resize',resize);};},[onClose]);
  useEffect(()=>{ref.current?.querySelector(`[data-active="true"]`)?.scrollIntoView?.({block:'nearest'});},[active]);
  function choose(k:NodeKind){if(chosen.current)return;chosen.current=true;onChoose(k);}
  return createPortal(<div ref={ref} className="node-menu" role="dialog" aria-label="Add a node" style={{left:position.x,top:position.y}} onContextMenu={e=>e.preventDefault()} onKeyDown={e=>{e.stopPropagation();if(e.key==='Escape'){e.preventDefault();onClose();}if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();setActive(i=>items.length?(i+(e.key==='ArrowDown'?1:-1)+items.length)%items.length:0);}if(e.key==='Enter'){e.preventDefault();if(items[active])choose(items[active]);}}}>
    <input ref={input} aria-label="Search nodes" placeholder="Search name or abbreviation…" value={query} onChange={e=>{setQuery(e.target.value);setActive(0);}} aria-controls="node-results" aria-activedescendant={items[active]?`choice-${items[active]}`:undefined}/>
    <div id="node-results" role="listbox" className="node-menu-results">{items.map((k,i)=><div key={k}>{!query.trim()&&(i===0||groups[items[i-1]]!==groups[k])&&<h4>{groups[k]}</h4>}<button id={`choice-${k}`} role="option" aria-selected={i===active} data-active={i===active} onMouseEnter={()=>setActive(i)} onClick={()=>choose(k)}><strong>{labels[k]}</strong><small>{fullNames[k]}</small></button></div>)}{!items.length&&<p>No matching nodes</p>}</div>
  </div>,document.body);
}
