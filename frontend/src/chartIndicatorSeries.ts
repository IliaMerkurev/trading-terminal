import {LineSeries, HistogramSeries} from 'lightweight-charts';
import {indicatorName, type ChartIndicator} from './ChartIndicators';

// Rebuild only owned display series. Derive pane indexes from visible kinds,
// then move the separate recorded IR series to the last pane.
export function installIndicatorSeries(
  chart: any,
  recorded: any,
  instances: ChartIndicator[],
  recordedVisible: boolean,
) {
  const owned: {id: string; port: string; kind: string; series: any; color: string}[] = [];
  const panes = new Map<string, number>();
  let next = 1;
  for (const [index, item] of instances.entries()) {
    if (!item.visible) continue;
    const group = ['rsi', 'macd', 'volume'].includes(item.type) ? item.type : 'price';
    if (group !== 'price' && !panes.has(group)) panes.set(group, next++);
    const pane = panes.get(group) ?? 0;
    const ports = item.type === 'bb' ? ['upper', 'middle', 'lower']
      : item.type === 'macd' ? ['macd', 'signal', 'histogram'] : ['value'];
    for (const port of ports) {
      const histogram = item.type === 'volume' || port === 'histogram';
      const options: any = {
        color: item.color,
        title: `${indicatorName(item)} #${index + 1} ${port === 'value' ? '' : port}`,
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
        crosshairMarkerVisible: !histogram,
      };
      if (['signal', 'upper', 'lower'].includes(port)) options.lineStyle = 2;
      if (item.type === 'rsi') {
        options.autoscaleInfoProvider = () => ({priceRange: {minValue: 0, maxValue: 100}});
      }
      if (item.type === 'volume') options.priceFormat = {type: 'volume'};
      const series = chart.addSeries(histogram ? HistogramSeries : LineSeries, options, pane);
      if (item.type === 'rsi') {
        // v5.2 also changes defaults for future right scales. Restore the
        // primary pane's unchanged margins immediately so only RSI loses padding.
        const primaryScale = chart.priceScale('right', 0);
        const primaryMargins = {...primaryScale.options().scaleMargins};
        series.priceScale().applyOptions({scaleMargins: {top: 0, bottom: 0}});
        primaryScale.applyOptions({scaleMargins: primaryMargins});
        for (const price of [30, 70]) {
          series.createPriceLine({price, color: '#879bb5', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: String(price)});
        }
      }
      if (item.type === 'macd' && port === 'macd') {
        series.createPriceLine({price: 0, color: '#879bb5', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: 'Zero'});
      }
      owned.push({id: item.id, port, kind: item.type, series, color: item.color});
    }
  }
  recorded?.moveToPane(recordedVisible ? next : 0);
  // Pixel-height setters redistribute neighboring panes. Relative weights
  // survive the final ResizeObserver layout without squeezing earlier panes.
  chart.panes?.().forEach((pane: any, index: number) => {
    pane.setStretchFactor(index === 0 ? 320 : 130);
  });
  return owned;
}

export function updateIndicatorSeries(owned: ReturnType<typeof installIndicatorSeries>, result: any) {
  for (const item of owned) {
    const column = result?.columns?.[item.id]?.[item.port] ?? [];
    item.series.setData((result?.times ?? []).map((time: number, index: number) => {
      const value = column[index];
      if (value == null) return {time};
      const color = item.kind === 'volume'
        ? (result.directions[index] >= 0 ? item.color : '#ed7e86')
        : item.port === 'histogram' ? (value >= 0 ? item.color : '#ed7e86') : undefined;
      return {time, value, ...(color ? {color} : {})};
    }));
  }
}
