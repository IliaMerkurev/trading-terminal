import {afterEach, expect, it} from 'vitest';
import {cleanup, fireEvent, render, screen, within} from '@testing-library/react';
import IndicatorAgreementPanel from './IndicatorAgreementPanel';
import {makeAgreementInput} from './currentAgreementTestFixture';
afterEach(cleanup);
it('shows compact expected distributions, exact UTC and warning while details start collapsed', () => {
  const input = makeAgreementInput(); render(<IndicatorAgreementPanel {...input}/>);
  expect(screen.getByLabelText('Overall agreement').textContent).toBe('Up 67%Down 0%Neutral 33%');
  expect(screen.getByText('1970-01-01 00:03:00 UTC')).toBeTruthy();
  expect(screen.getByText(/Percentages are not probabilities/).closest('details')).toBeNull();
  expect(document.querySelector('details')!.open).toBe(false);
  expect(screen.getByLabelText('Agreement coverage').textContent).toContain('3/3 fully covered');
});
it('keeps disclosure open over polling and status transitions, resets on actual remount', () => {
  const input = makeAgreementInput(); const view = render(<IndicatorAgreementPanel {...input}/>);
  const details = document.querySelector('details')!;
  fireEvent.click(within(details).getByText(/Agreement details/));
  expect(details.open).toBe(true);
  view.rerender(<IndicatorAgreementPanel {...makeAgreementInput()}/>); expect(details.open).toBe(true);
  view.rerender(<IndicatorAgreementPanel {...input} active={false}/>); expect(details.open).toBe(true);
  expect(screen.queryByLabelText('Overall agreement')).toBeNull();
  view.rerender(<IndicatorAgreementPanel {...input}/>); expect(details.open).toBe(true);
  view.unmount(); render(<IndicatorAgreementPanel {...input}/>); expect(document.querySelector('details')!.open).toBe(false);
});
it('removes all stale distributions on a mismatched or historical snapshot with clear guidance', () => {
  const input = makeAgreementInput(); const view = render(<IndicatorAgreementPanel {...input}/>);
  view.rerender(<IndicatorAgreementPanel {...input} historical/>);
  expect(screen.getByRole('status').textContent).toContain('Return to latest');
  expect(screen.queryByLabelText('Overall agreement')).toBeNull(); expect(screen.queryByLabelText('Trend agreement')).toBeNull();
  view.rerender(<IndicatorAgreementPanel {...input} rawSnapshotKey="outdated"/>);
  expect(screen.getByRole('status').textContent).toContain('Snapshot mismatch');
  expect(screen.queryByText(/Confirmed raw close/)).toBeNull();
});
it('makes exact member parameters, rule, values and unavailable reason inspectable', () => {
  const input = makeAgreementInput(); input.response.columns.sma.value[2] = null;
  render(<IndicatorAgreementPanel {...input}/>);
  expect(screen.getAllByText('Parameters: period=1')).toHaveLength(3);
  expect(screen.getByText('Raw close above value: up; below: down; equal: neutral.')).toBeTruthy();
  expect(screen.getByText('Missing output at this exact close; no older value substituted.')).toBeTruthy();
  expect(screen.getByText('Observed: value=unavailable')).toBeTruthy();
});
it('labels no-data, hidden, context-only and unsupported members without manufacturing neutral', () => {
  const input = makeAgreementInput(); input.response = null; input.settings.instances = [
    {id:'hidden',type:'sma',params:{period:20},visible:false,color:'#ffffff'},
    {id:'volume',type:'volume',params:{},visible:true,color:'#ffffff'},
    {id:'cloud',type:'ichimoku',params:{conversion:9,base:26,span_b:52,displacement:26},visible:true,color:'#ffffff'},
  ];
  render(<IndicatorAgreementPanel {...input}/>);
  expect(screen.getByText('Hidden')).toBeTruthy(); expect(screen.getByText('Context only')).toBeTruthy(); expect(screen.getByText('Unsupported')).toBeTruthy();
  expect(screen.queryByText('Neutral 100%')).toBeNull();
});
