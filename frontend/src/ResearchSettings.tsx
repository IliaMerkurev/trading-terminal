import type {Profile} from './model';
import {timeframe} from './research';

export default function ResearchSettings({profile,onChange}:{profile:Profile;onChange:(p:Profile)=>void}){
 const update=(key:string,value:string|number)=>onChange({...profile,[key]:value});
 const resolution=Number(profile.execution_minutes??1);
 return <div className="research-settings">
  <div className="two-columns">
   <label className="field">Market<select aria-label="Research market" value={profile.market} onChange={e=>onChange({...profile,market:e.target.value,leverage:'1',execution_minutes:e.target.value==='linear'?1:resolution})}><option value="spot">Spot · unleveraged</option><option value="linear">Perpetual · detailed M1</option></select></label>
   <label className="field">Instrument<input aria-label="Research instrument" autoComplete="off" spellCheck={false} value={profile.symbol} onChange={e=>update('symbol',e.target.value.toUpperCase())}/></label>
  </div>
  <label className="field">Initial capital · USDT<input aria-label="Research capital" type="number" min="1" value={String(profile.capital)} onChange={e=>update('capital',e.target.value)}/></label>
  <label className="field">Simulation detail<select aria-label="Research resolution" value={resolution} onChange={e=>onChange({...profile,execution_minutes:Number(e.target.value),primary_minutes:Math.max(profile.primary_minutes,Number(e.target.value))})}>
   {(profile.market==='spot'?[60,240,1440,15,5,1]:[1]).map(m=><option key={m} value={m}>{m===1?'Detailed · 1m':`Fast · ${timeframe(m)} candles`}</option>)}
  </select></label>
  <p className="resolution-note">{resolution===1?'Detailed minute paths. Supports every strategy timeframe.':`${timeframe(resolution)} source candles. Strategy timeframes must be a multiple of ${timeframe(resolution)}. Stops and drawdown use a modeled candle path.`}</p>
  <details><summary>Costs, sizing & execution assumptions</summary>
   <div className="two-columns">{[['fee_rate','Fee per fill'],['slippage','Adverse slippage']].map(([key,label])=><label className="field" key={key}>{label} · %<input aria-label={label} type="number" min="0" step="0.01" value={Number(profile[key])*100} onChange={e=>update(key,String(Number(e.target.value)/100))}/></label>)}</div>
   <label className="field">Allocation · % of available capital<input aria-label="Research allocation" type="number" min="1" max="100" value={String(profile.allocation)} onChange={e=>onChange({...profile,sizing:'percent',allocation:e.target.value})}/></label>
   {profile.market==='linear'&&<label className="field">Leverage<input aria-label="Research leverage" type="number" min="1" value={String(profile.leverage)} onChange={e=>update('leverage',e.target.value)}/></label>}
   <label className="field">Modeled candle path<select value={profile.path} onChange={e=>update('path',e.target.value)}><option value="OLHC">Open → Low → High → Close</option><option value="OHLC">Open → High → Low → Close</option></select></label>
   <p>Closed-bar signals, full close at the end, independent account per test. No future candle values. Different execution detail can change returns and drawdown.</p>
   <p>Quantity step {String(profile.quantity_step)} · minimum order {String(profile.min_notional)} USDT. {profile.tier_assumption}.</p>
  </details>
 </div>;
}
