import {act,render,screen,fireEvent} from '@testing-library/react';
import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
import {api} from './api';
import {displayRecorder,observeChartDisplay,observeDisplay,DisplayedMetrics,DisplayedComparisonRow,DisplayTrackingNotice,finishDisplayWrites} from './DisplayedEvidence';
import EvidenceFreeze,{EvidenceSummary} from './EvidenceFreeze';
vi.mock('./api',()=>({api:vi.fn()}));
let observers:{callback:(entries:any[])=>void;target:HTMLElement|null}[]=[];
let frames:(()=>void)[]=[];
const intersection=(target:HTMLElement,visible=true)=>{for(const o of observers)if(o.target===target)o.callback([{target,isIntersecting:visible,intersectionRect:{width:visible?100:0,height:visible?100:0}}]);};
const flush=()=>{const current=frames;frames=[];current.forEach(f=>f());};
beforeEach(()=>{
 observers=[];frames=[];vi.mocked(api).mockReset().mockResolvedValue({recorded:1});
 vi.stubGlobal('IntersectionObserver',class {entry:any;constructor(callback:any){this.entry={callback,target:null};observers.push(this.entry);}observe(target:HTMLElement){this.entry.target=target;}disconnect(){this.entry.target=null;}});
 vi.stubGlobal('requestAnimationFrame',(f:()=>void)=>{frames.push(f);return frames.length;});vi.stubGlobal('cancelAnimationFrame',()=>{});
 vi.spyOn(HTMLElement.prototype,'getClientRects').mockReturnValue([{width:100,height:100}] as any);
});
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});

