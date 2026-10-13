import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,within} from '@testing-library/react';
import {useState} from 'react';
import StrategyLibrary from './StrategyLibrary';
import {api} from './api';
import {defaultProfile,type Profile} from './model';
vi.mock('./api',()=>({api:vi.fn()}));
const entry={id:'rsi-threshold',version:1,name:'RSI threshold reversion',family:'mean_reversion',kind:'Adapted',source_url:'https://example.org/source',license:'Apache-2.0',markets:['spot'],directions:['long'],source_default_minutes:1440,author_recommended_minutes:null,local_default_minutes:1440,timeframes:[1,60,1440],timeframe_evidence:'Daily is a source default.',adaptation:'Long only.',review:'Static review.',compatibility:'Closed bars.',verification:'Integration pending.',parameters:{period:{type:'integer',default:14,min:2,max:1000}}};

it('keeps independent Lab and Saved tests scroll offsets across visible and hidden route returns',async()=>{
 vi.mocked(api).mockClear().mockImplementation(async command=>command==='library_catalog'?[entry]:command==='library_batch_history'?{rows:[],next:null}:{});
 const props={onCopy:vi.fn(),profile:defaultProfile};
 const surface=(view:'catalog'|'saved',hidden=false)=><div hidden={hidden}><StrategyLibrary {...props} view={view} suspendSetup={hidden}/></div>;
 const {container,rerender}=render(surface('catalog'));
 const card=await screen.findByRole('article',{name:entry.name});
 const host=container.querySelector<HTMLElement>('.lab-studio')!;
 const input=within(card).getByLabelText(`${entry.name} period`);
 fireEvent.change(input,{target:{value:'7'}});fireEvent.click(within(card).getByLabelText(`Include ${entry.name}`));
 host.scrollTop=465;fireEvent.scroll(host);
 rerender(surface('saved'));expect(host.scrollTop).toBe(0);
 host.scrollTop=120;fireEvent.scroll(host);
 rerender(surface('catalog'));expect(host.scrollTop).toBe(465);
 expect(screen.getByRole('article',{name:entry.name})).toBe(card);
 expect((input as HTMLInputElement).value).toBe('7');
 expect((within(card).getByLabelText(`Include ${entry.name}`) as HTMLInputElement).checked).toBe(true);
 rerender(surface('saved'));expect(host.scrollTop).toBe(120);
 // App keeps the library mounted but switches its view to catalog off-route.
 rerender(surface('catalog',true));host.scrollTop=0;fireEvent.scroll(host);
 rerender(surface('catalog'));expect(host.scrollTop).toBe(465);
 input.focus();host.scrollTop=530;fireEvent.scroll(host);
 rerender(surface('catalog'));expect(host.scrollTop).toBe(530);expect(document.activeElement).toBe(input);
 expect(vi.mocked(api).mock.calls.some(([command])=>/preview|start|trust|library_copy/.test(command))).toBe(false);
});

it('opens a visible setup on every card click and returns keyboard focus without starting work',async()=>{
 vi.mocked(api).mockImplementation(async(command)=>command==='library_catalog'?[entry]:command==='library_batch_history'?{rows:[],next:null}:{});
 render(<StrategyLibrary onCopy={vi.fn()} profile={defaultProfile}/>);
 const trigger=await screen.findByRole('button',{name:'Test this strategy'});
 expect(screen.getByRole('region',{name:'Current test context'})).toBeTruthy();
 expect(screen.queryByLabelText('Batch dataset')).toBeNull();
 trigger.focus();fireEvent.click(trigger);
 const dialog=screen.getByRole('dialog',{name:'Set up backtest'});
 const summary=within(dialog).getByText('1 selected test · 1 strategy · 1 timeframe',{selector:'summary'});
 expect(summary.closest('details')?.open).toBe(false);
 // jsdom exposes closed-details descendants; assert the native disclosure boundary.
 expect(within(dialog).getByRole('region',{name:'Selected test details'}).closest('details:not([open])')).toBe(summary.parentElement);
 expect(within(dialog).getByRole('button',{name:'Prepare market data'})).toBeTruthy();
 expect(document.activeElement?.id).toBe('test-setup');
 summary.focus();expect(document.activeElement).toBe(summary);fireEvent.click(summary);
 const selection=within(dialog).getByRole('region',{name:'Selected test details'});
 expect(selection.getAttribute('tabindex')).toBe('0');
 expect(within(selection).getByText(entry.name)).toBeTruthy();
 expect(within(selection).getByText('rsi-threshold · v1')).toBeTruthy();
 expect(within(selection).getByText('Parameters: period: 14')).toBeTruthy();
 expect(within(selection).getByText('1d')).toBeTruthy();
 fireEvent.change(within(dialog).getByLabelText('DCA schedule'),{target:{value:'monthly'}});
 fireEvent(dialog,new Event('cancel',{bubbles:false,cancelable:true}));
 expect(screen.queryByRole('dialog')).toBeNull();
 expect(document.activeElement).toBe(trigger);
 expect(screen.queryByLabelText('Batch dataset')).toBeNull();
 fireEvent.click(trigger);
 expect(screen.getAllByRole('dialog')).toHaveLength(1);
 expect((within(screen.getByRole('dialog')).getByLabelText('DCA schedule') as HTMLSelectElement).value).toBe('monthly');
 expect(screen.getByText('1 selected test · 1 strategy · 1 timeframe',{selector:'summary'}).closest('details')?.open).toBe(false);
 expect(screen.getAllByLabelText('Batch dataset')).toHaveLength(1);
 fireEvent.click(screen.getByRole('button',{name:'Back to strategies'}));
 expect(screen.queryByRole('dialog')).toBeNull();
 expect(vi.mocked(api).mock.calls.some(([command])=>/start|cancel|trust/.test(command))).toBe(false);
});

