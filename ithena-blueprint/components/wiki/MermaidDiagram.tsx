'use client';

import { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

interface MermaidDiagramProps {
  chart: string;
}

export function MermaidDiagram({ chart }: MermaidDiagramProps) {
  const elementRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: true,
      theme: 'dark',
      themeVariables: {
        primaryColor: '#06b6d4',
        primaryTextColor: '#f3f4f6',
        primaryBorderColor: '#0891b2',
        lineColor: '#8b5cf6',
        secondaryColor: '#8b5cf6',
        tertiaryColor: '#f59e0b',
        background: '#1e293b',
        mainBkg: '#1e293b',
        secondBkg: '#334155',
        textColor: '#f3f4f6',
        fontSize: '14px',
      },
    });

    if (elementRef.current) {
      elementRef.current.innerHTML = chart;
      mermaid.contentLoaded();
    }
  }, [chart]);

  return (
    <div className="my-6 p-4 rounded-lg bg-[var(--code-bg)] border border-[var(--background-tertiary)] overflow-x-auto">
      <div ref={elementRef} className="mermaid flex justify-center" />
    </div>
  );
}
