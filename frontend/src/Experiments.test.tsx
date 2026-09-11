import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import Experiments,{rankedRows} from './Experiments';
import {fillGroups} from './RunChart';
import {defaultProfile} from './model';
import {api} from './api';
vi.mock('./api',()=>({isDesktop:()=>true,api:vi.fn()}));
it('ranks only completed IS rows, keeps undefined win rate last and honors filters',()=>{
 const rows=[{ordinal:0,status:'completed',summary:{metrics:{net_pnl:'2',max_drawdown:'.1',trade_count:2,win_rate:.5}}},{ordinal:1,status:'completed',summary:{metrics:{net_pnl:'0',max_drawdown:'0',trade_count:0,win_rate:null}}},{ordinal:2,status:'failed',summary:{metrics:{net_pnl:999}}}];
 expect(rankedRows(rows,'net_pnl','','0').map(r=>r.ordinal)).toEqual([0,1]);expect(rankedRows(rows,'win_rate','','0').map(r=>r.ordinal)).toEqual([0,1]);expect(rankedRows(rows,'net_pnl','5','1')).toEqual([]);
});
it('groups same-minute fills without losing executions or changing their values',()=>{const fills=[{time_ns:10e9,side:'buy',price:100},{time_ns:20e9,side:'buy',price:101},{time_ns:30e9,side:'sell',price:102}];const groups=fillGroups(fills);expect(groups).toHaveLength(2);expect(groups[0].fills).toEqual(fills.slice(0,2));expect(groups.flatMap(g=>g.fills)).toHaveLength(3);});
it('requires preview before starting and sends typed field lists with both frozen UTC periods',async()=>{
 vi.mocked(api).mockImplementation(async(command:string)=>{if(command==='list_experiments')return [];if(command==='experiment_fields')return [{key:'node.mean.period',label:'mean / period',type:'integer',current:2}];if(command==='experiment_preview')return {count:2,warnings:['In-sample selection only']};if(command==='experiment_start')return {experiment_id:'new-experiment'};if(command==='experiment_status')return {status:'running',finished:0,snapshot:{count:2,is_range:[0,2340],oos_range:[2340,3600]},rows:[],validations:[],active_id:'new-experiment'};return {};});
 const active=vi.fn();render(<Experiments strategies={[{id:'strategy',kind:'graph',name:'Saved graph'}]} datasets={[{id:'dataset',market:'spot',symbol:'BTCUSDT',source:'Synthetic',range:[0,3600]}]} profile={defaultProfile} onActive={active} onOpenRun={()=>{}} onCopy={()=>{}}/>);
 fireEvent.change(screen.getByLabelText('Experiment strategy'),{target:{value:'strategy'}});fireEvent.change(screen.getByLabelText('Experiment dataset'),{target:{value:'dataset'}});
 await waitFor(()=>expect((screen.getByText('Add parameter') as HTMLButtonElement).disabled).toBe(false));fireEvent.click(screen.getByText('Add parameter'));fireEvent.change(screen.getByLabelText('Values 1'),{target:{value:'2,3'}});
 expect(screen.queryByText('Start frozen experiment')).toBeNull();fireEvent.click(screen.getByText('Preview combinations'));await screen.findByText('2 unique combinations');fireEvent.click(screen.getByText('Start frozen experiment'));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('experiment_start',expect.objectContaining({strategy_id:'strategy',dataset_id:'dataset',is_range:[0,2340],oos_range:[2340,3600],axes:[{key:'node.mean.period',values:['2','3']}]})));expect(active).toHaveBeenCalledWith('new-experiment');
 await waitFor(()=>expect((screen.getByLabelText('Saved experiments') as HTMLSelectElement).disabled).toBe(true));
 vi.mocked(api).mockImplementation(async(command:string)=>command==='experiment_status'?{status:'completed',finished:2,snapshot:{count:2,is_range:[0,2340],oos_range:[2340,3600]},rows:[],validations:[],active_id:null}:[]);
 await waitFor(()=>expect((screen.getByLabelText('Saved experiments') as HTMLSelectElement).disabled).toBe(false),{timeout:2000});
 expect(active).toHaveBeenLastCalledWith(null);
});
