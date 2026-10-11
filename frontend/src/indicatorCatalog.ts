import type {IndicatorKind} from './ChartIndicators';

export const indicatorCategories = ['Trend', 'Volatility', 'Momentum', 'Volume'] as const;
export type IndicatorCategory = typeof indicatorCategories[number];
// Display metadata only. An entry must already have a validated calculation contract.
export const indicatorCatalog: {kind: IndicatorKind; name: string; category: IndicatorCategory; description: string}[] = [
  {kind:'sma', name:'Simple moving average', category:'Trend', description:'Rolling mean of confirmed closes'},
  {kind:'ema', name:'Exponential moving average', category:'Trend', description:'First-close seeded smoothing'},
  {kind:'bb', name:'Bollinger Bands', category:'Volatility', description:'Mean and population deviation bands'},
  {kind:'atr', name:'Average true range', category:'Volatility', description:'Wilder smoothing · SMA seed · price units'},
  {kind:'rsi', name:'Relative strength index', category:'Momentum', description:'Wilder smoothing · zero-difference seed'},
  {kind:'macd', name:'Moving average convergence divergence', category:'Momentum', description:'Fast / slow EMA with signal'},
  {kind:'stochastic', name:'Stochastic oscillator', category:'Momentum', description:'Rolling high / low · SMA K / D · percent'},
  {kind:'volume', name:'Volume', category:'Volume', description:'Source-native units · overlay or pane'},
  {kind:'obv', name:'On balance volume', category:'Volume', description:'Signed source-native volume · zero origin'},
];
export const favoritesKey = 'trading-terminal.indicator-favorites.v1';
export function parseIndicatorFavorites(raw: string | null): IndicatorKind[] {
  if (!raw || raw.length > 4096) return [];
  try {
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value) || value.length > 64) return [];
    return indicatorCatalog.filter(entry => value.includes(entry.kind)).map(entry => entry.kind);
  } catch { return []; }
}
