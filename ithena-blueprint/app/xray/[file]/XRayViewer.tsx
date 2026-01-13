'use client';

import { useEffect } from 'react';
import { useXRaySync } from '@/hooks/useXRaySync';
import { CodeViewer } from '@/components/xray/CodeViewer';
import { CommentaryPanel } from '@/components/xray/CommentaryPanel';
import type { XRayFile, HighlightedLine } from '@/lib/types';
import { ArrowLeft, FileCode, Hash, GitBranch } from 'lucide-react';
import Link from 'next/link';

interface XRayViewerProps {
  xray: XRayFile;
  code: string;
  highlightedLines: HighlightedLine[];
}

export function XRayViewer({ xray, code, highlightedLines }: XRayViewerProps) {
  const { reset } = useXRaySync();

  // Reset sync state when component mounts
  useEffect(() => {
    reset();
    return () => reset();
  }, [reset]);

  const lineCount = code.split('\n').length;

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="h-16 bg-[var(--background-secondary)] border-b border-[var(--background-tertiary)] px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link
            href="/xray"
            className="flex items-center gap-2 text-[var(--foreground-muted)] hover:text-[var(--foreground)] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm">Back</span>
          </Link>
          <div className="w-px h-6 bg-[var(--background-tertiary)]" />
          <div className="flex items-center gap-2">
            <FileCode className="w-5 h-5 text-[var(--accent-cyan)]" />
            <span className="font-mono font-medium text-[var(--accent-cyan)]">
              {xray.filePath.split('/').pop()}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm text-[var(--foreground-muted)]">
          <div className="flex items-center gap-1">
            <Hash className="w-4 h-4" />
            <span>{lineCount} lines</span>
          </div>
          <div className="flex items-center gap-1">
            <GitBranch className="w-4 h-4" />
            <span className="font-mono text-xs">{xray.fileHash}</span>
          </div>
          <div className="px-2 py-1 rounded bg-[var(--background-tertiary)]">
            {xray.entries.length} sections
          </div>
        </div>
      </header>

      {/* Split Pane */}
      <div className="split-pane flex-1">
        {/* Code Pane */}
        <div className="split-pane-left">
          <CodeViewer code={code} language={xray.language} entries={xray.entries} highlightedLines={highlightedLines} />
        </div>

        {/* Commentary Pane */}
        <div className="split-pane-right bg-[var(--background)]">
          <CommentaryPanel entries={xray.entries} />
        </div>
      </div>
    </div>
  );
}
