import {LineSeries, HistogramSeries, BaselineSeries} from 'lightweight-charts';
import {type ChartIndicator} from './ChartIndicators';
import {isVmcKind} from './vmcSettings';

import {legacyPaneLayout, visiblePanes, type PaneLayout} from './chartPanes';
export {auxiliaryKinds} from './chartPanes';

// Rebuild only owned display series. Derive pane indexes from visible kinds,
// then move the separate recorded IR series to the last pane.
export function installIndicatorSeries(
  chart: any,
  recorded: any,
  instances: ChartIndicator[],
  recordedVisible: boolean,
  layout?: PaneLayout,
) {
  const owned: {id: string; port: string; kind: string; series: any; color: string}[] = [];
  const panes = new Map<string, number>();
  const resolved = layout ?? legacyPaneLayout(instances);
  const activePanes = visiblePanes(instances, resolved);
  activePanes.forEach((pane,index) => pane.instance_ids.forEach(id => panes.set(id,index+1)));
  const next = activePanes.length + 1;
  // Create panes in index order: hidden/empty groups never reserve space.
  for (const item of [...instances].sort((a,b) => (panes.get(a.id) ?? 0) - (panes.get(b.id) ?? 0))) {
    if (!item.visible) continue;
    const volumeOverlay = item.type === 'volume' && item.placement !== 'pane';
    const pane = panes.get(item.id) ?? 0;
    const ports = item.type === 'vmc_cipher_b' ? ['flow','wt1','wt2','fast_wave','rsi','stoch_k','stoch_d'] : item.type === 'vmc_cipher_a' ? Array.from({length:8},(_,i)=>`ema${i+1}`) : item.type === 'vmc_swing' ? ['filter','upper','lower'] : item.type === 'ichimoku' ? ['tenkan', 'kijun'] : ['bb', 'donchian', 'keltner'].includes(item.type) ? ['upper', 'middle', 'lower']
      : item.type === 'macd' ? ['macd', 'signal', 'histogram'] : ['stochastic', 'stochrsi'].includes(item.type) ? ['k', 'd'] : item.type === 'dmi' ? ['plus_di', 'minus_di', 'adx'] : item.type === 'supertrend' ? ['up', 'down'] : ['value'];
    for (const port of ports) {
      const histogram = item.type === 'volume' || port === 'histogram' || item.type === 'vmc_cipher_b' && port === 'flow';
      const options: any = {
        color: item.color,
        // Full names/parameters live in the accessible outside-plot legend.
        title: '',
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
        crosshairMarkerVisible: !histogram,
      };
      const wave = item.type === 'vmc_cipher_b' && ['wt1','wt2'].includes(port);
      if (isVmcKind(item.type)) {
        options.color = vmcPortColor(item.type, port, item.color);
        if (item.type === 'vmc_cipher_b') options.priceFormat = {type:'price',precision:2,minMove:0.01};
        if (wave) Object.assign(options, {baseValue:{type:'price',price:0}, topLineColor:options.color,bottomLineColor:options.color,
          topFillColor1:options.color+'50',topFillColor2:options.color+'18',bottomFillColor1:options.color+'18',bottomFillColor2:options.color+'50'});
      }
      if (item.type === 'sar') Object.assign(options, {lineVisible: false, pointMarkersVisible: true, pointMarkersRadius: 3});
      if (item.type === 'supertrend' && port === 'down') options.color = '#ed7e86';
      if (['signal', 'upper', 'lower', 'd', 'minus_di', 'adx'].includes(port)) options.lineStyle = 2;
      if (['rsi', 'stochastic', 'mfi', 'williamsr', 'stochrsi', 'dmi'].includes(item.type)) {
        options.autoscaleInfoProvider = () => ({priceRange: {minValue: item.type === 'williamsr' ? -100 : 0, maxValue: item.type === 'williamsr' ? 0 : 100}});
      }
      if (['roc', 'williamsr', 'mfi', 'dmi', 'stochrsi', 'bbwidth'].includes(item.type)) options.priceFormat = {type: 'percent', precision: 2, minMove: 0.01};
      if (['cmf', 'bbpercentb'].includes(item.type)) options.priceFormat = {type: 'price', precision: 4, minMove: 0.0001};
      if (item.type === 'obv') options.priceFormat = {type: 'volume'};
      if (item.type === 'volume') {
        options.priceFormat = {type: 'volume'};
        if (volumeOverlay) {options.priceScaleId = `volume-${item.id}`; options.lastValueVisible = false;}
      }
      const series = chart.addSeries(histogram ? HistogramSeries : wave ? BaselineSeries : LineSeries, options, pane);
      if (volumeOverlay) series.priceScale().applyOptions({mode: 0, autoScale: true, scaleMargins: {top: 0.80, bottom: 0}, visible: false});
      if (pane !== 0) {
        // v5 updates defaults for future right scales. Normalize auxiliary
        // panes, then restore the primary options (including log/manual mode).
        const primaryScale = chart.priceScale('right', 0);
        const original = primaryScale.options();
        const margins = {...original.scaleMargins};
        series.priceScale().applyOptions({mode: 0, autoScale: true,
          scaleMargins: ['rsi', 'stochastic', 'mfi', 'williamsr', 'stochrsi', 'dmi'].includes(item.type) ? {top: 0, bottom: 0} : {top: 0.2, bottom: 0.1}});
        primaryScale.applyOptions({mode: original.mode ?? 0, autoScale: original.autoScale ?? true, scaleMargins: margins});
      }
      if (['rsi', 'stochastic', 'mfi', 'williamsr', 'stochrsi', 'dmi'].includes(item.type)) {
        for (const price of (item.type === 'rsi' ? [30, 70] : item.type === 'williamsr' ? [-80, -20] : item.type === 'mfi' || port === 'k' ? [20, 80] : [])) {
          series.createPriceLine({price, color: '#879bb5', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: String(price)});
        }
      }
      if (item.type === 'vmc_cipher_b' && port === 'wt1') {
        for (const price of [0, Number(item.params.overbought), Number(item.params.oversold)]) series.createPriceLine({price,color:'#879bb5',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:price===0?'Zero':'WT'});
      }
      if (item.type === 'macd' && port === 'macd') {
        series.createPriceLine({price: 0, color: '#879bb5', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: 'Zero'});
      }
      owned.push({id: item.id, port, kind: item.type, series, color: options.color});
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
    pane.setStretchFactor(index === 0 ? resolved.price_weight : activePanes[index-1]?.weight ?? resolved.recorded_weight);
  });
  return owned;
}

