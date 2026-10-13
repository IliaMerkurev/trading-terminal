import {useState} from 'react';
import type {ChartIndicator} from './ChartIndicators';
import {indicatorShortLabel} from './indicatorCatalog';
import {paneUnit, type PaneLayout} from './chartPanes';

type Props = {instances: ChartIndicator[]; layout: PaneLayout; busy: boolean; onChange: (layout: PaneLayout) => void; onVisibility: (ids: string[], visible: boolean) => void};
export default function PaneLayoutEditor({instances, layout, busy, onChange, onVisibility}: Props) {
  const [open, setOpen] = useState(false);
  const byId = new Map(instances.map(item => [item.id,item]));
  const label = (id: string) => `${instances.findIndex(item => item.id === id) + 1} ${indicatorShortLabel(byId.get(id)!.type)}`;
  const editWeight = (field: 'price_weight' | 'recorded_weight', value: string) => onChange({...layout,[field]:value === '' ? NaN : Number(value)});
  const move = (index: number, offset: number) => {
    const panes = [...layout.panes];
    [panes[index],panes[index+offset]] = [panes[index+offset],panes[index]];
    onChange({...layout,panes});
  };
  const assign = (id: string, destination: string) => {
    let panes = layout.panes.map(pane => ({...pane,instance_ids:pane.instance_ids.filter(member => member !== id)}));
    if (destination) panes = panes.map(pane => pane.id === destination ? {...pane,instance_ids:[...pane.instance_ids,id]} : pane);
    else panes.push({id:'pane_'+crypto.randomUUID().replaceAll('-',''),weight:130,instance_ids:[id]});
    onChange({...layout,panes:panes.filter(pane => pane.instance_ids.length)});
  };
  return <section className="chart-pane-editor" aria-label="Chart pane layout">
    <button aria-expanded={open} onClick={() => setOpen(value => !value)}>Pane layout</button>
    {open && <fieldset disabled={busy}>
      <legend>Relative pane heights and compatible groups</legend>
      <p>Price stays first; Recorded IR stays separate and last. Hidden panes release space and keep their order and weight. Weights are relative, not pixels. Extra panes use linear scales.</p>
      <div className="chart-pane-weights">
        <label>Price weight<input aria-label="Price pane weight" type="number" min={1} max={10000} step="any" value={Number.isFinite(layout.price_weight)?layout.price_weight:''} onChange={event => editWeight('price_weight',event.target.value)}/></label>
        <label>Recorded IR weight<input aria-label="Recorded IR pane weight" type="number" min={1} max={10000} step="any" value={Number.isFinite(layout.recorded_weight)?layout.recorded_weight:''} onChange={event => editWeight('recorded_weight',event.target.value)}/></label>
      </div>
      {layout.panes.map((pane,index) => {
        const first = byId.get(pane.instance_ids[0])!, unit = paneUnit(first);
        const visible = pane.instance_ids.some(id => byId.get(id)?.visible);
        return <section key={pane.id} className="chart-pane-row" aria-label={`Pane ${index+1}`}>
          <strong>Pane {index+1} · {unit?.replaceAll('_',' ')}{visible?'':' · hidden'}</strong>
          <div className="chart-pane-weights">
            <label>Weight<input aria-label={`Pane ${index+1} weight`} type="number" min={1} max={10000} step="any" value={Number.isFinite(pane.weight)?pane.weight:''} onChange={event => onChange({...layout,panes:layout.panes.map(value => value.id === pane.id ? {...value,weight:event.target.value === '' ? NaN : Number(event.target.value)} : value)})}/></label>
            <button disabled={busy || index===0} aria-label={`Move pane ${index+1} up`} onClick={() => move(index,-1)}>Move up</button>
            <button disabled={busy || index===layout.panes.length-1} aria-label={`Move pane ${index+1} down`} onClick={() => move(index,1)}>Move down</button>
            <button onClick={() => onVisibility(pane.instance_ids,!visible)}>{visible?'Hide':'Show'} pane {index+1}</button>
          </div>
          {pane.instance_ids.map(id => <label key={id}>{label(id)}{byId.get(id)?.visible?'':' · hidden'}<select aria-label={`Pane for ${label(id)}`} value={pane.id} onChange={event => assign(id,event.target.value)}>
            {layout.panes.filter(value => paneUnit(byId.get(value.instance_ids[0])!) === unit).map(value => <option key={value.id} value={value.id}>Pane {layout.panes.indexOf(value)+1} · {value.instance_ids.map(label).join(', ')}</option>)}
            {pane.instance_ids.length > 1 && <option value="">New separate pane</option>}
          </select></label>)}
        </section>;
      })}
      {!layout.panes.length && <p>No extra panes. Add a pane indicator or place volume in a separate pane.</p>}
    </fieldset>}
  </section>;
}
