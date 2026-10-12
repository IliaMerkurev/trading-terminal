import React,{StrictMode} from 'react';
import {it,expect,vi,beforeEach,afterEach} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup,within} from '@testing-library/react';
import saved from '../../tests/fixtures/agreement_ui_saved.json';
import {AgreementTimeline,SavedAgreementEvidence} from './AgreementHistory';
import IndicatorAlerts,{FrozenAlert} from './IndicatorAlerts';
import {AlertSessionProvider,AlertChartBridge} from './AlertSession';
import {AlertResearchProvider,useAlertResearch} from './AlertResearch';
import {supportedAgreementCapability} from './agreementAlert';
const mock=vi.hoisted(()=>({api:vi.fn(),calls:[] as any[],session:'',capability:true}));
vi.mock('./api',()=>({api:mock.api}));
vi.mock('./ResearchChart',()=>({default:(p:any)=><div aria-label="raw price probe" data-target={p.target??''}/> }));
const definition:any=saved.definition,rows:any[]=saved.rows,base=1800000000;
const capability={version:1,predicate:'agreement',definition_version:2,contract:definition.contract,agreement_version:definition.agreement.version,weight_version:definition.agreement.weight_version,manifest_hash:definition.agreement.manifest_hash,directions:['up','down'],groups:['trend','momentum','volume'],threshold_min:0,threshold_max:1,threshold_inclusive:true,required_group_threshold:'strictly_greater_than_half'};
const ctx={...definition.context,visible:true};
const settings=(revision=7,hide=false):any=>({version:1,revision,origins:{'1':definition.origin},instances:definition.instances.map((m:any)=>({...m,color:'#ffffff',visible:!(hide&&m.id==='volume')}))});
const run:any={id:'b'.repeat(32),sequence:1,request_id:'c'.repeat(32),created_at:base,status:'completed',cancel_requested:false,rule_id:'a'.repeat(32),rule_name:'Frozen independent',rule_revision:1,definition_revision:1,definition_hash:'d'.repeat(64),context:definition.context,origin:definition.origin,start:base+60,end:base+480,input_count:8,input_hash:'e'.repeat(64),coverage_complete:true,summary:{match_count:1,requested_rows:8,known_rows:7,unknown_rows:1},error:null,definition};
const windowOf=(part:any[],next:number|null= null,target?:number)=>({run_id:run.id,total_rows:8,start_index:part[0]?.row_index??0,next_index:next,rows:part,markers:part.filter(r=>r.evaluation.hit).map(r=>({row_index:r.row_index,confirmed_at:r.evaluation.confirmed_at,raw_open_time:r.candle.time})),target:target===undefined?null:{status:'available',confirmed_at:target,raw_open_time:target-60,row_index:(target-base)/60-1,included:part.some(r=>r.evaluation.confirmed_at===target)},byte_limited:next!==null});
beforeEach(()=>{localStorage.clear();mock.calls=[];mock.session='';mock.capability=true;mock.api.mockReset();mock.api.mockImplementation(async(c:string,p:any={})=>{mock.calls.push({c,p:structuredClone(p)});
 if(c==='alert_session_init'){mock.session=p.session_id;return p;}if(c==='alert_context')return p;if(c==='alert_status')return{session_id:mock.session,rules:[]};
 if(c==='alert_catalog')return{version:1,ports:{sma:{value:'price'}},predicates:['above','below','cross_above','cross_below','divergence'],divergences:['bullish_regular'],oscillators:['wt'],combine:['ALL','ANY'],max_conditions:16,price_ports:['close'],price_unit:'price',...(mock.capability?{agreement_capability:capability}:{})};
 if(c==='alert_list')return{rules:[],next_cursor:null};if(c==='alert_events')return{events:[],next_cursor:null};
 if(c==='alert_preview')return{definition:{...definition,settings_revision:p.settings_revision,conditions:p.conditions},definition_hash:'f'.repeat(64),settings_revision:p.settings_revision};
 if(c==='alert_history_list')return{runs:[run],next_cursor:null};if(c==='alert_history_get')return run;if(c==='alert_history_matches')return{matches:[],next_cursor:null};if(c==='alert_history_chart')return windowOf(rows);throw Error('Unexpected '+c);
 });});
