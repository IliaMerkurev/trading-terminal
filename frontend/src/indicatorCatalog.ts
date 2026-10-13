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
  {kind:'wma', name:'Weighted moving average', category:'Trend', description:'Rolling closes · newest weight N'},
  {kind:'rma', name:'Wilder moving average', category:'Trend', description:'SMA seed · Wilder smoothing'},
  {kind:'vwma', name:'Volume weighted moving average', category:'Trend', description:'Raw closes weighted by source-native volume'},
  {kind:'donchian', name:'Donchian channel', category:'Volatility', description:'Current-inclusive high / low and midpoint'},
  {kind:'keltner', name:'Keltner channel', category:'Volatility', description:'EMA with SMA-seeded Wilder ATR bands'},
  {kind:'roc', name:'Rate of change', category:'Momentum', description:'N-bar close change · percent'},
  {kind:'momentum', name:'Momentum', category:'Momentum', description:'Close minus N-bar prior close · price units'},
  {kind:'cci', name:'Commodity channel index', category:'Momentum', description:'HLC3 mean deviation · dimensionless'},
  {kind:'williamsr', name:'Williams %R', category:'Momentum', description:'Rolling high / low · -100 to 0 percent'},
  {kind:'mfi', name:'Money flow index', category:'Volume', description:'HLC3 changes weighted by source-native volume · percent'},
  {kind:'cmf', name:'Chaikin money flow', category:'Volume', description:'Rolling volume-weighted flow · dimensionless'},
  {kind:'stddev', name:'Standard deviation', category:'Volatility', description:'Population deviation of closes · price units'},
  {kind:'dmi', name:'Directional movement index / ADX', category:'Trend', description:'Wilder +DI / −DI and ADX · percent'},
  {kind:'supertrend', name:'Supertrend', category:'Trend', description:'ATR median bands · split up / down lines · signed direction readout'},
  {kind:'stochrsi', name:'Stochastic RSI', category:'Momentum', description:'Rolling RSI range · SMA K / D · percent'},
  {kind:'hma', name:'Hull moving average', category:'Trend', description:'Nested WMA · floor half and square-root windows'},
  {kind:'bbpercentb', name:'Bollinger %B', category:'Volatility', description:'Fraction within bands · unbounded dimensionless ratio'},
  {kind:'bbwidth', name:'Bollinger bandwidth', category:'Volatility', description:'Band width / middle · percent'},
  {kind:'vwap', name:'Volume weighted average price', category:'Volume', description:'HLC3 · exact UTC-day or fixed-anchor coverage'},
  {kind:'sar', name:'Parabolic SAR', category:'Trend', description:'Local causal SAR contract · dots · no platform parity claim'},
  {kind:'ichimoku', name:'Ichimoku cloud', category:'Trend', description:'Tenkan / Kijun · causal raw-bar shifted cloud and later-known Chikou'},
  {kind:'vmc_cipher_b', name:'VMC Cipher B Core + confirmed divergences', category:'Momentum', description:'WaveTrend waves · Fast WT (not VWAP) · candle-body flow (no volume) · RSI / Stoch RSI'},
  {kind:'vmc_cipher_a', name:'VMC Cipher A ribbon', category:'Trend', description:'Eight EMA ribbon · confirmed raw-price events · vumanchu'},
  {kind:'vmc_swing', name:'Swing Range Filter', category:'Trend', description:'Jazal / DonovanWall · filtered raw price and bands · confirmed direction events'},
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


export function indicatorShortLabel(kind: IndicatorKind): string {
  return ({vmc_cipher_b: 'VMC B', vmc_cipher_a: 'VMC A', vmc_swing: 'Swing'} as Partial<Record<IndicatorKind, string>>)[kind] ?? kind.toUpperCase();
}
