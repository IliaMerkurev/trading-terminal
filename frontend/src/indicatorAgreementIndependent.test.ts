import {it,expect,beforeAll,vi} from 'vitest';
import fixtureData from '../../tests/fixtures/indicator_agreement_v1.json';
import {evaluateAgreement,thresholdEvidence} from './indicatorAgreement';
const fixtures:any=fixtureData;
let parity:Record<string,unknown>;
beforeAll(async()=>{
 const {execFileSync}=await vi.importActual<any>('node:child_process');
 const {platform}=await vi.importActual<any>('node:os');
 const python=platform()==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python';
 parity=JSON.parse(execFileSync(python,['-c', "import json; from terminal.indicator_agreement import evaluate_agreement; f=json.load(open('tests/fixtures/indicator_agreement_v1.json')); print(json.dumps({c['name']:evaluate_agreement(c['input']) for c in f['cases']},allow_nan=False))"],{encoding:'utf8',maxBuffer:4*1024*1024}));
});
const exact=(value:any)=>Object.fromEntries(Object.entries(value).map(([d,v]:any)=>[d,v.map(String)]));
for(const c of fixtures.cases)it('independent expected agreement: '+c.name,()=>{
 const result=evaluateAgreement(c.input),e=c.expected;
 if('overall'in e)expect(result.overall===null?null:result.overall.exact).toEqual(e.overall===null?null:exact(e.overall));
 if(e.trend)expect(result.groups.find(g=>g.group==='trend')?.distribution?.exact).toEqual(exact(e.trend));
 if(e.percentages)expect(result.overall?.percentages).toEqual(e.percentages);
 for(const [id,direction] of Object.entries(e.member_direction??{}))expect(result.members.find(m=>m.id===id)?.status).toBe(direction);
 for(const id of e.member_unavailable??[])expect(result.members.find(m=>m.id===id)?.status).toBe('unavailable');
 for(const [key,field] of [['fully_available_types','fully_covered_types'],['total_supported_types','total_types'],['available_variants','available_variants'],['total_variants','total_variants']])if(key in e)expect((result.coverage as any)[field]).toBe(e[key]);
 if('group_conflict'in e)expect(result.group_conflict).toBe(e.group_conflict);
 for(const dist of [result.overall,...result.groups.map(g=>g.distribution)])if(dist)expect(Object.values(dist.percentages).reduce((a,b)=>a+b,0)).toBe(100);
 expect(result).toEqual(parity[c.name]);
});
for(const c of fixtures.threshold_cases)it('independent threshold: '+c.name,()=>{
 const input=fixtures.cases.find((v:any)=>v.name===c.result_case).input;
 expect(thresholdEvidence(evaluateAgreement(input),c.direction,c.threshold,c.required_groups).truth).toBe(c.expected);
});
