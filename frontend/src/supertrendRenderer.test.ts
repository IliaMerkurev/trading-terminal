import {it,expect,vi} from 'vitest';
import {installIndicatorSeries,updateIndicatorSeries} from './chartIndicatorSeries';
import {indicatorWindow} from './chartWindow';
import {defaults,type ChartIndicator} from './ChartIndicators';
const {readFileSync}=await vi.importActual<{readFileSync(path:string,encoding:'utf8'):string}>('node:fs');
// Execute the installed pinned vendor's actual simple-line walker. Nothing is
// copied into production; this regression intentionally detects renderer drift.
const source=readFileSync('node_modules/lightweight-charts/dist/lightweight-charts.development.mjs','utf8');
const start=source.indexOf('function walkLine('),end=source.indexOf('\nconst curveTension',start);
const walkLine=new Function(`return (${source.slice(start,end)})`)();
it('renders no Supertrend stroke across inactive whitespace using actual LWC left-point segment colors',()=>{
 const item:ChartIndicator={id:'st',type:'supertrend',params:defaults.supertrend,color:'#123456',visible:true};
 const chart={addSeries:(_kind:any,options:any)=>({options,setData:vi.fn()}),panes:()=>[]};
 const owned=installIndicatorSeries(chart,null,[item],false);
 updateIndicatorSeries(owned,{times:[60,120,180,240,300,360,420,480],columns:{st:{up:[10,11,null,null,14,15,null,17],down:[null,null,22,23,null,null,26,null]}}});
 for(const row of owned){
  const data=row.series.setData.mock.calls[0][0];
  expect(data.map((point:any)=>point.time)).toEqual([60,120,180,240,300,360,420,480]);
  const points=data.filter((point:any)=>point.value!=null).map((point:any)=>({_internal_x:point.time/60,_internal_y:point.value,color:point.color}));
  let path:any[]=[];const strokes:{color:string;path:any[]}[]=[];
  const context={beginPath:()=>{path=[];},moveTo:(x:number,y:number)=>path.push([x,y]),lineTo:(x:number,y:number)=>path.push([x,y])};
  walkLine({context,horizontalPixelRatio:1,verticalPixelRatio:1},points,0,{from:0,to:points.length},1,(_scope:any,point:any)=>point.color,(_scope:any,color:string)=>strokes.push({color,path:[...path]}));
  const visible=strokes.filter(stroke=>stroke.color!=='transparent');
  for(const stroke of visible)for(let i=1;i<stroke.path.length;i++)expect(stroke.path[i][0]-stroke.path[i-1][0]).toBe(1);
  expect(visible.flatMap(stroke=>stroke.path)).toEqual(row.port==='up'?[[1,10],[2,11],[5,14],[6,15]]:[[3,22],[4,23]]);
  expect(strokes.some(stroke=>stroke.color==='transparent')).toBe(true);
 }
});


it('preserves a period-one reset break after raw-window clipping removes the synthetic gap slot',()=>{
 for(const minutes of [1,5]) {
  const width=minutes*60;
  const item:ChartIndicator={id:'st',type:'supertrend',params:{period:1,multiplier:1},color:'#123456',visible:true};
  const chart={addSeries:(_kind:any,options:any)=>({options,setData:vi.fn()}),panes:()=>[]};
  const owned=installIndicatorSeries(chart,null,[item],false);
  const rows=[0,1,3,4].map(index=>({time:index*width,open:10,high:11,low:9,close:10,volume:1}));
  const filtered=indicatorWindow({times:[1,2,3,4,5].map(index=>index*width),columns:{st:{up:[8,8,null,8,8],down:[null,null,null,null,null]}}},rows,minutes);
  updateIndicatorSeries(owned,filtered,minutes);
  const data=owned[0].series.setData.mock.calls[0][0];
  expect(data.map((point:any)=>point.time)).toEqual([1,2,4,5].map(index=>index*width));
  const points=data.map((point:any)=>({_internal_x:point.time/width,_internal_y:point.value,color:point.color}));
  let path:number[]=[];const strokes:{color:string;path:number[]}[]=[];
  const context={beginPath:()=>{path=[];},moveTo:(x:number)=>path.push(x),lineTo:(x:number)=>path.push(x)};
  walkLine({context,horizontalPixelRatio:1,verticalPixelRatio:1},points,0,{from:0,to:points.length},1,(_scope:any,point:any)=>point.color,(_scope:any,color:string)=>strokes.push({color,path:[...path]}));
  expect(strokes.filter(stroke=>stroke.color!=='transparent').map(stroke=>stroke.path)).toEqual([[1,2],[4,5]]);
  expect(strokes.find(stroke=>stroke.color==='transparent')!.path).toEqual([2,4]);
 }
});
