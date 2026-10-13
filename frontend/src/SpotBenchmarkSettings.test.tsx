import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import SpotBenchmarkSettings,{PassiveAssumptions,buildSpotBenchmark} from './SpotBenchmarkSettings';
import {defaultProfile} from './model';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));
const strategy={...defaultProfile,market:'linear',leverage:'3',fee_rate:'.001',slippage:'.0005',quantity_step:'9',max_notional:'99'};
const metadata={tick_size:'.5',quantity_step:'.1',min_quantity:'.1',max_quantity:'20',min_notional:'1',max_notional:'2000',tier_assumption:'Synthetic spot constraints; not historical truth'};

it('loads independent spot constraints and only copies numerical costs after explicit action',async()=>{
 vi.mocked(api).mockResolvedValue(metadata);const onChange=vi.fn();
 const {rerender}=render(<SpotBenchmarkSettings datasetId="spot" strategy={strategy} onChange={onChange}/>);
 await waitFor(()=>expect((screen.getByLabelText('Spot quantity step') as HTMLInputElement).value).toBe('.1'));
 expect((screen.getByLabelText('Spot fee (%)') as HTMLInputElement).value).toBe('');
 expect(onChange.mock.lastCall?.[0].value).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Copy strategy cost assumptions explicitly'}));
 fireEvent.click(screen.getByLabelText('Review independent spot assumptions'));
 await waitFor(()=>expect(onChange.mock.lastCall?.[0].value?.profile.fee_rate).toBe('.001'));
 const frozen=onChange.mock.lastCall![0].value;
 expect(frozen.profile).toMatchObject({quantity_step:'.1',max_notional:'2000',leverage:'1',maintenance_rate:'0',funding_mode:'assumed_zero',stop_loss:'0'});
 expect(frozen.assumptions).toMatchObject({fee_source:'explicit_shared',slippage_source:'explicit_shared',precision_source:'dataset_metadata'});
 rerender(<SpotBenchmarkSettings datasetId="spot" strategy={{...strategy,fee_rate:'.5'}} onChange={onChange}/>);
 expect((screen.getByLabelText('Spot fee (%)') as HTMLInputElement).value).toBe('0.1');
 expect((screen.getByLabelText('Spot slippage (%)') as HTMLInputElement).value).toBe('0.05');
 expect(frozen.profile.slippage).toBe('.0005');
 fireEvent.change(screen.getByLabelText('Spot fee (%)'),{target:{value:'0.2'}});
 expect(onChange.mock.lastCall?.[0].value).toBeNull();
 fireEvent.click(screen.getByLabelText('Review independent spot assumptions'));
 expect(onChange.mock.lastCall?.[0].value.assumptions.fee_source).toBe('explicit_spot');
 expect(onChange.mock.lastCall?.[0].value.profile.fee_rate).toBe('0.002');
});

it('ignores old counterpart metadata and supports explicit reviewed manual settings after failure',async()=>{
 let oldResolve:(v:any)=>void=()=>{};
 vi.mocked(api).mockImplementation((_command,p:any)=>p.dataset_id==='old'?new Promise(resolve=>{oldResolve=resolve;}):Promise.reject(Error('Spot metadata unavailable')));
 const onChange=vi.fn();const {rerender}=render(<SpotBenchmarkSettings datasetId="old" strategy={strategy} onChange={onChange}/>);
 rerender(<SpotBenchmarkSettings datasetId="new" strategy={strategy} onChange={onChange}/>);
 expect(await screen.findByText('Spot metadata unavailable')).toBeTruthy();
 oldResolve(metadata);
 await waitFor(()=>expect((screen.getByLabelText('Spot quantity step') as HTMLInputElement).value).toBe(''));
 fireEvent.change(screen.getByLabelText('Spot precision source'),{target:{value:'reviewed_manual'}});
 for(const [label,value] of [['Spot tick size','.5'],['Spot quantity step','.1'],['Spot minimum quantity','.1'],['Spot maximum quantity','20'],['Spot minimum notional','1'],['Spot maximum notional','2000'],['Spot fee (%)','0'],['Spot slippage (%)','0'],['Spot cost assumption note','Zero modeled costs'],['Spot precision assumption note','Reviewed invented manual limits']])fireEvent.change(screen.getByLabelText(label),{target:{value}});
 fireEvent.click(screen.getByLabelText('Review independent spot assumptions'));
 expect(onChange.mock.lastCall?.[0].datasetId).toBe('new');
 expect(onChange.mock.lastCall?.[0].value.assumptions.precision_source).toBe('reviewed_manual');
 expect(onChange.mock.lastCall?.[0].value.profile.quantity_step).toBe('.1');
});

it('saved review displays frozen provenance and calls out legacy missing provenance',()=>{
 const assumptions={version:1,fee_source:'explicit_spot',slippage_source:'explicit_spot',fee_note:'Original spot costs',precision_source:'reviewed_manual',precision_note:'Original precision note'};
 const value=buildSpotBenchmark(strategy,{...metadata,fee_rate:'.01',slippage:'0'},assumptions);
 const row={kind:'benchmark',contract:{source:'Synthetic',profile:value.profile,execution_assumptions:assumptions}};
 const {rerender}=render(<PassiveAssumptions rows={[row]}/>);
 expect(screen.getByText(/Original spot costs/)).toBeTruthy();expect(screen.getByText(/not leverage\/risk equivalent/)).toBeTruthy();
 rerender(<PassiveAssumptions rows={[{...row,contract:{...row.contract,execution_assumptions:undefined}}]}/>);
 expect(screen.getByText(/Legacy contract: cost and precision provenance was not recorded separately/)).toBeTruthy();
});
