import type {LiveCandle} from './liveChartData';
export type PriceStyle = 'candles' | 'heikin_ashi' | 'line';
// The raw timestamp domain remains authoritative. Never seed synthetic prices
// in the browser, or fall back to raw OHLC while HA is pending/unavailable.
export function chartPriceData(rows: LiveCandle[], minutes: number, style: PriceStyle, result: any) {
  const synthetic = new Map<number, any>((result?.price_style === 'heikin_ashi' ? result.price_candles ?? [] : []).map((bar: any) => [bar.time, bar]));
  return rows.map(row => {
    const time = row.time + minutes * 60;
    if (style === 'line') return {time};
    if (style === 'candles') return {...row, time};
    const bar = synthetic.get(time);
    return bar && ['open', 'high', 'low', 'close'].every(key => Number.isFinite(bar[key]))
      ? {time, open: bar.open, high: bar.high, low: bar.low, close: bar.close} : {time};
  });
}
