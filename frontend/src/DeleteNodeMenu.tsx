import {useEffect,useRef} from 'react';
import {createPortal} from 'react-dom';

export default function DeleteNodeMenu({at,disabled,onClose,onDelete}:{at:{x:number;y:number};disabled:boolean;onClose:()=>void;onDelete:()=>void}){
  const menu=useRef<HTMLDivElement>(null);
  useEffect(()=>{
    menu.current?.focus();
    const outside=(event:PointerEvent)=>{if(!menu.current?.contains(event.target as Node))onClose();};
    document.addEventListener('pointerdown',outside);
    return()=>document.removeEventListener('pointerdown',outside);
  },[onClose]);
  return createPortal(<div ref={menu} tabIndex={-1} role="menu" aria-label="Node actions" className="delete-node-menu" style={{left:Math.max(0,Math.min(at.x,window.innerWidth-190)),top:Math.max(0,Math.min(at.y,window.innerHeight-70))}} onContextMenu={event=>event.preventDefault()} onKeyDown={event=>{event.stopPropagation();if(event.key==='Escape')onClose();if(!disabled&&(event.key==='Enter'||event.key==='Delete')){event.preventDefault();onDelete();}}}>
    <button role="menuitem" disabled={disabled} onClick={onDelete}>Delete node</button>
  </div>,document.body);
}
