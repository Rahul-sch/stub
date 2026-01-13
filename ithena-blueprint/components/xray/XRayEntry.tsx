'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, AlertTriangle, TestTube, Zap, Shield, Link2 } from 'lucide-react';
import type { XRayEntry as XRayEntryType } from '@/lib/types';
import clsx from 'clsx';

interface XRayEntryProps {
  entry: XRayEntryType;
  isActive: boolean;
  onHover: () => void;
  onLeave: () => void;
  onClick: () => void;
}

export function XRayEntry({ entry, isActive, onHover, onLeave, onClick }: XRayEntryProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const getBadgeClass = (kind: string) => {
    switch (kind) {
      case 'function':
        return 'badge-function';
      case 'class':
        return 'badge-class';
      case 'import':
        return 'badge-import';
      case 'variable':
        return 'badge-variable';
      case 'decorator':
        return 'badge-decorator';
      default:
        return 'badge-function';
    }
  };

  return (
    <div
      className={clsx('commentary-entry', isActive && 'active')}
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
    >
      {/* Header */}
      <div
        className="flex items-start gap-3 cursor-pointer"
        onClick={onClick}
      >
        <button
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
          }}
          className="mt-1 text-[var(--foreground-muted)] hover:text-[var(--foreground)] transition-colors"
        >
          {isExpanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <h3 className="font-semibold text-[var(--foreground)]">{entry.title}</h3>
            <span className="text-xs text-[var(--foreground-muted)]">
              L{entry.startLine}-{entry.endLine}
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5 mb-3">
            {entry.anchors.slice(0, 4).map((anchor, i) => (
              <span key={i} className={clsx('badge', getBadgeClass(anchor.kind))}>
                {anchor.kind}: {anchor.value}
              </span>
            ))}
            {entry.anchors.length > 4 && (
              <span className="badge bg-[var(--background-tertiary)] text-[var(--foreground-muted)]">
                +{entry.anchors.length - 4} more
              </span>
            )}
          </div>
          <p className="text-sm text-[var(--foreground-muted)] leading-relaxed">
            {entry.whatItDoes}
          </p>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-[var(--background-tertiary)] space-y-4 animate-fade-in">
          {/* Why */}
          <div>
            <h4 className="text-sm font-medium text-[var(--accent-blue)] mb-2 flex items-center gap-2">
              <Zap className="w-4 h-4" />
              Why This Code Exists
            </h4>
            <p className="text-sm text-[var(--foreground-muted)] leading-relaxed pl-6">
              {entry.why}
            </p>
          </div>

          {/* Failure Modes */}
          {entry.failureModes.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-[var(--accent-yellow)] mb-2 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Failure Modes
              </h4>
              <div className="space-y-2 pl-6">
                {entry.failureModes.map((fm, i) => (
                  <div key={i} className="text-sm">
                    <p className="text-[var(--foreground)]">
                      <strong>If:</strong> {fm.condition}
                    </p>
                    <p className="text-[var(--foreground-muted)]">
                      <strong>Then:</strong> {fm.behavior}
                    </p>
                    <p className="text-[var(--accent-green)]">
                      <strong>Fix:</strong> {fm.recovery}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tests */}
          {entry.tests.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-[var(--accent-purple)] mb-2 flex items-center gap-2">
                <TestTube className="w-4 h-4" />
                Testing
              </h4>
              <div className="space-y-2 pl-6">
                {entry.tests.map((test, i) => (
                  <div key={i} className="text-sm">
                    <p className="text-[var(--foreground)]">{test.what}</p>
                    <p className="text-[var(--foreground-muted)] text-xs">{test.how}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Performance & Security Notes */}
          <div className="flex gap-4">
            {entry.perfNotes && (
              <div className="flex-1">
                <h4 className="text-sm font-medium text-[var(--accent-cyan)] mb-1 flex items-center gap-2">
                  <Zap className="w-3 h-3" />
                  Performance
                </h4>
                <p className="text-xs text-[var(--foreground-muted)]">{entry.perfNotes}</p>
              </div>
            )}
            {entry.securityNotes && (
              <div className="flex-1">
                <h4 className="text-sm font-medium text-[var(--accent-red)] mb-1 flex items-center gap-2">
                  <Shield className="w-3 h-3" />
                  Security
                </h4>
                <p className="text-xs text-[var(--foreground-muted)]">{entry.securityNotes}</p>
              </div>
            )}
          </div>

          {/* Related Links */}
          {(entry.relatedDocs.length > 0 || entry.relatedNodes.length > 0) && (
            <div>
              <h4 className="text-sm font-medium text-[var(--foreground-muted)] mb-2 flex items-center gap-2">
                <Link2 className="w-4 h-4" />
                Related
              </h4>
              <div className="flex flex-wrap gap-2 pl-6">
                {entry.relatedDocs.map((doc, i) => (
                  <a
                    key={i}
                    href={`/wiki/${doc}`}
                    className="text-xs px-2 py-1 rounded bg-[var(--accent-purple)]/10 text-[var(--accent-purple)] hover:bg-[var(--accent-purple)]/20 transition-colors"
                  >
                    {doc}
                  </a>
                ))}
                {entry.relatedNodes.map((node, i) => (
                  <a
                    key={i}
                    href={`/map?node=${node}`}
                    className="text-xs px-2 py-1 rounded bg-[var(--accent-orange)]/10 text-[var(--accent-orange)] hover:bg-[var(--accent-orange)]/20 transition-colors"
                  >
                    {node}
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
