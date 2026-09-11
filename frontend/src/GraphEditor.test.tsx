import {useEffect} from 'react';
import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,act} from '@testing-library/react';
import GraphEditor from './GraphEditor';
import {exampleGraph} from './model';
const mock=vi.hoisted(()=>({convert:vi.fn(),fitView:vi.fn(),props:null as any}));
vi.mock('@xyflow/react',()=>({Position:{Left:'left',Right:'right'},Handle:()=>null,Background:()=>null,Controls:()=>null,
 ReactFlow:(props:any)=>{mock.props=props;useEffect(()=>{props.onInit({screenToFlowPosition:mock.convert,fitView:mock.fitView});},[]);return <div data-testid="pane" onContextMenu={props.onPaneContextMenu}>{props.children}</div>;}}));
it('retains measured node dimensions without committing a graph edit',()=>{
 const change=vi.fn();render(<GraphEditor graph={exampleGraph()} layout={{}} onChange={change} onSelect={()=>{}} onCreate={()=>{}} selected={null} locate={null} onBegin={()=>{}} onEnd={()=>{}}/>);
 act(()=>mock.props.onNodesChange([{type:'dimensions',id:'mean',dimensions:{width:200,height:110}}]));
 act(()=>mock.props.onNodesChange([{type:'select',id:'mean',selected:true}]));
 expect(mock.props.nodes.find((n:any)=>n.id==='mean').measured).toEqual({width:200,height:110});expect(change).not.toHaveBeenCalled();
});
it.each([{x:800,y:600,world:{x:123,y:-55}},{x:1800,y:1300,world:{x:-320,y:900}}])('freezes library-converted original click coordinates independently of popup clamping (%s)',({x,y,world})=>{
 mock.convert.mockReturnValue(world);const create=vi.fn(),change=vi.fn();
 render(<GraphEditor graph={exampleGraph()} layout={{}} onChange={change} onSelect={()=>{}} onCreate={create} selected={null} locate={null} onBegin={()=>{}} onEnd={()=>{}}/>);
 fireEvent.contextMenu(screen.getByTestId('pane'),{clientX:x,clientY:y});expect(mock.convert).toHaveBeenLastCalledWith({x,y});
 fireEvent.change(screen.getByLabelText('Search nodes'),{target:{value:'SMA'}});fireEvent.keyDown(screen.getByLabelText('Search nodes'),{key:'Enter'});
 expect(create).toHaveBeenCalledExactlyOnceWith('sma',world);expect(change).not.toHaveBeenCalled();expect(screen.queryByRole('dialog')).toBeNull();
});
it('canceling context search leaves graph untouched and input Ctrl+D is not a graph shortcut',()=>{
 const change=vi.fn(),create=vi.fn();render(<GraphEditor graph={exampleGraph()} layout={{}} onChange={change} onSelect={()=>{}} onCreate={create} selected="mean" locate={null} onBegin={()=>{}} onEnd={()=>{}}/>);
 fireEvent.contextMenu(screen.getByTestId('pane'),{clientX:5,clientY:5});const search=screen.getByLabelText('Search nodes');fireEvent.keyDown(search,{key:'d',ctrlKey:true});fireEvent.keyDown(search,{key:'Escape'});expect(create).not.toHaveBeenCalled();expect(change).not.toHaveBeenCalled();
});
it('Delete is scoped to the canvas and ignores typing while removing the selected node',()=>{
 const change=vi.fn();render(<GraphEditor graph={exampleGraph()} layout={{}} onChange={change} onSelect={()=>{}} onCreate={()=>{}} selected="mean" locate={null} onBegin={()=>{}} onEnd={()=>{}}/>);
 fireEvent.keyDown(document.body,{key:'Delete'});expect(change).not.toHaveBeenCalled();
 const canvas=screen.getByLabelText('Strategy canvas'),input=document.createElement('input');canvas.append(input);
 fireEvent.keyDown(input,{key:'Delete'});expect(change).not.toHaveBeenCalled();input.remove();
 fireEvent.keyDown(canvas,{key:'Delete'});expect(change).toHaveBeenCalledTimes(1);expect(change.mock.calls[0][0].nodes.map((n:any)=>n.id)).toEqual(['close','above','below']);
 expect(mock.props.deleteKeyCode).toBeNull();
});
it('node context delete is separate from canvas add and fixed outputs cannot be removed',()=>{
 const change=vi.fn();render(<GraphEditor graph={exampleGraph()} layout={{}} onChange={change} onSelect={()=>{}} onCreate={()=>{}} selected={null} locate={null} onBegin={()=>{}} onEnd={()=>{}}/>);
 const event={preventDefault:vi.fn(),stopPropagation:vi.fn(),clientX:20,clientY:30};
 act(()=>mock.props.onNodeContextMenu(event,{id:'mean'}));expect(event.stopPropagation).toHaveBeenCalled();expect(screen.queryByLabelText('Search nodes')).toBeNull();
 fireEvent.click(screen.getByRole('menuitem',{name:'Delete node'}));expect(change).toHaveBeenCalledTimes(1);
 act(()=>mock.props.onNodeContextMenu(event,{id:'out:entry_long'}));expect((screen.getByRole('menuitem',{name:'Delete node'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.keyDown(screen.getByRole('menu'),{key:'Delete'});expect(change).toHaveBeenCalledTimes(1);
 fireEvent.contextMenu(screen.getByTestId('pane'),{clientX:10,clientY:20});expect(screen.queryByRole('menu')).toBeNull();expect(screen.getByLabelText('Search nodes')).not.toBeNull();
});
