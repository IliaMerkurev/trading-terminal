import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import ProfileTransfer from './ProfileTransfer';
import {defaultProfile} from './model';

it('shows raw cost differences below rounded percentage precision and discloses model conversion',()=>{
 const onChoose=vi.fn();
 render(<ProfileTransfer lab={{...defaultProfile,fee_rate:'0.00001'}} editor={{...defaultProfile,version:1,fee_rate:'0.00002'}} minutes={240} onChoose={onChoose} onCancel={vi.fn()}/>);
 expect(screen.getByText('0.001% (fraction 0.00001)')).toBeTruthy();
 expect(screen.getByText('0.002% (fraction 0.00002)')).toBeTruthy();
 expect(screen.getByText(/converts model 1 to model 2/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Keep current editor settings'}));
 expect(onChoose).toHaveBeenCalledWith(expect.objectContaining({version:2,primary_minutes:240,fee_rate:'0.00002'}));
});

it('refuses incompatible source/timeframe choices before creating any copy',()=>{
 const onChoose=vi.fn();
 render(<ProfileTransfer lab={{...defaultProfile,execution_minutes:1440}} editor={{...defaultProfile,execution_minutes:60}} minutes={240} onChoose={onChoose} onCancel={vi.fn()}/>);
 expect(screen.getByText(/Lab source resolution 1d cannot evaluate 4h/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Use Lab test settings'}));
 expect(onChoose).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Keep current editor settings'}));
 expect(onChoose).toHaveBeenCalledWith(expect.objectContaining({execution_minutes:60,primary_minutes:240}));
});
