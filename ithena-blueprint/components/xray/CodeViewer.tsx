'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useXRaySync } from '@/hooks/useXRaySync';
import type { XRayEntry, HighlightedLine } from '@/lib/types';
import clsx from 'clsx';

interface CodeViewerProps {
  code: string;
  language: string;
  entries: XRayEntry[];
  highlightedLines: HighlightedLine[];
}

export function CodeViewer({ code, language, entries, highlightedLines }: CodeViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const lineRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  const {
    highlightedLines: highlightedRange,
    scrollTarget,
    hoveredLine,
    setHighlightedLines,
    setActiveEntry,
    setScrollTarget,
    setHoveredLine,
  } = useXRaySync();

  // Find which entry a line belongs to
  const findEntryForLine = useCallback(
    (lineNum: number): XRayEntry | undefined => {
      return entries.find(
        (entry) => lineNum >= entry.startLine && lineNum <= entry.endLine
      );
    },
    [entries]
  );

  // Handle line hover
  const handleLineHover = useCallback(
    (lineNum: number) => {
      setHoveredLine(lineNum);
      const entry = findEntryForLine(lineNum);
      if (entry) {
        setHighlightedLines({ start: entry.startLine, end: entry.endLine });
        setActiveEntry(entry.id);
      }
    },
    [findEntryForLine, setHighlightedLines, setActiveEntry, setHoveredLine]
  );

  // Handle line leave
  const handleLineLeave = useCallback(() => {
    setHoveredLine(null);
  }, [setHoveredLine]);

  // Handle line click - scroll to entry in commentary
  const handleLineClick = useCallback(
    (lineNum: number) => {
      const entry = findEntryForLine(lineNum);
      if (entry) {
        setActiveEntry(entry.id);
        setScrollTarget('commentary');
      }
    },
    [findEntryForLine, setActiveEntry, setScrollTarget]
  );

  // Scroll to highlighted lines when scrollTarget is 'code'
  useEffect(() => {
    if (scrollTarget === 'code' && highlightedRange) {
      const lineElement = lineRefs.current.get(highlightedRange.start);
      if (lineElement && containerRef.current) {
        const container = containerRef.current;
        const lineTop = lineElement.offsetTop;
        const containerHeight = container.clientHeight;
        const scrollTo = lineTop - containerHeight / 3;
        container.scrollTo({ top: scrollTo, behavior: 'smooth' });
      }
      setScrollTarget(null);
    }
  }, [scrollTarget, highlightedRange, setScrollTarget]);

  // Check if a line should be highlighted
  const isLineHighlighted = (lineNum: number): boolean => {
    if (!highlightedRange) return false;
    return lineNum >= highlightedRange.start && lineNum <= highlightedRange.end;
  };

  // Check if a line is the hovered line
  const isLineHovered = (lineNum: number): boolean => {
    return hoveredLine === lineNum;
  };

  return (
    <div ref={containerRef} className="code-viewer h-full overflow-y-auto">
      <div className="py-4">
        {highlightedLines.map((line) => {
          const lineNum = line.lineNumber;
          const highlighted = isLineHighlighted(lineNum);
          const hovered = isLineHovered(lineNum);
          const entry = findEntryForLine(lineNum);

          return (
            <div
              key={lineNum}
              ref={(el) => {
                if (el) lineRefs.current.set(lineNum, el);
              }}
              className={clsx(
                'code-line',
                highlighted && 'highlighted',
                hovered && 'bg-[var(--code-line-highlight)]',
                entry && 'cursor-pointer'
              )}
              onMouseEnter={() => handleLineHover(lineNum)}
              onMouseLeave={handleLineLeave}
              onClick={() => handleLineClick(lineNum)}
            >
              <span className="code-gutter">{lineNum}</span>
              <code 
                className="code-content"
                dangerouslySetInnerHTML={{ __html: line.html }}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
