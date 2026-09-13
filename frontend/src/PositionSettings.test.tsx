import {useState} from 'react';
import {it,expect} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import PositionSettings from './PositionSettings';
import {defaultProfile,type Profile} from './model';

it('keeps legacy defaults until enabled and edits a versioned bounded policy',()=>{
 let latest:Profile={...defaultProfile};
 function Host(){const [profile,setProfile]=useState<Profile>(latest);return <PositionSettings profile={profile} onChange={p=>{latest=p;setProfile(p);}}/>;}
 render(<Host/>);expect(latest.position_management).toBeUndefined();
 fireEvent.click(screen.getByLabelText('Enable Position Management'));
 expect(latest.position_management?.version).toBe(1);expect(latest.version).toBe(2);
 fireEvent.change(screen.getByLabelText('Maximum entries'),{target:{value:'5'}});
 fireEvent.change(screen.getByLabelText('Repeated entry'),{target:{value:'scale'}});
 fireEvent.click(screen.getByText('Add DCA step'));
 fireEvent.change(screen.getByLabelText('DCA 1 distance (%)'),{target:{value:'4'}});
 fireEvent.click(screen.getByText('Add partial take'));
 fireEvent.change(screen.getByLabelText('Take 1 reduction (%)'),{target:{value:'50'}});
 fireEvent.change(screen.getByLabelText('Trailing activation (%)'),{target:{value:'3'}});
 expect(latest.position_management).toMatchObject({max_entries:5,repeated_entry:'scale',dca:[{distance:'0.04',allocation_percent:'10'}],partial_take:[{distance:'0.03',fraction:'0.5'}],trailing_activation:'0.03'});
 fireEvent.click(screen.getByLabelText('Enable Position Management'));expect(latest.position_management).toBeUndefined();expect(latest.capital).toBe(defaultProfile.capital);
});

it('disables all settings for a frozen session or native strategy',()=>{
 render(<PositionSettings profile={defaultProfile} onChange={()=>{throw new Error('Must not edit');}} disabled/>);
 expect(screen.getByLabelText('Enable Position Management').closest('fieldset')?.disabled).toBe(true);
});
