import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import HistoryWorkspace from './HistoryWorkspace';
import {defaultProfile} from './model';
const data={id:'history',market:'spot',symbol:'BTCUSDT',source:'Synthetic',interval_seconds:14400,range:[0,28800],coverage:{trade:{complete:true,count:2,gaps:[]}}};
it('updates using the saved interval and original range and selects existing history',()=>{
 const onPrepare=vi.fn(),onUse=vi.fn();
 render(<HistoryWorkspace datasets={[data]} profile={defaultProfile} status={null} onPrepare={onPrepare} onUse={onUse} onCancel={vi.fn()} disabled={false}/>);
 fireEvent.click(screen.getByRole('button',{name:'Update to latest'}));
 expect(onPrepare).toHaveBeenCalledWith(expect.objectContaining({market:'spot',symbol:'BTCUSDT',minutes:240,start:0}));
 expect(onPrepare.mock.calls[0][0].end%14400).toBe(0);
 fireEvent.click(screen.getByRole('button',{name:'Use for research →'}));
 expect(onUse).toHaveBeenCalledWith(data);
});
it('does not call trade-only perpetual history complete',()=>{
 render(<HistoryWorkspace datasets={[{...data,market:'linear',coverage:{...data.coverage,mark:{complete:false},funding:{complete_against_current_interval:false}}}]} profile={defaultProfile} status={null} onPrepare={vi.fn()} onUse={vi.fn()} onCancel={vi.fn()} disabled={false}/>);
 expect(screen.getByText('Incomplete coverage')).toBeTruthy();
 expect((screen.getByRole('button',{name:'Use for research →'}) as HTMLButtonElement).disabled).toBe(true);
});
