import type {ChartIndicator} from './ChartIndicators';

export function indicatorValue(item: ChartIndicator, port: string, value: unknown) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return `${port} N/A (warmup, missing coverage or unconfirmed)`;
  if (item.type === 'supertrend' && port === 'direction') return `direction ${value === 1 ? 'Up (+1)' : value === -1 ? 'Down (−1)' : 'Unavailable'}`;
  return `${port} ${value.toLocaleString(undefined, {maximumSignificantDigits: 10})}`;
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
