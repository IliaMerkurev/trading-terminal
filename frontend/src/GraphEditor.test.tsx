import {useEffect} from 'react';
import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import GraphEditor from './GraphEditor';
import {exampleGraph} from './model';
const mock=vi.hoisted(()=>({convert:vi.fn(),fitView:vi.fn(),props:null as any}));
vi.mock('@xyflow/react',()=>({Position:{Left:'left',Right:'right'},Handle:()=>null,Background:()=>null,Controls:()=>null,
 ReactFlow:(props:any)=>{mock.props=props;useEffect(()=>{props.onInit({screenToFlowPosition:mock.convert,fitView:mock.fitView});},[]);return <div data-testid="pane" onContextMenu={props.onPaneContextMenu}>{props.children}</div>;}}));
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
