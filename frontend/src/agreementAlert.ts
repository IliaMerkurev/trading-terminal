import {AGREEMENT_VERSION, AGREEMENT_WEIGHT_VERSION, AGREEMENT_MANIFEST_HASH} from './indicatorAgreement';

export const agreementGroups = ['trend', 'momentum', 'volume'] as const;
export const agreementWarning = 'Descriptive heuristic. Percentages are not probabilities, confidence or trading advice.';
export type AgreementCapability = {
 version:number; predicate:string; definition_version:number; contract:string;
 agreement_version:string; weight_version:string; manifest_hash:string;
 directions:string[]; groups:string[]; threshold_min:number; threshold_max:number;
 threshold_inclusive:boolean; required_group_threshold:string;
};
// A legacy catalog remains usable when its optional extension is absent or newer.
export function supportedAgreementCapability(value:unknown):value is AgreementCapability {
 const v=value as AgreementCapability|undefined;
 const same=(actual:unknown,expected:readonly string[])=>Array.isArray(actual)&&actual.length===expected.length&&expected.every(item=>actual.includes(item));
 return !!v&&v.version===1&&v.predicate==='agreement'&&v.definition_version===2&&v.contract==='frozen-indicator-alert-v2'
  &&v.agreement_version===AGREEMENT_VERSION&&v.weight_version===AGREEMENT_WEIGHT_VERSION&&v.manifest_hash===AGREEMENT_MANIFEST_HASH
  &&same(v.directions,['up','down'])&&same(v.groups,agreementGroups)&&v.threshold_min===0&&v.threshold_max===1
  &&v.threshold_inclusive===true&&v.required_group_threshold==='strictly_greater_than_half';
}
export function supportedAgreementBinding(value:any):boolean {
 return !!value&&value.version===AGREEMENT_VERSION&&value.weight_version===AGREEMENT_WEIGHT_VERSION
  &&value.manifest_hash===AGREEMENT_MANIFEST_HASH&&Array.isArray(value.member_ids)
  &&value.member_ids.every((id:unknown)=>typeof id==='string')&&new Set(value.member_ids).size===value.member_ids.length;
}
export const agreementConditionLabel=(condition:any)=>`${condition.direction} ≥ ${condition.threshold} fraction · required groups: ${condition.required_groups?.join(', ')||'none'}`;
