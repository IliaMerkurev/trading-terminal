import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import ReplayControl from './ReplayControl';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));

it('reports background progress and cancellation without a successful result',async()=>{
 let job:any=null;
 vi.mocked(api).mockImplementation(async(command:string)=>{
  if(command==='live_replay'){job={id:'j',session_id:'s',status:'running',progress:{processed:2,total:50}};return {replay_id:'j'};}
  if(command==='replay_cancel')job={...job,status:'cancelled',result:null};
  return job;
 });
 render(<ReplayControl sessionId="s" active={false}/>);
 fireEvent.click(screen.getByRole('button',{name:'Verify recorded signals with replay'}));
 expect(await screen.findByText('Replay: running · 2 / 50 candles')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Cancel replay'}));
 expect(await screen.findByText('Replay: cancelled')).toBeTruthy();
 expect(api).toHaveBeenCalledWith('replay_cancel',{replay_id:'j'});
 expect(screen.queryByText(/MATCH/)).toBeNull();
});

it('restores a persisted result and distinguishes a failed job',async()=>{
 let job:any={id:'j',session_id:'s',status:'completed',result:{match:true,checked_events:3}};
 vi.mocked(api).mockImplementation(async()=>job);
 render(<ReplayControl sessionId="s" active={false}/>);
 expect(await screen.findByText(/MATCH — 3 recorded signal events/)).toBeTruthy();
 job={id:'j2',session_id:'s',status:'failed',error:'Synthetic replay error',result:null};
 await waitFor(()=>expect(screen.getByRole('alert').textContent).toBe('Synthetic replay error'),{timeout:2000});
 expect(screen.queryByText(/MATCH/)).toBeNull();
});
