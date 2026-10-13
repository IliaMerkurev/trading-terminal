import type {AutoscaleInfo, IPrimitivePaneRenderer, IPrimitivePaneView, ISeriesPrimitive,
  Logical, SeriesAttachedParameter, Time} from 'lightweight-charts';

/** Display-only raw-ordinal transport. Never pass these shifted points to setData. */
export interface IchimokuProjectionInstance {
  displacement: number;
  source_logical: number[];
  computed_at: number[];
  segment: number[];
  senkou_a: (number | null)[];
  senkou_b: (number | null)[];
  chikou: (number | null)[];
  senkou_plotted_at: (number | null)[];
  chikou_plotted_at: (number | null)[];
  senkou_estimated: boolean[];
}
export interface IchimokuProjections {
  version: 1;
  contract: 'ichimoku-raw-ordinal-v1';
  raw_times: number[];
  horizon: number;
  instances: Record<string, IchimokuProjectionInstance>;
}
export type IchimokuPort = 'senkou_a' | 'senkou_b' | 'chikou';
export interface IchimokuPoint {
  logical: number;
  value: number;
  segment: number;
  computedAt: number;
  plottedAt: number;
  estimated: boolean;
}
export type IchimokuLines = Record<IchimokuPort, IchimokuPoint[]>;
export interface IchimokuHover extends IchimokuPoint {
  port: IchimokuPort;
  /** Chikou's historical location must not imply historical availability. */
  laterKnown: boolean;
}
export interface CloudCell {
  points: {x: number; y: number}[];
  bullish: boolean;
}
const ports: IchimokuPort[] = ['senkou_a', 'senkou_b', 'chikou'];
const emptyLines = (): IchimokuLines => ({senkou_a: [], senkou_b: [], chikou: []});
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);

/** Fail closed on stale raw windows. Source/generation acceptance remains the caller's job. */
export function ichimokuProjectionLines(
  envelope: IchimokuProjections | null | undefined, id: string, rawTimes: readonly number[],
): IchimokuLines {
  const empty = emptyLines();
  if (!envelope || envelope.version !== 1 || envelope.contract !== 'ichimoku-raw-ordinal-v1'
    || !Array.isArray(envelope.raw_times) || !rawTimes.length
    || envelope.raw_times.length !== rawTimes.length
    || !rawTimes.every((time, i) => finite(time) && time === envelope.raw_times[i]
      && (i === 0 || time > rawTimes[i - 1]))
    || !finite(envelope.horizon) || envelope.horizon < rawTimes[rawTimes.length - 1]) return empty;
  const item = envelope.instances?.[id];
  if (!item || !Number.isInteger(item.displacement) || item.displacement < 1 || item.displacement > 100
    || !Array.isArray(item.source_logical)) return empty;
  const n = item.source_logical.length, d = item.displacement;
  if (n > rawTimes.length + d || ![item.computed_at, item.segment, item.senkou_a, item.senkou_b,
    item.chikou, item.senkou_plotted_at, item.chikou_plotted_at, item.senkou_estimated]
    .every(column => Array.isArray(column) && column.length === n)) return empty;
  const lines = emptyLines();
  for (let i = 0; i < n; i++) {
    const source = item.source_logical[i], computedAt = item.computed_at[i], segment = item.segment[i];
    if (!Number.isInteger(source) || source < -d || source >= rawTimes.length
      || (i > 0 && source <= item.source_logical[i - 1]) || !finite(computedAt)
      || computedAt > envelope.horizon || !Number.isInteger(segment) || segment < 0
      || (source >= 0 && computedAt !== rawTimes[source])
      || (source < 0 && computedAt >= rawTimes[0])
      || (i > 0 && computedAt <= item.computed_at[i - 1])
      || typeof item.senkou_estimated[i] !== 'boolean') return empty;
    for (const port of ports) {
      const value = item[port][i], logical = source + (port === 'chikou' ? -d : d);
      const plottedAt = (port === 'chikou' ? item.chikou_plotted_at : item.senkou_plotted_at)[i];
      if (value === null) continue;
      if (!finite(value) || !finite(plottedAt) || logical < 0 || logical > rawTimes.length - 1 + d
        || (logical < rawTimes.length && (plottedAt !== rawTimes[logical]
          || (port !== 'chikou' && item.senkou_estimated[i])))
        || (logical >= rawTimes.length && (port === 'chikou' || !item.senkou_estimated[i]
          || plottedAt <= rawTimes[rawTimes.length - 1]))) return empty;
      lines[port].push({logical, value, segment, computedAt, plottedAt,
        estimated: port !== 'chikou' && item.senkou_estimated[i]});
    }
  }
  return lines;
}

