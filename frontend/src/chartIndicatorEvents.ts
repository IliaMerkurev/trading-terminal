import type {AutoscaleInfo, IPrimitivePaneRenderer, IPrimitivePaneView, ISeriesPrimitive,
  Logical, SeriesAttachedParameter, Time} from 'lightweight-charts';
import type {LiveCandle} from './liveChartData';

/** Original display adapter. Formula evaluation and interval-end conversion belong to replay. */
export const indicatorEventKinds = [
  'cross_up', 'cross_down', 'buy_dot', 'sell_dot', 'regular_bullish', 'regular_bearish',
  'hidden_bullish', 'hidden_bearish', 'divergence_buy_dot', 'divergence_sell_dot', 'gold_buy_dot',
  'long_ema', 'short_ema', 'red_cross', 'blue_triangle', 'red_diamond', 'blood_diamond',
  'yellow_cross', 'bull_candle', 'swing_long', 'swing_short',
] as const;
export type IndicatorEventKind = typeof indicatorEventKinds[number];
export interface IndicatorEvent {
  id: string; kind: IndicatorEventKind; oscillator?: string; confirmed_at: number; pivot_time: number;
  previous_pivot_time?: number; value: number; previous_value?: number; segment: number;
}
export interface IndicatorEventPoint extends IndicatorEvent {
  /** Marker always uses the confirmation slot, never the earlier pivot slot. */
  logical: number;
  connector?: {from: number; to: number; fromValue: number; toValue: number};
}
export type IndicatorEventsContext = {
  source: string; market: string; symbol: string; minutes: number; revision: number;
};
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
const stamp = (value: unknown): value is number => finite(value) && Number.isSafeInteger(value) && Math.abs(value) <= 8_640_000_000_000;
const knownKinds = new Set<string>(indicatorEventKinds);
const oscillators = new Set(['wt', 'wt_secondary', 'wt2', 'rsi', 'stoch', 'stoch_k']);
const closed = (row: LiveCandle) => ['closed_rest', 'provider_confirmed', 'synthetic_closed'].includes(row.confirmation ?? '');
const divergence = (kind: string) => /^(regular|hidden)_(bullish|bearish)$/.test(kind);

/** Call only with the immutable raw snapshot that accepted the accompanying numeric columns.
 * Replacing results replaces events; never merge request generations. Unknown or missing raw
 * confirmation cannot prove a connector is continuous. Off-window predecessors are omitted,
 * because this envelope carries no independent evidence for their intervening raw candles.
 */
