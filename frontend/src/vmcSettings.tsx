// Original display adapter. Calculation provenance: vumanchu A/B; Jazal/DonovanWall Swing (MPL-2.0).
export type VmcKind = 'vmc_cipher_b' | 'vmc_cipher_a' | 'vmc_swing';
export type VmcParams = Record<string, number | boolean | string>;
export const isVmcKind = (kind: string): kind is VmcKind => ['vmc_cipher_b', 'vmc_cipher_a', 'vmc_swing'].includes(kind);
export const vmcDefaults: Record<VmcKind, VmcParams> = {
  "vmc_cipher_b": {
    "source": "hlc3",
    "channel": 9,
    "average": 12,
    "signal": 3,
    "flow_period": 60,
    "flow_multiplier": 150.0,
    "rsi_period": 14,
    "flow_offset": 2.5,
    "overbought": 53.0,
    "oversold": -53.0,
    "gold_oversold": -75.0,
    "stoch_period": 14,
    "stoch_rsi_period": 14,
    "stoch_k": 3,
    "stoch_d": 3,
    "stoch_log": true,
    "stoch_average": false,
    "wt_regular": true,
    "wt_secondary": true,
    "wt_hidden": false,
    "hidden_no_limits": true,
    "wt_div_top": 45.0,
    "wt_div_bottom": -65.0,
    "wt_secondary_top": 15.0,
    "wt_secondary_bottom": -40.0,
    "rsi_regular": false,
    "rsi_hidden": false,
    "rsi_div_top": 60.0,
    "rsi_div_bottom": 30.0,
    "stoch_regular": false,
    "stoch_hidden": false
  },
  "vmc_cipher_a": {
    "source": "hlc3",
    "channel": 9,
    "average": 13,
    "signal": 3,
    "flow_period": 60,
    "flow_multiplier": 150.0,
    "rsi_period": 14,
    "ema1": 5,
    "ema2": 11,
    "ema3": 15,
    "ema4": 18,
    "ema5": 21,
    "ema6": 24,
    "ema7": 28,
    "ema8": 34,
    "yellow_oversold": -80.0
  },
  "vmc_swing": {
    "source": "close",
    "period": 20,
    "multiplier": 3.5
  }
};
export const vmcParameterOrder = Object.fromEntries(Object.entries(vmcDefaults).map(([kind, params]) => [kind, Object.keys(params)])) as Record<VmcKind, string[]>;
const sources = {open:'Open', high:'High', low:'Low', close:'Close', hl2:'HL2 (high + low) / 2', hlc3:'HLC3 (high + low + close) / 3', ohlc4:'OHLC4 (open + high + low + close) / 4'};
const lengths = new Set('channel average signal flow_period rsi_period stoch_period stoch_rsi_period stoch_k stoch_d period ema1 ema2 ema3 ema4 ema5 ema6 ema7 ema8'.split(' '));
export function validateVmcParams(kind: VmcKind, params: VmcParams): string {
 const expected = vmcDefaults[kind];
 if (Object.keys(params).length !== Object.keys(expected).length || Object.keys(expected).some(key => !(key in params))) return 'VMC settings require the complete known parameter set.';
 for (const [key, value] of Object.entries(params)) {
  if (key === 'source') {if (typeof value !== 'string' || !Object.prototype.hasOwnProperty.call(sources,value)) return 'Choose a supported raw OHLC source.';}
  else if (typeof expected[key] === 'boolean') {if (typeof value !== 'boolean') return 'VMC switches must be on or off.';}
  else if (typeof value !== 'number' || !Number.isFinite(value) || Math.abs(value) > 10000) return 'VMC values must be finite and within −10000 to 10000.';
  else if (lengths.has(key) && (!Number.isInteger(value) || value < 1 || value > 1000)) return 'VMC periods must be whole numbers from 1 to 1000.';
  else if (['multiplier', 'flow_multiplier'].includes(key) && value <= 0) return 'VMC multipliers must be positive.';
 }
 for (const [top, bottom] of [['overbought','oversold'],['wt_div_top','wt_div_bottom'],['wt_secondary_top','wt_secondary_bottom'],['rsi_div_top','rsi_div_bottom']]) {
  if (top in params && Number(params[top]) <= Number(params[bottom])) return 'VMC upper thresholds must be greater than their lower thresholds.';
 }
 return '';
}
const labels: Record<string,string> = {
 source:'Raw price source', channel:'WT channel length', average:'WT average length', signal:'WT signal smoothing',
 flow_period:'Flow smoothing length', flow_multiplier:'Flow multiplier', flow_offset:'Flow vertical offset',
 rsi_period:'RSI length', overbought:'WT overbought', oversold:'WT oversold', gold_oversold:'Gold previous trough threshold',
 stoch_period:'Stochastic lookback', stoch_rsi_period:'Stoch RSI length', stoch_k:'Stoch K smoothing', stoch_d:'Stoch D smoothing',
 stoch_log:'Use log(close) for Stoch RSI', stoch_average:'Average Stoch K with D',
 wt_regular:'WT regular divergences', wt_secondary:'Secondary WT regular divergences', wt_hidden:'WT hidden divergences', hidden_no_limits:'Hidden divergences without thresholds',
 wt_div_top:'WT divergence upper threshold',wt_div_bottom:'WT divergence lower threshold',wt_secondary_top:'Secondary WT upper threshold',wt_secondary_bottom:'Secondary WT lower threshold',
 rsi_regular:'RSI regular divergences',rsi_hidden:'RSI hidden divergences',rsi_div_top:'RSI divergence upper threshold',rsi_div_bottom:'RSI divergence lower threshold',
 stoch_regular:'Stoch regular divergences',stoch_hidden:'Stoch hidden divergences',yellow_oversold:'Yellow-cross WT lower threshold',period:'Range smoothing length',multiplier:'Range multiplier',
};
export function vmcGroup(key: string) {
 if (key.startsWith('ema')) return 'EMA ribbon';
 if (key.includes('div') || ['wt_regular','wt_secondary','wt_hidden','hidden_no_limits','wt_secondary_top','wt_secondary_bottom','rsi_regular','rsi_hidden','stoch_regular','stoch_hidden'].includes(key)) return 'Confirmed divergences';
 if (key.startsWith('flow')) return 'Candle-body flow';
 if (key.startsWith('rsi') || key.startsWith('stoch')) return 'RSI and Stoch RSI';
 return 'Wave / range and signals';
}
export function VmcFields({kind, params, prefix, onChange}: {kind:VmcKind;params:VmcParams;prefix:string;onChange:(params:VmcParams)=>void}) {
 const keys=vmcParameterOrder[kind];
 return <>{[...new Set(keys.map(vmcGroup))].map(group => <fieldset className="vmc-parameter-group" key={group}><legend>{group}</legend>{keys.filter(key=>vmcGroup(key)===group).map(key => {
  const value=params[key], label=labels[key] ?? `EMA ${key.slice(3)} length`;
  const update=(next:number|boolean|string)=>onChange({...params,[key]:next});
  return <label key={key}>{label}{key==='source' ? <select aria-label={`${prefix} ${key}`} value={String(value)} onChange={event=>update(event.target.value)}>{Object.entries(sources).map(([id,name])=><option key={id} value={id}>{name}</option>)}</select>
   : typeof vmcDefaults[kind][key]==='boolean' ? <input type="checkbox" aria-label={`${prefix} ${key}`} checked={value===true} onChange={event=>update(event.target.checked)}/>
   : <input type="number" aria-label={`${prefix} ${key}`} min={lengths.has(key)?1:['multiplier','flow_multiplier'].includes(key)?0:-10000} max={lengths.has(key)?1000:10000} step={lengths.has(key)?1:'any'} value={typeof value==='number' && Number.isFinite(value)?value:''} onChange={event=>update(event.target.value===''?NaN:Number(event.target.value))}/>}</label>;
 })}</fieldset>)}<small>Raw OHLC, confirmed bars only. Fast WT is WT1−WT2, not VWAP. VMC flow is a candle-body proxy without volume, not Money Flow Index. Divergences become available two bars after the pivot. Semantic colors are fixed; the selected color accents the main wave / line. Sommi, higher-timeframe colors and Schaff are omitted.</small></>;
}
