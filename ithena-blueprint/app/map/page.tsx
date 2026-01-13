import { Map as MapIcon } from 'lucide-react';
import { SystemCanvas } from '@/components/map/SystemCanvas';
import path from 'path';
import fs from 'fs';
import { Node, Edge } from '@xyflow/react';

interface SystemTopology {
  nodes: Array<{
    id: string;
    type: string;
    position: { x: number; y: number };
    data: {
      label: string;
      description: string;
      facts: string[];
      wikiLinks: string[];
      xrayLinks: Array<{ file: string; entryId: string }>;
    };
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    label?: string;
    animated: boolean;
    data?: {
      description: string;
      throughput?: string;
      pattern?: string;
      guarantee?: string;
      frequency?: string;
      timeout?: string;
    };
  }>;
}

async function getTopologyData(): Promise<{ nodes: Node[]; edges: Edge[] }> {
  const topologyPath = path.join(
    process.cwd(),
    'content',
    'map',
    'system-topology.json'
  );

  const topologyContent = fs.readFileSync(topologyPath, 'utf-8');
  const topology: SystemTopology = JSON.parse(topologyContent);

  // Convert to ReactFlow format
  const nodes: Node[] = topology.nodes.map((node) => ({
    id: node.id,
    type: node.type,
    position: node.position,
    data: node.data,
  }));

  const edges: Edge[] = topology.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label,
    animated: edge.animated,
    style: {
      stroke: edge.animated ? 'var(--accent-cyan)' : 'var(--foreground-muted)',
      strokeWidth: edge.animated ? 2 : 1,
    },
    labelStyle: {
      fontSize: 12,
      fill: 'var(--foreground)',
      fontWeight: 500,
    },
    labelBgStyle: {
      fill: 'var(--background-secondary)',
      fillOpacity: 0.9,
    },
    sourceHandle: edge.source === 'database-neon' ? 'bottom' : undefined,
    targetHandle: edge.target === 'twin-dashboard' && edge.source === 'consumer-ml' ? undefined : undefined,
  }));

  return { nodes, edges };
}

export default async function SystemMapPage() {
  const { nodes, edges } = await getTopologyData();

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="h-20 bg-[var(--background-secondary)] border-b border-[var(--background-tertiary)] px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-[var(--accent-orange)]/20 flex items-center justify-center">
            <MapIcon className="w-6 h-6 text-[var(--accent-orange)]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">System Map</h1>
            <p className="text-sm text-[var(--foreground-muted)]">
              Interactive node graph showing data flow
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--background-tertiary)]">
              <div className="w-2 h-2 rounded-full bg-[var(--accent-cyan)]" />
              <span>Animated = Real-time</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--background-tertiary)]">
              <div className="w-2 h-2 rounded-full bg-[var(--foreground-muted)]" />
              <span>Static = On-demand</span>
            </div>
          </div>
        </div>
      </header>

      {/* Canvas */}
      <div className="flex-1">
        <SystemCanvas nodes={nodes} edges={edges} />
      </div>

      {/* Instructions */}
      <div className="absolute bottom-6 left-6 bg-[var(--background-secondary)]/90 backdrop-blur-sm border border-[var(--background-tertiary)] rounded-lg p-4 max-w-sm">
        <div className="text-sm font-semibold mb-2 text-[var(--foreground)]">
          How to Use
        </div>
        <ul className="text-xs text-[var(--foreground-muted)] space-y-1">
          <li>• Click nodes to expand details</li>
          <li>• Drag to pan, scroll to zoom</li>
          <li>• Click wiki/code links to navigate</li>
          <li>• Use minimap (bottom right) for overview</li>
        </ul>
      </div>
    </div>
  );
}
