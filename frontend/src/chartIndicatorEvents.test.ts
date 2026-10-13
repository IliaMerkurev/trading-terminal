import {describe, expect, it, vi} from 'vitest';
import type {Logical, SeriesAttachedParameter, Time} from 'lightweight-charts';
import {acceptedIndicatorEvents, indicatorEventsHoverAtLogical, indicatorEventStyle, IndicatorEventsPrimitive} from './chartIndicatorEvents';
const item = {id: 'b', type: 'vmc_cipher_b', visible: true};
const rows = [0,60,120,180,240,300].map(time => ({time, open: 10, high: 12, low: 8, close: 11,
  volume: 1, confirmation: 'synthetic_closed'}));
const context = {source:'bybit',market:'spot',symbol:'BTCUSDT',minutes:1,revision:7};
const event = {id:'div',kind:'regular_bullish',oscillator:'wt',confirmed_at:360,pivot_time:240,
  previous_pivot_time:120,value:-20,previous_value:-40,segment:0};
function result(events: any[] = [event]) {return {status:'ready',origin:{generation:3,time:0},indicator_events:{version:1,
  contract:'confirmed-vmc-events-v1',horizon:360,context:{...context,settings_revision:7,start:0,end:300,generation:3,origin:0},instances:{b:events}}};}
const accept = (data = result(), candles = rows) => acceptedIndicatorEvents(data,item,candles,context);

describe('immutable confirmed VMC event acceptance', () => {
  it('keeps numeric y and confirmation marker separate from actual pivot connectors', () => {
    expect(accept()).toEqual([{...event,logical:5,connector:{from:1,to:3,fromValue:-40,toValue:-20}}]);
    expect(rows.map(row=>row.time)).toEqual([0,60,120,180,240,300]);
  });
  it('rejects every stale context dimension, horizon, version and origin', () => {
    for (const key of ['source','market','symbol','minutes','start','end','settings_revision','generation','origin']) {
      const data = result(); (data.indicator_events.context as any)[key]='stale'; expect(accept(data)).toEqual([]);
    }
    for (const patch of [{version:2},{contract:'other'},{horizon:420}]) {
      const data=result(); Object.assign(data.indicator_events,patch); expect(accept(data)).toEqual([]);
    }
    const data=result(); data.origin.generation=4; expect(accept(data)).toEqual([]);
  });
  it('clears pending, hidden, removed and empty outputs without merging older events', () => {
    expect(acceptedIndicatorEvents(result(),{...item,visible:false},rows,context)).toEqual([]);
    expect(acceptedIndicatorEvents(result(),{...item,id:'removed'},rows,context)).toEqual([]);
    expect(accept({...result(),status:'loading'})).toEqual([]);
    expect(accept(result([]))).toEqual([]); expect(accept(result(),[])).toEqual([]);
  });
  it('deduplicates exact repeats and returns deterministic complete same-bar groups', () => {
    const second = {...event,id:'a',kind:'buy_dot',pivot_time:360};
    const values=accept(result([event,second,{...event}]));
    expect(values.map(v=>v.id)).toEqual(['div','a']);
    expect(accept(result([{...event,value:5},event]))).toEqual([]);
    expect(accept(result([event,{...event,value:5}]))).toEqual([]);
    const details=indicatorEventsHoverAtLogical(values,5);
    expect(details).toHaveLength(2);
    expect(details[0]).toMatchObject({pivotUtc:'1970-01-01T00:04:00.000Z',confirmedUtc:'1970-01-01T00:06:00.000Z',laterKnown:true});
    expect(details[1].laterKnown).toBe(false);
  });
  it.each([{value:NaN},{confirmed_at:420},{confirmed_at:350},{pivot_time:420},{segment:-1},
    {kind:'invented'},{oscillator:'price'},{previous_value:undefined},{previous_pivot_time:240},
    {pivot_time:1e20}])('rejects malformed events %j', patch => {
    expect(accept(result([{...event,...patch}]))).toEqual([]);
  });
  it('omits connectors across gaps, unknown raw rows or a segment boundary but preserves markers', () => {
    const gap=rows.filter(row=>row.time!==120), unknown=rows.map((r,i)=>i===2?{...r,confirmation:'legacy_unknown'}:r);
    expect(accept(result(),gap)[0].connector).toBeUndefined();
    expect(accept(result(),unknown)[0].connector).toBeUndefined();
    expect(accept(result([{...event,segment:120}]))[0].connector).toBeUndefined();
  });
  it('omits unverifiable prior endpoint outside viewport without fabricating logical slots', () => {
    const data=result(), slice=rows.slice(2); data.indicator_events.context.start=120;
    const values=accept(data,slice); expect(values[0].logical).toBe(3); expect(values[0].connector).toBeUndefined();
    expect(values[0].previous_pivot_time).toBe(120);
  });
});

