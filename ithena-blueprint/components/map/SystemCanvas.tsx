'use client';

import { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  ConnectionLineType,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { CustomNode } from './CustomNode';

interface SystemCanvasProps {
  nodes: Node[];
  edges: Edge[];
}

const nodeTypes = {
  sensor: CustomNode,
  kafka: CustomNode,
  consumer: CustomNode,
  database: CustomNode,
  dashboard: CustomNode,
  twin: CustomNode,
};

const edgeOptions = {
  animated: false,
  style: {
    stroke: 'var(--accent-cyan)',
    strokeWidth: 2,
  },
  type: ConnectionLineType.SmoothStep,
};

export function SystemCanvas({ nodes: initialNodes, edges: initialEdges }: SystemCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const proOptions = { hideAttribution: true };

  const defaultEdgeOptions = useMemo(
    () => ({
      ...edgeOptions,
    }),
    []
  );

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        connectionLineType={ConnectionLineType.SmoothStep}
        fitView
        proOptions={proOptions}
        minZoom={0.2}
        maxZoom={1.5}
        className="bg-[var(--background)]"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="var(--background-tertiary)"
        />
        <Controls
          className="bg-[var(--background-secondary)] border border-[var(--background-tertiary)] rounded-lg"
        />
        <MiniMap
          nodeColor={(node) => {
            const colors: Record<string, string> = {
              sensor: 'var(--accent-cyan)',
              kafka: 'var(--accent-orange)',
              consumer: 'var(--accent-green)',
              database: 'var(--accent-purple)',
              dashboard: 'var(--accent-cyan)',
              twin: '#ec4899',
            };
            return colors[node.type || 'sensor'] || 'var(--accent-cyan)';
          }}
          className="bg-[var(--background-secondary)] border border-[var(--background-tertiary)] rounded-lg"
          maskColor="rgba(10, 15, 26, 0.7)"
        />
      </ReactFlow>
    </div>
  );
}