it('keeps history, dates, capital and costs when an expanded selection is dismissed and reopened',async()=>{
 vi.mocked(api).mockClear().mockImplementation(async command=>command==='library_catalog'?[entry]:command==='library_batch_history'?{rows:[],next:null}:command==='library_warmup'?{start:86400,end:259200,available:true}:{});
 function EditableLibrary(){const [profile,setProfile]=useState<Profile>({...defaultProfile,execution_minutes:60});return <StrategyLibrary onCopy={vi.fn()} profile={profile} onProfile={setProfile} datasets={[{id:'history',market:'spot',symbol:'BTCUSDT',interval_seconds:3600,range:[0,259200],source:'Synthetic'}]}/>;}
 render(<EditableLibrary/>);
 const trigger=await screen.findByRole('button',{name:'Test this strategy'});trigger.focus();fireEvent.click(trigger);
 fireEvent.change(screen.getByLabelText('Batch dataset'),{target:{value:'history'}});
 await vi.waitFor(()=>expect((screen.getByRole('button',{name:'Review test'}) as HTMLButtonElement).disabled).toBe(false));
 fireEvent.change(screen.getByLabelText('Evaluation start (UTC)'),{target:{value:'1970-01-02T12:00'}});
 fireEvent.change(screen.getByLabelText('Research capital'),{target:{value:'2500'}});
 fireEvent.click(screen.getByText('Costs, sizing & execution assumptions',{selector:'summary'}));
 fireEvent.change(screen.getByLabelText('Fee per fill'),{target:{value:'0.15'}});
 fireEvent.change(screen.getByLabelText('Adverse slippage'),{target:{value:'0.02'}});
 fireEvent.click(screen.getByText('1 selected test · 1 strategy · 1 timeframe',{selector:'summary'}));
 fireEvent(screen.getByRole('dialog'),new Event('cancel',{bubbles:false,cancelable:true}));
 expect(document.activeElement).toBe(trigger);
 fireEvent.click(trigger);
 expect(screen.getAllByRole('dialog')).toHaveLength(1);
 for(const [label,value] of [['Batch dataset','history'],['Research market','spot'],['Research instrument','BTCUSDT'],['Research resolution','60'],['Evaluation start (UTC)','1970-01-02T12:00'],['Evaluation end, exclusive (UTC)','1970-01-04T00:00'],['Research capital','2500'],['Fee per fill','0.15'],['Adverse slippage','0.02']])expect((screen.getByLabelText(label) as HTMLInputElement).value).toBe(value);
 fireEvent.click(screen.getByRole('button',{name:'Back to strategies'}));
 expect(document.activeElement).toBe(trigger);
 expect(vi.mocked(api).mock.calls.some(([command])=>/preview|start|cancel|trust|library_copy/.test(command))).toBe(false);
});

