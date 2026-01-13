'use client';

import { useEffect, useState } from 'react';
import type { Heading } from '@/lib/mdx';

interface TableOfContentsProps {
  headings: Heading[];
}

export function TableOfContents({ headings }: TableOfContentsProps) {
  const [activeId, setActiveId] = useState<string>('');

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        });
      },
      {
        rootMargin: '-20% 0% -35% 0%',
        threshold: 1.0,
      }
    );

    // Observe all heading elements
    const elements = headings
      .map((h) => document.getElementById(h.slug))
      .filter((el): el is HTMLElement => el !== null);

    elements.forEach((el) => observer.observe(el));

    return () => {
      elements.forEach((el) => observer.unobserve(el));
    };
  }, [headings]);

  if (headings.length === 0) {
    return null;
  }

  return (
    <nav className="sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto">
      <div className="text-sm font-semibold mb-4 text-[var(--foreground)]">
        On This Page
      </div>
      <ul className="space-y-2 text-sm">
        {headings.map((heading) => {
          const isActive = activeId === heading.slug;
          const indent = (heading.level - 1) * 12;

          return (
            <li key={heading.slug} style={{ paddingLeft: `${indent}px` }}>
              <a
                href={`#${heading.slug}`}
                className={`block py-1 border-l-2 pl-3 transition-colors ${
                  isActive
                    ? 'border-[var(--accent-cyan)] text-[var(--accent-cyan)]'
                    : 'border-transparent text-[var(--foreground-muted)] hover:text-[var(--foreground)] hover:border-[var(--accent-cyan)]/50'
                }`}
                onClick={(e) => {
                  e.preventDefault();
                  const element = document.getElementById(heading.slug);
                  element?.scrollIntoView({ behavior: 'smooth' });
                }}
              >
                {heading.text}
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
