import type {LiveCandle} from './liveChartData';
export type Anchor = {time:number; price:number};
export type DrawingKind = 'horizontal'|'vertical'|'trend'|'ray'|'rectangle'|'fib'|'text';
export type Drawing = {id:string;kind:DrawingKind;anchors:Anchor[];color:string;width:number;style:'solid'|'dashed'|'dotted';text:string;visible:boolean;locked:boolean};
export type DrawingDocument = {version:1;revision:number;drawings:Drawing[]};
export const drawingTools: {kind:DrawingKind|'pointer'|'ruler';label:string;icon:string}[] = [
 {kind:'pointer',label:'Select / pan',icon:'↖'},{kind:'horizontal',label:'Horizontal line',icon:'━'},
 {kind:'vertical',label:'Vertical line',icon:'┃'},{kind:'trend',label:'Trend line',icon:'╱'},
 {kind:'ray',label:'Ray',icon:'↗'},{kind:'rectangle',label:'Rectangle',icon:'▭'},
 {kind:'fib',label:'Fibonacci retracement',icon:'≋'},{kind:'text',label:'Text annotation',icon:'T'},
 {kind:'ruler',label:'Ruler (temporary)',icon:'↔'},
];
// Time anchors survive prepends, irregular gaps and native timeframe changes.
// Logical positions are only transient chart coordinates, never persisted.
export function timeToLogical(time:number, rows:LiveCandle[], seconds:number):number|null {
 if(!rows.length)return null;
 const first=rows[0].time+seconds,last=rows.at(-1)!.time+seconds;
 if(time<=first)return (time-first)/seconds;
 if(time>=last)return rows.length-1+(time-last)/seconds;
 let low=0,high=rows.length-1;
 while(high-low>1){const middle=(low+high)>>1;if(rows[middle].time+seconds<=time)low=middle;else high=middle;}
 return low+(time-(rows[low].time+seconds))/(rows[high].time-rows[low].time);
}
export function logicalToTime(logical:number, rows:LiveCandle[], seconds:number):number|null {
 if(!rows.length)return null;
 if(logical<=0)return rows[0].time+seconds+logical*seconds;
 if(logical>=rows.length-1)return rows.at(-1)!.time+seconds+(logical-rows.length+1)*seconds;
 const low=Math.floor(logical);return rows[low].time+seconds+(logical-low)*(rows[low+1].time-rows[low].time);
}
export function sanitizeAnnotation(text:string){return text.replace(/[\x00-\x1f\x7f]/g,' ').slice(0,200);}
export function isTypingTarget(target:EventTarget|null){return target instanceof HTMLElement && (!!target.closest('input,textarea,select,[contenteditable="true"]'));}
export function moveDrawing(drawing:Drawing, from:Anchor, to:Anchor):Drawing {
 return {...drawing,anchors:drawing.anchors.map(anchor=>({time:anchor.time+to.time-from.time,price:anchor.price+to.price-from.price}))};
}
export function validAnchors(anchors:Anchor[]){return anchors.every(a=>Number.isFinite(a.time)&&a.time>0&&a.time<=253402300799&&Number.isFinite(a.price)&&a.price>0&&a.price<=1e15);}