export function vmcPortColor(kind: string, port: string, accent: string) {
 if (kind === 'vmc_cipher_b') return ({wt1:accent,wt2:'#936be8',fast_wave:'#c2edf5',flow:'#39b990',rsi:'#df8ac7',stoch_k:'#e7be65',stoch_d:'#71d5d0'} as Record<string,string>)[port];
 if (kind === 'vmc_cipher_a') return ['#99dcff','#81caff','#69b6f5','#52a0e6','#4287d2','#376fbb','#315ca3',accent][Number(port.slice(3))-1];
 return port === 'filter' ? accent : '#91a4bb';
}

export function updateIndicatorSeries(owned: ReturnType<typeof installIndicatorSeries>, result: any, minutes = 1) {
  for (const item of owned) {
    const column = result?.columns?.[item.id]?.[item.port] ?? [];
    item.series.setData((result?.times ?? []).map((time: number, index: number) => {
      const value = column[index];
      if (value == null) return {time};
      // LWC 5.2.1 removes whitespace before walkLine. Simple-line segments
      // inherit the LEFT finite point's color, so hide only its outgoing bridge.
      const color = item.kind === 'supertrend'
        ? (index + 1 < column.length && (column[index + 1] == null || result.times[index + 1] - time !== minutes * 60) ? 'transparent' : item.port === 'down' ? '#ed7e86' : item.color)
        : item.kind === 'volume'
        ? (result.directions[index] >= 0 ? item.color : '#ed7e86')
        : item.port === 'histogram' ? (value >= 0 ? item.color : '#ed7e86') : undefined;
      if (isVmcKind(item.kind)) {
        const direction=result?.regimes?.[item.id]?.[index];
        const semantic = item.port === 'flow' ? (value >= 0 ? '#39b990' : '#e78389')
          : item.kind === 'vmc_swing' ? (direction === 1 ? '#39b990' : direction === -1 ? '#e78389' : item.color)
          : item.kind === 'vmc_cipher_a' && direction === -1 ? '#65748a'
          : item.port === 'rsi' ? (value >= 60 ? '#e78389' : value <= 30 ? '#39b990' : item.color) : item.color;
        const gap = index+1<column.length && (column[index+1] == null || result.times[index+1]-time !== minutes*60);
        const outgoing = gap && item.port !== 'flow' ? 'transparent' : semantic;
        if (['wt1','wt2'].includes(item.port)) return {time,value,topLineColor:outgoing,bottomLineColor:outgoing,
          ...(gap ? {topFillColor1:'transparent',topFillColor2:'transparent',bottomFillColor1:'transparent',bottomFillColor2:'transparent'} : {})};
        return {time,value,color:outgoing};
      }
      return {time, value, ...(color ? {color} : {})};
    }));
  }
}
