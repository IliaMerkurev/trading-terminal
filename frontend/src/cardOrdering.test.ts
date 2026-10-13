import {describe,it,expect} from 'vitest';
import {cohortKey} from './LibraryResearch';
import {cardOrderChoices,finiteCardMetric,orderCards,rankCard,type CardOrderMetric} from './cardOrdering';

const entries=[{id:'z',version:1,name:'Zulu'},{id:'a',version:1,name:'Alpha'},{id:'b',version:1,name:'Beta'},{id:'n',version:1,name:'Absent'}];
const profile={market:'spot',symbol:'BTCUSDT',primary_minutes:240,execution_minutes:60,capital:'1000',fee_rate:'.001',version:1};
const spec=(id:string,changes:any={})=>({kind:'graph',name:id,profile,dataset:{id:'history'},selection:{entry_id:id,version:1,minutes:240,parameters:{period:14}},...changes});
const result=(ordinal:number,value:unknown,status='completed')=>({ordinal,status,metrics:{period_return:value,max_drawdown:value,completed_positions:value}});
const report=(specs:any[],rows:any[]=specs.map((_,i)=>result(i,i)))=>({id:'saved',snapshot:{phase:'selection',rows:specs},rows});
const group=cohortKey(spec('z'));

describe('saved-comparison card ordering',()=>{
 it.each(['period_return','max_drawdown','completed_positions'] as CardOrderMetric[])('orders %s in both directions, retains losses/zero, and always puts N/A last',metric=>{
  const saved=report(entries.slice(0,3).map(e=>spec(e.id)),[result(0,'-.05'),result(1,'0'),result(2,'.1')]);
  const names=(direction:'asc'|'desc')=>orderCards(entries,saved,240,group,metric,direction).map(item=>item.entry.name);
  expect(names('desc')).toEqual(['Beta','Alpha','Zulu','Absent']);
  expect(names('asc')).toEqual(['Zulu','Alpha','Beta','Absent']);
 });
 it('uses deterministic name and identity ties without modifying catalog or saved inputs',()=>{
  const catalog=[...entries,{id:'c',version:2,name:'Beta'},{id:'c',version:1,name:'Beta'}];
  const saved=report(entries.slice(0,3).map(e=>spec(e.id)),[result(0,0),result(1,0),result(2,0)]),before=JSON.stringify([catalog,saved]);
  for(const direction of ['asc','desc'] as const)expect(orderCards(catalog,saved,240,group,'period_return',direction).map(v=>`${v.entry.id}:${v.entry.version}`)).toEqual(['a:1','b:1','z:1','n:1','c:1','c:2']);
  expect(orderCards(entries,null,null,'','name','asc').map(v=>v.entry.name)).toEqual(['Absent','Alpha','Beta','Zulu']);
  expect(orderCards(entries,null,null,'','name','desc').map(v=>v.entry.name)).toEqual(['Zulu','Beta','Alpha','Absent']);
  expect(JSON.stringify([catalog,saved])).toBe(before);
 });
 it('requires the exact saved timeframe and catalog version',()=>{
  const saved=report([spec('z'),spec('z',{selection:{entry_id:'z',version:1,minutes:1440,parameters:{}}}),spec('a',{selection:{entry_id:'a',version:2,minutes:240,parameters:{}}})],[result(0,-2),result(1,9),result(2,99)]);
  expect(rankCard(entries[0],saved,240,group,'period_return').value).toBe(-2);
  expect(rankCard(entries[0],saved,1440,group,'period_return').value).toBe(9);
  expect(rankCard(entries[0],saved,60,group,'period_return').reason).toBe('not tested at this timeframe');
  expect(rankCard(entries[1],saved,240,group,'period_return').reason).toBe('saved catalog version differs');
 });
 it.each([{dataset:{id:'different'}},{profile:{...profile,version:2}},{profile:{...profile,capital:'2000'}},{profile:{...profile,fee_rate:'.002'}},{profile:{...profile,execution_minutes:240}}])('keeps incompatible contracts outside the chosen group: %j',change=>{
  const saved=report([spec('z'),spec('a',change)],[result(0,-10),result(1,100)]);
  expect(rankCard(entries[1],saved,240,group,'period_return')).toEqual({value:null,reason:'outside selected group'});
  expect(orderCards(entries,saved,240,group,'period_return','desc')[0].entry.id).toBe('z');
 });
 it('does not choose a first, best, completed-only or current-default parameter variant',()=>{
  const saved=report([spec('z'),spec('z',{selection:{entry_id:'z',version:1,minutes:240,parameters:{period:7}}})],[result(0,5),result(1,null,'failed')]);
  expect(rankCard(entries[0],saved,240,group,'period_return')).toEqual({value:null,reason:'multiple saved variants'});
  saved.rows.pop();expect(rankCard(entries[0],saved,240,group,'period_return').reason).toBe('multiple saved variants');
 });
 it('distinguishes unfinished, incompatible, missing and non-finite results from zero',()=>{
  for(const value of [null,undefined,'','  ','NaN',NaN,Infinity,'Infinity',true,[],{}])expect(finiteCardMetric(value)).toBeNull();
  expect(finiteCardMetric('0')).toBe(0);expect(finiteCardMetric(-1)).toBe(-1);
  for(const status of ['pending','failed','incompatible'])expect(rankCard(entries[0],report([spec('z')],[result(0,10,status)]),240,group,'period_return').reason).toBe(status);
  expect(rankCard(entries[0],report([spec('z')],[result(0,'NaN')]),240,group,'period_return').reason).toBe('metric unavailable');
  expect(rankCard(entries[0],report([spec('z')],[]),240,group,'period_return').reason).toBe('saved result unavailable');
 });
 it('excludes passive baselines and holdouts and requires explicit context',()=>{
  const saved=report([spec('z',{kind:'benchmark'}),spec('a')]);
  expect(rankCard(entries[0],saved,240,group,'period_return').reason).toBe('not in selected comparison');
  expect(rankCard(entries[1],saved,null,group,'period_return').reason).toContain('choose a saved timeframe');
  expect(rankCard(entries[1],saved,240,'','period_return').value).toBeNull();
  saved.snapshot.phase='out_of_sample';expect(cardOrderChoices(saved)).toEqual({timeframes:[],groups:[]});
  expect(rankCard(entries[1],saved,240,group,'period_return').value).toBeNull();
 });
 it('uses the full Saved tests cohort numbering but only offers strategy timeframes/groups',()=>{
  const baseline=spec('passive',{kind:'benchmark',profile:{...profile,capital:'0500'}}),other=spec('a',{profile:{...profile,version:2},selection:{entry_id:'a',version:1,minutes:1440,parameters:{}}});
  const saved=report([baseline,spec('z'),other]),keys=[...new Set(saved.snapshot.rows.map(cohortKey))].sort(),choices=cardOrderChoices(saved);
  expect(choices.timeframes).toEqual([240,1440]);expect(choices.groups).toHaveLength(2);
  expect(choices.groups.find(g=>g.key===group)?.number).toBe(keys.indexOf(group)+1);
  expect(choices.groups.find(g=>g.key===cohortKey(other))?.minutes).toEqual([1440]);
 });
});
