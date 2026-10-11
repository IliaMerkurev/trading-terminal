import {describe, expect, it, vi} from 'vitest';
import type {Logical, SeriesAttachedParameter, Time} from 'lightweight-charts';
import {IchimokuPrimitive, ichimokuAutoscale, ichimokuCloudCells, ichimokuHoverAtLogical,
  ichimokuLogicalExtent, ichimokuProjectionLines, splitIchimokuCloudCell,
  type IchimokuLines, type IchimokuPoint, type IchimokuProjections} from './chartIchimokuPrimitive';

function point(logical: number, value: number, segment = 0): IchimokuPoint {
  return {logical, value, segment, computedAt: 100 + logical, plottedAt: 200 + logical, estimated: false};
}
function lines(a: IchimokuPoint[] = [], b: IchimokuPoint[] = [], c: IchimokuPoint[] = []): IchimokuLines {
  return {senkou_a: a, senkou_b: b, chikou: c};
}
function envelope(): IchimokuProjections {
  return {version: 1, contract: 'ichimoku-raw-ordinal-v1', raw_times: [100, 200, 400, 500], horizon: 500,
    instances: {cloud: {displacement: 2, source_logical: [-1, 0, 1, 2],
      computed_at: [50, 100, 200, 400], segment: [0, 0, 1, 1],
      senkou_a: [10, 11, 12, 13], senkou_b: [9, 10, 11, 12], chikou: [null, null, null, 15],
      senkou_plotted_at: [200, 400, 500, 600], chikou_plotted_at: [null, null, null, 100],
      senkou_estimated: [false, false, false, true]}}};
}

describe('Ichimoku raw-ordinal projection boundary', () => {
  it('retains left-edge sources and shifts by raw bars rather than elapsed time', () => {
    const data = envelope(), result = ichimokuProjectionLines(data, 'cloud', data.raw_times);
    expect(result.senkou_a.map(p => [p.logical, p.plottedAt])).toEqual([[1, 200], [2, 400], [3, 500], [4, 600]]);
    expect(result.senkou_a[0].computedAt).toBe(50);
    expect(result.chikou).toEqual([{logical: 0, value: 15, segment: 1, computedAt: 400, plottedAt: 100, estimated: false}]);
    expect(ichimokuLogicalExtent(result)).toEqual({from: 0, to: 4});
  });
  it('matches the independent 2/3/4-period, displacement-2 projection golden', () => {
    const data: IchimokuProjections = {version: 1, contract: 'ichimoku-raw-ordinal-v1',
      raw_times: [60, 120, 180, 240, 300, 360], horizon: 360, instances: {golden: {
        displacement: 2, source_logical: [2, 3, 4, 5], computed_at: [180, 240, 300, 360], segment: [0, 0, 0, 0],
        senkou_a: [2.25, 3.25, 4.25, 5.25], senkou_b: [null, 2.5, 3.5, 4.5], chikou: [3, 4, 5, 6],
        senkou_plotted_at: [300, 360, 420, 480], chikou_plotted_at: [60, 120, 180, 240],
        senkou_estimated: [false, false, true, true],
      }}};
    const result = ichimokuProjectionLines(data, 'golden', data.raw_times);
    expect(result.senkou_a[0]).toMatchObject({value: 2.25, logical: 4});
    expect(result.senkou_b[0]).toMatchObject({value: 2.5, logical: 5});
    expect(result.senkou_a.at(-1)).toMatchObject({value: 5.25, logical: 7, estimated: true});
    expect(result.senkou_b.at(-1)).toMatchObject({value: 4.5, logical: 7});
    expect(result.chikou[0]).toMatchObject({value: 3, logical: 0, computedAt: 180, plottedAt: 60});
  });
  it('does not put synthetic projected times into the raw timestamp array', () => {
    const data = envelope(), before = structuredClone(data);
    ichimokuProjectionLines(data, 'cloud', data.raw_times);
    expect(data).toEqual(before);
    expect(data.raw_times).not.toContain(600);
  });
  it('rejects disjoint/stale raw windows and missing instances', () => {
    const data = envelope();
    expect(ichimokuProjectionLines(data, 'cloud', [200, 400, 500, 600])).toEqual(lines());
    expect(ichimokuProjectionLines(data, 'missing', data.raw_times)).toEqual(lines());
  });
  it.each(['source', 'computed', 'length', 'segment', 'time', 'finite', 'displacement', 'contract', 'estimated', 'prefix'])(
    'fails closed for invalid %s', kind => {
      const data = envelope(), item = data.instances.cloud;
      if (kind === 'source') item.source_logical[0] = -3;
      if (kind === 'computed') item.computed_at[3] = 501;
      if (kind === 'length') item.senkou_b.pop();
      if (kind === 'segment') item.segment[1] = -1;
      if (kind === 'time') item.senkou_plotted_at[1] = 300;
      if (kind === 'finite') item.senkou_a[1] = NaN;
      if (kind === 'displacement') item.displacement = 101;
      if (kind === 'estimated') item.senkou_estimated[0] = true;
      if (kind === 'prefix') item.computed_at[0] = 100;
      if (kind === 'contract') (data as {version: number}).version = 2;
      expect(ichimokuProjectionLines(data, 'cloud', data.raw_times)).toEqual(lines());
    });
  it('preserves computation provenance when future values alter historical Chikou', () => {
    const data = envelope(), before = ichimokuProjectionLines(data, 'cloud', data.raw_times);
    data.instances.cloud.chikou[3] = 99;
    const after = ichimokuProjectionLines(data, 'cloud', data.raw_times);
    expect(after.senkou_a.filter(p => p.computedAt < 400)).toEqual(before.senkou_a.filter(p => p.computedAt < 400));
    expect(after.chikou[0]).toMatchObject({logical: 0, computedAt: 400, plottedAt: 100, value: 99});
  });
});

