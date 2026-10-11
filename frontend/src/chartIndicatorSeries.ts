import {LineSeries, HistogramSeries} from 'lightweight-charts';
import {type ChartIndicator} from './ChartIndicators';

export const auxiliaryKinds = ['rsi', 'macd', 'volume', 'atr', 'stochastic', 'obv', 'roc', 'momentum', 'cci', 'williamsr', 'mfi', 'cmf', 'stddev'];

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
  for (const item of instances) {
    if (!item.visible) continue;
    const volumeOverlay = item.type === 'volume' && item.placement !== 'pane';
    const group = auxiliaryKinds.includes(item.type) && !volumeOverlay ? item.type : 'price';
    if (group !== 'price' && !panes.has(group)) panes.set(group, next++);
    const pane = panes.get(group) ?? 0;
    const ports = ['bb', 'donchian', 'keltner'].includes(item.type) ? ['upper', 'middle', 'lower']
      : item.type === 'macd' ? ['macd', 'signal', 'histogram'] : item.type === 'stochastic' ? ['k', 'd'] : ['value'];
    for (const port of ports) {
      const histogram = item.type === 'volume' || port === 'histogram';
      const options: any = {
        color: item.color,
        // Full names/parameters live in the accessible outside-plot legend.
        title: '',
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
        crosshairMarkerVisible: !histogram,
      };
      if (['signal', 'upper', 'lower', 'd'].includes(port)) options.lineStyle = 2;
      if (['rsi', 'stochastic', 'mfi', 'williamsr'].includes(item.type)) {
        options.autoscaleInfoProvider = () => ({priceRange: {minValue: item.type === 'williamsr' ? -100 : 0, maxValue: item.type === 'williamsr' ? 0 : 100}});
      }
      if (['roc', 'williamsr', 'mfi'].includes(item.type)) options.priceFormat = {type: 'percent', precision: 2, minMove: 0.01};
      if (item.type === 'cmf') options.priceFormat = {type: 'price', precision: 4, minMove: 0.0001};
      if (item.type === 'obv') options.priceFormat = {type: 'volume'};
      if (item.type === 'volume') {
        options.priceFormat = {type: 'volume'};
        if (volumeOverlay) {options.priceScaleId = `volume-${item.id}`; options.lastValueVisible = false;}
      }
      const series = chart.addSeries(histogram ? HistogramSeries : LineSeries, options, pane);
      if (volumeOverlay) series.priceScale().applyOptions({mode: 0, autoScale: true, scaleMargins: {top: 0.80, bottom: 0}, visible: false});
      if (pane !== 0) {
        // v5 updates defaults for future right scales. Normalize auxiliary
        // panes, then restore the primary options (including log/manual mode).
        const primaryScale = chart.priceScale('right', 0);
        const original = primaryScale.options();
        const margins = {...original.scaleMargins};
        series.priceScale().applyOptions({mode: 0, autoScale: true,
          scaleMargins: ['rsi', 'stochastic', 'mfi', 'williamsr'].includes(item.type) ? {top: 0, bottom: 0} : {top: 0.2, bottom: 0.1}});
        primaryScale.applyOptions({mode: original.mode ?? 0, autoScale: original.autoScale ?? true, scaleMargins: margins});
      }
      if (['rsi', 'stochastic', 'mfi', 'williamsr'].includes(item.type)) {
        for (const price of (item.type === 'rsi' ? [30, 70] : item.type === 'williamsr' ? [-80, -20] : item.type === 'mfi' || port === 'k' ? [20, 80] : [])) {
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
  if (recordedVisible && recorded?.priceScale) {
    const primary = chart.priceScale('right', 0), original = primary.options();
    recorded.priceScale().applyOptions({mode: 0, autoScale: true, scaleMargins: {top: 0.2, bottom: 0.1}});
    primary.applyOptions({mode: original.mode, autoScale: original.autoScale, scaleMargins: {...original.scaleMargins}});
  }
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
