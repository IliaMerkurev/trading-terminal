import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import LiveChart from './LiveChart';
const mock=vi.hoisted(()=>({api:vi.fn(),setData:vi.fn(),remove:vi.fn(),fit:vi.fn(),pane:vi.fn()}));
vi.mock('./api',()=>({api:mock.api}));
vi.mock('lightweight-charts',()=>({CandlestickSeries:'candle',LineSeries:'line',ColorType:{Solid:'solid'},createSeriesMarkers:()=>({setMarkers:vi.fn()}),createChart:()=>({addSeries:()=>({setData:mock.setData,applyOptions:vi.fn(),moveToPane:mock.pane,createPriceLine:vi.fn(),removePriceLine:vi.fn()}),remove:mock.remove,timeScale:()=>({fitContent:mock.fit,subscribeVisibleLogicalRangeChange:vi.fn(),unsubscribeVisibleLogicalRangeChange:vi.fn(),getVisibleLogicalRange:()=>null})})}));

it('chart interval updates only presentation, maintains recorded values and cleans up',async()=>{
 mock.api.mockResolvedValue({candles:[{time:0,open:100,high:110,low:90,close:105,volume:1}],evaluations:[{time:60,values:{ema:102.5}}],signals:[],fills:[]});
 const {unmount}=render(<LiveChart sessionId="s" fresh/>);
 await waitFor(()=>expect(mock.setData).toHaveBeenCalledWith(expect.arrayContaining([expect.objectContaining({close:105,time:60})])));
 fireEvent.change(screen.getByLabelText('Chart display timeframe'),{target:{value:'60'}});
 fireEvent.change(screen.getByLabelText('Live chart indicator'),{target:{value:'ema'}});
 await waitFor(()=>expect(mock.setData).toHaveBeenCalledWith([{time:3600,value:102.5,observed:60}]));
 expect(mock.api.mock.calls.every(call=>['live_chart','market_chart'].includes(call[0]))).toBe(true);
 expect(mock.api).toHaveBeenCalledWith('market_chart',{market:'spot',symbol:'BTCUSDT',minutes:60,before:null});
 unmount();expect(mock.remove).toHaveBeenCalledOnce();
});

it('does not refit on strategy readiness and allocates an indicator pane only when selected',async()=>{
 mock.fit.mockClear();mock.pane.mockClear();
 mock.api.mockResolvedValue({candles:[{time:0,open:100,high:110,low:90,close:105,volume:1}],evaluations:[{time:60,values:{ema:102.5}}]});
 const {rerender}=render(<LiveChart sessionId="recovery" fresh={false}/>);
 await waitFor(()=>expect(mock.fit).toHaveBeenCalledOnce());
 expect(mock.pane).toHaveBeenLastCalledWith(0);
 rerender(<LiveChart sessionId="recovery" fresh/>);
 await waitFor(()=>expect(mock.fit).toHaveBeenCalledTimes(1));
 rerender(<LiveChart sessionId="recovery" fresh price="106"/>);
 expect(mock.fit).toHaveBeenCalledTimes(1);
 fireEvent.change(screen.getByLabelText('Live chart indicator'),{target:{value:'ema'}});
 expect(mock.pane).toHaveBeenLastCalledWith(1);
 fireEvent.change(screen.getByLabelText('Live chart indicator'),{target:{value:''}});
 expect(mock.pane).toHaveBeenLastCalledWith(0);
});

it('loads the market without a strategy and does not reset candles when one is selected',async()=>{
 mock.api.mockClear();mock.fit.mockClear();
 mock.api.mockResolvedValue({candles:[{time:0,open:100,high:110,low:90,close:105,volume:1}],evaluations:[],signals:[],fills:[]});
 const {rerender}=render(<LiveChart fresh market="linear" symbol="BTCUSDT"/>);
 await waitFor(()=>expect(mock.fit).toHaveBeenCalledOnce());
 expect(mock.api).toHaveBeenCalledWith('market_chart',{market:'linear',symbol:'BTCUSDT',minutes:1,before:null});
 expect(mock.api.mock.calls.some(c=>c[0]==='live_chart')).toBe(false);
 rerender(<LiveChart fresh market="linear" symbol="BTCUSDT" sessionId="selected"/>);
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('live_chart',{session_id:'selected'}));
 expect(mock.fit).toHaveBeenCalledOnce();
 expect(mock.api.mock.calls.some(c=>c[0]==='live_start_terminal')).toBe(false);
});

it('requests older history only on demand with the oldest exclusive cursor',async()=>{
 mock.api.mockClear();mock.fit.mockClear();
 mock.api.mockImplementation(async(command:string,params:any)=>({candles:[{time:600,open:100,high:110,low:90,close:105,volume:1}],loading:false,evaluations:[],signals:[],fills:[]}));
 render(<LiveChart fresh/>);
 await waitFor(()=>expect((screen.getByRole('button',{name:'Older history'}) as HTMLButtonElement).disabled).toBe(false));
 expect(mock.api.mock.calls.some(c=>c[1]?.before!=null)).toBe(false);
 fireEvent.click(screen.getByRole('button',{name:'Older history'}));
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('market_chart',{market:'spot',symbol:'BTCUSDT',minutes:1,before:600}),{timeout:2500});
});
