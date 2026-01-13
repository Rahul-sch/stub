'use client';

import { Handle, Position, NodeProps } from '@xyflow/react';
import {
  Cpu,
  Database,
  Activity,
  Layers,
  Monitor,
  Box,
  ExternalLink,
} from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

interface NodeData {
  label: string;
  description?: string;
  facts?: string[];
  wikiLinks?: string[];
  xrayLinks?: Array<{ file: string; entryId: string }>;
}


const nodeConfig = {
  sensor: {
    icon: Cpu,
    color: 'var(--accent-cyan)',
    bgColor: 'rgba(6, 182, 212, 0.1)',
    borderColor: 'var(--accent-cyan)',
  },
  kafka: {
    icon: Layers,
    color: 'var(--accent-orange)',
    bgColor: 'rgba(245, 158, 11, 0.1)',
    borderColor: 'var(--accent-orange)',
  },
  consumer: {
    icon: Activity,
    color: 'var(--accent-green)',
    bgColor: 'rgba(34, 197, 94, 0.1)',
    borderColor: 'var(--accent-green)',
  },
  database: {
    icon: Database,
    color: 'var(--accent-purple)',
    bgColor: 'rgba(139, 92, 246, 0.1)',
    borderColor: 'var(--accent-purple)',
  },
  dashboard: {
    icon: Monitor,
    color: 'var(--accent-cyan)',
    bgColor: 'rgba(6, 182, 212, 0.1)',
    borderColor: 'var(--accent-cyan)',
  },
  twin: {
    icon: Box,
    color: '#ec4899',
    bgColor: 'rgba(236, 72, 153, 0.1)',
    borderColor: '#ec4899',
  },
};

export function CustomNode({ data, type = 'sensor' }: NodeProps) {
  const nodeData = data as unknown as NodeData;
  const [isExpanded, setIsExpanded] = useState(false);
  const config = nodeConfig[type as keyof typeof nodeConfig] || nodeConfig.sensor;
  const Icon = config.icon;

  return (
    <div className="relative">
      {/* Input Handle */}
      {type !== 'sensor' && (
        <Handle
          type="target"
          position={Position.Left}
          className="w-3 h-3"
          style={{ background: config.color }}
        />
      )}

      {/* Node Body */}
      <div
        className={`px-6 py-4 rounded-lg border-2 shadow-lg min-w-[200px] cursor-pointer transition-all duration-200 ${
          isExpanded ? 'scale-105' : ''
        }`}
        style={{
          backgroundColor: config.bgColor,
          borderColor: config.borderColor,
          boxShadow: isExpanded
            ? `0 0 20px ${config.color}40`
            : `0 0 10px ${config.color}20`,
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3 mb-2">
          <Icon className="w-6 h-6" style={{ color: config.color }} />
          <div className="font-semibold text-[var(--foreground)]">
            {nodeData.label}
          </div>
        </div>

        {nodeData.description && (
          <div className="text-sm text-[var(--foreground-muted)] mb-3">
            {nodeData.description}
          </div>
        )}

        {/* Expandable Details */}
        {isExpanded && (
          <div className="mt-4 pt-4 border-t" style={{ borderColor: config.borderColor }}>
            {nodeData.facts && nodeData.facts.length > 0 && (
              <div className="mb-4">
                <div className="text-xs font-semibold mb-2 uppercase" style={{ color: config.color }}>
                  Key Facts
                </div>
                <ul className="space-y-1">
                  {nodeData.facts.map((fact: string, idx: number) => (
                    <li key={idx} className="text-xs text-[var(--foreground-muted)] flex items-start gap-2">
                      <span style={{ color: config.color }}>•</span>
                      <span>{fact}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Wiki Links */}
            {nodeData.wikiLinks && nodeData.wikiLinks.length > 0 && (
              <div className="mb-3">
                <div className="text-xs font-semibold mb-2 uppercase" style={{ color: config.color }}>
                  Learn More
                </div>
                <div className="flex flex-wrap gap-2">
                  {nodeData.wikiLinks.map((slug: string) => (
                    <Link
                      key={slug}
                      href={`/wiki/${slug}`}
                      className="text-xs px-2 py-1 rounded bg-[var(--background-tertiary)] hover:bg-[var(--background-secondary)] transition-colors flex items-center gap-1"
                      style={{ color: config.color }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {slug}
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* X-Ray Links */}
            {nodeData.xrayLinks && nodeData.xrayLinks.length > 0 && (
              <div>
                <div className="text-xs font-semibold mb-2 uppercase" style={{ color: config.color }}>
                  Code References
                </div>
                <div className="flex flex-wrap gap-2">
                  {nodeData.xrayLinks.map((link: { file: string; entryId: string }, idx: number) => (
                    <Link
                      key={idx}
                      href={`/xray/${link.file}#${link.entryId}`}
                      className="text-xs px-2 py-1 rounded bg-[var(--background-tertiary)] hover:bg-[var(--background-secondary)] transition-colors flex items-center gap-1"
                      style={{ color: config.color }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {link.file}
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Output Handle */}
      {type !== 'dashboard' && type !== 'database' && (
        <Handle
          type="source"
          position={Position.Right}
          className="w-3 h-3"
          style={{ background: config.color }}
        />
      )}

      {/* Special handles for nodes with multiple outputs */}
      {type === 'database' && (
        <>
          <Handle
            type="source"
            position={Position.Bottom}
            id="bottom"
            className="w-3 h-3"
            style={{ background: config.color }}
          />
        </>
      )}
      {type === 'consumer' && (
        <Handle
          type="source"
          position={Position.Top}
          id="top"
          className="w-3 h-3"
          style={{ background: config.color }}
        />
      )}
    </div>
  );
}
