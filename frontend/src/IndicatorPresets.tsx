import {useEffect, useRef, useState} from 'react';
import {unsupportedPaneExtensions} from './chartPanes';
import {api} from './api';
import {indicatorName, type ChartIndicator} from './ChartIndicators';

export type IndicatorNamespace = {source: string; market: string; symbol: string};
export type PresetMetadata = {id: string; name: string; revision: number; deleted: boolean; instance_count: number};
export type IndicatorPreset = PresetMetadata & {content: {version: 1; instances: ChartIndicator[]; extensions: Record<string, unknown>}};
type Props = {namespace: IndicatorNamespace; revision: number; dirty: boolean; busy: boolean; onStage: (preset: IndicatorPreset) => void};

// This component is keyed by namespace by its owner. Reads are cancellable;
// writes are never retried and obsolete replies cannot affect a new chart.
export default function IndicatorPresets({namespace, revision, dirty, busy, onStage}: Props) {
  const [opened, setOpened] = useState(false);
  const [trashed, setTrashed] = useState(false);
  const [rows, setRows] = useState<PresetMetadata[]>([]);
  const [selected, setSelected] = useState('');
  const [preview, setPreview] = useState<IndicatorPreset | null>(null);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [writing, setWriting] = useState(false);
  const [error, setError] = useState('');
  const [uncertain, setUncertain] = useState(false);
  const [notice, setNotice] = useState('');
  const [refresh, setRefresh] = useState(0);
  const alive = useRef(true);
  const readEpoch = useRef(0);
  const writeLock = useRef(false);
  useEffect(() => {alive.current = true; return () => {alive.current = false; ++readEpoch.current;};}, []);
  useEffect(() => {
    if (!opened) return;
    const token = ++readEpoch.current, controller = new AbortController();
    setLoading(true); setPreview(null); setSelected('');
    api<{version: 1; presets: PresetMetadata[]}>('chart_preset_list', {trashed}, {signal: controller.signal}).then(value => {
      if (!alive.current || token !== readEpoch.current) return;
      setRows(value.presets); setError(''); setUncertain(false);
    }).catch(cause => {if (alive.current && token === readEpoch.current) setError(String(cause instanceof Error ? cause.message : cause));})
      .finally(() => {if (alive.current && token === readEpoch.current) setLoading(false);});
    return () => {controller.abort(); ++readEpoch.current;};
  }, [opened, trashed, refresh]);
  const choose = async (id: string) => {
    const row = rows.find(value => value.id === id);
    const token = ++readEpoch.current;
    setSelected(id); setPreview(null); setNotice('');
    if (!row) {setLoading(false); return;}
    setName(row.name); setLoading(true);
    try {
      const value = await api<IndicatorPreset>('chart_preset_get', {preset_id: row.id, revision: row.revision});
      if (alive.current && token === readEpoch.current) {setPreview(value); if (!uncertain) setError('');}
    } catch (cause) {if (alive.current && token === readEpoch.current) setError(String(cause instanceof Error ? cause.message : cause));}
    finally {if (alive.current && token === readEpoch.current) setLoading(false);}
  };
  const mutation = async (command: string) => {
    if (writeLock.current || loading || uncertain || busy) return;
    const row = rows.find(value => value.id === selected);
    const saving = command === 'chart_preset_save_current';
    if (saving ? dirty : !row) return;
    const params = saving ? {...namespace, revision, name: name.trim()} : {
      preset_id: row!.id, revision: row!.revision,
      ...(['chart_preset_duplicate', 'chart_preset_rename'].includes(command) ? {name: name.trim()} : {}),
    };
    writeLock.current = true; setWriting(true); setNotice(''); setError(''); ++readEpoch.current;
    try {
      const result = await api<PresetMetadata>(command, params);
      if (!alive.current) return;
      setNotice(`Saved library change: ${result.name}. Active chart indicators are unchanged.`);
      setRefresh(value => value + 1);
    } catch (cause) {
      if (!alive.current) return;
      const definite = (cause as {definiteRejection?: boolean})?.definiteRejection;
      setUncertain(!definite);
      setError(`${definite ? 'Library change rejected.' : 'Library change could not be confirmed. It may have completed. Refresh library before trying again.'} ${cause instanceof Error ? cause.message : String(cause)}`);
    } finally {if (alive.current) {writeLock.current = false; setWriting(false);}}
  };
  const validName = name.trim().length > 0 && [...name.trim()].length <= 120;
  const blocked = busy || loading || writing || uncertain;
  const row = rows.find(value => value.id === selected);
  const unsupported = preview && unsupportedPaneExtensions(preview.content);
  return <section className="indicator-presets" aria-label="Indicator preset library">
    <button aria-expanded={opened} onClick={() => setOpened(value => !value)}>Named presets</button>
    {opened && <>
      <p>Workspace-wide library · Stage replaces the current chart draft only. Apply indicators saves it to {namespace.source} / {namespace.market} / {namespace.symbol}.</p>
      <div className="indicator-preset-actions">
        <label>Library view<select aria-label="Preset library view" disabled={writing || loading} value={trashed ? 'trash' : 'active'} onChange={event => setTrashed(event.target.value === 'trash')}><option value="active">Active presets</option><option value="trash">Trash</option></select></label>
        <button disabled={writing || loading} onClick={() => setRefresh(value => value + 1)}>Refresh library</button>
        <label>Preset<select aria-label="Named indicator preset" value={selected} disabled={loading || writing} onChange={event => {void choose(event.target.value);}}><option value="">Select a preset</option>{rows.map(value => <option key={value.id} value={value.id}>{value.name} · {value.instance_count} instances</option>)}</select></label>
        <label>Name<input aria-label="Preset name" value={name} maxLength={240} disabled={writing} onChange={event => setName(event.target.value)}/></label>
        <button disabled={blocked || dirty || !validName} onClick={() => {void mutation('chart_preset_save_current');}}>Save current as preset</button>
        <button disabled={blocked || !row || trashed || !validName} onClick={() => {void mutation('chart_preset_duplicate');}}>Duplicate preset / Save as</button>
        <button disabled={blocked || !row || trashed || !validName} onClick={() => {void mutation('chart_preset_rename');}}>Rename preset</button>
        <button disabled={blocked || !row} onClick={() => {void mutation(trashed ? 'chart_preset_restore' : 'chart_preset_trash');}}>{trashed ? 'Restore preset' : 'Move preset to Trash'}</button>
      </div>
      {dirty && <p>Apply or Cancel edits first before saving current indicators or staging another preset.</p>}
      {!validName && name && <p>Use a nonempty name of at most 120 characters. Active names must be unique, ignoring case.</p>}
      {loading && <p role="status">Loading preset library…</p>}
      {!loading && !rows.length && <p>{trashed ? 'Trash is empty.' : 'No named presets yet.'}</p>}
      {preview && <section aria-label="Preset preview"><strong>Preview: {preview.name} · revision {preview.revision}</strong><p>{preview.content.instances.length} instances. Preview does not change the chart.</p>
        <ul className="indicator-preset-preview">{preview.content.instances.map((item, index) => <li key={item.id}>{index + 1}. {indicatorName(item)}{item.visible ? '' : ' · hidden'}{item.type === 'volume' ? ` · ${item.placement ?? 'overlay'}` : ''}</li>)}</ul>
        {unsupported && <p role="alert">This preset contains unsupported extensions. It cannot be staged by this version; duplication remains available.</p>}
        <button disabled={blocked || dirty || preview.deleted || !!unsupported} onClick={() => onStage(preview)}>Stage preset</button>
      </section>}
      {notice && <p role="status">{notice}</p>}
    </>}
    {error && <p role="alert">{error}</p>}
    {!opened && writing && <p role="status">Saving preset library change…</p>}
    {opened && writing && <p role="status">Saving preset library change…</p>}
  </section>;
}
