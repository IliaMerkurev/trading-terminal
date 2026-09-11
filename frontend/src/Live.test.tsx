import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import Live from './Live';
import {defaultProfile} from './model';
const mock=vi.hoisted(()=>({api:vi.fn()}));
vi.mock('./api',()=>({api:mock.api}));

it('starts only a saved strategy with explicit paper/channels and displays live state',async()=>{
 mock.api.mockImplementation(async(command:string)=>command==='live_status'?{active:false,telegram:{configured:false}}:{session_id:'fixture'});
 render(<Live strategyId="saved" profile={defaultProfile}/>);
 fireEvent.click(screen.getByLabelText('Paper trading'));
 fireEvent.click(screen.getByRole('button',{name:'Start new live session'}));
 await waitFor(()=>expect(mock.api).toHaveBeenCalledWith('live_start',{strategy_id:'saved',profile:defaultProfile,paper:true,channels:[]}));
 expect(screen.getByText('No real orders')).not.toBeNull();
});

it('sends Telegram values only to configure and clears fields after secure save',async()=>{
 mock.api.mockImplementation(async(command:string)=>command==='live_status'?{telegram:{configured:true}}:{configured:true});
 render(<Live strategyId={null} profile={defaultProfile}/>);
 fireEvent.click(screen.getByRole('button',{name:'Configure Telegram'}));
 const token=screen.getByLabelText('Bot token'),chat=screen.getByLabelText('Chat ID');
 expect(token.getAttribute('type')).toBe('password');expect(chat.getAttribute('type')).toBe('password');
 fireEvent.change(token,{target:{value:'synthetic placeholder'}});fireEvent.change(chat,{target:{value:'0'}});
 fireEvent.click(screen.getByRole('button',{name:'Save to protected storage'}));
 await waitFor(()=>expect(screen.queryByLabelText('Bot token')).toBeNull());
 expect(mock.api).toHaveBeenCalledWith('telegram_configure',{token:'synthetic placeholder',chat_id:'0'});
 expect((screen.getByRole('button',{name:'Start new live session'}) as HTMLButtonElement).disabled).toBe(true);
});
