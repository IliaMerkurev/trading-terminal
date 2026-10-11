import {useEffect, useId, useRef, useState} from 'react';
import {isTypingTarget} from './chartDrawings';
import {indicatorCatalog, indicatorCategories, favoritesKey, parseIndicatorFavorites} from './indicatorCatalog';

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
  focusMode?: boolean;
  toolbar?: React.ReactNode;
  toolbarActions?: React.ReactNode;
  settings: IndicatorSettings;
  onApply: (items: ChartIndicator[]) => void;
  busy: boolean;
  error: string;
  volumeUnit?: string;
};

export default function ChartIndicators({settings, onApply, busy, error, volumeUnit, toolbar, toolbarActions}: Props) {
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
  const invalid = validateIndicators(draft);
  const dirty = JSON.stringify(draft) !== JSON.stringify(settings.instances);
  const edit = (id: string, change: Partial<ChartIndicator>) => {
    setDraft(rows => rows.map(row => row.id === id ? {...row, ...change} : row));
  };
  const add = (kind: IndicatorKind) => {
    if (busy || draft.length >= 8) return;
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
          <strong>{index + 1}. {item.type.toUpperCase()}</strong><span>{parameterOrder[item.type].map(key => `${key} ${item.params[key]}`).join(' · ') || (item.type === 'volume' ? item.placement === 'pane' ? 'separate pane' : 'price overlay' : 'zero origin')}</span>
        </button>
        <button disabled={busy || open || dirty} aria-label={`${item.visible ? 'Hide' : 'Show'} ${index + 1} ${item.type.toUpperCase()}`} aria-pressed={item.visible} title={open || dirty ? 'Apply or cancel edits before changing visibility here' : 'Save visibility immediately'} onClick={() => onApply(settings.instances.map(row => row.id === item.id ? {...row, visible: !row.visible} : row))}>{item.visible ? 'Hide' : 'Show'}</button>
      </li>)}
    </ul>}
    {settings.instances.some(item => ['atr', 'volume', 'obv'].includes(item.type)) && <details className="indicator-unit-note"><summary>Indicator units and seed notes</summary><p>ATR: price units, Wilder smoothing with an SMA true-range seed; initialization differs from graph/recorded IR. Volume/OBV: {volumeUnit ?? 'source-native units (unverified)'}. OBV starts at zero at the saved origin or segment reset. Stochastic: percent. Full calculation details are below the chart.</p></details>}
    {open && <div id={panelId} className="chart-indicator-controls" aria-label="Chart indicator settings">
      <div className="indicator-editor-heading"><strong>Display indicators · {draft.length}/8 instances</strong>{!catalogOpen && <button onClick={() => {setCatalogOpen(true);setTarget('search');}}>Browse indicators</button>}<button onClick={collapse} aria-label="Close indicator settings">Collapse · keep edits</button></div>
      <div className={catalogOpen ? "indicator-workbench" : "indicator-workbench indicator-editor-only"}>
      {catalogOpen && <section className="indicator-catalog" aria-label="Indicator catalog">
        <div className="indicator-catalog-filters">
          <label>Search<input ref={searchInput} aria-label="Search indicators" value={search} onChange={event => setSearch(event.target.value)} placeholder="Name or abbreviation" maxLength={120}/></label>
          <label>Category<select aria-label="Indicator category" value={category} onChange={event => setCategory(event.target.value)}>
            {['All', 'Favorites', ...indicatorCategories].map(value => <option key={value}>{value}</option>)}
          </select></label>
        </div>
        <ul className="indicator-catalog-list" aria-label="Available indicators">
          {matches.map(entry => <li key={entry.kind}>
            <button className="indicator-catalog-add" disabled={busy || draft.length >= 8} aria-label={`Add ${entry.kind.toUpperCase()}`} title={entry.description} onClick={() => add(entry.kind)}>
              <strong>{entry.kind.toUpperCase()}</strong><span>{entry.name}</span><small>{entry.category}</small>
            </button>
            <button className="indicator-favorite" aria-label={`Favorite ${entry.kind.toUpperCase()}`} aria-pressed={favorites.includes(entry.kind)} onClick={() => favorite(entry.kind)}>{favorites.includes(entry.kind) ? '★' : '☆'}</button>
          </li>)}
        </ul>
        {!matches.length && <p role="status">No indicators match. Try another search or category.</p>}
        {draft.length >= 8 && <p role="status">Limit reached: 8 instances, including hidden ones. Remove an instance to add another.</p>}
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
      <small>Display only · confirmed native-timeframe closes. Apply saves all valid edits together in this source workspace. Cancel discards edits; Collapse retains them. Recorded IR and trading settings are separate. Defaults are examples, not trading recommendations.</small>
    </div>}
  </div>;
}
