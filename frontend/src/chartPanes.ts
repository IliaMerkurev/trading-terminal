import type {ChartIndicator} from './ChartIndicators';

export type ChartPane = {id: string; weight: number; instance_ids: string[]};
export type PaneLayout = {version: 1; price_weight: number; recorded_weight: number; panes: ChartPane[]};
export const auxiliaryKinds = ['vmc_cipher_b', 'rsi', 'macd', 'volume', 'atr', 'stochastic', 'obv', 'roc', 'momentum', 'cci', 'williamsr', 'mfi', 'cmf', 'stddev', 'dmi', 'stochrsi', 'bbpercentb', 'bbwidth'];
export function paneUnit(item: ChartIndicator): string | null {
  if (!auxiliaryKinds.includes(item.type) || item.type === 'volume' && item.placement !== 'pane') return null;
  return ({rsi:'bounded100', stochastic:'bounded100', macd:'price_difference', momentum:'price_difference', atr:'price_distance', stddev:'price_distance'} as Record<string,string>)[item.type] ?? item.type;
}
export function legacyPaneLayout(instances: ChartIndicator[]): PaneLayout {
  const panes: ChartPane[] = [];
  for (const item of instances) {
    if (paneUnit(item) === null) continue;
    const id = `legacy_${item.type}`, pane = panes.find(value => value.id === id);
    if (pane) pane.instance_ids.push(item.id);
    else panes.push({id, weight:130, instance_ids:[item.id]});
  }
  return {version:1, price_weight:320, recorded_weight:130, panes};
}
// Reconcile only deliberate instance add/remove/placement edits. Visibility never
// deletes membership; it only determines which panes occupy chart space.
export function reconcilePaneLayout(layout: PaneLayout, instances: ChartIndicator[]): PaneLayout {
  const eligible = new Map(instances.filter(item => paneUnit(item) !== null).map(item => [item.id,item]));
  const panes = layout.panes.map(pane => ({...pane, instance_ids:pane.instance_ids.filter(id => eligible.has(id))})).filter(pane => pane.instance_ids.length);
  const assigned = new Set(panes.flatMap(pane => pane.instance_ids));
  for (const item of eligible.values()) {
    if (assigned.has(item.id)) continue;
    const existing = panes.find(pane => pane.instance_ids.some(id => eligible.get(id)?.type === item.type));
    if (existing) existing.instance_ids.push(item.id);
    else {
      let id = `pane_${item.id}`.slice(0,64), suffix = 0;
      while (panes.some(pane => pane.id === id)) id = `pane_${++suffix}_${item.id}`.slice(0,64);
      panes.push({id, weight:130, instance_ids:[item.id]});
    }
  }
  return {...layout, panes};
}
export function validatePaneLayout(value: unknown, instances: ChartIndicator[]): string {
  const invalid = 'Invalid or unsupported pane layout. Use compatible panes and weights from 1 to 10000.';
  if (!value || typeof value !== 'object' || Array.isArray(value)) return invalid;
  const doc = value as PaneLayout;
  const keys = (obj: object, names: string[]) => Object.keys(obj).sort().join(',') === names.sort().join(',');
  const weight = (v: number) => typeof v === 'number' && Number.isFinite(v) && v >= 1 && v <= 10000;
  if (!keys(doc,['version','price_weight','recorded_weight','panes']) || doc.version !== 1 || !weight(doc.price_weight) || !weight(doc.recorded_weight) || !Array.isArray(doc.panes)) return invalid;
  const eligible = new Map(instances.filter(item => paneUnit(item) !== null).map(item => [item.id,paneUnit(item)]));
  const assigned = new Set<string>(), ids = new Set<string>();
  for (const pane of doc.panes) {
    if (!pane || typeof pane !== 'object' || !keys(pane,['id','weight','instance_ids']) || typeof pane.id !== 'string' || !/^[a-zA-Z][a-zA-Z0-9_-]{0,63}$/.test(pane.id) || ['price','recorded'].includes(pane.id) || ids.has(pane.id) || !weight(pane.weight) || !Array.isArray(pane.instance_ids) || !pane.instance_ids.length) return invalid;
    ids.add(pane.id);
    let unit: string | null | undefined;
    for (const id of pane.instance_ids) {
      if (typeof id !== 'string' || !eligible.has(id) || assigned.has(id) || unit !== undefined && unit !== eligible.get(id)) return invalid;
      unit = eligible.get(id); assigned.add(id);
    }
  }
  return assigned.size === eligible.size ? '' : invalid;
}
export function presetPaneLayout(content: {instances: ChartIndicator[]; extensions: Record<string,unknown>}): PaneLayout | null {
  return (content.extensions?.pane_layout as PaneLayout | undefined) ?? null;
}
export function unsupportedPaneExtensions(content: {version: number; instances: ChartIndicator[]; extensions: Record<string,unknown>}): boolean {
  return content.version !== 1 || !content.extensions || Object.keys(content.extensions).some(key => key !== 'pane_layout') ||
    ('pane_layout' in content.extensions && !!validatePaneLayout(content.extensions.pane_layout, content.instances));
}
export function visiblePanes(instances: ChartIndicator[], layout?: PaneLayout | null): ChartPane[] {
  const visible = new Set(instances.filter(item => item.visible).map(item => item.id));
  return (layout ?? legacyPaneLayout(instances)).panes.filter(pane => pane.instance_ids.some(id => visible.has(id)));
}
