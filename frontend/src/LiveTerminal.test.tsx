import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import Live from './Live';
import {defaultProfile} from './model';
import {OrderBookPanel,TradeTape} from './MarketPanels';
import {displayCandles,displayIndicator} from './liveChartData';
const mock=vi.hoisted(()=>({api:vi.fn()}));
vi.mock('./api',()=>({api:mock.api}));
vi.mock('./LiveChart',()=>({default:()=> <div aria-label="Live candlestick chart"/>}));
const state=()=>({active:true,terminal_state:'CONNECTED',market:{fresh:true,ticker:{lastPrice:'100'},book:{valid:true,bids:[['99','2']],asks:[['101','3']]},book_age:0,trades:[]},session:{id:'s',status:'CONNECTED',snapshot:{strategy_name:'Fixture',profile:{...defaultProfile,primary_minutes:60}}},options:{paper:true,execution_source:'manual',channels:[]},paper:{cash:'1000',equity:'1000',position:null},evaluation:{time:120,values:{'rsi.value':28.7},signals:{entry_long:true}}});

it('keeps chart-led layout, frozen strategy timeframe and switchable panels',async()=>{
 mock.api.mockResolvedValue(state());render(<Live strategyId="s" profile={defaultProfile}/>);
 await screen.findByText('Strategy timeframe: 60m / closed');
 expect(screen.getByLabelText('Live candlestick chart')).toBeTruthy();
 expect(screen.getByLabelText('Order book')).toBeTruthy();expect(screen.getByLabelText('Recent trades')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Strategy'}));
 expect(await screen.findByText('TRUE')).toBeTruthy();expect(screen.getByText('28.7')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Log'}));expect(screen.getByLabelText('Log')).toBeTruthy();
 expect(screen.getByText('Live settings')).toBeTruthy();
});

it('manual PAPER actions use a unique request and spot shorts stay disabled',async()=>{
 mock.api.mockImplementation(async(command:string)=>command==='live_status'?state():{status:'queued'});
 render(<Live strategyId="s" profile={defaultProfile}/>);
 await waitFor(()=>expect((screen.getByRole('button',{name:'Paper Buy'}) as HTMLButtonElement).disabled).toBe(false));
 expect((screen.getByRole('button',{name:'Paper Sell'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Paper Buy'}));
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('paper_manual',expect.objectContaining({session_id:'s',action:'buy',request_id:expect.stringMatching(/^[a-f0-9]{32}$/)})));
});

it('disables manual actions in Strategy source and degraded market state',async()=>{
 const s=state();s.terminal_state='DEGRADED';s.options.execution_source='strategy';mock.api.mockResolvedValue(s);
 render(<Live strategyId="s" profile={defaultProfile}/>);await screen.findByText('● DEGRADED');
 expect((screen.getByRole('button',{name:'Paper Buy'}) as HTMLButtonElement).disabled).toBe(true);
});

it('shows safe Telegram diagnostics without credential fields in reports',async()=>{
 mock.api.mockResolvedValue({...state(),log:[{time:1000,message:'Telegram test failed: chat not found. Check the Chat ID and start the bot.'}]});
 render(<Live strategyId="s" profile={defaultProfile}/>);fireEvent.click(screen.getByRole('button',{name:'Notifications'}));
 expect(await screen.findByText(/Telegram test failed: chat not found/)).toBeTruthy();expect(screen.queryByLabelText('Bot token')).toBeNull();
});

it('book renders updated snapshot without removed levels and caps both sides',()=>{
 const {rerender}=render(<OrderBookPanel book={{valid:true,bids:[['99','2']],asks:[['101','3']]}} age={0} active/>);
 expect(screen.getByText('99')).toBeTruthy();
 rerender(<OrderBookPanel book={{valid:true,bids:[['98','4']],asks:[['101','3']]}} age={0} active/>);
 expect(screen.queryByText('99')).toBeNull();expect(screen.getByText('98')).toBeTruthy();
 rerender(<OrderBookPanel book={{valid:false,bids:[],asks:[]}} age={null} active/>);expect(screen.getByText('Waiting / stale')).toBeTruthy();
});

it('tape rendering stays bounded and preserves observed taker direction',()=>{
 const trades=Array.from({length:200},(_,i)=>({id:String(i),time:1000+i,price:String(100+i),size:'1',side:i%2?'Buy':'Sell'}));
 const {container}=render(<TradeTape trades={trades} active/>);
 expect(container.querySelectorAll('.tape-rows>div').length).toBe(50);
 expect(screen.getAllByText('Buy').length).toBe(25);
});

it('display aggregation is causal, deduplicated and never mutates input',()=>{
 const bars=[{time:0,open:100,high:105,low:99,close:102,volume:1},{time:60,open:102,high:110,low:101,close:108,volume:2}];
 const original=JSON.stringify(bars);const formed={time:120,open:108,high:109,low:103,close:104,volume:3};
 expect(displayCandles(bars,formed,5)).toEqual([{time:300,open:100,high:110,low:99,close:104,volume:6}]);
 expect(displayCandles(bars,{...formed,time:60,high:999},1).at(-1)?.high).toBe(110);
 expect(JSON.stringify(bars)).toBe(original);
});

it('indicator display samples only recorded IR values without recomputing indicators',()=>{
 const points=[{time:60,values:{rsi:28.7}},{time:120,values:{rsi:30.2}},{time:360,values:{rsi:55}}];
 expect(displayIndicator(points,'rsi',5)).toEqual([{time:300,value:30.2,observed:120},{time:600,value:55,observed:360}]);
});