describe('Ichimoku cloud geometry', () => {
  it('splits a crossing into two non-bow-tie polygons with opposite colors', () => {
    const cells = splitIchimokuCloudCell(0, 10, 10, 30, 30, 10, true, false);
    expect(cells).toEqual([
      {bullish: true, points: [{x: 0, y: 10}, {x: 5, y: 20}, {x: 5, y: 20}, {x: 0, y: 30}]},
      {bullish: false, points: [{x: 5, y: 20}, {x: 10, y: 30}, {x: 10, y: 10}, {x: 5, y: 20}]},
    ]);
  });
  it('uses screen-space crossings after logarithmic price conversion', () => {
    const data = lines([point(0, 100), point(1, 10)], [point(0, 1), point(1, 100)]);
    const cells = ichimokuCloudCells(data, logical => logical * 30, price => -Math.log10(price));
    expect(cells).toHaveLength(2);
    expect(cells[0].points[1].x).toBeCloseTo(20);
    expect(cells[0].points[1].y).toBeCloseTo(-4 / 3);
    expect(cells.map(c => c.bullish)).toEqual([true, false]);
  });
  it('handles a crossing exactly at a vertex without a spurious opposite-color area', () => {
    expect(splitIchimokuCloudCell(0, 1, 2, 1, 2, 3, false, true)).toEqual([
      {bullish: true, points: [{x: 0, y: 2}, {x: 1, y: 1}, {x: 1, y: 3}, {x: 0, y: 2}]},
    ]);
  });
  it('does not join across missing values, missing ordinals, or computation segments', () => {
    const a = [point(0, 3), point(1, 4, 1), point(3, 6, 1)];
    expect(ichimokuCloudCells(lines(a, [point(0, 1), point(1, 2, 1), point(3, 4, 1)]), x => x, y => y)).toEqual([]);
    expect(ichimokuCloudCells(lines([point(0, 3), point(1, 4)], [point(0, 1)]), x => x, y => y)).toEqual([]);
    expect(ichimokuCloudCells(lines([point(0, 3), point(1, 4)], [point(0, 1, 1), point(1, 2, 1)]), x => x, y => y)).toEqual([]);
  });
  it('omits unavailable coordinates and rejects nonfinite geometry', () => {
    expect(ichimokuCloudCells(lines([point(0, 3), point(1, 4)], [point(0, 1), point(1, 2)]), () => null, y => y)).toEqual([]);
    expect(splitIchimokuCloudCell(0, 1, 2, NaN, 3, 4, true, false)).toEqual([]);
  });
});

