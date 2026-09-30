import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,within} from '@testing-library/react';
import StrategyLibrary from './StrategyLibrary';
import {api} from './api';
import {defaultProfile} from './model';
vi.mock('./api',()=>({api:vi.fn()}));
const entry={id:'rsi-threshold',version:1,name:'RSI threshold reversion',family:'mean_reversion',kind:'Adapted',source_url:'https://example.org/source',license:'Apache-2.0',markets:['spot'],directions:['long'],source_default_minutes:1440,author_recommended_minutes:null,local_default_minutes:1440,timeframes:[1,60,1440],timeframe_evidence:'Daily is a source default.',adaptation:'Long only.',review:'Static review.',compatibility:'Closed bars.',verification:'Integration pending.',parameters:{period:{type:'integer',default:14,min:2,max:1000}}};

it('opens a visible setup on every card click and returns keyboard focus without starting work',async()=>{
 vi.mocked(api).mockImplementation(async(command)=>command==='library_catalog'?[entry]:command==='library_batches'?[]:{});
 render(<StrategyLibrary onCopy={vi.fn()} profile={defaultProfile}/>);
 const trigger=await screen.findByRole('button',{name:'Test this strategy'});
 trigger.focus();fireEvent.click(trigger);
 const dialog=screen.getByRole('dialog',{name:'Set up backtest'});
 expect(within(dialog).getByText(entry.name)).toBeTruthy();
 expect(within(dialog).getByRole('button',{name:'Prepare market data'})).toBeTruthy();
 expect(document.activeElement?.id).toBe('test-setup');
 fireEvent.change(within(dialog).getByLabelText('DCA schedule'),{target:{value:'monthly'}});
 fireEvent(dialog,new Event('cancel',{bubbles:false,cancelable:true}));
 expect(screen.queryByRole('dialog')).toBeNull();
 expect(document.activeElement).toBe(trigger);
 fireEvent.click(trigger);
 expect(screen.getAllByRole('dialog')).toHaveLength(1);
 expect((within(screen.getByRole('dialog')).getByLabelText('DCA schedule') as HTMLSelectElement).value).toBe('monthly');
 expect(screen.getAllByLabelText('Batch dataset')).toHaveLength(1);
 fireEvent.click(screen.getByRole('button',{name:'Back to strategies'}));
 expect(screen.queryByRole('dialog')).toBeNull();
 expect(vi.mocked(api).mock.calls.some(([command])=>/start|cancel|trust/.test(command))).toBe(false);
});

it('explains a selected timeframe that cannot use the source interval instead of leaving an inert test',async()=>{
 vi.mocked(api).mockImplementation(async(command)=>command==='library_catalog'?[{...entry,timeframes:[60,240,360,1440]}]:command==='library_batches'?[]:{});
 render(<StrategyLibrary onCopy={vi.fn()} profile={{...defaultProfile,execution_minutes:240}} onProfile={vi.fn()} datasets={[{id:'h4',market:'spot',symbol:'BTCUSDT',interval_seconds:14400,range:[0,172800],source:'Synthetic'}]}/>);
 fireEvent.change(await screen.findByLabelText(entry.name+' timeframe'),{target:{value:'360'}});
 fireEvent.click(screen.getByRole('button',{name:'Test this strategy'}));
 expect(screen.getByRole('alert').textContent).toContain('6h cannot use 4h history. Choose 1h');
 fireEvent.change(screen.getByLabelText('Batch dataset'),{target:{value:'h4'}});
 expect((screen.getByRole('button',{name:'Review test'}) as HTMLButtonElement).disabled).toBe(true);
 expect(vi.mocked(api).mock.calls.some(([command])=>command==='library_batch_start')).toBe(false);
});

it('browses without execution or invented metrics and copies explicit timeframe/parameters',async()=>{
 const onCopy=vi.fn(async()=>{});
 vi.mocked(api).mockImplementation(async(command)=>command==='library_catalog'?[entry]:{strategy_id:'copy-1'});
 render(<StrategyLibrary onCopy={onCopy}/>);
 const card=await screen.findByRole('article',{name:entry.name});
 expect(api).toHaveBeenCalledTimes(1);
 expect(within(card).getByRole('status').textContent).toContain('Performance: N/A');
 expect(card.textContent).toContain('Author recommendation: unknown');
 fireEvent.change(within(card).getByLabelText(entry.name+' timeframe'),{target:{value:'60'}});
 fireEvent.change(within(card).getByLabelText(entry.name+' period'),{target:{value:'7'}});
 fireEvent.click(within(card).getByRole('button',{name:'Customize strategy'}));
 await vi.waitFor(()=>expect(onCopy).toHaveBeenCalledWith('copy-1'));
 expect(api).toHaveBeenCalledWith('library_copy',{entry_id:'rsi-threshold',version:1,minutes:60,parameters:{period:7}});
});

it('shows copy errors without navigating or granting consent',async()=>{
 const onCopy=vi.fn();vi.mocked(api).mockImplementation(async(command)=>{if(command==='library_catalog')return [entry];throw Error('Source review required');});
 render(<StrategyLibrary onCopy={onCopy}/>);
 fireEvent.click(await screen.findByRole('button',{name:'Customize strategy'}));
 expect((await screen.findByRole('alert')).textContent).toContain('Source review required');
 expect(onCopy).not.toHaveBeenCalled();
});

it('previews explicit timeframe variants from one selected card',async()=>{
 vi.mocked(api).mockImplementation(async(command)=>{
  if(command==='library_catalog')return [{...entry,timeframes:[60,240,1440]}];
  if(command==='library_batches')return [];
  if(command==='library_warmup')return {start:86400,end:172800,available:true};
  if(command==='library_batch_preview')return {rows:[],modeled_minutes:0};
  return {};
 });
 render(<StrategyLibrary onCopy={vi.fn()} profile={{...defaultProfile,execution_minutes:60}} datasets={[{id:'h1',market:'spot',symbol:'BTCUSDT',interval_seconds:3600,range:[0,172800],source:'Synthetic'}]}/>);
 fireEvent.click(await screen.findByLabelText('Include '+entry.name));
 fireEvent.click(screen.getByRole('button',{name:entry.name+' compare 4h'}));
 fireEvent.change(screen.getByLabelText('Batch dataset'),{target:{value:'h1'}});
 await vi.waitFor(()=>expect((screen.getByRole('button',{name:'Review test'}) as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(screen.getByRole('button',{name:'Review test'}));
 await vi.waitFor(()=>expect(api).toHaveBeenCalledWith('library_batch_preview',expect.objectContaining({selections:[{entry_id:entry.id,version:1,minutes:240,parameters:{period:14}},{entry_id:entry.id,version:1,minutes:1440,parameters:{period:14}}]})));
});
