import {it,expect,vi} from 'vitest';
import {act,render,screen,fireEvent,waitFor} from '@testing-library/react';
import EvidenceFreeze from './EvidenceFreeze';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
const summary={groups:[{route:'custom',kind:'started',role:'strategy',market:'linear',source:'Synthetic fixture',provenance:'synthetic',count:2,cohort:'abc123def456'}],message:'2 recorded admissions overlap.',limitation:'Views are unrecorded. No clean holdout claim.',coverage_start:'2026-10-10',symbol:'BTCUSDT',source:'Synthetic fixture',provenance:'synthetic'};
it('reviews cross-route evidence before freeze, cancellation never freezes, double confirm submits once',async()=>{
 vi.mocked(api).mockResolvedValue(summary);let finish!:()=>void;const freeze=vi.fn(()=>new Promise<void>(resolve=>{finish=resolve;}));
 render(<EvidenceFreeze label="Freeze candidate" disabled={false} request={{dataset_id:'data',start:60,end:120}} onFreeze={freeze}/>);
 fireEvent.click(screen.getByText('Freeze candidate'));await screen.findByText(summary.message);expect(freeze).not.toHaveBeenCalled();
 expect(screen.getByText(/custom · started · strategy · linear/)).toBeTruthy();fireEvent.click(screen.getByText('Cancel freeze'));expect(freeze).not.toHaveBeenCalled();
 fireEvent.click(screen.getByText('Freeze candidate'));const button=await screen.findByText('Confirm candidate freeze');fireEvent.click(button);fireEvent.click(button);await waitFor(()=>expect(freeze).toHaveBeenCalledTimes(1));finish();await waitFor(()=>expect(screen.queryByRole('dialog')).toBeNull());
});
it('failed preview cannot authorize freeze',async()=>{
 vi.mocked(api).mockRejectedValue(new Error('Storage unavailable'));const freeze=vi.fn();
 render(<EvidenceFreeze label="Freeze candidate" disabled={false} request={{dataset_id:'data',start:60,end:120}} onFreeze={freeze}/>);
 fireEvent.click(screen.getByText('Freeze candidate'));await screen.findByRole('alert');expect(screen.queryByText('Confirm candidate freeze')).toBeNull();expect(freeze).not.toHaveBeenCalled();
});

it.each(['Cancel freeze','Escape'])('returns to the explicit origin after delayed preview and %s',async(dismiss)=>{
 let resolve!:(value:any)=>void;
 vi.mocked(api).mockImplementation(()=>new Promise(done=>{resolve=done;}));
 const freeze=vi.fn();
 render(<EvidenceFreeze label="Freeze candidate" disabled={false} request={{dataset_id:'data',start:60,end:120}} onFreeze={freeze}/>);
 const trigger=screen.getByRole('button',{name:'Freeze candidate'}) as HTMLButtonElement;
 trigger.focus();fireEvent.click(trigger);
 expect(trigger.disabled).toBe(true);
 // A real browser drops focus when the active trigger becomes disabled.
 document.body.tabIndex=-1;document.body.focus();document.body.removeAttribute('tabindex');expect(document.activeElement).toBe(document.body);
 await waitFor(()=>expect(resolve).toBeTypeOf('function'));
 await act(async()=>resolve(summary));
 const dialog=screen.getByRole('dialog');expect(dialog.contains(document.activeElement)).toBe(true);
 if(dismiss==='Escape')fireEvent(dialog,new Event('cancel',{bubbles:false,cancelable:true}));else fireEvent.click(screen.getByRole('button',{name:dismiss}));
 expect(screen.queryByRole('dialog')).toBeNull();expect(document.activeElement).toBe(trigger);
 expect(freeze).not.toHaveBeenCalled();
});

it('does not steal focus from another open dialog when the review closes',async()=>{
 vi.mocked(api).mockResolvedValue(summary);
 render(<EvidenceFreeze label="Freeze candidate" disabled={false} request={{dataset_id:'data',start:60,end:120}} onFreeze={vi.fn()}/>);
 const trigger=screen.getByRole('button',{name:'Freeze candidate'});
 fireEvent.click(trigger);await screen.findByText(summary.message);
 const other=document.createElement('dialog'),focus=document.createElement('button');
 other.append(focus);document.body.append(other);other.showModal();focus.focus();
 fireEvent.click(screen.getByRole('button',{name:'Cancel freeze'}));
 expect(document.activeElement).toBe(focus);other.remove();
});
