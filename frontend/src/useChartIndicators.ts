import {useEffect, useRef, useState} from 'react';
import {api} from './api';
import {poll} from './poll';
import {emptySettings, type ChartIndicator, type IndicatorSettings} from './ChartIndicators';
import type {LiveCandle} from './liveChartData';

export function useChartIndicators(
  market: string,
  symbol: string,
  minutes: number,
  active: boolean,
  rows: React.MutableRefObject<LiveCandle[]>,
  source = 'bybit',
  windowEpoch = 0,
  priceStyle: 'candles' | 'heikin_ashi' | 'line' = 'candles',
) {
  const [settings, setSettings] = useState<IndicatorSettings>(emptySettings);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const generation = useRef(0);
  const settingsRef = useRef(settings);
  const anchor = useRef(false);
  const calculationEpoch = useRef(0);
  const resultWindow = useRef(windowEpoch);
  const resultKey = useRef('');
  const resultRows = useRef('');
  const requestKey = JSON.stringify([source, market, symbol, minutes, priceStyle]);
  settingsRef.current = settings;

  useEffect(() => {
    const token = ++generation.current;
    const controller = new AbortController();
    setLoaded(false);
    setSettings(emptySettings);
    setResult(null);
    setError('');
    setSaving(false);
    anchor.current = false;
    api<IndicatorSettings>('chart_indicator_settings', {market, symbol, ...(source==='bybit'?{}:{source})}, {signal: controller.signal}).then(doc => {
      if (token !== generation.current) return;
      if (doc.version !== 1 || !Array.isArray(doc.instances)) {
        throw new Error('Settings unavailable');
      }
      setSettings(doc);
      setError(doc.warning ?? '');
      setLoaded(true);
    }).catch(() => {
      if (token === generation.current) {
        setError('Indicator settings could not be read. Price browsing remains available; reopen the chart to retry.');
      }
    });
    return () => { ++generation.current; controller.abort(); };
  }, [source, market, symbol]);

  useEffect(() => {
    setResult(null);
    anchor.current = false;
    ++calculationEpoch.current;
    if (!active || !loaded || (!settings.instances.some(item => item.visible) && priceStyle !== 'heikin_ashi')) return;
    let stopped = false;
    const controller = new AbortController();
    const cancel = poll(async () => {
      const current = rows.current;
      if (!current.length) return null;
      const start = current[0].time;
      const end = current.at(-1)!.time;
      const key = JSON.stringify(current);
      const epoch = calculationEpoch.current;
      const reanchor = anchor.current;
      anchor.current = false;
      const value = await api<any>('chart_indicator_read', {
        market, symbol, ...(source==='bybit'?{}:{source}), minutes, start, end, revision: settings.revision, reanchor, ...(priceStyle === 'heikin_ashi' ? {price_style: 'heikin_ashi'} : {}),
      }, {signal: controller.signal});
      return {key, epoch, value};
    }, reply => {
      if (!reply || stopped) return;
      if (reply.key !== JSON.stringify(rows.current) || reply.epoch !== calculationEpoch.current) return;
      resultRows.current = reply.key;
      resultWindow.current = windowEpoch;
      resultKey.current = requestKey;
      setResult(reply.value);
      setError(reply.value.error ?? reply.value.settings?.warning ?? '');
    }, reason => {
      if (!stopped) {
        setResult(null);
        setError(String(reason instanceof Error
          ? reason.message
          : 'Indicator calculation unavailable; price browsing remains available.'));
      }
    }, 1000);
    return () => {
      stopped = true;
      controller.abort();
      cancel();
    };
  }, [source, market, symbol, minutes, active, loaded, settings, windowEpoch, priceStyle]);

  const apply = async (instances: ChartIndicator[]) => {
    const token = generation.current;
    setSaving(true);
    setError('');
    try {
      const doc = await api<IndicatorSettings>('chart_indicator_save', {
        market, symbol, ...(source==='bybit'?{}:{source}), instances, revision: settingsRef.current.revision,
      });
      if (token === generation.current) {
        setSettings(doc);
        setResult(null);
      }
    } catch (cause) {
      if (token === generation.current) {
        setError('Settings save could not be confirmed. Reload the chart before retrying. ' + (cause instanceof Error ? cause.message : 'Try again.'));
      }
    } finally {
      if (token === generation.current) setSaving(false);
    }
  };

  const reanchor = () => {
    ++calculationEpoch.current;
    anchor.current = true;
    setResult(null);
  };
  return {settings, projectionCurrent: resultRows.current === JSON.stringify(rows.current), result: resultWindow.current === windowEpoch && resultKey.current === requestKey ? result : null, error, saving, loaded, apply, reanchor};
}
