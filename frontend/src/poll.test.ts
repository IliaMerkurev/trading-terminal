import {it,expect,vi} from 'vitest';
import {poll} from './poll';
it('does not queue slow requests or publish a disposed response',async()=>{
  vi.useFakeTimers();
  try{
    let resolve!:(value:number)=>void;
    const read=vi.fn(()=>new Promise<number>(r=>{resolve=r;})),receive=vi.fn(),fail=vi.fn();
    const stop=poll(read,receive,fail,500);
    await vi.advanceTimersByTimeAsync(10000);
    expect(read).toHaveBeenCalledTimes(1);
    resolve(1);await vi.advanceTimersByTimeAsync(0);
    expect(receive).toHaveBeenCalledWith(1);
    await vi.advanceTimersByTimeAsync(500);expect(read).toHaveBeenCalledTimes(2);
    stop();resolve(2);await vi.advanceTimersByTimeAsync(10000);
    expect(receive).toHaveBeenCalledTimes(1);expect(fail).not.toHaveBeenCalled();
    expect(read).toHaveBeenCalledTimes(2);
  }finally{vi.useRealTimers();}
});