describe('Ichimoku extent, hover and scaling', () => {
  it('provides projection hover without event.time and discloses later-known Chikou', () => {
    const data = envelope(), result = ichimokuProjectionLines(data, 'cloud', data.raw_times);
    expect(ichimokuHoverAtLogical(result, 4.2)).toMatchObject([
      {port: 'senkou_a', logical: 4, computedAt: 400, plottedAt: 600, estimated: true, laterKnown: false},
      {port: 'senkou_b', logical: 4, estimated: true},
    ]);
    expect(ichimokuHoverAtLogical(result, 0)[0]).toMatchObject({port: 'chikou', laterKnown: true});
    expect(ichimokuHoverAtLogical(result, 7)).toEqual([]);
  });
  it('includes projected-only values and segments crossing viewport edges in autoscale', () => {
    const data = lines([point(4, 10), point(5, 20)], [], [point(1, 1000)]);
    expect(ichimokuAutoscale(data, 4, 5)).toEqual({priceRange: {minValue: 10, maxValue: 20}});
    expect(ichimokuAutoscale(data, 4.4, 4.6)).toEqual({priceRange: {minValue: 10, maxValue: 20}});
    expect(ichimokuAutoscale(data, 2, 3)).toBeNull();
    expect(ichimokuAutoscale(lines([point(4, 10), point(5, 20, 1)]), 4.4, 4.6)).toBeNull();
    expect(ichimokuLogicalExtent(lines())).toBeNull();
  });
});

function attachedContext() {
  const requestUpdate = vi.fn(), options = {autoScale: true};
  const priceToCoordinate = vi.fn((value: number) => -Math.log10(value));
  const logicalToCoordinate = vi.fn((value: number) => value * 10);
  return {requestUpdate, options, priceToCoordinate, logicalToCoordinate, context: {
    chart: {timeScale: () => ({logicalToCoordinate})}, series: {priceToCoordinate, priceScale: () => ({options: () => options})},
    requestUpdate,
  } as unknown as SeriesAttachedParameter<Time>};
}

describe('Ichimoku primitive lifecycle and actual canvas calls', () => {
  it('redraws, preserves manual scale, detaches cleanly, and reattaches a snapshot', () => {
    const primitive = new IchimokuPrimitive(), attached = attachedContext();
    const data = lines([point(0, 10), point(1, 20)]);
    primitive.setData(data); primitive.attached(attached.context);
    data.senkou_a[0].value = 999;
    expect(primitive.autoscaleInfo(0 as Logical, 1 as Logical)).toEqual({priceRange: {minValue: 10, maxValue: 20}});
    attached.options.autoScale = false;
    expect(primitive.autoscaleInfo(0 as Logical, 1 as Logical)).toBeNull();
    primitive.detached(); const calls = attached.requestUpdate.mock.calls.length;
    primitive.clear(); expect(attached.requestUpdate).toHaveBeenCalledTimes(calls);
    expect(primitive.extent()).toBeNull();
    primitive.attached(attached.context); primitive.setData(lines([point(5, 7)]));
    expect(primitive.extent()).toEqual({from: 5, to: 5});
  });
  it('renders fill behind prices and strokes separately with the carrier price converter', () => {
    const primitive = new IchimokuPrimitive(), attached = attachedContext();
    primitive.attached(attached.context);
    primitive.setData(lines([point(0, 100), point(1, 10)], [point(0, 1), point(1, 100)], [point(0, 5), point(2, 6)]));
    const context = {save: vi.fn(), restore: vi.fn(), beginPath: vi.fn(), moveTo: vi.fn(), lineTo: vi.fn(),
      closePath: vi.fn(), fill: vi.fn(), stroke: vi.fn(), fillStyle: '', strokeStyle: '', lineWidth: 0};
    const target = {useMediaCoordinateSpace: (draw: (scope: unknown) => void) => draw({context})};
    expect(primitive.paneViews().map(view => view.zOrder?.())).toEqual(['bottom', 'normal']);
    for (const view of primitive.paneViews()) view.renderer()!.draw(target as never);
    expect(context.fill).toHaveBeenCalledTimes(2);
    expect(context.stroke).toHaveBeenCalledTimes(3);
    expect(attached.priceToCoordinate).toHaveBeenCalledWith(100);
    expect(attached.logicalToCoordinate).toHaveBeenCalledWith(2);
    // Two cloud quadrilaterals plus two connected Senkou line segments; Chikou's gap has no line.
    expect(context.lineTo).toHaveBeenCalledTimes(8);
    primitive.detached();
    for (const view of primitive.paneViews()) view.renderer()!.draw(target as never);
    expect(context.fill).toHaveBeenCalledTimes(2);
  });
});
