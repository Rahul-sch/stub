'use client';

import { useState, useRef, useEffect } from 'react';
import { glossaryData } from '@/content/glossary';

interface GlossaryTermProps {
  term: string;
  children?: React.ReactNode;
}

export function GlossaryTerm({ term, children }: GlossaryTermProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [position, setPosition] = useState<'top' | 'bottom'>('top');
  const termRef = useRef<HTMLSpanElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const entry = glossaryData[term];

  useEffect(() => {
    if (isHovered && termRef.current && tooltipRef.current) {
      const termRect = termRef.current.getBoundingClientRect();
      const tooltipHeight = tooltipRef.current.offsetHeight;
      const spaceAbove = termRect.top;
      const spaceBelow = window.innerHeight - termRect.bottom;

      // Show tooltip below if not enough space above
      if (spaceAbove < tooltipHeight + 10 && spaceBelow > tooltipHeight + 10) {
        setPosition('bottom');
      } else {
        setPosition('top');
      }
    }
  }, [isHovered]);

  if (!entry) {
    // If term not found in glossary, just return the text
    return <span>{children || term}</span>;
  }

  return (
    <span className="relative inline-block">
      <span
        ref={termRef}
        className="glossary-term cursor-help border-b-2 border-dotted border-[var(--accent-cyan)] text-[var(--accent-cyan)]"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {children || term}
      </span>

      {isHovered && (
        <div
          ref={tooltipRef}
          className={`absolute left-1/2 -translate-x-1/2 z-50 w-80 p-4 rounded-lg bg-[var(--background-secondary)] border border-[var(--background-tertiary)] shadow-xl ${
            position === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'
          }`}
        >
          <div className="text-sm font-semibold text-[var(--accent-cyan)] mb-2">
            {entry.term}
          </div>
          <div className="text-sm text-[var(--foreground-muted)] leading-relaxed">
            {entry.definition}
          </div>
          {entry.seeAlso && entry.seeAlso.length > 0 && (
            <div className="mt-3 pt-3 border-t border-[var(--background-tertiary)]">
              <div className="text-xs text-[var(--foreground-muted)] mb-1">
                See also:
              </div>
              <div className="flex flex-wrap gap-2">
                {entry.seeAlso.map((relatedTerm) => (
                  <span
                    key={relatedTerm}
                    className="text-xs px-2 py-1 rounded bg-[var(--background-tertiary)] text-[var(--accent-purple)]"
                  >
                    {relatedTerm}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </span>
  );
}
