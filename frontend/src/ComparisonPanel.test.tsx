import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import ComparisonPanel from './ComparisonPanel';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
it('shows differences and identifies imported reports instead of declaring equivalence',async()=>{
  const summary={profile:{symbol:'BTCUSDT'},metrics:{net_pnl:'1',max_drawdown:'0.1',trade_count:1,win_rate:1,fees:'.2',funding:'0'}};
  const runs=[{id:'first',created_at:'2026-01-01',status:'completed',summary},{id:'second',created_at:'2026-01-02',status:'completed',summary:{...summary,origin:'imported'}}];
  vi.mocked(api).mockResolvedValue({runs,differences:[{field:'profile.fee_rate',values:['0.001','0.002']}],same_contract:false,note:'Recorded inputs differ.'});
  render(<ComparisonPanel runs={runs} selected={['first','second']} onSelect={()=>{}}/>);
  fireEvent.click(screen.getByText('Compare and select runs for export'));
  fireEvent.click(screen.getByText('Compare selected runs'));
  await waitFor(()=>expect(screen.getByText('profile.fee_rate')).toBeTruthy());
  expect(screen.getByText('0.002')).toBeTruthy();expect(screen.getByText(/imported report/)).toBeTruthy();
});
