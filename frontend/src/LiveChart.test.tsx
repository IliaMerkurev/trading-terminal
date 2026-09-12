import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import LiveChart from './LiveChart';
const mock=vi.hoisted(()=>({api:vi.fn(),setData:vi.fn(),remove:vi.fn(),fit:vi.fn(),pane:vi.fn()}));
vi.mock('./api',()=>({api:mock.api}));
vi.mock('lightweight-charts',()=>({CandlestickSeries:'candle',LineSeries:'line',ColorType:{Solid:'solid'},createSeriesMarkers:()=>({setMarkers:vi.fn()}),createChart:()=>({addSeries:()=>({setData:mock.setData,applyOptions:vi.fn(),moveToPane:mock.pane,createPriceLine:vi.fn(),removePriceLine:vi.fn()}),remove:mock.remove,timeScale:()=>({fitContent:mock.fit})})}));

it('chart interval updates only presentation, maintains recorded values and cleans up',async()=>{
 mock.api.mockResolvedValue({candles:[{time:0,open:100,high:110,low:90,close:105,volume:1}],evaluations:[{time:60,values:{ema:102.5}}],signals:[],fills:[]});
 const {unmount}=render(<LiveChart sessionId="s" fresh/>);
 await waitFor(()=>expect(mock.setData).toHaveBeenCalledWith(expect.arrayContaining([expect.objectContaining({close:105,time:60})])));
 fireEvent.change(screen.getByLabelText('Chart display timeframe'),{target:{value:'60'}});
 fireEvent.change(screen.getByLabelText('Live chart indicator'),{target:{value:'ema'}});
 await waitFor(()=>expect(mock.setData).toHaveBeenCalledWith([{time:3600,value:102.5,observed:60}]));
 expect(mock.api.mock.calls.every(call=>call[0]==='live_chart'&&Object.keys(call[1]).join(',')==='session_id')).toBe(true);
 unmount();expect(mock.remove).toHaveBeenCalledOnce();
});

it('fits after initial recovery and allocates an indicator pane only when selected',async()=>{
 mock.fit.mockClear();mock.pane.mockClear();
 mock.api.mockResolvedValue({candles:[{time:0,open:100,high:110,low:90,close:105,volume:1}],evaluations:[{time:60,values:{ema:102.5}}]});
 const {rerender}=render(<LiveChart sessionId="recovery" fresh={false}/>);
 await waitFor(()=>expect(mock.fit).toHaveBeenCalledOnce());
 expect(mock.pane).toHaveBeenLastCalledWith(0);
 rerender(<LiveChart sessionId="recovery" fresh/>);
 await waitFor(()=>expect(mock.fit).toHaveBeenCalledTimes(2));
 rerender(<LiveChart sessionId="recovery" fresh price="106"/>);
 expect(mock.fit).toHaveBeenCalledTimes(2);
 fireEvent.change(screen.getByLabelText('Live chart indicator'),{target:{value:'ema'}});
 expect(mock.pane).toHaveBeenLastCalledWith(1);
 fireEvent.change(screen.getByLabelText('Live chart indicator'),{target:{value:''}});
 expect(mock.pane).toHaveBeenLastCalledWith(0);
});