it('explains a selected timeframe that cannot use the source interval instead of leaving an inert test',async()=>{
 vi.mocked(api).mockImplementation(async(command)=>command==='library_catalog'?[{...entry,timeframes:[60,240,360,1440]}]:command==='library_batch_history'?{rows:[],next:null}:{});
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
  if(command==='library_batch_history')return {rows:[],next:null};
  if(command==='library_warmup')return {start:86400,end:172800,available:true};
  if(command==='library_batch_preview')return {rows:[],modeled_minutes:0};
  return {};
 });
 render(<StrategyLibrary onCopy={vi.fn()} profile={{...defaultProfile,execution_minutes:60}} datasets={[{id:'h1',market:'spot',symbol:'BTCUSDT',interval_seconds:3600,range:[0,172800],source:'Synthetic'}]}/>);
 fireEvent.click(await screen.findByLabelText('Include '+entry.name));
 fireEvent.click(screen.getByRole('button',{name:entry.name+' compare 4h'}));
 fireEvent.click(screen.getByRole('button',{name:'Edit test setup'}));
 fireEvent.change(screen.getByLabelText('Batch dataset'),{target:{value:'h1'}});
 await vi.waitFor(()=>expect((screen.getByRole('button',{name:'Review test'}) as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(screen.getByRole('button',{name:'Review test'}));
 await vi.waitFor(()=>expect(api).toHaveBeenCalledWith('library_batch_preview',expect.objectContaining({selections:[{entry_id:entry.id,version:1,minutes:240,parameters:{period:14}},{entry_id:entry.id,version:1,minutes:1440,parameters:{period:14}}]})));
});


it('batches every catalog card despite filters with shared settings and fixed per-strategy parameters',async()=>{
 const entries=Array.from({length:7},(_,i)=>({...entry,id:`idea-${i}`,name:`Idea ${i}`,timeframes:[60,240,1440]}));
 vi.mocked(api).mockImplementation(async(command)=>command==='library_catalog'?entries:command==='library_batch_history'?{rows:[],next:null}:command==='library_warmup'?{start:86400,end:172800,available:true}:{});
 render(<StrategyLibrary onCopy={vi.fn()} profile={{...defaultProfile,execution_minutes:60}} datasets={[{id:'history',market:'spot',symbol:'BTCUSDT',interval_seconds:3600,range:[0,172800],source:'Synthetic'}]}/>);
 await screen.findByRole('article',{name:'Idea 0'});
 fireEvent.change(screen.getByLabelText('Idea 0 period'),{target:{value:'7'}});
 fireEvent.change(screen.getByLabelText('Search strategies'),{target:{value:'Idea 0'}});
 fireEvent.click(screen.getByRole('button',{name:'Test all strategies'}));
 const dialog=screen.getByRole('dialog',{name:'Set up backtest'});
 const summary=within(dialog).getByText('14 selected tests · 7 strategies · 2 timeframes',{selector:'summary'});
 expect(summary.closest('details')?.open).toBe(false);
 expect(within(dialog).getByRole('region',{name:'Selected test details'}).closest('details:not([open])')).toBe(summary.parentElement);
 fireEvent.click(summary);
 const selection=within(dialog).getByRole('region',{name:'Selected test details'});
 expect(within(selection).getAllByRole('listitem')).toHaveLength(14);
 expect(within(selection).getAllByText('Parameters: period: 7')).toHaveLength(2);
 expect(within(selection).getAllByText('Parameters: period: 14')).toHaveLength(12);
 fireEvent.click(screen.getByLabelText('Batch timeframe 1h'));
 expect(summary.textContent).toBe('21 selected tests · 7 strategies · 3 timeframes');
 expect(within(selection).getAllByRole('listitem')).toHaveLength(21);
 expect(within(selection).getAllByRole('listitem').map(row=>row.textContent)).toEqual(entries.flatMap((e,i)=>['1h','4h','1d'].map(frame=>`${e.name}${e.id} · v1Parameters: period: ${i===0?7:14}${frame}`)));
 fireEvent.click(summary);
 expect(summary.closest('details')?.open).toBe(false);
 fireEvent.change(screen.getByLabelText('Batch dataset'),{target:{value:'history'}});
 await vi.waitFor(()=>expect((screen.getByRole('button',{name:'Review test'}) as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(screen.getByRole('button',{name:'Review test'}));
 await vi.waitFor(()=>expect(api).toHaveBeenCalledWith('library_batch_preview',expect.objectContaining({dataset_id:'history',start:86400,end:172800,profile:expect.objectContaining({capital:defaultProfile.capital,fee_rate:defaultProfile.fee_rate}),selections:entries.flatMap((e,i)=>[60,240,1440].map(minutes=>({entry_id:e.id,version:1,minutes,parameters:{period:i===0?7:14}})))})));
 expect(vi.mocked(api).mock.calls.some(([command])=>/start|trust|library_copy/.test(command))).toBe(false);
});

it('discloses daily candidate authored-rule provenance and separates synthetic from empirical verification',async()=>{
 const daily={...entry,id:'double-seven-reversion',name:"Double 7's daily reversion",candidate_id:'C12',availability:'implementation_verified',timeframes:[1440],
  source_version_date:'2016-02-10',source_retrieved_date:'2026-10-11',source_sha256:'a'.repeat(64),rule_summary_version:1,
  source_hash_basis:'Exact authored UTF-8 rule bytes, not upstream page content.',empirical_validation:'not_performed',verification_artifact:'tests/test_daily_reversion.py',
  verification:'Synthetic independent fixtures only. No profitability claim.'};
 vi.mocked(api).mockClear().mockImplementation(async command=>command==='library_catalog'?[daily]:command==='library_batch_history'?{rows:[],next:null}:{});
 render(<StrategyLibrary onCopy={vi.fn()}/>);const card=await screen.findByRole('article',{name:daily.name});
 expect(within(card).getByText('Synthetic implementation verified')).toBeTruthy();
 expect(within(card).getByText('Empirical validation: not performed.')).toBeTruthy();
 expect(within(card).getByText(daily.source_hash_basis)).toBeTruthy();
 expect(within(card).getByRole('link',{name:'Inspect primary rule source ↗'}).getAttribute('href')).toBe(daily.source_url);
 expect(within(card).getByLabelText(`${daily.name} timeframe`).querySelectorAll('option')).toHaveLength(1);
});

it('retains all-strategy 4h and 1d defaults when a new card supports only daily',async()=>{
 const existing={...entry,timeframes:[60,240,1440]},daily={...entry,id:'improved-r2-reversion',name:'Improved R2 daily reversion',timeframes:[1440]};
 vi.mocked(api).mockClear().mockImplementation(async command=>command==='library_catalog'?[existing,daily]:command==='library_batch_history'?{rows:[],next:null}:command==='library_warmup'?{start:86400,end:172800,available:true}:command==='library_batch_preview'?{rows:[],contract_sha256:'f'.repeat(64)}:{});
 render(<StrategyLibrary onCopy={vi.fn()} profile={{...defaultProfile,execution_minutes:60}} datasets={[{id:'history',market:'spot',symbol:'BTCUSDT',interval_seconds:3600,range:[0,172800],source:'Synthetic'}]}/>);
 const card=await screen.findByRole('article',{name:daily.name});
 expect(within(card).getByLabelText(`${daily.name} timeframe`).querySelectorAll('option')).toHaveLength(1);
 fireEvent.click(screen.getByRole('button',{name:'Test all strategies'}));
 expect((screen.getByLabelText('Batch timeframe 4h') as HTMLInputElement).checked).toBe(true);
 expect((screen.getByLabelText('Batch timeframe 1d') as HTMLInputElement).checked).toBe(true);
 expect(screen.getByText('4 selected tests · 2 strategies · 2 timeframes',{selector:'summary'})).toBeTruthy();
 fireEvent.change(screen.getByLabelText('Batch dataset'),{target:{value:'history'}});
 await vi.waitFor(()=>expect((screen.getByRole('button',{name:'Review test'}) as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(screen.getByRole('button',{name:'Review test'}));
 await vi.waitFor(()=>expect(api).toHaveBeenCalledWith('library_batch_preview',expect.objectContaining({selections:[existing,daily].flatMap(e=>[240,1440].map(minutes=>({entry_id:e.id,version:1,minutes,parameters:{period:14}})))})));
 fireEvent.click(screen.getByRole('button',{name:'Back to strategies'}));
 fireEvent.change(screen.getByLabelText(`${existing.name} timeframe`),{target:{value:'60'}});
 await vi.waitFor(()=>expect(api).toHaveBeenCalledWith('library_warmup',expect.objectContaining({selections:[...([60,1440].map(minutes=>({entry_id:existing.id,version:1,minutes,parameters:{period:14}}))),...([240,1440].map(minutes=>({entry_id:daily.id,version:1,minutes,parameters:{period:14}})))]})));
 fireEvent.click(screen.getByLabelText(`${existing.name} compare 1d`));
 await vi.waitFor(()=>expect(api).toHaveBeenCalledWith('library_warmup',expect.objectContaining({selections:[{entry_id:existing.id,version:1,minutes:60,parameters:{period:14}},...([240,1440].map(minutes=>({entry_id:daily.id,version:1,minutes,parameters:{period:14}})))]})));

});
