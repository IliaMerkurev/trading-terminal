import {createContext, useRef, type ReactNode} from 'react';
import type {PaneLayout} from './chartPanes';
import type {ChartIndicator, IndicatorSettings} from './ChartIndicators';

export type IndicatorDraft = {
  draft: ChartIndicator[];
  paneLayout: PaneLayout | null;
  submittedLayout: PaneLayout | null;
  base: IndicatorSettings;
  stagedName: string;
  selected: string | null;
  submitted: ChartIndicator[] | null;
  open: boolean;
  catalogOpen: boolean;
};
export const IndicatorDraftContext = createContext<Map<string, IndicatorDraft> | null>(null);

// Session-only ownership above keyed chart mounts. A new terminal/workspace
// starts with a fresh map; nothing is written to module globals or localStorage.
export function IndicatorDraftProvider({children}: {children: ReactNode}) {
  const drafts = useRef(new Map<string, IndicatorDraft>());
  return <IndicatorDraftContext.Provider value={drafts.current}>{children}</IndicatorDraftContext.Provider>;
}
