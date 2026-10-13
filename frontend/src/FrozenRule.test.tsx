import {expect,it} from 'vitest';
import {render,screen} from '@testing-library/react';
import {conversionPreview,conversionRule} from './ruleStrategyTestFixture';
import FrozenRuleDetails from './FrozenRuleDetails';
import {readFrozenRule} from './frozenRule';
import {createNode,deleteNodes,duplicateNodes,graphProblems,searchNodes} from './editor';
import {canConnect} from './model';
const graph=()=>conversionPreview({name:'Independent strategy',direction:'long'}).graph;
it('excludes the immutable source from Add, search, duplicate and delete while retaining ordinary graph editing',()=>{
  const original=graph();expect(searchNodes('')).not.toContain('frozen_rule');expect(searchNodes('frozen')).toEqual([]);expect(()=>createNode('frozen_rule')).toThrow(/reviewed saved-rule/);
  expect(deleteNodes(original,{},['frozen'])).toBeNull();expect(duplicateNodes(original,{},['frozen']).selected).toEqual([]);
  const exit=createNode('not');exit.inputs.source='frozen.value';original.nodes.push(exit);original.outputs.exit_long=exit.id+'.value';
  const copy=duplicateNodes(original,{},['frozen',exit.id]);expect(copy.selected).toHaveLength(1);expect(copy.graph.nodes.at(-1)?.inputs.source).toBe('frozen.value');expect(copy.graph.nodes.filter(node=>node.type==='frozen_rule')).toHaveLength(1);expect(graphProblems(copy.graph)).toEqual([]);
  expect(canConnect(original,'frozen','value','out:exit_long','signal')).toBe(true);expect(canConnect(original,exit.id,'value','frozen','snapshot')).toBe(false);
});
it('preserves the entire independent source across serialization and whole strategy copying',()=>{
  const source=conversionRule(),g=conversionPreview({name:'Independent',direction:'long'},source).graph;
  const copied=structuredClone(g),reopened=JSON.parse(JSON.stringify(g));source.definition.instances[0].params.period=99;source.definition.origin.time=120;source.revision=4;
  expect(copied).toEqual(reopened);expect(readFrozenRule(copied.nodes[0])?.definition.instances[0].params.period).toBe(3);expect(readFrozenRule(copied.nodes[0])?.definition.origin.time).toBe(60);expect(graphProblems(reopened)).toEqual([]);
});
it('rejects duplicate and corrupted frozen sources and displays immutable text rather than fake numeric controls',()=>{
  const g=graph();render(<FrozenRuleDetails node={g.nodes[0]}/>);expect(screen.getByText('Exact frozen parameters and provenance')).toBeTruthy();expect(screen.queryByRole('spinbutton')).toBeNull();expect(screen.queryByRole('textbox')).toBeNull();
  g.nodes.push({...g.nodes[0],id:'duplicate'});expect(graphProblems(g).some(problem=>problem.message==='Use at most one frozen rule source')).toBe(true);
  g.nodes.pop();g.nodes[0].params.snapshot='{}';expect(readFrozenRule(g.nodes[0])).toBeNull();expect(graphProblems(g).some(problem=>problem.field==='snapshot')).toBe(true);
});
