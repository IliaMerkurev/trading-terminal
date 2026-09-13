import {it,expect} from 'vitest';
import {render,screen} from '@testing-library/react';
import PositionLifecycle from './PositionLifecycle';
it('presents a scaled and reduced position as one lifecycle with costs',()=>{
 render(<PositionLifecycle trades={[{position_id:1,side:'long',entry_count:2,peak_quantity:'5',max_notional:'500',gross_pnl:'20',fees:'1',funding:'-.5',net_pnl:'18.5',events:[{type:'scale',time_ns:60000000000,quantity:'2',price:'90',remaining_quantity:'5',average_entry:'96',fee:'.18',reason:'dca_1'},{type:'reduction',time_ns:120000000000,quantity:'1',price:'110',remaining_quantity:'4',average_entry:'96',fee:'.11',reduction_net_pnl:'13.69',reason:'partial_take_1'}]}]}/>);
 expect(screen.getByLabelText('Lifecycle position').querySelectorAll('option')).toHaveLength(1);expect(screen.getByText('dca 1')).toBeTruthy();expect(screen.getByText('partial take 1')).toBeTruthy();expect(screen.getByText('13.69')).toBeTruthy();
});