function attached() {
  const options={autoScale:true},requestUpdate=vi.fn(), priceToCoordinate=vi.fn((value:number)=>value*2),logicalToCoordinate=vi.fn((value:number)=>value*10);
  return {options,requestUpdate,priceToCoordinate,logicalToCoordinate,context:{requestUpdate,
    chart:{timeScale:()=>({logicalToCoordinate})},series:{priceToCoordinate,priceScale:()=>({options:()=>options})}} as unknown as SeriesAttachedParameter<Time>};
}
describe('original event primitive lifecycle and canvas', () => {
  it('owns snapshots, preserves manual scales, clears/detaches all prior event geometry', () => {
    const primitive=new IndicatorEventsPrimitive(),owner=attached(),data=accept();
    primitive.attached(owner.context); primitive.setData(data); data[0].value=999; data[0].connector!.fromValue=999;
    expect(primitive.autoscaleInfo(0 as Logical,5 as Logical)).toEqual({priceRange:{minValue:-40,maxValue:-20}});
    owner.options.autoScale=false; expect(primitive.autoscaleInfo(0 as Logical,5 as Logical)).toBeNull();
    primitive.clear(); expect(primitive.hover(5)).toEqual([]);
    primitive.setData(accept()); primitive.detached(); expect(primitive.hover(5)).toEqual([]);
    primitive.attached(owner.context); expect(primitive.hover(5)).toEqual([]);
  });
  it('draws actual pivot endpoints and grouped count while marker stays at confirmed precise y', () => {
    const primitive=new IndicatorEventsPrimitive('#abc'),owner=attached(); primitive.attached(owner.context);
    primitive.setData(accept(result([event,{...event,id:'second',kind:'divergence_buy_dot'}])));
    const canvas={save:vi.fn(),restore:vi.fn(),beginPath:vi.fn(),moveTo:vi.fn(),lineTo:vi.fn(),stroke:vi.fn(),
      arc:vi.fn(),fill:vi.fn(),closePath:vi.fn(),fillText:vi.fn(),strokeStyle:'',fillStyle:'',lineWidth:0,font:''};
    const target={useMediaCoordinateSpace:(fn:any)=>fn({context:canvas})};
    primitive.paneViews()[0].renderer()!.draw(target as never);
    expect(canvas.moveTo).toHaveBeenCalledWith(10,-80); expect(canvas.lineTo).toHaveBeenCalledWith(30,-40);
    expect(canvas.arc).toHaveBeenCalledWith(50,-40,3.5,0,Math.PI*2);
    expect(canvas.fillText).toHaveBeenCalledWith('2',55,-45); expect(primitive.hover(5)).toHaveLength(2);
    primitive.detached(); primitive.paneViews()[0].renderer()!.draw(target as never); expect(canvas.fill).toHaveBeenCalledTimes(2);
  });
});

it('uses recognizable original semantic colors/shapes and keeps the instance accent separate', () => {
  expect(indicatorEventStyle('gold_buy_dot')).toEqual({color:'#e9bd45',shape:'circle'});
  expect(indicatorEventStyle('buy_dot')).toEqual({color:'#42cda8',shape:'circle'});
  expect(indicatorEventStyle('sell_dot')).toEqual({color:'#ed7e86',shape:'circle'});
  expect(indicatorEventStyle('swing_long')).toEqual({color:'#42cda8',shape:'triangle_up'});
  expect(indicatorEventStyle('swing_short')).toEqual({color:'#ed7e86',shape:'triangle_down'});
  expect(indicatorEventStyle('blue_triangle')).toEqual({color:'#5ba7ee',shape:'triangle_up'});
  expect(indicatorEventStyle('blood_diamond')).toEqual({color:'#b82e49',shape:'diamond'});
  expect(indicatorEventStyle('red_diamond')).toEqual({color:'#ed7e86',shape:'diamond'});
  expect(indicatorEventStyle('yellow_cross')).toEqual({color:'#e9bd45',shape:'cross'});
  expect(indicatorEventStyle('red_cross')).toEqual({color:'#ed7e86',shape:'cross'});
  const primitive=new IndicatorEventsPrimitive('#abc'),owner=attached(); primitive.attached(owner.context);
  primitive.setData(accept(result(['gold_buy_dot','blue_triangle','blood_diamond','yellow_cross'].map((kind,i)=>({...event,id:String(i),kind})))));
  const paints:string[]=[];
  const canvas={save:vi.fn(),restore:vi.fn(),beginPath:vi.fn(),moveTo:vi.fn(),lineTo:vi.fn(),
    arc:vi.fn(),closePath:vi.fn(),fillText:vi.fn(),strokeStyle:'',fillStyle:'',lineWidth:0,font:'',
    fill(){paints.push(this.fillStyle);},stroke(){paints.push(this.strokeStyle);}};
  primitive.paneViews()[0].renderer()!.draw({useMediaCoordinateSpace:(fn:any)=>fn({context:canvas})} as never);
  expect(paints).toEqual(['#e9bd45','#5ba7ee','#b82e49','#e9bd45']);
  expect(canvas.closePath).toHaveBeenCalledTimes(2); expect(canvas.fillText).toHaveBeenCalledWith('4',55,-45);
  expect(primitive.hover(5)).toHaveLength(4);
});
