import {useEffect, useId, useRef, useState} from 'react';
import {isTypingTarget} from './chartDrawings';
import {indicatorCatalog, indicatorCategories, favoritesKey, parseIndicatorFavorites} from './indicatorCatalog';

export type IndicatorKind = 'sma' | 'ema' | 'bb' | 'rsi' | 'macd' | 'volume' | 'atr' | 'stochastic' | 'obv' | 'wma' | 'rma' | 'vwma' | 'donchian' | 'keltner' | 'roc' | 'momentum' | 'cci' | 'williamsr' | 'mfi' | 'cmf' | 'stddev' | 'dmi' | 'supertrend' | 'stochrsi' | 'hma' | 'bbpercentb' | 'bbwidth' | 'vwap' | 'sar' | 'ichimoku';
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
  wma: {period: 20},
  rma: {period: 20},
  vwma: {period: 20},
  donchian: {period: 20},
  keltner: {period: 14, atr_period: 10, multiplier: 2},
  roc: {period: 14},
  momentum: {period: 14},
  cci: {period: 14},
  williamsr: {period: 14},
  mfi: {period: 14},
  cmf: {period: 14},
  stddev: {period: 20},
  dmi: {period: 14, adx_period: 14},
  supertrend: {period: 10, multiplier: 3},
  stochrsi: {period: 14, stochastic_period: 14, smooth: 3, signal: 3},
  hma: {period: 20},
  bbpercentb: {period: 20, deviations: 2},
  bbwidth: {period: 20, deviations: 2},
  vwap: {mode: 0, anchor: 0},
  sar: {step: 0.02, max: 0.2},
  ichimoku: {conversion: 9, base: 26, span_b: 52, displacement: 26},

};

