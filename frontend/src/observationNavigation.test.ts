import {describe,it,expect} from 'vitest';
import {navigationBounds,navigationDraft,navigationUTC,navigationWindow,parseNavigationUTC} from './observationNavigation';

const origin=1704067200;
describe('native saved-history boundaries',()=>{
 it.each([1,500,501,900,1000,1001,1200])('anchors the latest page for %s slots',slots=>{
  const bounds=navigationBounds({range:[origin,origin+slots*3600],interval_seconds:3600})!;
  const expected=slots<=500?0:slots<=1000?500:1000;
  expect(bounds.latest).toBe(origin+expected*3600);
  expect(navigationWindow(bounds,bounds.start)).toEqual({start:origin,end:origin+Math.min(500,slots)*3600});
  expect(navigationWindow(bounds,bounds.latest)).toEqual({start:origin+expected*3600,end:origin+slots*3600});
 });
 it.each([60,300,900,3600,14400,86400])('uses exact %s-second boundaries independently of display widths or row counts',step=>{
  const bounds=navigationBounds({range:[origin,origin+1200*step],interval_seconds:step})!;
  expect(navigationWindow(bounds,origin+613*step)).toEqual({start:origin+613*step,end:origin+1113*step});
  expect(navigationWindow(bounds,origin+1113*step)).toEqual({start:origin+1113*step,end:origin+1200*step});
  expect(navigationDraft(navigationUTC(origin),bounds)).toEqual({start:origin,issue:null});
  expect(navigationDraft(navigationUTC(bounds.end-step),bounds)).toEqual({start:bounds.end-step,issue:null});
  for(const time of [origin-step,bounds.end,bounds.end+step,origin+1])expect(navigationDraft(navigationUTC(time),bounds).issue).toBeTruthy();
  for(let index=0;index<1200;index+=37){const window=navigationWindow(bounds,origin+index*step)!;expect((window.end-window.start)/step).toBeGreaterThan(0);expect((window.end-window.start)/step).toBeLessThanOrEqual(500);}
 });
 it.each([null,{}, {range:[0,0]},{range:[60,0]},{range:[0,61]},{range:[0,60],interval_seconds:0},{range:[0,60],interval_seconds:-1},{range:[0,60],interval_seconds:0.5},{range:[0,60],interval_seconds:Infinity},{range:[0,NaN]},{range:[0,Infinity]},{range:[0,Number.MAX_SAFE_INTEGER]},{range:[0,60,120]},{range:['0',60]},{range:[1,61]},{range:[-8640000000001,0]}])('rejects malformed source arithmetic: %j',source=>{
  expect(navigationBounds(source)).toBeNull();
 });
 it('defaults only an omitted native interval to one minute',()=>{
  expect(navigationBounds({range:[0,60]})).toEqual({start:0,end:60,step:60,slots:1,latest:0});
 });
});
describe('literal UTC parsing',()=>{
 it.each(['','2024-01-01','2024-1-01T00:00','2024-02-31T00:00','2023-02-29T00:00','2024-04-31T00:00','2024-00-01T00:00','2024-13-01T00:00','2024-01-00T00:00','2024-01-01T24:00','2024-01-01T00:60','2024-01-01T00:00:60','2024-01-01T00:00:00.0','2024-01-01T00:00Z','2024-01-01T00:00+02:00','0000-01-01T00:00',' 2024-01-01T00:00','2024-01-01T00:00 '])('rejects incomplete, normalized or timezone-bearing input %s',value=>expect(parseNavigationUTC(value)).toBeNull());
 it('round-trips valid leap days and years below 100 without local time conversion',()=>{
  expect(parseNavigationUTC('2024-02-29T12:34:56')).toBe(1709210096);
  expect(parseNavigationUTC('2024-01-01T00:00')).toBe(1704067200);
  expect(navigationUTC(parseNavigationUTC('0099-01-01T00:00')!)).toBe('0099-01-01T00:00');
  expect(navigationUTC(parseNavigationUTC('2024-02-29T12:34:56')!)).toBe('2024-02-29T12:34:56');
 });
 it('does not truncate supplied seconds or align to a coarser display bucket',()=>{
  const bounds=navigationBounds({range:[origin,origin+3600*1200],interval_seconds:3600})!;
  expect(navigationDraft('2024-01-01T01:00:00',bounds)).toEqual({start:origin+3600,issue:null});
  expect(navigationDraft('2024-01-01T01:00:01',bounds).issue).toContain('not rounded');
  expect(navigationDraft('2024-01-01T00:30',bounds).issue).toContain('3600-second');
 });
});
