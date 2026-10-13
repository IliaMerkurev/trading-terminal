import {render,screen} from '@testing-library/react';
import {describe,it,expect} from 'vitest';
import {WorkloadSummary} from './WorkloadSummary';

describe('immutable workload presentation',()=>{
 it('shows execution units, row breakdown and independent full-source bounds',()=>{
  render(<WorkloadSummary value={{workload_version:2,modeled_source_candles:66,modeled_minutes:66,workload_breakdown:[{ordinal:0,kind:'graph',modeled_source_candles:30,prefix_source_candles:12,evaluation_source_candles:18,execution_minutes:60}]}}/>);
  expect(screen.getByText('66 modeled source-candle executions').nextElementSibling?.tagName).toBe('BR');
  expect(screen.getByText(/Row 1 · graph · 30 executions \(12 prefix \+ 18 evaluation\) · 60m source/)).toBeTruthy();
  expect(screen.getByText(/history after the evaluation end and all trade, mark and funding/)).toBeTruthy();
  expect(screen.getByText(/not a peak-memory guarantee/)).toBeTruthy();
 });
 it('labels old counts unchanged without reinterpreting them',()=>{
  render(<WorkloadSummary value={{modeled_minutes:90,rows:[{kind:'benchmark'}],start:12,end:30}}/>);
  expect(screen.getByText('90 legacy workload count').nextElementSibling?.tagName).toBe('BR');
  expect(screen.getByText(/not recalculated/)).toBeTruthy();
  expect(screen.queryByText(/66/)).toBeNull();
 });
 it('does not fabricate missing historical counts',()=>{
  const {container}=render(<WorkloadSummary value={{}}/>);expect(container.textContent).toBe('');
 });
});
