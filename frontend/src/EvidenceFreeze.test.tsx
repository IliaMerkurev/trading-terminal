import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import EvidenceFreeze from './EvidenceFreeze';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
const summary={groups:[{route:'custom',kind:'started',role:'strategy',market:'linear',source:'Synthetic fixture',provenance:'synthetic',count:2,cohort:'abc123def456'}],message:'2 recorded admissions overlap.',limitation:'Views are unrecorded. No clean holdout claim.',coverage_start:'2026-10-10',symbol:'BTCUSDT',source:'Synthetic fixture',provenance:'synthetic'};
it('reviews cross-route evidence before freeze, cancellation never freezes, double confirm submits once',async()=>{
 vi.mocked(api).mockResolvedValue(summary);let finish!:()=>void;const freeze=vi.fn(()=>new Promise<void>(resolve=>{finish=resolve;}));
 render(<EvidenceFreeze label="Freeze candidate" disabled={false} request={{dataset_id:'data',start:60,end:120}} onFreeze={freeze}/>);
 fireEvent.click(screen.getByText('Freeze candidate'));await screen.findByText(summary.message);expect(freeze).not.toHaveBeenCalled();
 expect(screen.getByText(/custom · started · strategy · linear/)).toBeTruthy();fireEvent.click(screen.getByText('Cancel freeze'));expect(freeze).not.toHaveBeenCalled();
 fireEvent.click(screen.getByText('Freeze candidate'));const button=await screen.findByText('Confirm candidate freeze');fireEvent.click(button);fireEvent.click(button);expect(freeze).toHaveBeenCalledTimes(1);finish();await waitFor(()=>expect(screen.queryByRole('dialog')).toBeNull());
});
it('failed preview cannot authorize freeze',async()=>{
 vi.mocked(api).mockRejectedValue(new Error('Storage unavailable'));const freeze=vi.fn();
 render(<EvidenceFreeze label="Freeze candidate" disabled={false} request={{dataset_id:'data',start:60,end:120}} onFreeze={freeze}/>);
 fireEvent.click(screen.getByText('Freeze candidate'));await screen.findByRole('alert');expect(screen.queryByText('Confirm candidate freeze')).toBeNull();expect(freeze).not.toHaveBeenCalled();
});