function adjacent(a: IchimokuPoint, b: IchimokuPoint) {
  return b.logical === a.logical + 1 && b.segment === a.segment;
}

/** Split in rendered coordinates, so logarithmic conversion cannot create bow-ties. */
export function splitIchimokuCloudCell(
  x0: number, x1: number, a0: number, a1: number, b0: number, b1: number,
  bullish0: boolean, bullish1: boolean,
): CloudCell[] {
  if (![x0, x1, a0, a1, b0, b1].every(finite) || x1 <= x0) return [];
  const cell = (left: number, right: number, al: number, ar: number, bl: number, br: number,
    bullish: boolean): CloudCell => ({bullish, points: [
    {x: left, y: al}, {x: right, y: ar}, {x: right, y: br}, {x: left, y: bl},
  ]});
  const delta0 = a0 - b0, delta1 = a1 - b1;
  if (delta0 * delta1 < 0) {
    const t = delta0 / (delta0 - delta1), x = x0 + (x1 - x0) * t, y = a0 + (a1 - a0) * t;
    return [cell(x0, x, a0, y, b0, y, bullish0), cell(x, x1, y, a1, y, b1, bullish1)];
  }
  return [cell(x0, x1, a0, a1, b0, b1, delta0 === 0 ? bullish1 : bullish0)];
}

export function ichimokuCloudCells(lines: IchimokuLines,
  x: (logical: number) => number | null, y: (price: number) => number | null): CloudCell[] {
  const cells: CloudCell[] = [], bByLogical = new Map(lines.senkou_b.map(point => [point.logical, point]));
  for (let i = 1; i < lines.senkou_a.length; i++) {
    const a0 = lines.senkou_a[i - 1], a1 = lines.senkou_a[i];
    const b0 = bByLogical.get(a0.logical), b1 = bByLogical.get(a1.logical);
    if (!b0 || !b1 || !adjacent(a0, a1) || !adjacent(b0, b1)
      || a0.segment !== b0.segment || a1.segment !== b1.segment) continue;
    const coords = [x(a0.logical), x(a1.logical), y(a0.value), y(a1.value), y(b0.value), y(b1.value)];
    if (coords.some(value => value === null)) continue;
    cells.push(...splitIchimokuCloudCell(...coords as [number, number, number, number, number, number],
      a0.value >= b0.value, a1.value >= b1.value));
  }
  return cells;
}

/** Explicit Fit can include this extent; Return must still target the last raw row. */
export function ichimokuLogicalExtent(lines: IchimokuLines): {from: number; to: number} | null {
  const all = ports.flatMap(port => lines[port].map(point => point.logical));
  return all.length ? {from: Math.min(...all), to: Math.max(...all)} : null;
}

export function ichimokuHoverAtLogical(lines: IchimokuLines, logical: number, tolerance = 0.5): IchimokuHover[] {
  if (!finite(logical) || !finite(tolerance) || tolerance < 0) return [];
  return ports.flatMap(port => {
    let nearest: IchimokuPoint | undefined;
    for (const point of lines[port]) if (Math.abs(point.logical - logical) <= tolerance
      && (!nearest || Math.abs(point.logical - logical) < Math.abs(nearest.logical - logical))) nearest = point;
    return nearest ? [{...nearest, port, laterKnown: port === 'chikou' && nearest.computedAt > nearest.plottedAt}] : [];
  });
}

