import {useEffect,useMemo,useRef,useState} from 'react';
import {api} from './api';
import type {LiveCandle} from './liveChartData';
import {drawingTools,isTypingTarget,logicalToTime,moveDrawing,sanitizeAnnotation,timeToLogical,validAnchors,type Anchor,type Drawing,type DrawingDocument,type DrawingKind} from './chartDrawings';

type Props={children:React.ReactNode;chart:React.MutableRefObject<any>;series:React.MutableRefObject<any>;rows:LiveCandle[];minutes:number;source:string;market:string;symbol:string;active:boolean};
type Gesture={id:string;endpoint:number|null;start:Anchor;original:Drawing;creating:boolean};
const empty:DrawingDocument={version:1,revision:0,drawings:[]};
export default function ChartDrawings({children,chart,series,rows,minutes,source,market,symbol,active}:Props){
 const [doc,setDoc]=useState<DrawingDocument>(empty),[loaded,setLoaded]=useState(false),[saving,setSaving]=useState(false),[error,setError]=useState('');
 const [tool,setTool]=useState<DrawingKind|'pointer'|'ruler'>('pointer'),[selected,setSelected]=useState<string|null>(null),[preview,setPreview]=useState<Drawing|null>(null),[magnet,setMagnet]=useState(false),[hide,setHide]=useState(false);
 const [ruler,setRuler]=useState(false);
 const [color,setColor]=useState('#e0b95e'),[width,setWidth]=useState(2),[style,setStyle]=useState<Drawing['style']>('solid'),[text,setText]=useState('Note');
 const [history,setHistory]=useState<{past:Drawing[][];future:Drawing[][]}>({past:[],future:[]});
 const [geometry,setGeometry]=useState({width:0,height:0,points:{} as Record<string,number[][]>});
 const epoch=useRef(0),docRef=useRef(doc),gesture=useRef<Gesture|null>(null),svg=useRef<SVGSVGElement>(null),pending=useRef<null|{next:Drawing[];history:typeof history}>(null);
 docRef.current=doc;
 const namespace=JSON.stringify([source,market,symbol]);
 useEffect(()=>{
  const token=++epoch.current;setDoc(empty);setLoaded(false);setSaving(false);setError('');setSelected(null);setPreview(null);gesture.current=null;pending.current=null;setTool('pointer');setHide(false);setHistory({past:[],future:[]});
  api<DrawingDocument>('chart_drawing_settings',{source,market,symbol}).then(value=>{
   if(token!==epoch.current)return;
   if(value.version!==1||!Array.isArray(value.drawings))throw new Error('Unsupported drawing settings');
   setDoc(value);setLoaded(true);
  }).catch(()=>{if(token===epoch.current)setError('Drawings unavailable. Existing saved data is preserved. Reopen this market to retry.');});
  return()=>{++epoch.current;};
 },[namespace]);
 useEffect(()=>{gesture.current=null;setPreview(null);setSelected(null);setTool('pointer');setRuler(false);},[minutes,active]);
 const cancel=()=>{gesture.current=null;setPreview(null);setTool('pointer');setRuler(false);};
 useEffect(()=>{chart.current?.applyOptions?.({handleScroll:tool==='pointer'&&!gesture.current,handleScale:tool==='pointer'&&!gesture.current});return()=>{chart.current?.applyOptions?.({handleScroll:true,handleScale:true});};},[tool,!!preview,chart]);
 const save=async(next:Drawing[],nextHistory=history)=>{
  if(saving||!loaded||next.length>100||next.some(d=>!validAnchors(d.anchors)))return;
  const token=epoch.current;pending.current={next,history:nextHistory};setSaving(true);setError('');
  try{
   const value=await api<DrawingDocument>('chart_drawing_save',{source,market,symbol,drawings:next,revision:docRef.current.revision});
   if(token===epoch.current){setDoc(value);setHistory(nextHistory);pending.current=null;}
  }catch(reason){if(token===epoch.current)setError('Drawing changes not saved. '+(reason instanceof Error?reason.message:'Retry or reopen this market.'));}
  finally{if(token===epoch.current){setSaving(false);setPreview(null);}}
 };
 const commit=(next:Drawing[])=>void save(next,{past:[...history.past,doc.drawings].slice(-50),future:[]});
 const undo=()=>{if(gesture.current){cancel();return;}if(history.past.length&&!saving&&!pending.current){const previous=history.past.at(-1)!;void save(previous,{past:history.past.slice(0,-1),future:[doc.drawings,...history.future].slice(0,50)});setSelected(null);}};
 const redo=()=>{if(gesture.current){cancel();return;}if(history.future.length&&!saving&&!pending.current){void save(history.future[0],{past:[...history.past,doc.drawings].slice(-50),future:history.future.slice(1)});setSelected(null);}};
 const current=doc.drawings.find(d=>d.id===selected);
 const edit=(change:Partial<Drawing>)=>{if(current&&!saving&&!pending.current)commit(doc.drawings.map(d=>d.id===selected?{...d,...change}:d));};
 const remove=()=>{if(gesture.current){cancel();return;}if(current&&!current.locked&&!saving&&!pending.current){commit(doc.drawings.filter(d=>d.id!==selected));setSelected(null);}};
 const drawings=useMemo(()=>preview?[...doc.drawings.filter(d=>d.id!==preview.id),preview]:doc.drawings,[preview,doc.drawings]);
 // Price-scale drags do not emit a public range event. Sample chart conversions,
 // updating React only when projected geometry changes; suspend while hidden.
 useEffect(()=>{
  if(!active)return;
  let frame=0,previous='';
  const update=()=>{
   const api=chart.current,price=series.current,size=api?.paneSize?.(0);
   if(size&&price){
    const points:Record<string,number[][]>={};
    for(const drawing of drawings){points[drawing.id]=drawing.anchors.map(anchor=>{
     const logical=timeToLogical(anchor.time,rows,minutes*60);
     return [logical==null?NaN:api.timeScale().logicalToCoordinate(logical)??NaN,price.priceToCoordinate(anchor.price)??NaN];
    });}
    const value={width:size.width,height:size.height,points},key=JSON.stringify(value);
    if(key!==previous){previous=key;setGeometry(value);}
   }
   frame=requestAnimationFrame(update);
  };frame=requestAnimationFrame(update);return()=>cancelAnimationFrame(frame);
 },[chart,series,drawings,rows,minutes,active]);
 const anchorAt=(event:React.PointerEvent):Anchor|null=>{
  const bounds=svg.current?.getBoundingClientRect();if(!bounds)return null;
  const x=Math.max(0,Math.min(geometry.width,event.clientX-bounds.left)),y=Math.max(0,Math.min(geometry.height,event.clientY-bounds.top));
  const logical=chart.current?.timeScale().coordinateToLogical(x),price=series.current?.coordinateToPrice(y);
  if(logical==null||price==null)return null;
  const time=logicalToTime(logical,rows,minutes*60);if(time==null)return null;
  let anchor={time,price:Number(price)};
  if(magnet){const row=rows[Math.max(0,Math.min(rows.length-1,Math.round(logical)))];if(row){const prices=[row.open,row.high,row.low,row.close];anchor={time:row.time+minutes*60,price:prices.reduce((a,b)=>Math.abs((series.current.priceToCoordinate(a)??Infinity)-y)<Math.abs((series.current.priceToCoordinate(b)??Infinity)-y)?a:b)};}}
  return validAnchors([anchor])?anchor:null;
 };
 const begin=(event:React.PointerEvent,drawing?:Drawing,endpoint:number|null=null)=>{
  if(event.button!==0||saving||!loaded||pending.current||hide)return;
  const anchor=anchorAt(event);if(!anchor)return;
  if(drawing){setSelected(drawing.id);setText(drawing.text);if(drawing.locked){event.stopPropagation();return;}}
  else if(tool==='pointer'){setSelected(null);return;}
  else if(doc.drawings.length>=100&&tool!=='ruler')return;
  event.preventDefault();event.stopPropagation();svg.current?.focus();svg.current?.setPointerCapture?.(event.pointerId);
  if(drawing){gesture.current={id:drawing.id,endpoint,start:anchor,original:drawing,creating:false};setPreview(drawing);}
  else{
   setRuler(tool==='ruler');
   const kind=tool==='ruler'?'trend':tool as DrawingKind;
   const next:Drawing={id:'d'+crypto.randomUUID().replaceAll('-',''),kind,anchors:['horizontal','vertical','text'].includes(kind)?[anchor]:[anchor,anchor],color,width,style,text:sanitizeAnnotation(text),visible:true,locked:false};
   gesture.current={id:next.id,endpoint:next.anchors.length-1,start:anchor,original:next,creating:true};setPreview(next);setSelected(next.id);
  }
 };
 const move=(event:React.PointerEvent)=>{
  const operation=gesture.current;if(!operation)return;
  const anchor=anchorAt(event);if(!anchor)return;
  const next=operation.endpoint==null?moveDrawing(operation.original,operation.start,anchor):{...operation.original,anchors:operation.original.anchors.map((old,index)=>index===operation.endpoint?anchor:old)};
  if(validAnchors(next.anchors))setPreview(next);
 };
 const finish=(event:React.PointerEvent)=>{
  if(!gesture.current||!preview)return;
  const operation=gesture.current;
  svg.current?.releasePointerCapture?.(event.pointerId);gesture.current=null;
  if(!operation.creating&&JSON.stringify(preview.anchors)===JSON.stringify(operation.original.anchors)){setPreview(null);return;}
  if(tool==='ruler'){setTool('pointer');return;}
  commit([...doc.drawings.filter(d=>d.id!==preview.id),preview]);setTool('pointer');
 };
 const keyDown=(event:React.KeyboardEvent)=>{
  if(isTypingTarget(event.target))return;
  if(event.key==='Escape'){event.preventDefault();cancel();setSelected(null);return;}
  if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='z'){event.preventDefault();event.shiftKey?redo():undo();}
  else if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='y'){event.preventDefault();redo();}
  else if(event.key==='Delete'||event.key==='Backspace'){event.preventDefault();remove();}
 };
 const disabled=!loaded||saving||!!pending.current;
 const shape=(drawing:Drawing)=>{
  const points=geometry.points[drawing.id];if(!points?.every(p=>p.every(Number.isFinite)))return null;
  const [[x,y],[endX,endY]=[x,y]]=points,stroke={stroke:drawing.color,strokeWidth:drawing.width,strokeDasharray:drawing.style==='dashed'?'8 5':drawing.style==='dotted'?'2 4':undefined,fill:'none'};
  const line=(x1:number,y1:number,x2:number,y2:number,key?:string)=><line key={key} x1={x1} y1={y1} x2={x2} y2={y2}/>;
  let elements:React.ReactNode;
  if(drawing.kind==='horizontal')elements=line(0,y,geometry.width,y);
  else if(drawing.kind==='vertical')elements=line(x,0,x,geometry.height);
  else if(drawing.kind==='rectangle')elements=<rect x={Math.min(x,endX)} y={Math.min(y,endY)} width={Math.abs(endX-x)} height={Math.abs(endY-y)} fill={drawing.color} fillOpacity={0.07}/>;
  else if(drawing.kind==='text')elements=<text x={x+5} y={y-5} fill={drawing.color} stroke="none" fontSize={13}>{drawing.text}</text>;
  else if(drawing.kind==='ray'){
   const dx=endX-x,dy=endY-y;const factor=Math.abs(dx)>0.001?(dx>0?(geometry.width-x)/dx:-x/dx):Math.abs(dy)>0.001?(dy>0?(geometry.height-y)/dy:-y/dy):1;
   elements=line(x,y,x+dx*Math.max(1,factor),y+dy*Math.max(1,factor));
  }else if(drawing.kind==='fib')elements=[0,0.236,0.382,0.5,0.618,0.786,1].map(level=>{
   const price=drawing.anchors[0].price+(drawing.anchors[1].price-drawing.anchors[0].price)*level,coordinate=series.current?.priceToCoordinate(price);if(coordinate==null)return null;
   return <g key={level}>{line(x,coordinate,endX,coordinate)}<text x={Math.min(x,endX)+4} y={coordinate-4} stroke="none" fill={drawing.color} fontSize={11}>{level} · {price.toLocaleString(undefined,{maximumSignificantDigits:8})}</text></g>;
  });else elements=line(x,y,endX,endY);
  return <g key={drawing.id} {...stroke} style={{pointerEvents:tool==='pointer'&&!(ruler&&drawing.id===preview?.id)?'visiblePainted':'none',cursor:drawing.locked?'default':'move'}} onPointerDown={event=>begin(event,drawing)}>
   <g className="drawing-hit-target" strokeWidth={Math.max(12,drawing.width)} strokeOpacity={0} fillOpacity={0}>{elements}</g>{elements}
   {selected===drawing.id&&!drawing.locked&&points.map(([px,py],index)=><circle key={index} cx={px} cy={py} r={5} fill="#111720" stroke="#eaf2ff" strokeWidth={2} style={{cursor:'crosshair'}} onPointerDown={event=>begin(event,drawing,index)}/>)}
  </g>;
 };
 return <div className="drawing-workspace" onKeyDown={keyDown}><div className="drawing-stage">{children}
  <div className="drawing-toolbar" role="toolbar" aria-label="Drawing tools">{drawingTools.map(item=><button key={item.kind} title={item.label} aria-label={item.label} aria-pressed={tool===item.kind} disabled={disabled||hide} onClick={()=>{cancel();if(item.kind!=='pointer')setSelected(null);setTool(item.kind);}}>{item.icon}</button>)}
   <button title="Snap anchors to nearest candle OHLC" aria-label="Magnet snapping" aria-pressed={magnet} onClick={()=>setMagnet(v=>!v)}>⌁</button>
   <button title="Hide all drawings temporarily" aria-label="Hide drawings" aria-pressed={hide} onClick={()=>{cancel();setHide(v=>!v);}}>◉</button>
   <button title="Undo drawing change (Ctrl+Z)" aria-label="Undo drawing" disabled={disabled||!history.past.length} onClick={undo}>↶</button>
   <button title="Redo drawing change (Ctrl+Shift+Z)" aria-label="Redo drawing" disabled={disabled||!history.future.length} onClick={redo}>↷</button>
  </div>
  <svg ref={svg} className="drawing-overlay" width={geometry.width} height={geometry.height} tabIndex={0} aria-label="Price chart drawing canvas" style={{pointerEvents:tool==='pointer'&&!gesture.current?'none':'auto',cursor:tool==='pointer'?'default':'crosshair'}} onPointerDown={event=>begin(event)} onPointerMove={move} onPointerUp={finish} onPointerCancel={cancel}>{!hide&&drawings.filter(d=>d.visible).map(shape)}
   {preview&&ruler&&preview.anchors.length===2&&<text x={10} y={22} fill="#eaf2ff" fontSize={13}>{(preview.anchors[1].price-preview.anchors[0].price).toPrecision(5)} ({((preview.anchors[1].price/preview.anchors[0].price-1)*100).toFixed(2)}%) · {(Math.abs(preview.anchors[1].time-preview.anchors[0].time)/60).toFixed(1)} min</text>}
  </svg></div>
  <div className="drawing-properties" aria-label="Drawing properties">
   <span>{current?drawingTools.find(t=>t.kind===current.kind)?.label:tool==='pointer'?'Drawings':drawingTools.find(t=>t.kind===tool)?.label}</span>
   <label>Color<input aria-label="Drawing color" type="color" value={current?.color??color} disabled={disabled||current?.locked} onChange={event=>{setColor(event.target.value);if(current)edit({color:event.target.value});}}/></label>
   <label>Width<select aria-label="Drawing width" value={current?.width??width} disabled={disabled||current?.locked} onChange={event=>{setWidth(Number(event.target.value));if(current)edit({width:Number(event.target.value)});}}>{[1,2,3,4].map(value=><option key={value}>{value}</option>)}</select></label>
   <label>Style<select aria-label="Drawing style" value={current?.style??style} disabled={disabled||current?.locked} onChange={event=>{const value=event.target.value as Drawing['style'];setStyle(value);if(current)edit({style:value});}}>{['solid','dashed','dotted'].map(value=><option key={value}>{value}</option>)}</select></label>
   {(tool==='text'||current?.kind==='text')&&<label>Text<input aria-label="Annotation text" maxLength={200} value={text} onChange={event=>setText(sanitizeAnnotation(event.target.value))}/>{current&&<button disabled={disabled||current.locked} onClick={()=>edit({text})}>Apply text</button>}</label>}
   {current&&<><button aria-pressed={current.locked} disabled={disabled} onClick={()=>edit({locked:!current.locked})}>{current.locked?'Unlock':'Lock'} drawing</button><button disabled={disabled||current.locked} onClick={()=>edit({visible:!current.visible})}>{current.visible?'Hide':'Show'} selected</button><button disabled={disabled||current.locked} onClick={remove}>Delete drawing</button></>}
   <select aria-label="Select saved drawing" value={selected??''} onChange={event=>{setSelected(event.target.value||null);const item=doc.drawings.find(d=>d.id===event.target.value);if(item)setText(item.text);}}><option value="">Select drawing ({doc.drawings.length}/100)</option>{doc.drawings.map((drawing,index)=><option key={drawing.id} value={drawing.id}>{index+1}. {drawing.kind}{drawing.locked?' · locked':''}{drawing.visible?'':' · hidden'}</option>)}</select>
   <span role="status">{saving?'Saving drawing…':error?'Changes need attention':loaded?'Drawings saved locally':'Loading drawings…'}</span>
   {preview&&!gesture.current&&<button onClick={cancel}>Clear ruler</button>}
   {error&&<span role="alert">{error}{pending.current&&<><button disabled={saving} onClick={()=>{const retry=pending.current;if(retry)void save(retry.next,retry.history);}}>Retry saving</button><button disabled={saving} onClick={()=>{pending.current=null;setError('');setPreview(null);}}>Discard unsaved change</button></>}</span>}
  </div>
 </div>;
}
