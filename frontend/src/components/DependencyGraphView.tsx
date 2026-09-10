import React, { useState, useEffect, useRef, useMemo } from 'react';
import { DependencyGraphNode, DependencyGraphEdge } from '../types/api';
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

interface DependencyGraphViewProps {
  nodes: DependencyGraphNode[];
  edges: DependencyGraphEdge[];
  onSelectFile?: (fileId: string) => void;
  selectedFileId?: string | null;
}

interface SimNode extends DependencyGraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

export const DependencyGraphView: React.FC<DependencyGraphViewProps> = ({
  nodes,
  edges,
  onSelectFile,
  selectedFileId,
}) => {
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDraggingPan, setIsDraggingPan] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null);

  const svgRef = useRef<SVGSVGElement | null>(null);
  const width = 800;
  const height = 550;

  // Initialize nodes with 2D positions in a circle or force simulation
  const [simNodes, setSimNodes] = useState<SimNode[]>([]);

  useEffect(() => {
    const count = nodes.length;
    if (count === 0) {
      setSimNodes([]);
      return;
    }

    const radius = Math.min(width, height) * 0.38;
    const initial: SimNode[] = nodes.map((node, i) => {
      const angle = (2 * Math.PI * i) / count;
      return {
        ...node,
        x: width / 2 + radius * Math.cos(angle) + (Math.random() - 0.5) * 40,
        y: height / 2 + radius * Math.sin(angle) + (Math.random() - 0.5) * 40,
        vx: 0,
        vy: 0,
      };
    });

    // Run simple spring simulation steps to disperse nodes nicely
    for (let iter = 0; iter < 45; iter++) {
      // Repulsion between nodes
      for (let i = 0; i < initial.length; i++) {
        for (let j = i + 1; j < initial.length; j++) {
          const dx = initial[j].x - initial[i].x;
          const dy = initial[j].y - initial[i].y;
          const distSq = dx * dx + dy * dy || 1;
          const dist = Math.sqrt(distSq);
          if (dist < 200) {
            const force = 800 / (distSq + 10);
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            initial[i].x -= fx;
            initial[i].y -= fy;
            initial[j].x += fx;
            initial[j].y += fy;
          }
        }
      }

      // Edge spring attraction
      for (const edge of edges) {
        const src = initial.find((n) => n.id === edge.source);
        const tgt = initial.find((n) => n.id === edge.target);
        if (src && tgt) {
          const dx = tgt.x - src.x;
          const dy = tgt.y - src.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const targetDist = 90;
          const force = (dist - targetDist) * 0.04;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          src.x += fx;
          src.y += fy;
          tgt.x -= fx;
          tgt.y -= fy;
        }
      }

      // Center gravity
      for (const n of initial) {
        n.x += (width / 2 - n.x) * 0.03;
        n.y += (height / 2 - n.y) * 0.03;
      }
    }

    setSimNodes(initial);
  }, [nodes, edges]);

  // Quick lookup map of node positions
  const nodePosMap = useMemo(() => {
    const map = new Map<string, SimNode>();
    for (const n of simNodes) {
      map.set(n.id, n);
    }
    return map;
  }, [simNodes]);

  // Active focus: selected or hovered
  const activeNodeId = hoveredNodeId || selectedFileId;

  // Determine which edges and nodes are connected to the active node
  const { connectedNodeIds, connectedEdgeIds } = useMemo(() => {
    const cNodes = new Set<string>();
    const cEdges = new Set<string>();
    if (activeNodeId) {
      cNodes.add(activeNodeId);
      for (const e of edges) {
        if (e.source === activeNodeId || e.target === activeNodeId) {
          cNodes.add(e.source);
          cNodes.add(e.target);
          cEdges.add(e.id);
        }
      }
    }
    return { connectedNodeIds: cNodes, connectedEdgeIds: cEdges };
  }, [activeNodeId, edges]);

  // Mouse pan handlers
  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    if (e.button === 0 && !draggedNodeId) {
      setIsDraggingPan(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (isDraggingPan) {
      setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
    } else if (draggedNodeId) {
      // Drag individual node
      const rect = svgRef.current?.getBoundingClientRect();
      if (rect) {
        const mouseX = (e.clientX - rect.left - pan.x) / zoom;
        const mouseY = (e.clientY - rect.top - pan.y) / zoom;
        setSimNodes((prev) =>
          prev.map((n) => (n.id === draggedNodeId ? { ...n, x: mouseX, y: mouseY } : n))
        );
      }
    }
  };

  const handleMouseUp = () => {
    setIsDraggingPan(false);
    setDraggedNodeId(null);
  };

  const getNodeColor = (node: DependencyGraphNode) => {
    if (node.in_cycle) return '#ef4444'; // Red for cycles
    const lang = (node.language || '').toLowerCase();
    if (lang === 'python') return '#3b82f6'; // Blue
    if (lang === 'typescript') return '#0284c7'; // Sky
    if (lang === 'javascript') return '#f59e0b'; // Amber
    return '#6b7280'; // Gray
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden flex flex-col">
      {/* Controls toolbar */}
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex flex-wrap items-center justify-between gap-3 text-sm">
        <div className="flex items-center space-x-4">
          <span className="font-semibold text-gray-700">Directed Dependency Graph</span>
          <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
            {nodes.length} nodes · {edges.length} edges
          </span>
          <span className="text-xs text-gray-400">Arrow points from importer → imported</span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setZoom((z) => Math.min(z + 0.2, 2.5))}
            className="p-1.5 text-gray-600 hover:bg-gray-200 rounded transition"
            title="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(z - 0.2, 0.4))}
            className="p-1.5 text-gray-600 hover:bg-gray-200 rounded transition"
            title="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              setZoom(1);
              setPan({ x: 0, y: 0 });
            }}
            className="p-1.5 text-gray-600 hover:bg-gray-200 rounded transition"
            title="Reset View"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="relative w-full h-[550px] bg-slate-900 cursor-grab active:cursor-grabbing overflow-hidden">
        <svg
          ref={svgRef}
          className="w-full h-full"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <defs>
            {/* Arrowhead marker */}
            <marker
              id="arrow"
              viewBox="0 0 10 10"
              refX="18"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#94a3b8" />
            </marker>
            <marker
              id="arrow-active"
              viewBox="0 0 10 10"
              refX="18"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8" />
            </marker>
          </defs>

          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {/* Edges */}
            {edges.map((edge) => {
              const src = nodePosMap.get(edge.source);
              const tgt = nodePosMap.get(edge.target);
              if (!src || !tgt) return null;

              const isEdgeActive = activeNodeId && connectedEdgeIds.has(edge.id);
              const isDimmed = activeNodeId && !isEdgeActive;

              return (
                <line
                  key={edge.id}
                  x1={src.x}
                  y1={src.y}
                  x2={tgt.x}
                  y2={tgt.y}
                  stroke={isEdgeActive ? '#38bdf8' : '#475569'}
                  strokeWidth={isEdgeActive ? 2.5 : 1.2}
                  strokeOpacity={isDimmed ? 0.15 : isEdgeActive ? 0.95 : 0.45}
                  markerEnd={isEdgeActive ? 'url(#arrow-active)' : 'url(#arrow)'}
                />
              );
            })}

            {/* Nodes */}
            {simNodes.map((node) => {
              const isNodeActive = activeNodeId && connectedNodeIds.has(node.id);
              const isSelected = selectedFileId === node.id;
              const isDimmed = activeNodeId && !isNodeActive;
              const nodeColor = getNodeColor(node);
              const radius = Math.max(7, Math.min(18, 7 + node.fan_in * 1.5));

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  className="cursor-pointer transition-opacity duration-150"
                  opacity={isDimmed ? 0.25 : 1}
                  onMouseEnter={() => setHoveredNodeId(node.id)}
                  onMouseLeave={() => setHoveredNodeId(null)}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onSelectFile) onSelectFile(node.id);
                  }}
                  onMouseDown={(e) => {
                    e.stopPropagation();
                    setDraggedNodeId(node.id);
                  }}
                >
                  {/* Outer glow ring if in cycle or selected */}
                  {(node.in_cycle || isSelected || isNodeActive) && (
                    <circle
                      r={radius + 4}
                      fill="none"
                      stroke={node.in_cycle ? '#ef4444' : '#38bdf8'}
                      strokeWidth={2}
                      strokeDasharray={node.in_cycle ? '3,3' : undefined}
                      opacity={0.8}
                    />
                  )}

                  {/* Main Circle */}
                  <circle
                    r={radius}
                    fill={nodeColor}
                    stroke="#ffffff"
                    strokeWidth={1.5}
                  />

                  {/* Node Label */}
                  <text
                    dy={radius + 12}
                    textAnchor="middle"
                    fill={isNodeActive || isSelected ? '#ffffff' : '#cbd5e1'}
                    fontSize={10}
                    fontWeight={isNodeActive || isSelected ? '600' : '400'}
                    className="select-none pointer-events-none"
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        {/* Selected file detail card overlay */}
        {activeNodeId && nodePosMap.has(activeNodeId) && (
          <div className="absolute top-3 right-3 bg-slate-800/95 backdrop-blur text-white border border-slate-700 p-3 rounded-lg shadow-xl text-xs max-w-xs space-y-1.5">
            {(() => {
              const n = nodePosMap.get(activeNodeId)!;
              return (
                <>
                  <div className="font-semibold text-sky-400 truncate">{n.path}</div>
                  <div className="grid grid-cols-2 gap-2 text-slate-300 pt-1 border-t border-slate-700">
                    <div>Fan-In: <span className="text-white font-mono">{n.fan_in}</span></div>
                    <div>Fan-Out: <span className="text-white font-mono">{n.fan_out}</span></div>
                    <div>Instability: <span className="text-white font-mono">{n.instability}</span></div>
                    <div>Cycle: <span className={n.in_cycle ? "text-red-400 font-semibold" : "text-emerald-400"}>{n.in_cycle ? 'Yes' : 'No'}</span></div>
                  </div>
                  <div className="text-[10px] text-slate-400 pt-1">
                    Click node to inspect in Change Impact Explorer
                  </div>
                </>
              );
            })()}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 flex flex-wrap items-center gap-4 text-xs text-gray-600">
        <span className="font-medium text-gray-500">Legend:</span>
        <div className="flex items-center space-x-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" />
          <span>Python</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-sky-600 inline-block" />
          <span>TypeScript</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
          <span>JavaScript</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block ring-2 ring-red-300" />
          <span>In Cycle</span>
        </div>
        <span className="text-gray-400">| Circle radius proportional to Fan-In</span>
      </div>
    </div>
  );
};