afterEach(cleanup);
const app=(revision=7,hide=false)=><StrictMode><AlertSessionProvider><AlertChartBridge {...ctx} settings={settings(revision,hide)} available/><IndicatorAlerts/></AlertSessionProvider></StrictMode>;
async function open(){fireEvent.click(screen.getByRole('button',{name:'Local alerts'}));await screen.findByLabelText('Condition 1 predicate');await waitFor(()=>expect((screen.getByRole('button',{name:'Preview frozen alert'}).closest('fieldset') as HTMLFieldSetElement).disabled).toBe(false));}
it('renders real frozen contract objects and separates agreement membership from other dependencies',()=>{
 const extra={id:'numeric-only',type:'ema',params:{period:3},contract:{display:'native-close-engine-seeds-v1',vmc:null,metadata_sha256:'test'}};
 render(<FrozenAlert definition={{...definition,instances:[...definition.instances,extra]}}/>);
 const panel=screen.getByLabelText('Frozen agreement composition');expect(panel.textContent).toContain('3 frozen agreement members');expect(panel.textContent).toContain('Other frozen numeric/divergence dependencies');expect(panel.textContent).toContain('numeric-only');expect(panel.textContent).toContain('metadata_sha256');expect(panel.textContent).toContain('native-close-engine-seeds-v1');
});
it('renders four saved lanes with unknown distinct from neutral and exact nonhit selection',()=>{
 const choose=vi.fn();render(<AgreementTimeline rows={rows} conditionIndex={0} selectedIndex={1} onSelect={choose}/>);
 for(const name of ['Overall','Trend','Momentum','Volume'])expect(screen.getByLabelText(name+' timeline lane')).toBeTruthy();
 const overall=within(screen.getByLabelText('Overall timeline lane'));
 expect(overall.getByRole('button',{name:/row 1 .*Unknown/}).className).toContain('unknown');
 const neutral=overall.getByRole('button',{name:/row 2 .*Up 0% · Down 33% · Neutral 67%/});expect(neutral.getAttribute('aria-pressed')).toBe('true');fireEvent.click(neutral);expect(choose).toHaveBeenCalledWith(rows[1]);
 expect(overall.getByRole('button',{name:/row 3 .*Up 67% · Down 33% · Neutral 0%/})).toBeTruthy();expect(overall.getByRole('button',{name:/row 7 .*Down 100%/})).toBeTruthy();
});
it('shows immutable exact thirds, group conflict and saved truth rather than a current-panel substitute',()=>{
 render(<SavedAgreementEvidence condition={rows[2].evaluation.conditions[0]}/>);const panel=screen.getByLabelText('Saved agreement condition 1 evidence');
 expect(panel.textContent).toContain('Up 2/3');expect(panel.textContent).toContain('Down 1/3');expect(panel.textContent).toContain('saved verdict True');expect(panel.textContent).toContain('Group conflict: Yes');expect(panel.textContent).toContain('0.66 fraction');expect(panel.textContent).toContain('volume');expect(panel.textContent).toContain('native interval 60 seconds (1m)');
});
it('gates agreement capability by exact manifest while preserving legacy numeric controls',async()=>{
 expect(supportedAgreementCapability(capability)).toBe(true);expect(supportedAgreementCapability({...capability,manifest_hash:'0'.repeat(64)})).toBe(false);mock.capability=false;render(app());await open();const predicate=screen.getByLabelText('Condition 1 predicate');expect(within(predicate).queryByRole('option',{name:'agreement'})).toBeNull();expect(within(predicate).getByRole('option',{name:'cross above'})).toBeTruthy();expect(screen.getByLabelText('Condition 1 level')).toBeTruthy();
});
it('submits fraction units and selected strict-majority groups, rejecting percent-style 70',async()=>{
 render(app());await open();fireEvent.change(screen.getByLabelText('Condition 1 predicate'),{target:{value:'agreement'}});
 fireEvent.change(screen.getByLabelText('Condition 1 agreement threshold fraction'),{target:{value:'70'}});expect((screen.getByRole('button',{name:'Preview frozen alert'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.change(screen.getByLabelText('Condition 1 agreement threshold fraction'),{target:{value:'0.66'}});fireEvent.click(screen.getByLabelText('Condition 1 requires trend'));fireEvent.click(screen.getByLabelText('Condition 1 requires momentum'));fireEvent.click(screen.getByRole('button',{name:'Preview frozen alert'}));await screen.findByLabelText('Frozen agreement composition');
 expect(mock.calls.find(x=>x.c==='alert_preview').p.conditions).toEqual([{predicate:'agreement',direction:'up',threshold:.66,required_groups:['trend','momentum']}]);expect((screen.getByRole('button',{name:'Save alert paused'}) as HTMLButtonElement).disabled).toBe(true);
});
it('applied composition change invalidates reviewed preview and explicit refresh retains authored condition',async()=>{
 const mount=render(app());await open();fireEvent.change(screen.getByLabelText('Condition 1 predicate'),{target:{value:'agreement'}});fireEvent.change(screen.getByLabelText('Condition 1 agreement threshold fraction'),{target:{value:'0.66'}});fireEvent.click(screen.getByRole('button',{name:'Preview frozen alert'}));await screen.findByLabelText('Reviewed frozen alert preview');fireEvent.click(screen.getByLabelText('Reviewed frozen alert preview'));
 mount.rerender(app(8,true));await waitFor(()=>expect(screen.queryByLabelText('Reviewed frozen alert preview')).toBeNull());expect((screen.getByRole('button',{name:'Preview frozen alert'}).closest('fieldset') as HTMLFieldSetElement).disabled).toBe(true);fireEvent.click(screen.getByRole('button',{name:'Refresh applied composition'}));await waitFor(()=>expect((screen.getByRole('button',{name:'Preview frozen alert'}).closest('fieldset') as HTMLFieldSetElement).disabled).toBe(false));expect((screen.getByLabelText('Condition 1 agreement threshold fraction') as HTMLInputElement).value).toBe('0.66');fireEvent.click(screen.getByRole('button',{name:'Preview frozen alert'}));await screen.findByLabelText('Reviewed frozen alert preview');expect((screen.getByLabelText('Reviewed frozen alert preview') as HTMLInputElement).checked).toBe(false);expect(mock.calls.filter(x=>x.c==='alert_preview').at(-1).p.settings_revision).toBe(8);
});
function Launch(){const r=useAlertResearch()!;return <button onClick={()=>r.open({kind:'saved'})}>Independent saved research</button>;}
async function savedResearch(){render(<StrictMode><AlertResearchProvider><Launch/></AlertResearchProvider></StrictMode>);fireEvent.click(screen.getByRole('button',{name:'Independent saved research'}));fireEvent.click(await screen.findByRole('button',{name:'Open scan 1'}));await screen.findByLabelText('Select exact saved candle');}
it('selects a nonhit exact close and previous-next within the window without a market mutation',async()=>{
 await savedResearch();fireEvent.change(screen.getByLabelText('Select exact saved candle'),{target:{value:'1'}});await screen.findByText('Exact selected row 2');expect(screen.getByLabelText('raw price probe').getAttribute('data-target')).toBe(String(base+60));fireEvent.click(screen.getByRole('button',{name:'Next candle'}));await screen.findByText('Exact selected row 3');fireEvent.click(screen.getByRole('button',{name:'Previous candle'}));await screen.findByText('Exact selected row 2');expect(mock.calls.every(x=>x.c.startsWith('alert_history_'))).toBe(true);
});
it('uses exact row fallback for adjacent close beyond a byte-clipped page and retains its timeline',async()=>{
 const normal=mock.api.getMockImplementation()!;mock.api.mockImplementation((c,p)=>{if(c==='alert_history_chart'){mock.calls.push({c,p});if(p.start_index===2)return Promise.reject(Error('chart wrapper byte budget'));return Promise.resolve(windowOf(rows.slice(0,2),2,p.target_confirmed_at));}if(c==='alert_history_row'){mock.calls.push({c,p});return Promise.resolve(rows[2]);}return normal(c,p);});
 await savedResearch();fireEvent.change(screen.getByLabelText('Select exact saved candle'),{target:{value:'1'}});fireEvent.click(screen.getByRole('button',{name:'Next candle'}));await screen.findByText('Exact selected row 3');expect(mock.calls.find(x=>x.c==='alert_history_row').p.confirmed_at).toBe(base+180);expect(screen.getByLabelText('raw price probe').getAttribute('data-target')).toBe(String(base+120));expect(within(screen.getByLabelText('Overall timeline lane')).getAllByRole('button')).toHaveLength(1);expect(screen.getByText(/Only the exact saved row is shown/)).toBeTruthy();
});
