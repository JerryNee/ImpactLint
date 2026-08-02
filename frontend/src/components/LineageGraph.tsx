import { useMemo } from "react";
import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Node,
  type NodeProps,
  type NodeTypes,
} from "@xyflow/react";
import { BarChart3, Box, Database, Workflow } from "lucide-react";

import type { Asset, GraphEdge } from "../types";

interface AssetNodeData extends Record<string, unknown> {
  asset: Asset;
  affected: boolean;
}

function AssetNode({ data, selected }: NodeProps<Node<AssetNodeData>>) {
  const { asset, affected } = data;
  const Icon = asset.kind === "dashboard" ? BarChart3 : asset.platform === "dbt" ? Workflow : Database;
  return (
    <div className={`asset-node ${affected ? "asset-node-affected" : ""} ${selected ? "is-selected" : ""}`}>
      <Handle type="target" position={Position.Left} />
      <div className="asset-node-icon">
        <Icon aria-hidden="true" />
      </div>
      <div className="asset-node-copy">
        <strong>{asset.name.split(".").at(-1)}</strong>
        <span>{asset.platform}</span>
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes: NodeTypes = { asset: AssetNode };

interface LineageGraphProps {
  assets: Asset[];
  edges: GraphEdge[];
  affectedUrns: Set<string>;
  selectedUrn: string | null;
  onSelect: (urn: string) => void;
}

export function LineageGraph({
  assets,
  edges,
  affectedUrns,
  selectedUrn,
  onSelect,
}: LineageGraphProps) {
  const nodes = useMemo(() => {
    const byLayer = new Map<number, Asset[]>();
    for (const asset of assets) {
      byLayer.set(asset.layer, [...(byLayer.get(asset.layer) ?? []), asset]);
    }

    return [...byLayer.entries()].flatMap(([layer, layerAssets]) =>
      layerAssets.map((asset, index) => ({
        id: asset.urn,
        type: "asset",
        position: {
          x: layer * 310,
          y: index * 118 + Math.max(0, (3 - layerAssets.length) * 52),
        },
        data: { asset, affected: affectedUrns.has(asset.urn) },
        selected: selectedUrn === asset.urn,
      })),
    );
  }, [affectedUrns, assets, selectedUrn]);

  const flowEdges = useMemo(
    () =>
      edges.map((edge, index) => ({
        id: `${edge.source}-${edge.target}-${index}`,
        source: edge.source,
        target: edge.target,
        type: "smoothstep",
        animated: affectedUrns.has(edge.target),
        className: affectedUrns.has(edge.target) ? "flow-edge-affected" : "",
      })),
    [affectedUrns, edges],
  );

  if (assets.length === 0) {
    return (
      <div className="graph-empty">
        <Box aria-hidden="true" />
        <span>No lineage loaded</span>
      </div>
    );
  }

  return (
    <div className="lineage-canvas" aria-label="Data lineage graph">
      <ReactFlow
        nodes={nodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelect(node.id)}
        fitView
        fitViewOptions={{ padding: 0.18 }}
        minZoom={0.45}
        maxZoom={1.6}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        proOptions={{ hideAttribution: true }}
      >
        <Background color="var(--color-border)" gap={24} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
