import { create } from 'zustand';
import type { LineRange, XRaySyncState } from '@/lib/types';

export const useXRaySync = create<XRaySyncState>((set) => ({
  activeEntryId: null,
  highlightedLines: null,
  scrollTarget: null,
  hoveredLine: null,

  setActiveEntry: (id: string | null) => set({ activeEntryId: id }),

  setHighlightedLines: (range: LineRange | null) => set({ highlightedLines: range }),

  setScrollTarget: (target: 'code' | 'commentary' | null) => set({ scrollTarget: target }),

  setHoveredLine: (line: number | null) => set({ hoveredLine: line }),

  reset: () =>
    set({
      activeEntryId: null,
      highlightedLines: null,
      scrollTarget: null,
      hoveredLine: null,
    }),
}));