/** Include crossing viewport edges, but never bridge an unavailable slot or segment. */
export function ichimokuAutoscale(lines: IchimokuLines, from: number, to: number): AutoscaleInfo | null {
  if (!finite(from) || !finite(to) || from > to) return null;
  let min = Infinity, max = -Infinity;
  const include = (value: number) => {min = Math.min(min, value); max = Math.max(max, value);};
  for (const port of ports) {
    const points = lines[port];
    for (let i = 0; i < points.length; i++) {
      const point = points[i];
      if (point.logical >= from && point.logical <= to) include(point.value);
      const next = points[i + 1];
      // Bounding endpoint prices is conservative for both linear and log interpolation.
      if (next && adjacent(point, next) && point.logical < to && next.logical > from) {
        include(point.value); include(next.value);
      }
    }
  }
  return min === Infinity ? null : {priceRange: {minValue: min, maxValue: max}};
}

export interface IchimokuPalette {
  senkou_a: string; senkou_b: string; chikou: string; bullish: string; bearish: string;
}
const defaultPalette: IchimokuPalette = {senkou_a: '#39b990', senkou_b: '#e78389', chikou: '#a895eb',
  bullish: 'rgba(57,185,144,0.16)', bearish: 'rgba(231,131,137,0.16)'};

/** Attach to the populated raw-close carrier for every price style, including all-whitespace HA. */
export class IchimokuPrimitive implements ISeriesPrimitive<Time> {
  private context: SeriesAttachedParameter<Time> | null = null;
  private lines: IchimokuLines = emptyLines();
  private readonly palette: IchimokuPalette;
  private readonly views: IPrimitivePaneView[];
  constructor(palette: Partial<IchimokuPalette> = {}) {
    this.palette = {...defaultPalette, ...palette};
    const cloud: IPrimitivePaneRenderer = {draw: target => target.useMediaCoordinateSpace(({context}) => {
      if (!this.context) return;
      const x = (logical: number) => this.context!.chart.timeScale().logicalToCoordinate(logical as Logical);
      const y = (price: number) => this.context!.series.priceToCoordinate(price);
      context.save();
      for (const cell of ichimokuCloudCells(this.lines, x, y)) {
        context.beginPath();
        cell.points.forEach((point, index) => index ? context.lineTo(point.x, point.y) : context.moveTo(point.x, point.y));
        context.closePath(); context.fillStyle = cell.bullish ? this.palette.bullish : this.palette.bearish; context.fill();
      }
      context.restore();
    })};
    const strokes: IPrimitivePaneRenderer = {draw: target => target.useMediaCoordinateSpace(({context}) => {
      if (!this.context) return;
      context.save(); context.lineWidth = 1.5;
      for (const port of ports) {
        context.beginPath(); context.strokeStyle = this.palette[port];
        let previous: IchimokuPoint | undefined;
        for (const point of this.lines[port]) {
          const x = this.context.chart.timeScale().logicalToCoordinate(point.logical as Logical);
          const y = this.context.series.priceToCoordinate(point.value);
          if (x === null || y === null || !finite(x) || !finite(y)) {previous = undefined; continue;}
          if (previous && adjacent(previous, point)) context.lineTo(x, y); else context.moveTo(x, y);
          previous = point;
        }
        context.stroke();
      }
      context.restore();
    })};
    this.views = [{zOrder: () => 'bottom', renderer: () => cloud}, {zOrder: () => 'normal', renderer: () => strokes}];
  }
  attached(context: SeriesAttachedParameter<Time>) {this.context = context; context.requestUpdate();}
  detached() {this.context = null;}
  paneViews() {return this.views;}
  updateAllViews() { /* Coordinates are resolved per frame, including pan, scale and resize. */ }
  setData(lines: IchimokuLines) {
    // Own a snapshot so later transport mutations cannot alter a mounted chart silently.
    this.lines = {senkou_a: lines.senkou_a.map(p => ({...p})), senkou_b: lines.senkou_b.map(p => ({...p})),
      chikou: lines.chikou.map(p => ({...p}))};
    this.context?.requestUpdate();
  }
  clear() {this.setData(emptyLines());}
  extent() {return ichimokuLogicalExtent(this.lines);}
  hover(logical: number) {return ichimokuHoverAtLogical(this.lines, logical);}
  autoscaleInfo(from: Logical, to: Logical) {
    if (!this.context || !this.context.series.priceScale().options().autoScale) return null;
    return ichimokuAutoscale(this.lines, from, to);
  }
}