export function acceptedIndicatorEvents(result: any, item: {id: string; type: string; visible: boolean},
  rows: LiveCandle[], context: IndicatorEventsContext): IndicatorEventPoint[] {
  const envelope = result?.indicator_events, actual = envelope?.context, width = context.minutes * 60;
  if (result?.status !== 'ready' || !item.visible || !['vmc_cipher_b', 'vmc_cipher_a', 'vmc_swing'].includes(item.type)
    || !rows.length || !result.origin || !actual || envelope.version !== 1
    || envelope.contract !== 'confirmed-vmc-events-v1' || !stamp(width) || width <= 0) return [];
  const expected = {source: context.source, market: context.market, symbol: context.symbol,
    minutes: context.minutes, start: rows[0].time, end: rows.at(-1)!.time,
    settings_revision: context.revision, generation: result.origin.generation, origin: result.origin.time};
  if (!stamp(expected.generation) || expected.generation < 0 || !stamp(expected.origin)
    || Object.entries(expected).some(([key, value]) => actual[key] !== value)
    || envelope.horizon !== expected.end + width
    || rows.some((row, i) => !stamp(row.time) || (i > 0 && row.time <= rows[i - 1].time))) return [];
  const events = envelope.instances?.[item.id];
  if (!Array.isArray(events)) return [];
  const times = new Map(rows.map((row, i) => [row.time + width, i]));
  // Prefix sums make continuity checks O(1), even for dense divergence output.
  const breaks = rows.map(() => 0);
  for (let i = 0; i < rows.length; i++) breaks[i] = (i ? breaks[i - 1] : 0)
    + (!closed(rows[i]) || (i > 0 && rows[i].time !== rows[i - 1].time + width) ? 1 : 0);
  const contiguous = (a: number, b: number) => closed(rows[a]) && breaks[b] === breaks[a];
  const output = new Map<string, IndicatorEventPoint>();
  for (const raw of events) {
    if (!raw || typeof raw.id !== 'string' || !raw.id || !knownKinds.has(raw.kind)
      || (raw.oscillator !== undefined && !oscillators.has(raw.oscillator))
      || !stamp(raw.confirmed_at) || !stamp(raw.pivot_time) || raw.pivot_time > raw.confirmed_at
      || raw.confirmed_at > envelope.horizon || !finite(raw.value)
      || !stamp(raw.segment) || raw.segment < 0
      || ((raw.previous_pivot_time === undefined) !== (raw.previous_value === undefined))
      || (raw.previous_pivot_time !== undefined && (!stamp(raw.previous_pivot_time)
        || raw.previous_pivot_time >= raw.pivot_time || !finite(raw.previous_value)))) return [];
    const logical = times.get(raw.confirmed_at);
    if (logical === undefined || !closed(rows[logical]) || raw.pivot_time < raw.segment + width) return []; // A confirmation outside the requested raw domain is stale.
    const point: IndicatorEventPoint = {id: raw.id, kind: raw.kind, confirmed_at: raw.confirmed_at,
      pivot_time: raw.pivot_time, value: raw.value, segment: raw.segment, logical};
    if (raw.oscillator !== undefined) point.oscillator = raw.oscillator;
    if (raw.previous_pivot_time !== undefined) {
      point.previous_pivot_time = raw.previous_pivot_time; point.previous_value = raw.previous_value;
      const from = times.get(raw.previous_pivot_time), to = times.get(raw.pivot_time);
      if (divergence(raw.kind) && from !== undefined && to !== undefined
        && raw.previous_pivot_time >= raw.segment + width && contiguous(from, logical) && to <= logical) {
        point.connector = {from, to, fromValue: raw.previous_value, toValue: raw.value};
      }
    }
    const previous = output.get(point.id);
    // Identical repeats are harmless. Conflicting duplicates are an invalid result, regardless of order.
    if (previous && JSON.stringify(previous) !== JSON.stringify(point)) return [];
    output.set(point.id, point);
  }
  return [...output.values()].sort((a, b) => a.confirmed_at - b.confirmed_at
    || a.pivot_time - b.pivot_time || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

export interface IndicatorEventHover extends IndicatorEventPoint {
  pivotUtc: string; confirmedUtc: string; previousPivotUtc?: string; laterKnown: boolean;
  provenance: 'Confirmed raw-market event';
}
export function indicatorEventsHoverAtLogical(events: readonly IndicatorEventPoint[], logical: number,
  tolerance = 0.5): IndicatorEventHover[] {
  if (!finite(logical) || !finite(tolerance) || tolerance < 0) return [];
  return events.filter(event => Math.abs(event.logical - logical) <= tolerance).map(event => ({...event,
    pivotUtc: new Date(event.pivot_time * 1000).toISOString(),
    confirmedUtc: new Date(event.confirmed_at * 1000).toISOString(),
    ...(event.previous_pivot_time === undefined ? {} : {previousPivotUtc: new Date(event.previous_pivot_time * 1000).toISOString()}),
    laterKnown: event.pivot_time < event.confirmed_at, provenance: 'Confirmed raw-market event',
  }));
}

export function indicatorEventsAutoscale(events: readonly IndicatorEventPoint[], from: number, to: number): AutoscaleInfo | null {
  if (!finite(from) || !finite(to) || from > to) return null;
  let min = Infinity, max = -Infinity;
  const include = (value: number) => {min = Math.min(min, value); max = Math.max(max, value);};
  for (const event of events) {
    if (event.logical >= from && event.logical <= to) include(event.value);
    const line = event.connector;
    if (line && line.from <= to && line.to >= from) {include(line.fromValue); include(line.toValue);}
  }
  return min === Infinity ? null : {priceRange: {minValue: min, maxValue: max}};
}

export type IndicatorEventShape = 'circle' | 'triangle_up' | 'triangle_down' | 'diamond' | 'cross';
/** Fixed semantic marker roles are independent of the instance's connector accent. */
export function indicatorEventStyle(kind: IndicatorEventKind): {color: string; shape: IndicatorEventShape} {
  if (kind === 'gold_buy_dot') return {color: '#e9bd45', shape: 'circle'};
  if (kind === 'blue_triangle') return {color: '#5ba7ee', shape: 'triangle_up'};
  if (kind === 'blood_diamond') return {color: '#b82e49', shape: 'diamond'};
  if (kind === 'red_diamond') return {color: '#ed7e86', shape: 'diamond'};
  if (kind === 'yellow_cross') return {color: '#e9bd45', shape: 'cross'};
  if (kind === 'red_cross') return {color: '#ed7e86', shape: 'cross'};
  const bearish = /bearish|sell|short|down/.test(kind);
  const shape: IndicatorEventShape = kind.includes('dot') ? 'circle'
    : bearish ? 'triangle_down' : 'triangle_up';
  return {color: bearish ? '#ed7e86' : '#42cda8', shape};
}

function drawEventMarker(context: CanvasRenderingContext2D, x: number, y: number, shape: IndicatorEventShape) {
  const r = 4;
  context.beginPath();
  if (shape === 'circle') {context.arc(x, y, 3.5, 0, Math.PI * 2); context.fill(); return;}
  if (shape === 'cross') {
    context.moveTo(x - r, y - r); context.lineTo(x + r, y + r);
    context.moveTo(x - r, y + r); context.lineTo(x + r, y - r); context.stroke(); return;
  }
  const vertices = shape === 'diamond' ? [[x, y - r - 1], [x + r, y], [x, y + r + 1], [x - r, y]]
    : shape === 'triangle_up' ? [[x, y - r - 1], [x + r, y + r], [x - r, y + r]]
    : [[x, y + r + 1], [x + r, y - r], [x - r, y - r]];
  vertices.forEach(([px, py], i) => i ? context.lineTo(px, py) : context.moveTo(px, py));
  context.closePath(); context.fill();
}

/** Attach to an owning B oscillator series, or the populated raw-close price carrier for A/Swing.
 * Does not setData on any series or add shared-axis timestamps. The caller owns attach/detach.
 */
export class IndicatorEventsPrimitive implements ISeriesPrimitive<Time> {
  private context: SeriesAttachedParameter<Time> | null = null;
  private events: IndicatorEventPoint[] = [];
  private readonly views: IPrimitivePaneView[];
  constructor(private readonly color = '#d5b367') {
    const renderer: IPrimitivePaneRenderer = {draw: target => target.useMediaCoordinateSpace(({context}) => {
      if (!this.context) return;
      const x = (logical: number) => this.context!.chart.timeScale().logicalToCoordinate(logical as Logical);
      const y = (value: number) => this.context!.series.priceToCoordinate(value);
      context.save(); context.strokeStyle = this.color; context.fillStyle = this.color; context.lineWidth = 1.5;
      for (const event of this.events) {
        const line = event.connector;
        if (!line) continue;
        const coords = [x(line.from), y(line.fromValue), x(line.to), y(line.toValue)];
        if (!coords.every(finite)) continue;
        context.beginPath(); context.moveTo(coords[0]!, coords[1]!); context.lineTo(coords[2]!, coords[3]!); context.stroke();
      }
      const groups = new Map<string, {x: number; y: number; count: number}>();
      const drawn = new Set<string>();
      for (const event of this.events) {
        const px = x(event.logical), py = y(event.value);
        if (!finite(px) || !finite(py)) continue;
        const key = `${event.logical}:${event.value}`, old = groups.get(key);
        groups.set(key, {x: px, y: py, count: (old?.count ?? 0) + 1});
        const style = indicatorEventStyle(event.kind), styleKey = `${key}:${style.shape}:${style.color}`;
        // Preserve exact event coordinates, including overlapping events. A count plus full
        // same-bar hover details discloses overlap instead of displacing markers in time/value.
        if (!drawn.has(styleKey)) {
          context.fillStyle = style.color; context.strokeStyle = style.color;
          drawEventMarker(context, px, py, style.shape); drawn.add(styleKey);
        }
      }
      context.fillStyle = '#e5e9f0';
      for (const group of groups.values()) {
        if (group.count > 1) {context.font = '10px sans-serif'; context.fillText(String(group.count), group.x + 5, group.y - 5);}
      }
      context.restore();
    })};
    this.views = [{zOrder: () => 'top', renderer: () => renderer}];
  }
  attached(context: SeriesAttachedParameter<Time>) {this.context = context; context.requestUpdate();}
  detached() {this.context = null; this.events = [];}
  paneViews() {return this.views;}
  updateAllViews() { /* Resolve current pane/log scale coordinates each frame. */ }
  setData(events: readonly IndicatorEventPoint[]) {
    this.events = events.map(event => ({...event, ...(event.connector ? {connector: {...event.connector}} : {})}));
    this.context?.requestUpdate();
  }
  clear() {this.setData([]);}
  hover(logical: number) {return indicatorEventsHoverAtLogical(this.events, logical);}
  autoscaleInfo(from: Logical, to: Logical) {
    if (!this.context || !this.context.series.priceScale().options().autoScale) return null;
    return indicatorEventsAutoscale(this.events, from, to);
  }
}
