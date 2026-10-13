import type {IRNode} from './model';

export const frozenRuleContract = 'frozen-rule-strategy-v1' as const;
export type FrozenRuleIdentity = {id:string;name:string;revision:number;definition_revision:number;definition_hash:string};
export type FrozenRuleSnapshot = {version:1;contract:typeof frozenRuleContract;rule:FrozenRuleIdentity;definition:Record<string,any>};
export function readFrozenRule(node:IRNode):FrozenRuleSnapshot|null {
  if(node.type!=='frozen_rule'||typeof node.params.snapshot!=='string')return null;
  try {
    const value=JSON.parse(node.params.snapshot);
    if(value?.version!==1||value.contract!==frozenRuleContract||Object.keys(value).sort().join(',')!=='contract,definition,rule,version')return null;
    const rule=value.rule,definition=value.definition;
    if(!rule||typeof rule.id!=='string'||typeof rule.name!=='string'||!Number.isInteger(rule.revision)||!Number.isInteger(rule.definition_revision)||typeof rule.definition_hash!=='string'||!definition||typeof definition!=='object'||!definition.context)return null;
    return value;
  } catch {return null;}
}
