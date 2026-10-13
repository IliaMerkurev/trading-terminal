import type {ChartIndicator} from './ChartIndicators';

export function indicatorValue(item: ChartIndicator, port: string, value: unknown) {
  port = ({wt1:'WT1',wt2:'WT2',fast_wave:'Fast WT (WT1−WT2)',flow:'VMC flow (candle-body proxy)',stoch_k:'Stoch RSI K',stoch_d:'Stoch RSI D'} as Record<string,string>)[port] ?? port;
  if (typeof value !== 'number' || !Number.isFinite(value)) return `${port} N/A (warmup, missing coverage or unconfirmed)`;
  if (item.type === 'supertrend' && port === 'direction') return `direction ${value === 1 ? 'Up (+1)' : value === -1 ? 'Down (−1)' : 'Unavailable'}`;
  // Display-only cleanup for floating-point residue; underlying values stay untouched.
  const residue = item.type === 'vmc_cipher_b' && (port === 'Stoch RSI K' || port === 'Stoch RSI D') && Math.abs(value) < 1e-10;
  const shown = residue ? 0 : value;
  return `${port} ${shown.toLocaleString(undefined, {maximumSignificantDigits: 10, notation: Math.abs(shown) > 0 && (Math.abs(shown) < 1e-6 || Math.abs(shown) >= 1e12) ? 'scientific' : 'standard'})}`;
}

// This is the backend's latest evaluated status, not a historical cursor status.
export function vwapStatus(status: {status?: string; reason?: string} | undefined) {
  if (!status) return 'Awaiting cached calculation';
  if (status.status === 'ready') return 'Ready: complete coverage from the session boundary';
  const reasons: Record<string, string> = {
    before_anchor: 'Unavailable: the evaluated candles precede the fixed UTC anchor',
    missing_session_start: 'Unavailable: the exact session-start candle is missing from cached calculation history',
    incomplete_coverage: 'Unavailable: a missing, unconfirmed or invalid-volume candle interrupts this session',
    zero_total_volume: 'Unavailable: cumulative source volume is zero',
  };
  return reasons[status.reason ?? ''] ?? 'Unavailable: complete confirmed session coverage is required';
}
