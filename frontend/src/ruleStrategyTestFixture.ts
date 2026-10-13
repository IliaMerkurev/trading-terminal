import {defaultProfile,type Graph} from './model';
import type {RuleStrategyPreview} from './RuleStrategyConversion';
import type {FrozenRule} from './alertResearch';
export function conversionRule():FrozenRule {
  return {id:'a'.repeat(32),name:'Synthetic mean cross',revision:3,definition_revision:2,definition_hash:'b'.repeat(64),definition:{version:1,contract:'frozen-indicator-alert-v1',context:{source:'bybit',market:'spot',symbol:'BTCUSDT',minutes:1},origin:{time:60,contract:'synthetic-fixed-origin'},settings_revision:7,combine:'ALL',instances:[{id:'mean',type:'sma',params:{period:3},contract:'synthetic-sma-v1'}],conditions:[{predicate:'cross_above',left:{kind:'price',port:'close'},right:{kind:'series',instance_id:'mean',port:'value'}}]}};
}
export function conversionPreview(params:{name:string;direction:'long'|'short'},saved=conversionRule()):RuleStrategyPreview {
  const {definition,...rule}=saved;
  // Different JSON property order challenges semantic identity comparison.
  const snapshot=JSON.stringify({version:1,contract:'frozen-rule-strategy-v1',rule:{definition_hash:rule.definition_hash,definition_revision:rule.definition_revision,id:rule.id,name:rule.name,revision:rule.revision},definition});
  const graph:Graph={version:1,nodes:[{id:'frozen',type:'frozen_rule',inputs:{},params:{snapshot}}],outputs:{entry_long:params.direction==='long'?'frozen.value':null,entry_short:params.direction==='short'?'frozen.value':null,exit_long:null,exit_short:null}};
  return {contract:'frozen-rule-strategy-v1',preview_hash:'c'.repeat(64),rule,name:params.name,direction:params.direction,graph,layout:{frozen:{x:40,y:60}},profile:{...defaultProfile,primary_minutes:1,execution_minutes:1},warnings:['Synthetic fixture only; verify real dataset provenance before execution.']};
}
