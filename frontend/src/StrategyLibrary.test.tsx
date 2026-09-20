import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,within} from '@testing-library/react';
import StrategyLibrary from './StrategyLibrary';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
const entry={id:'rsi-threshold',version:1,name:'RSI threshold reversion',family:'mean_reversion',kind:'Adapted',source_url:'https://example.org/source',license:'Apache-2.0',markets:['spot'],directions:['long'],source_default_minutes:1440,author_recommended_minutes:null,local_default_minutes:1440,timeframes:[1,60,1440],timeframe_evidence:'Daily is a source default.',adaptation:'Long only.',review:'Static review.',compatibility:'Closed bars.',verification:'Integration pending.',parameters:{period:{type:'integer',default:14,min:2,max:1000}}};

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
 fireEvent.click(within(card).getByRole('button',{name:'Create my copy'}));
 await vi.waitFor(()=>expect(onCopy).toHaveBeenCalledWith('copy-1'));
 expect(api).toHaveBeenCalledWith('library_copy',{entry_id:'rsi-threshold',version:1,minutes:60,parameters:{period:7}});
});

it('shows copy errors without navigating or granting consent',async()=>{
 const onCopy=vi.fn();vi.mocked(api).mockImplementation(async(command)=>{if(command==='library_catalog')return [entry];throw Error('Source review required');});
 render(<StrategyLibrary onCopy={onCopy}/>);
 fireEvent.click(await screen.findByRole('button',{name:'Create my copy'}));
 expect((await screen.findByRole('alert')).textContent).toContain('Source review required');
 expect(onCopy).not.toHaveBeenCalled();
});
