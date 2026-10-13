import type {Profile} from './model';
import {timeframe} from './research';

// Schema-1 manifests without an interval are native M1. Explicit invalid values
// are not legacy defaults: the backend refuses them too.
export function historyIntervalSeconds(dataset:any):number|null {
  const value=dataset?.interval_seconds===undefined?60:dataset.interval_seconds;
  return typeof value==='number'&&Number.isSafeInteger(value)&&value>0?value:null;
}

export function historyExecutionMinutes(profile:Profile):number|null {
  const value=profile.execution_minutes===undefined?1:profile.execution_minutes;
  return typeof value==='number'&&[1,5,15,60,240,1440].includes(value)?value:null;
}

export function historyMismatch(dataset:any,profile:Profile):string|null {
  if(!dataset)return 'History is no longer available';
  if(dataset.market!==profile.market)return 'Market does not match';
  if(dataset.symbol!==profile.symbol)return 'Instrument does not match';
  const seconds=historyIntervalSeconds(dataset),minutes=historyExecutionMinutes(profile);
  if(seconds===null)return 'Native timeframe is unknown';
  if(minutes===null)return 'Execution resolution is invalid';
  return seconds===minutes*60?null:`Requires ${timeframe(minutes)} execution history`;
}

export const historyMatchesProfile=(dataset:any,profile:Profile)=>historyMismatch(dataset,profile)===null;