describe('actual displayed evidence',()=>{
 it('prefetched, hidden and document-hidden metrics produce zero writes; showing deduplicates',async()=>{
  const {container,rerender}=render(<div hidden><DisplayedMetrics reference={{surface:'run_metrics',run_id:'a'}}><span data-metric>Metrics</span></DisplayedMetrics></div>);
  const target=container.querySelector('span')!;
  expect(api).not.toHaveBeenCalled();act(()=>{intersection(target);flush();});expect(api).not.toHaveBeenCalled();
  rerender(<div><DisplayedMetrics reference={{surface:'run_metrics',run_id:'a'}}><span data-metric>Metrics</span></DisplayedMetrics></div>);
  vi.spyOn(document,'visibilityState','get').mockReturnValue('hidden');act(()=>{intersection(target);flush();});expect(api).not.toHaveBeenCalled();
  vi.spyOn(document,'visibilityState','get').mockReturnValue('visible');act(()=>{intersection(target);flush();intersection(target);flush();});
  await finishDisplayWrites();expect(api).toHaveBeenCalledTimes(1);expect(vi.mocked(api).mock.calls[0][1]).toMatchObject({viewport:null,reference:{surface:'run_metrics',run_id:'a'}});
 });
 it('does not record a mounted surface covered by an open app modal',()=>{
  const host=document.createElement('div'),dialog=document.createElement('dialog');dialog.setAttribute('open','');document.body.append(host,dialog);const send=vi.fn();const watch=observeDisplay(host,send);
  act(()=>{intersection(host);flush();});expect(send).not.toHaveBeenCalled();dialog.remove();act(()=>{watch.schedule();flush();});expect(send).toHaveBeenCalledOnce();watch.dispose();host.remove();
 });
 it('records inclusive visible candle labels only, skips whitespace and keeps open/close mapping at backend',()=>{
  const host=document.createElement('div');document.body.append(host);let range:any={from:661,to:779};let change:()=>void=()=>{};
  const chart={timeScale:()=>({getVisibleRange:()=>range,subscribeVisibleTimeRangeChange:(f:any)=>{change=f;},unsubscribeVisibleTimeRangeChange:vi.fn()})};const send=vi.fn();
  const stop=observeChartDisplay(host,chart,[{time:600},{time:660},{time:780}],60,false,send);
  act(()=>{intersection(host);flush();});expect(send).not.toHaveBeenCalled();
  range={from:660,to:840};act(()=>{change();flush();});expect(send).toHaveBeenLastCalledWith([660,780]);
  act(()=>{intersection(host,false);flush();change();flush();});expect(send).toHaveBeenCalledTimes(1);stop();host.remove();
 });
 it('comparison numeric cells share one recorder; state/name cells never count',async()=>{
  const {container}=render(<table><tbody><DisplayedComparisonRow reference={{surface:'comparison_metrics',batch_id:'b',ordinal:1}}><td>Name</td><td><span data-metric>12</span></td><td><span data-metric>20</span></td></DisplayedComparisonRow></tbody></table>);
  const cells=container.querySelectorAll('td'),values=container.querySelectorAll('span');expect(observers).toHaveLength(2);
  act(()=>{intersection(cells[0]);intersection(cells[1]);flush();});expect(api).not.toHaveBeenCalled();
  act(()=>{intersection(values[1]);flush();intersection(values[0]);flush();});await finishDisplayWrites();expect(api).toHaveBeenCalledTimes(1);
 });
 it('retains earlier ranges and bounds identical callbacks; freeze drain waits pending writes',async()=>{
  let resolve!:(v:any)=>void;vi.mocked(api).mockImplementationOnce(()=>new Promise(r=>resolve=r));
  const record=displayRecorder();for(let i=0;i<50;i++)record({surface:'observation_chart',page_id:'p'},[1,2]);
  let drained=false;const done=finishDisplayWrites().then(()=>{drained=true;});await Promise.resolve();expect(drained).toBe(false);
  resolve({recorded:1});await done;expect(drained).toBe(true);expect(api).toHaveBeenCalledTimes(1);
  record({surface:'observation_chart',page_id:'p'},[2,3]);await finishDisplayWrites();expect(api).toHaveBeenCalledTimes(2);
 });
 it('renders manual view summaries without cohort/profile and keeps separate coverage dates',()=>{
  render(<EvidenceSummary value={{message:'1 displayed range; zero attempts',range:[600,900],coverage_start:'old',view_coverage_start:'new',groups:[{kind:'viewed',role:'observation_chart',route:'observations',count:1}],limitation:'Partial'}}/>);
  expect(screen.getByText(/manual chart/)).toBeTruthy();expect(screen.getByText(/Display coverage begins new/)).toBeTruthy();
 });
 it('latches write failure visibly despite subsequent successful records and reading stays mounted',async()=>{
  vi.mocked(api).mockRejectedValueOnce(Error('disk unavailable'));
  render(<><p>Readable report</p><DisplayTrackingNotice/></>);const record=displayRecorder();
  await act(async()=>{record({surface:'run_metrics',run_id:'a'},null);await finishDisplayWrites();});
  expect(screen.getByText('Readable report')).toBeTruthy();expect(screen.getByRole('alert').textContent).toContain('could not be recorded');
  await act(async()=>{record({surface:'run_metrics',run_id:'b'},null);await finishDisplayWrites();});expect(screen.getByRole('alert').textContent).toContain('incomplete');
 });
 it('persists a frontend-only caveat before review and blocks confirmation visibly if persistence fails',async()=>{
  vi.mocked(api).mockRejectedValueOnce(Error('Synthetic frontend transport failure'));
  displayRecorder()({surface:'run_metrics',run_id:'transport-failure'},null);await finishDisplayWrites();
  vi.mocked(api).mockClear();
  const summary={groups:[],message:'Zero known events',limitation:'Incomplete'};
  vi.mocked(api).mockImplementation(async(command)=>{if(command==='research_display_incomplete')return {recorded:true};return summary;});
  const freeze=vi.fn().mockResolvedValue(undefined);
  render(<EvidenceFreeze label="Freeze checked candidate" disabled={false} request={{dataset_id:'data',start:60,end:120}} onFreeze={freeze}/>);
  fireEvent.click(screen.getByText('Freeze checked candidate'));
  await act(async()=>{flush();await Promise.resolve();await Promise.resolve();});
  expect(vi.mocked(api).mock.calls.map(c=>c[0])).toEqual(['research_display_incomplete','research_evidence_preview']);
  vi.mocked(api).mockRejectedValueOnce(Error('Cannot persist display caveat'));
  fireEvent.click(screen.getByText('Confirm candidate freeze'));
  await act(async()=>{flush();await Promise.resolve();await Promise.resolve();});
  expect(freeze).not.toHaveBeenCalled();expect(screen.getByText('Error: Cannot persist display caveat')).toBeTruthy();expect(screen.getByRole('dialog')).toBeTruthy();
 });

});