export function validateIndicators(items: ChartIndicator[], minutes = 1): string {
  for (const item of items) {
    if (!/^#[0-9a-fA-F]{6}$/.test(item.color)) return 'Choose a valid color.';
    if (item.type === 'vwap') {
      const {mode, anchor} = item.params;
      if (![0, 1].includes(mode) || !Number.isInteger(anchor) || anchor < 0 || anchor > 253402300799 || (mode === 0 && anchor !== 0)) return 'Choose a valid VWAP mode and UTC anchor.';
      if (item.visible && anchor % (minutes * 60)) return `VWAP anchor must align exactly with the native ${minutes}-minute candle open.`;
      continue;
    }
    if (item.type === 'sar') {
      const {step, max} = item.params;
      if (!Number.isFinite(step) || !Number.isFinite(max) || !(0 < step && step <= max && max <= 1)) return 'SAR requires 0 < step ≤ max ≤ 1.';
      continue;
    }
    for (const [key, value] of Object.entries(item.params)) {
      if ((key === 'deviations' || key === 'multiplier')) {
        if (!Number.isFinite(value) || value <= 0 || value > 10) {
          return `${key === 'multiplier' ? (item.type === 'keltner' ? 'Keltner multiplier' : 'Supertrend multiplier') : 'BB deviations'} must be greater than 0 and at most 10.`;
        }
      } else if (!Number.isInteger(value) || value < 1 || value > 1000) {
        return 'Periods must be whole numbers from 1 to 1000.';
      }
    }
    if (item.type === 'ichimoku' && item.params.displacement > 100) return 'Ichimoku displacement must be a whole number from 1 to 100.';
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
  wma: ['period'],
  rma: ['period'],
  vwma: ['period'],
  donchian: ['period'],
  keltner: ['period', 'atr_period', 'multiplier'],
  roc: ['period'],
  momentum: ['period'],
  cci: ['period'],
  williamsr: ['period'],
  mfi: ['period'],
  cmf: ['period'],
  stddev: ['period'],
  dmi: ['period', 'adx_period'],
  supertrend: ['period', 'multiplier'],
  stochrsi: ['period', 'stochastic_period', 'smooth', 'signal'],
  hma: ['period'],
  bbpercentb: ['period', 'deviations'],
  bbwidth: ['period', 'deviations'],
  vwap: ['mode', 'anchor'],
  sar: ['step', 'max'],
  ichimoku: ['conversion', 'base', 'span_b', 'displacement'],

};

export function utcAnchorInput(anchor: number) {
  return Number.isFinite(anchor) && anchor >= 0 && anchor <= 253402300799 ? new Date(anchor * 1000).toISOString().slice(0, 19) : '';
}
export function UtcAnchorPicker({value, label, onChange}: {value:number; label:string; onChange:(value:number)=>void}) {
  // Keep the browser's segmented editing state independent of numeric params.
  // Writing a controlled empty value during an incomplete year wipes that state.
  const initial = useRef(utcAnchorInput(value));
  const lastInput = useRef<string | null>(null);
  const [text, setText] = useState(initial.current);
  const input = (event: React.FormEvent<HTMLInputElement>) => {
    const next = event.currentTarget.value;
    if (lastInput.current === next) return;
    lastInput.current = next;
    setText(next);
    const complete = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/.test(next);
    onChange(complete ? Date.parse(next + 'Z') / 1000 : NaN);
  };
  return <input aria-label={label} aria-invalid={!text} type="datetime-local" step={1}
    min="1970-01-01T00:00:00" max="9999-12-31T23:59:59" defaultValue={initial.current}
    onInput={input} onChange={input}/>;
}
export function indicatorParameters(item: ChartIndicator) {
  if (item.type === 'vwap') return item.params.mode === 0 ? 'UTC day · midnight reset' : `Fixed anchor · ${utcAnchorInput(item.params.anchor).replace('T', ' ') || 'Choose timestamp'} UTC`;
  return parameterOrder[item.type].map(key => `${key} ${item.params[key]}`).join(' · ');
}
export function indicatorName(item: ChartIndicator) {
  if (item.type === 'vwap') return `VWAP (${indicatorParameters(item)})`;
  const label = item.type === 'bb' ? 'Bollinger Bands' : item.type === 'atr' ? 'ATR · Wilder, SMA seed' : item.type.toUpperCase();
  const parameters = parameterOrder[item.type].map(key => item.params[key]);
  return label + (parameters.length ? ' (' + parameters.join(', ') + ')' : '');
}

type Props = {
  focusMode?: boolean;
  toolbar?: React.ReactNode;
  toolbarActions?: React.ReactNode;
  settings: IndicatorSettings;
  onApply: (items: ChartIndicator[]) => void;
  busy: boolean;
  error: string;
  volumeUnit?: string;
  minutes?: number;
};

export default function ChartIndicators({settings, onApply, busy, error, volumeUnit, toolbar, toolbarActions, minutes = 1}: Props) {
  const [open, setOpen] = useState(false);
  const [catalogOpen, setCatalogOpen] = useState(true);
  const panelId = useId();
  const toggle = useRef<HTMLButtonElement>(null);
  const initiator = useRef<HTMLElement | null>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const editor = useRef<HTMLFieldSetElement>(null);
  const [target, setTarget] = useState<'search' | 'editor' | null>(null);
  const [selected, setSelected] = useState<string | null>(settings.instances[0]?.id ?? null);
  const [draft, setDraft] = useState<ChartIndicator[]>(settings.instances);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');
  const [page, setPage] = useState(0);
  const pageSize = 9;
  const [favorites, setFavorites] = useState<IndicatorKind[]>(() => {
    try { return parseIndicatorFavorites(localStorage.getItem(favoritesKey)); } catch { return []; }
  });
  const [favoriteNotice, setFavoriteNotice] = useState('');
  useEffect(() => {
    setDraft(settings.instances);
    setSelected(previous => settings.instances.some(item => item.id === previous) ? previous : settings.instances[0]?.id ?? null);
  }, [settings]);
  useEffect(() => {
    if (!open || !target) return;
    (target === 'search' ? searchInput.current : editor.current)?.focus({preventScroll:true});
    setTarget(null);
  }, [open, target, selected]);
  const matches = indicatorCatalog.filter(entry =>
    (category === 'All' || category === entry.category || category === 'Favorites' && favorites.includes(entry.kind)) &&
    `${entry.kind} ${entry.name} ${entry.description}`.toLowerCase().includes(search.trim().toLowerCase()));
  const lastPage = Math.max(0, Math.ceil(matches.length / pageSize) - 1);
  const currentPage = Math.min(page, lastPage);
  const invalid = validateIndicators(draft, minutes);
  const dirty = JSON.stringify(draft) !== JSON.stringify(settings.instances);
  const edit = (id: string, change: Partial<ChartIndicator>) => {
    setDraft(rows => rows.map(row => row.id === id ? {...row, ...change} : row));
  };
  const add = (kind: IndicatorKind) => {
    if (busy) return;
    const item: ChartIndicator = {
      id: 'i' + crypto.randomUUID().replaceAll('-', ''), type: kind,
      params: {...defaults[kind]}, color: kind === 'volume' ? '#42cda8' : '#7eabff', visible: true,
      ...(kind === 'volume' ? {placement: 'overlay' as const} : {}),
    };
    setDraft(rows => [...rows, item]); setSelected(item.id); setTarget('editor');
  };
  const favorite = (kind: IndicatorKind) => {
    const next = indicatorCatalog.filter(entry => entry.kind === kind ? !favorites.includes(kind) : favorites.includes(entry.kind)).map(entry => entry.kind);
    setFavorites(next);
    try { localStorage.setItem(favoritesKey, JSON.stringify(next)); setFavoriteNotice(''); }
    catch { setFavoriteNotice('Favorites are available for this session only; local preferences could not be saved.'); }
  };
  const collapse = () => {
    setOpen(false); setTarget(null);
    (initiator.current?.isConnected && !initiator.current.matches(':disabled') ? initiator.current : toggle.current)?.focus({preventScroll:true});
  };
  const cancel = () => {setDraft(settings.instances); setSelected(settings.instances[0]?.id ?? null); collapse();};
  const selectedItem = draft.find(item => item.id === selected) ?? draft[0];
  return <div className="chart-indicator-manager" onKeyDown={event=>{
    if(open && event.key==='Escape' && !event.isDefaultPrevented() && !event.nativeEvent.isComposing && !isTypingTarget(event.target)){
      event.preventDefault(); event.stopPropagation(); collapse();
    }
  }}>
    <div className="live-chart-toolbar chart-indicator-heading" aria-label="Market chart toolbar">
      {toolbar}
      <button ref={toggle} aria-expanded={open} aria-controls={panelId} onClick={event => {
        if(open && catalogOpen) collapse(); else {initiator.current=event.currentTarget; setCatalogOpen(true); setOpen(true); setTarget('search');}
      }}>Indicators ({settings.instances.length})</button>
      {toolbarActions}
    </div>
    {!open && dirty && <small className="indicator-draft-note">Unapplied edits retained. Open Indicators to apply or cancel.</small>}
    {settings.instances.length > 0 && <ul className="chart-indicator-legend" aria-label="Chart indicator legend">
      {settings.instances.map((item, index) => <li key={item.id} className={item.visible ? '' : 'indicator-hidden'}>
        <span className="indicator-swatch" style={{backgroundColor: item.color}} aria-hidden="true"/>
        <button disabled={busy} className="indicator-settings-link" aria-label={`Settings for ${index + 1} ${item.type.toUpperCase()}`} title={indicatorName(item)} onClick={event => {initiator.current=event.currentTarget; setSelected(item.id); setCatalogOpen(false); setOpen(true); setTarget('editor');}}>
          <strong>{index + 1}. {item.type.toUpperCase()}</strong><span>{indicatorParameters(item) || (item.type === 'volume' ? item.placement === 'pane' ? 'separate pane' : 'price overlay' : 'zero origin')}</span>
        </button>
        <button disabled={busy || open || dirty} aria-label={`${item.visible ? 'Hide' : 'Show'} ${index + 1} ${item.type.toUpperCase()}`} aria-pressed={item.visible} title={open || dirty ? 'Apply or cancel edits before changing visibility here' : 'Save visibility immediately'} onClick={() => onApply(settings.instances.map(row => row.id === item.id ? {...row, visible: !row.visible} : row))}>{item.visible ? 'Hide' : 'Show'}</button>
      </li>)}
    </ul>}
    {settings.instances.some(item => ['atr', 'volume', 'obv', 'keltner', 'vwma', 'mfi', 'cmf'].includes(item.type)) && <details className="indicator-unit-note"><summary>Indicator units and seed notes</summary><p>ATR/Keltner ATR: price units, Wilder smoothing with an SMA true-range seed; initialization differs from graph/recorded IR. Volume-weighted formulas use raw source volume. Volume/OBV: {volumeUnit ?? 'source-native units (unverified)'}. OBV starts at zero at the saved origin or segment reset. Stochastic: percent. Full calculation details are below the chart.</p></details>}
    {open && <div id={panelId} className="chart-indicator-controls" aria-label="Chart indicator settings">
      <div className="indicator-editor-heading"><strong>Display indicators · {draft.length} instances</strong>{!catalogOpen && <button onClick={() => {setCatalogOpen(true);setTarget('search');}}>Browse indicators</button>}<button onClick={collapse} aria-label="Close indicator settings">Collapse · keep edits</button></div>
      <div className={catalogOpen ? "indicator-workbench" : "indicator-workbench indicator-editor-only"}>
      {catalogOpen && <section className="indicator-catalog" aria-label="Indicator catalog">
        <div className="indicator-catalog-filters">
          <label>Search<input ref={searchInput} aria-label="Search indicators" value={search} onChange={event => {setSearch(event.target.value); setPage(0);}} placeholder="Name or abbreviation" maxLength={120}/></label>
          <label>Category<select aria-label="Indicator category" value={category} onChange={event => {setCategory(event.target.value); setPage(0);}}>
            {['All', 'Favorites', ...indicatorCategories].map(value => <option key={value}>{value}</option>)}
          </select></label>
        </div>
        <ul className="indicator-catalog-list" aria-label="Available indicators">
          {matches.slice(currentPage * pageSize, (currentPage + 1) * pageSize).map(entry => <li key={entry.kind}>
            <button className="indicator-catalog-add" disabled={busy} aria-label={`Add ${entry.kind.toUpperCase()}`} title={entry.description} onClick={() => add(entry.kind)}>
              <strong>{entry.kind.toUpperCase()}</strong><span>{entry.name}</span><small>{entry.category}</small>
            </button>
            <button className="indicator-favorite" aria-label={`Favorite ${entry.kind.toUpperCase()}`} aria-pressed={favorites.includes(entry.kind)} onClick={() => favorite(entry.kind)}>{favorites.includes(entry.kind) ? '★' : '☆'}</button>
          </li>)}
        </ul>
        {matches.length > pageSize && <div className="indicator-catalog-pages" aria-label="Indicator catalog pages"><button disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>Previous indicators</button><span>Page {currentPage + 1} of {lastPage + 1} · {matches.length} types</span><button disabled={currentPage === lastPage} onClick={() => setPage(currentPage + 1)}>Next indicators</button></div>}
        {!matches.length && <p role="status">No indicators match. Try another search or category.</p>}
        {favoriteNotice && <p role="status">{favoriteNotice}</p>}
      </section>}
      <section className="indicator-instance-editor" aria-label="Selected indicator editor">
      <label>On chart<select aria-label="Selected indicator instance" disabled={busy || !draft.length} value={selectedItem?.id ?? ''} onChange={event => setSelected(event.target.value)}>
        {!draft.length && <option value="">No instances yet</option>}
        {draft.map((item, index) => <option value={item.id} key={item.id}>{index+1}. {indicatorName(item)}{item.visible ? '' : ' · hidden'}</option>)}
      </select></label>
      {!draft.length && <p>Add an indicator from the catalog, then edit its inputs and style here.</p>}
      {draft.map((item, index) => item.id === selectedItem?.id && <fieldset disabled={busy} key={item.id} tabIndex={-1} ref={editor}>
        <legend>{index + 1}. {item.type === 'bb' ? 'Bollinger Bands' : item.type.toUpperCase()}</legend>
        <div className="chart-indicator-fields">
          {parameterOrder[item.type].filter(() => item.type !== 'vwap').map(key => [key, item.params[key]] as const).map(([key, value]) => <label key={key}>{key}
            <input
              aria-label={`${index + 1} ${item.type.toUpperCase()} ${key}`}
              type="number"
              min={item.type === 'sar' ? 0.001 : (key === 'deviations' || key === 'multiplier') ? 0.01 : 1}
              max={key === 'displacement' ? 100 : item.type === 'sar' ? 1 : (key === 'deviations' || key === 'multiplier') ? 10 : 1000}
              step={item.type === 'sar' ? 'any' : (key === 'deviations' || key === 'multiplier') ? 'any' : 1}
              value={Number.isNaN(value) ? '' : value}
              onChange={event => edit(item.id, {params: {
                ...item.params,
                [key]: event.target.value === '' ? NaN : Number(event.target.value),
              }})}
            />
          </label>)}
          {item.type === 'vwap' && <>
            <label>Session<select aria-label={`${index + 1} VWAP session`} value={item.params.mode} onChange={event => edit(item.id, {params: {mode: Number(event.target.value), anchor: 0}})}><option value={0}>UTC day (midnight reset)</option><option value={1}>Fixed UTC anchor</option></select></label>
            {item.params.mode === 1 && <label>Anchor candle open (UTC)<UtcAnchorPicker label={`${index + 1} VWAP anchor UTC`} value={item.params.anchor} onChange={anchor => edit(item.id, {params: {...item.params, anchor}})}/></label>}
            <small>UTC candle-open time, not your local timezone. Requires the exact boundary and every confirmed native {minutes}-minute candle since it. Missing coverage is unavailable; no automatic backfill.</small>
          </>}
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
          <button disabled={busy} onClick={() => {const remaining=draft.filter(row => row.id !== item.id);setDraft(remaining);setSelected(remaining[Math.min(index,remaining.length-1)]?.id ?? null);if(!remaining.length)setCatalogOpen(true);setTarget(remaining.length ? 'editor' : 'search');}}>
            Remove {index + 1} {item.type.toUpperCase()}
          </button>
        </div>
      </fieldset>)}
      </section>
      </div>
      {(invalid || error) && <p role="alert">{invalid || error}</p>}
      <button disabled={busy || !!invalid} onClick={() => onApply(draft)}>{busy ? 'Saving…' : 'Apply indicators'}</button>
      <button disabled={busy} onClick={cancel}>Cancel edits</button>
      <small>Display only · confirmed native-timeframe closes. More visible instances increase calculation and rendering work; hidden instances are not calculated. Apply saves all valid edits together in this source workspace. Cancel discards edits; Collapse retains them. Recorded IR and trading settings are separate. Defaults are examples, not trading recommendations.</small>
    </div>}
  </div>;
}
