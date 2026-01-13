'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useXRaySync } from '@/hooks/useXRaySync';
import { XRayEntry } from './XRayEntry';
import type { XRayEntry as XRayEntryType } from '@/lib/types';

interface CommentaryPanelProps {
  entries: XRayEntryType[];
}

export function CommentaryPanel({ entries }: CommentaryPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const entryRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const {
    activeEntryId,
    scrollTarget,
    setActiveEntry,
    setHighlightedLines,
    setScrollTarget,
  } = useXRaySync();

  // Handle entry hover
  const handleEntryHover = useCallback(
    (entry: XRayEntryType) => {
      setActiveEntry(entry.id);
      setHighlightedLines({ start: entry.startLine, end: entry.endLine });
    },
    [setActiveEntry, setHighlightedLines]
  );

  // Handle entry leave
  const handleEntryLeave = useCallback(() => {
    // Don't immediately clear to allow for smooth transition
  }, []);

  // Handle entry click - scroll to code section
  const handleEntryClick = useCallback(
    (entry: XRayEntryType) => {
      setActiveEntry(entry.id);
      setHighlightedLines({ start: entry.startLine, end: entry.endLine });
      setScrollTarget('code');
    },
    [setActiveEntry, setHighlightedLines, setScrollTarget]
  );

  // Scroll to active entry when scrollTarget is 'commentary'
  useEffect(() => {
    if (scrollTarget === 'commentary' && activeEntryId) {
      const entryElement = entryRefs.current.get(activeEntryId);
      if (entryElement && containerRef.current) {
        const container = containerRef.current;
        const entryTop = entryElement.offsetTop;
        const containerHeight = container.clientHeight;
        const scrollTo = entryTop - containerHeight / 4;
        container.scrollTo({ top: scrollTo, behavior: 'smooth' });
      }
      setScrollTarget(null);
    }
  }, [scrollTarget, activeEntryId, setScrollTarget]);

  return (
    <div ref={containerRef} className="h-full overflow-y-auto p-6 space-y-4">
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-1">Code Commentary</h2>
        <p className="text-sm text-[var(--foreground-muted)]">
          {entries.length} sections • Hover to highlight code • Click to navigate
        </p>
      </div>
      {entries.map((entry) => (
        <div
          key={entry.id}
          ref={(el) => {
            if (el) entryRefs.current.set(entry.id, el);
          }}
        >
          <XRayEntry
            entry={entry}
            isActive={activeEntryId === entry.id}
            onHover={() => handleEntryHover(entry)}
            onLeave={handleEntryLeave}
            onClick={() => handleEntryClick(entry)}
          />
        </div>
      ))}
    </div>
  );
}
