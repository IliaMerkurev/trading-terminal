import {useEffect, useState} from 'react';

export type IndicatorKind = 'sma' | 'ema' | 'bb' | 'rsi' | 'macd' | 'volume' | 'atr' | 'stochastic' | 'obv';
export type ChartIndicator = {
  id: string;
  type: IndicatorKind;
  params: Record<string, number>;
  color: string;
  visible: boolean;
  placement?: 'overlay' | 'pane';
};
export type IndicatorSettings = {
  version: 1;
  revision: number;
  instances: ChartIndicator[];
  origins: Record<string, {time: number; generation: number; contract: string}>;
  warning?: string;
};
export const emptySettings: IndicatorSettings = {version: 1, revision: 0, instances: [], origins: {}};
export const defaults: Record<IndicatorKind, Record<string, number>> = {
  sma: {period: 20},
  ema: {period: 20},
  bb: {period: 20, deviations: 2},
  rsi: {period: 14},
  macd: {fast: 12, slow: 26, signal: 9},
  volume: {},
  atr: {period: 14},
  stochastic: {period: 14, smooth: 3, signal: 3},
  obv: {},
};

export function validateIndicators(items: ChartIndicator[]): string {
  if (items.length > 8) return 'Use at most 8 indicators.';
  for (const item of items) {
    if (!/^#[0-9a-fA-F]{6}$/.test(item.color)) return 'Choose a valid color.';
    for (const [key, value] of Object.entries(item.params)) {
      if (key === 'deviations') {
        if (!Number.isFinite(value) || value <= 0 || value > 10) {
          return 'BB deviations must be greater than 0 and at most 10.';
        }
      } else if (!Number.isInteger(value) || value < 1 || value > 1000) {
        return 'Periods must be whole numbers from 1 to 1000.';
      }
    }
    if (item.type === 'macd' && item.params.fast >= item.params.slow) {
      return 'MACD fast must be less than slow.';
    }
  }
  return '';
}

export const parameterOrder: Record<IndicatorKind, string[]> = {
  sma: ['period'],
  ema: ['period'],
  bb: ['period', 'deviations'],
  rsi: ['period'],
  macd: ['fast', 'slow', 'signal'],
  volume: [],
  atr: ['period'],
  stochastic: ['period', 'smooth', 'signal'],
  obv: [],
};

export function indicatorName(item: ChartIndicator) {
  const label = item.type === 'bb' ? 'Bollinger Bands' : item.type === 'atr' ? 'ATR · Wilder, SMA seed' : item.type.toUpperCase();
  const parameters = parameterOrder[item.type].map(key => item.params[key]);
  return label + (parameters.length ? ' (' + parameters.join(', ') + ')' : '');
}

type Props = {
  settings: IndicatorSettings;
  onApply: (items: ChartIndicator[]) => void;
  busy: boolean;
  error: string;
};

export default function ChartIndicators({settings, onApply, busy, error}: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<ChartIndicator[]>(settings.instances);
  const [search, setSearch] = useState('');
  const [kind, setKind] = useState<IndicatorKind>('ema');
  useEffect(() => { setDraft(settings.instances); }, [settings]);
  const matches = (Object.keys(defaults) as IndicatorKind[]).filter(type => (type + ' ' + ({sma:'Simple moving average',ema:'Exponential moving average',bb:'Bollinger Bands',rsi:'Relative strength index',macd:'Moving average convergence divergence',volume:'Volume',atr:'Average true range',stochastic:'Stochastic oscillator',obv:'On balance volume'}[type])).toLowerCase().includes(search.toLowerCase()));
  const selectedKind = matches.includes(kind) ? kind : matches[0];
  const invalid = validateIndicators(draft);
  const edit = (id: string, change: Partial<ChartIndicator>) => {
    setDraft(rows => rows.map(row => row.id === id ? {...row, ...change} : row));
  };
  const add = () => {
    if (!selectedKind) return;
    const kind = selectedKind;
    setDraft(rows => [...rows, {
      id: 'i' + crypto.randomUUID().replaceAll('-', ''),
      type: kind,
      params: {...defaults[kind]},
      color: kind === 'volume' ? '#42cda8' : '#7eabff',
      visible: true,
      ...(kind === 'volume' ? {placement: 'overlay' as const} : {}),
    }]);
  };

  return <>
    <button aria-expanded={open} onClick={() => setOpen(value => !value)}>Indicators ({settings.instances.length})</button>
    {open && <div className="chart-indicator-controls" aria-label="Chart indicator settings">
      <p>Display only · selected native chart timeframe · confirmed closes. Recorded IR and trading settings are separate. ATR uses price units; Stochastic uses percent; OBV uses the disclosed source-native volume units and starts at zero at the saved origin or segment reset.</p>
      <div className="chart-indicator-add">
        <label>Search indicators<input aria-label="Search indicators" value={search} onChange={event => setSearch(event.target.value)} placeholder="EMA, volume…"/></label>
        <label>Indicator type
          <select aria-label="Add indicator type" value={selectedKind ?? ''} onChange={event => setKind(event.target.value as IndicatorKind)}>
            {matches.map(type => <option key={type} value={type}>{type === 'bb' ? 'Bollinger Bands' : type === 'atr' ? 'ATR · Wilder, SMA seed' : type.toUpperCase()}</option>)}
          </select>
        </label>
        <button disabled={draft.length >= 8 || busy || !selectedKind} onClick={add}>Add indicator</button>
        <small>{draft.length}/8</small>
      </div>
      {draft.map((item, index) => <fieldset key={item.id}>
        <legend>{index + 1}. {item.type === 'bb' ? 'Bollinger Bands' : item.type.toUpperCase()}</legend>
        <div className="chart-indicator-fields">
          {parameterOrder[item.type].map(key => [key, item.params[key]] as const).map(([key, value]) => <label key={key}>{key}
            <input
              aria-label={`${index + 1} ${item.type.toUpperCase()} ${key}`}
              type="number"
              min={key === 'deviations' ? 0.01 : 1}
              max={key === 'deviations' ? 10 : 1000}
              step={key === 'deviations' ? 'any' : 1}
              value={Number.isNaN(value) ? '' : value}
              onChange={event => edit(item.id, {params: {
                ...item.params,
                [key]: event.target.value === '' ? NaN : Number(event.target.value),
              }})}
            />
          </label>)}
          {item.type === 'volume' && <label>Placement<select aria-label={`${index + 1} VOLUME placement`} value={item.placement ?? 'overlay'} onChange={event => edit(item.id, {placement: event.target.value as 'overlay' | 'pane'})}><option value="overlay">Price overlay</option><option value="pane">Separate pane</option></select></label>}
          <label>Color
            <input aria-label={`${index + 1} ${item.type.toUpperCase()} color`} type="color" value={item.color}
              onChange={event => edit(item.id, {color: event.target.value})}/>
          </label>
          <label>
            <input type="checkbox" aria-label={`${index + 1} ${item.type.toUpperCase()} visible`} checked={item.visible}
              onChange={event => edit(item.id, {visible: event.target.checked})}/>
            Visible
          </label>
          <button disabled={busy} onClick={() => setDraft(rows => rows.filter(row => row.id !== item.id))}>
            Remove {index + 1} {item.type.toUpperCase()}
          </button>
        </div>
      </fieldset>)}
      {(invalid || error) && <p role="alert">{invalid || error}</p>}
      <button disabled={busy || !!invalid} onClick={() => onApply(draft)}>{busy ? 'Saving…' : 'Apply indicators'}</button>
      <button disabled={busy} onClick={() => {setDraft(settings.instances); setOpen(false);}}>Cancel edits</button>
      <small>Apply saves all valid edits together in this workspace. Hidden indicators retain their settings. Defaults are examples, not trading recommendations.</small>
    </div>}
  </>;
}
