import {beforeEach,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,act} from '@testing-library/react';
import ChartDrawings from './ChartDrawings';
import type {Drawing,DrawingDocument} from './chartDrawings';
const mock=vi.hoisted(()=>({api:vi.fn()}));
vi.mock('./api',()=>({api:mock.api}));
const rows=[0,60,120].map(time=>({time,open:10,high:12,low:9,close:11,volume:1}));
const drawing:Drawing={id:'d1',kind:'trend',anchors:[{time:60,price:10},{time:120,price:20}],color:'#abcdef',width:2,style:'solid',text:'Note',visible:true,locked:false};
let saved:DrawingDocument;
const chart={current:{applyOptions:vi.fn(),paneSize:()=>({width:600,height:320}),timeScale:()=>({logicalToCoordinate:(n:number)=>n*100,coordinateToLogical:(n:number)=>n/100})}};
const series={current:{priceToCoordinate:(n:number)=>320-n,coordinateToPrice:(n:number)=>320-n}};
const props={chart,series,rows,minutes:1,source:'bybit',market:'spot',symbol:'BTCUSDT',active:true,children:<div>Price chart</div>};
beforeEach(()=>{
 vi.stubGlobal('PointerEvent',MouseEvent);saved={version:1,revision:1,drawings:[structuredClone(drawing)]};mock.api.mockReset();
 mock.api.mockImplementation(async(command:string,p:any)=>{if(command==='chart_drawing_settings')return structuredClone(saved);saved={version:1,revision:saved.revision+1,drawings:p.drawings};return structuredClone(saved);});
});
async function ready(){await waitFor(()=>expect((screen.getByRole('button',{name:'Trend line'}) as HTMLButtonElement).disabled).toBe(false));await waitFor(()=>expect(screen.getByLabelText('Price chart drawing canvas').getAttribute('width')).toBe('600'));}
it('creates all seven tools with absolute anchors and persists each gesture once',async()=>{
 render(<ChartDrawings {...props}/>);await ready();
 for(const label of ['Horizontal line','Vertical line','Trend line','Ray','Rectangle','Fibonacci retracement','Text annotation']){
  fireEvent.click(screen.getByRole('button',{name:label}));
  const canvas=screen.getByLabelText('Price chart drawing canvas');
  fireEvent.pointerDown(canvas,{clientX:50,clientY:200,button:0,pointerId:1});
  fireEvent.pointerMove(canvas,{clientX:150,clientY:180,pointerId:1});
  fireEvent.pointerUp(canvas,{clientX:150,clientY:180,pointerId:1});
  await waitFor(()=>expect(screen.getByText('Drawings saved locally')).toBeTruthy());
 }
 expect(mock.api.mock.calls.filter(c=>c[0]==='chart_drawing_save')).toHaveLength(7);
 expect(saved.drawings).toHaveLength(8);expect(saved.drawings.at(-1)?.anchors).toEqual([{time:150,price:140}]);
});
it('keeps ruler transient, escapes unfinished gestures and never steals input shortcuts',async()=>{
 render(<ChartDrawings {...props}/>);await ready();
 fireEvent.click(screen.getByRole('button',{name:'Ruler (temporary)'}));const canvas=screen.getByLabelText('Price chart drawing canvas');
 fireEvent.pointerDown(canvas,{clientX:50,clientY:200,button:0});fireEvent.pointerMove(canvas,{clientX:150,clientY:180});fireEvent.pointerUp(canvas);
 expect(screen.getByRole('button',{name:'Clear ruler'})).toBeTruthy();expect(chart.current.applyOptions).toHaveBeenLastCalledWith({handleScroll:true,handleScale:true});expect(mock.api.mock.calls.filter(c=>c[0]==='chart_drawing_save')).toHaveLength(0);
 fireEvent.keyDown(canvas,{key:'Escape'});expect(screen.queryByRole('button',{name:'Clear ruler'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Text annotation'}));fireEvent.keyDown(screen.getByLabelText('Annotation text'),{key:'z',ctrlKey:true});
 fireEvent.pointerDown(canvas,{clientX:50,clientY:200,button:0});fireEvent.keyDown(canvas,{key:'Escape'});fireEvent.pointerUp(canvas);
 expect(mock.api.mock.calls.filter(c=>c[0]==='chart_drawing_save')).toHaveLength(0);
});
it('supports properties, lock, hidden selection and bounded undo/redo without cross-source state',async()=>{
 const {rerender}=render(<ChartDrawings {...props}/>);await ready();
 fireEvent.change(screen.getByLabelText('Select saved drawing'),{target:{value:'d1'}});
 fireEvent.click(screen.getByRole('button',{name:'Lock drawing'}));await screen.findByRole('button',{name:'Unlock drawing'});
 expect((screen.getByRole('button',{name:'Delete drawing'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Unlock drawing'}));await screen.findByRole('button',{name:'Lock drawing'});
 fireEvent.click(screen.getByRole('button',{name:'Hide selected'}));await screen.findByRole('button',{name:'Show selected'});
 fireEvent.click(screen.getByRole('button',{name:'Undo drawing'}));await waitFor(()=>expect(saved.drawings[0].visible).toBe(true));
 fireEvent.click(screen.getByRole('button',{name:'Redo drawing'}));await waitFor(()=>expect(saved.drawings[0].visible).toBe(false));
 rerender(<ChartDrawings {...props} source="okx"/>);await ready();
 expect((screen.getByRole('button',{name:'Undo drawing'}) as HTMLButtonElement).disabled).toBe(true);
 expect(mock.api).toHaveBeenCalledWith('chart_drawing_settings',{source:'okx',market:'spot',symbol:'BTCUSDT'});
});
it('shows save failure, retries same revision and rejects stale namespace replies',async()=>{
 let resolveOld:(doc:DrawingDocument)=>void=()=>{};
 mock.api.mockImplementation((command:string,p:any)=>{
  if(command==='chart_drawing_settings')return Promise.resolve(structuredClone(saved));
  if(p.source==='bybit')return new Promise(resolve=>{resolveOld=resolve;});
  return Promise.reject(new Error('disk unavailable'));
 });
 const {rerender}=render(<ChartDrawings {...props}/>);await ready();
 fireEvent.change(screen.getByLabelText('Select saved drawing'),{target:{value:'d1'}});fireEvent.click(screen.getByRole('button',{name:'Delete drawing'}));
 rerender(<ChartDrawings {...props} source="okx"/>);await ready();
 await act(async()=>resolveOld({version:1,revision:2,drawings:[]}));expect(screen.getByLabelText('Select saved drawing').textContent).toContain('trend');
 fireEvent.change(screen.getByLabelText('Select saved drawing'),{target:{value:'d1'}});fireEvent.click(screen.getByRole('button',{name:'Delete drawing'}));
 expect((await screen.findByRole('alert')).textContent).toContain('not saved');
 fireEvent.click(screen.getByRole('button',{name:'Retry saving'}));await waitFor(()=>expect(mock.api.mock.calls.filter(c=>c[0]==='chart_drawing_save'&&c[1].source==='okx')).toHaveLength(2));
 expect(mock.api.mock.calls.filter(c=>c[0]==='chart_drawing_save').every(c=>c[1].revision===1)).toBe(true);
});

it('moves endpoints/body, snaps OHLC and aborts pointer cancellation without a write',async()=>{
 const {container}=render(<ChartDrawings {...props}/>);await ready();
 fireEvent.change(screen.getByLabelText('Select saved drawing'),{target:{value:'d1'}});
 const canvas=screen.getByLabelText('Price chart drawing canvas');
 await waitFor(()=>expect(container.querySelector('circle')).toBeTruthy());
 const handle=container.querySelector('circle')!;
 fireEvent.pointerDown(handle,{clientX:0,clientY:310,button:0});fireEvent.pointerMove(canvas,{clientX:50,clientY:300});fireEvent.pointerUp(canvas);
 await waitFor(()=>expect(saved.drawings[0].anchors[0]).toEqual({time:90,price:20}));
 fireEvent.pointerDown(container.querySelector('line')!,{clientX:50,clientY:300,button:0});fireEvent.pointerMove(canvas,{clientX:100,clientY:290});fireEvent.pointerUp(canvas);
 await waitFor(()=>expect(saved.drawings[0].anchors).toEqual([{time:120,price:30},{time:150,price:30}]));
 fireEvent.click(screen.getByRole('button',{name:'Magnet snapping'}));
 fireEvent.click(screen.getByRole('button',{name:'Horizontal line'}));
 fireEvent.pointerDown(canvas,{clientX:90,clientY:309,button:0});fireEvent.pointerUp(canvas);
 await waitFor(()=>expect(saved.drawings).toHaveLength(2));expect(saved.drawings[1].anchors[0]).toEqual({time:120,price:11});
 const count=mock.api.mock.calls.filter(c=>c[0]==='chart_drawing_save').length;
 fireEvent.click(screen.getByRole('button',{name:'Rectangle'}));fireEvent.pointerDown(canvas,{clientX:50,clientY:200,button:0});fireEvent.pointerCancel(canvas);fireEvent.pointerUp(canvas);
 expect(mock.api.mock.calls.filter(c=>c[0]==='chart_drawing_save')).toHaveLength(count);
});

it('cancels an active endpoint drag before Delete or undo can commit history',async()=>{
 const {container}=render(<ChartDrawings {...props}/>);await ready();
 fireEvent.change(screen.getByLabelText('Select saved drawing'),{target:{value:'d1'}});
 await waitFor(()=>expect(container.querySelector('circle')).toBeTruthy());
 const canvas=screen.getByLabelText('Price chart drawing canvas');
 for(const key of ['Delete','z']){
  fireEvent.pointerDown(container.querySelector('circle')!,{clientX:0,clientY:310,button:0});
  fireEvent.pointerMove(canvas,{clientX:50,clientY:300});
  fireEvent.keyDown(canvas,{key,ctrlKey:key==='z'});fireEvent.pointerUp(canvas);
 }
 expect(mock.api.mock.calls.filter(c=>c[0]==='chart_drawing_save')).toHaveLength(0);
 expect(saved.drawings).toEqual([drawing]);
});


it('selects an existing drawing without a no-op save or undo entry',async()=>{
 const {container}=render(<ChartDrawings {...props}/>);await ready();
 await waitFor(()=>expect(container.querySelector('line')).toBeTruthy());
 const canvas=screen.getByLabelText('Price chart drawing canvas');
 fireEvent.pointerDown(container.querySelector('line')!,{clientX:0,clientY:310,button:0});
 fireEvent.pointerUp(canvas,{clientX:0,clientY:310});
 expect(mock.api.mock.calls.filter(c=>c[0]==='chart_drawing_save')).toHaveLength(0);
 expect((screen.getByRole('button',{name:'Undo drawing'}) as HTMLButtonElement).disabled).toBe(true);
 expect(screen.getByRole('button',{name:'Delete drawing'})).toBeTruthy();
});


it('clears prior object selection before configuring a new tool',async()=>{
 render(<ChartDrawings {...props}/>);await ready();
 fireEvent.change(screen.getByLabelText('Select saved drawing'),{target:{value:'d1'}});
 expect(screen.getByRole('button',{name:'Delete drawing'})).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Text annotation'}));
 expect(screen.queryByRole('button',{name:'Delete drawing'})).toBeNull();
 expect(screen.queryByRole('button',{name:'Apply text'})).toBeNull();
 expect((screen.getByLabelText('Select saved drawing') as HTMLSelectElement).value).toBe('');
 fireEvent.change(screen.getByLabelText('Drawing color'),{target:{value:'#112233'}});
 fireEvent.change(screen.getByLabelText('Annotation text'),{target:{value:'New annotation'}});
 expect(mock.api.mock.calls.filter(c=>c[0]==='chart_drawing_save')).toHaveLength(0);
 expect(saved.drawings[0]).toEqual(drawing);
 const canvas=screen.getByLabelText('Price chart drawing canvas');
 fireEvent.pointerDown(canvas,{clientX:50,clientY:200,button:0});fireEvent.pointerUp(canvas);
 await waitFor(()=>expect(saved.drawings).toHaveLength(2));
 expect(saved.drawings[1]).toMatchObject({kind:'text',color:'#112233',text:'New annotation'});
 expect(saved.drawings[0]).toEqual(drawing);
});

it('edits custom Fib ratios and names, rejects invalid input, resets and undoes without rewriting legacy on read',async()=>{
 saved.drawings=[{...drawing,kind:'fib'}];const {container}=render(<ChartDrawings {...props}/>);await ready();
 expect(mock.api.mock.calls.filter(c=>c[0]==='chart_drawing_save')).toHaveLength(0);
 fireEvent.change(screen.getByLabelText('Select saved drawing'),{target:{value:'d1'}});
 expect((screen.getByLabelText('Fibonacci levels') as HTMLInputElement).value).toBe('0, 0.236, 0.382, 0.5, 0.618, 0.786, 1');
 for(const value of ['','0,0','NaN','Infinity','6','0,','0x1']){
  fireEvent.change(screen.getByLabelText('Fibonacci levels'),{target:{value}});expect((screen.getByRole('button',{name:'Apply levels'}) as HTMLButtonElement).disabled).toBe(true);
 }
 fireEvent.change(screen.getByLabelText('Fibonacci levels'),{target:{value:'0, 0.25, 1.5, -0.5'}});fireEvent.click(screen.getByRole('button',{name:'Apply levels'}));
 await waitFor(()=>expect(saved.drawings[0].levels).toEqual([0,.25,1.5,-.5]));
 await waitFor(()=>expect(container.querySelector('svg')?.textContent).toContain('0.25 · 12.5'));
 expect(container.querySelector('svg')?.textContent).toContain('1.5 · 25');expect(container.querySelector('svg')?.textContent).toContain('-0.5 · 5');
 fireEvent.change(screen.getByLabelText('Drawing name'),{target:{value:'Retracement study'}});fireEvent.click(screen.getByRole('button',{name:'Rename drawing'}));
 await waitFor(()=>expect(screen.getByLabelText('Select saved drawing').textContent).toContain('Retracement study'));
 fireEvent.click(screen.getByRole('button',{name:'Reset levels'}));await waitFor(()=>expect(saved.drawings[0].levels).toHaveLength(7));
 fireEvent.click(screen.getByRole('button',{name:'Undo drawing'}));await waitFor(()=>expect(saved.drawings[0].levels).toEqual([0,.25,1.5,-.5]));
 expect(saved.drawings[0].name).toBe('Retracement study');
});

it('preserves independent unsaved name and Fib drafts across unrelated property saves',async()=>{
 saved.drawings=[{...drawing,kind:'fib',levels:[0,1],name:'Initial'}];render(<ChartDrawings {...props}/>);await ready();
 fireEvent.change(screen.getByLabelText('Select saved drawing'),{target:{value:'d1'}});
 fireEvent.change(screen.getByLabelText('Fibonacci levels'),{target:{value:'0, 0.25, 1'}});
 fireEvent.change(screen.getByLabelText('Drawing name'),{target:{value:'Renamed'}});fireEvent.click(screen.getByRole('button',{name:'Rename drawing'}));
 await waitFor(()=>expect((screen.getByLabelText('Drawing name') as HTMLInputElement).disabled).toBe(false));
 expect(saved.drawings[0].name).toBe('Renamed');
 expect((screen.getByLabelText('Fibonacci levels') as HTMLInputElement).value).toBe('0, 0.25, 1');
 fireEvent.change(screen.getByLabelText('Drawing name'),{target:{value:'Unsaved name'}});fireEvent.click(screen.getByRole('button',{name:'Apply levels'}));
 await waitFor(()=>expect(saved.drawings[0].levels).toEqual([0,.25,1]));
 expect((screen.getByLabelText('Drawing name') as HTMLInputElement).value).toBe('Unsaved name');
 fireEvent.change(screen.getByLabelText('Drawing color'),{target:{value:'#123456'}});await waitFor(()=>expect(saved.drawings[0].color).toBe('#123456'));
 expect((screen.getByLabelText('Drawing name') as HTMLInputElement).value).toBe('Unsaved name');
});

it('projects reversed custom Fib levels in price space under nonlinear scales and omits nonpositive prices',async()=>{
 saved.drawings=[{...drawing,kind:'fib',anchors:[{time:60,price:200},{time:120,price:100}],levels:[0,.25,1,1.5,3]}];
 const nonlinear={current:{priceToCoordinate:(n:number)=>Math.log(n)*10,coordinateToPrice:(n:number)=>Math.exp(n/10)}};
 const {container}=render(<ChartDrawings {...props} series={nonlinear}/>);await ready();
 await waitFor(()=>expect(container.querySelector('svg')?.textContent).toContain('0.25 · 175'));
 expect(container.querySelector('svg')?.textContent).toContain('1.5 · 50');expect(container.querySelector('svg')?.textContent).not.toContain('3 · -100');
 const label=Array.from(container.querySelectorAll('svg text')).find(n=>n.textContent==='0.25 · 175')!;
 expect(Number(label.getAttribute('y'))).toBeCloseTo(Math.log(175)*10-4);
});
