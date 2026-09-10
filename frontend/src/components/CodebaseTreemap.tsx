import React, { useState, useEffect, useMemo } from "react";
import {
  Folder,
  FileCode,
  ChevronRight,
  AlertTriangle,
  X,
} from "lucide-react";
import { TreemapNodeData } from "../types/api";
import { apiService } from "../services/api";

interface CodebaseTreemapProps {
  analysisId: string;
}

type ColorMetric = "maintainability" | "complexity" | "issues";

export const CodebaseTreemap: React.FC<CodebaseTreemapProps> = ({ analysisId }) => {
  const [rootNode, setRootNode] = useState<TreemapNodeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPath, setCurrentPath] = useState<string[]>([]);
  const [colorMetric, setColorMetric] = useState<ColorMetric>("maintainability");
  const [hoveredNode, setHoveredNode] = useState<TreemapNodeData | null>(null);
  const [selectedFile, setSelectedFile] = useState<TreemapNodeData | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    apiService
      .getTreemap(analysisId)
      .then((data) => {
        if (isMounted) {
          setRootNode(data.root);
          setCurrentPath([]);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.response?.data?.detail || "Failed to load codebase treemap");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [analysisId]);

  // Navigate to current subtree based on currentPath
  const currentNode = useMemo(() => {
    if (!rootNode) return null;
    let curr: TreemapNodeData = rootNode;
    for (const segment of currentPath) {
      const match = curr.children?.find((c) => c.name === segment);
      if (match && match.type === "directory") {
        curr = match;
      } else {
        break;
      }
    }
    return curr;
  }, [rootNode, currentPath]);

  // Color generator based on metric
  const getNodeColor = (node: TreemapNodeData): string => {
    if (node.type === "directory") {
      return "rgba(30, 41, 59, 0.4)"; // Slate-800
    }

    if (colorMetric === "maintainability") {
      const mi = node.maintainability_score ?? 100;
      if (mi >= 70) return "#10b981"; // Emerald-500
      if (mi >= 40) return "#f59e0b"; // Amber-500
      return "#ef4444"; // Rose-500
    }

    if (colorMetric === "complexity") {
      const cc = node.max_cyclomatic_complexity ?? 0;
      if (cc <= 5) return "#10b981"; // Low complexity: Emerald
      if (cc <= 15) return "#f59e0b"; // Moderate complexity: Amber
      return "#ef4444"; // Critical complexity: Rose
    }

    if (colorMetric === "issues") {
      const count = node.issue_count ?? 0;
      if (count === 0) return "#64748b"; // Slate-500 (clean)
      if (node.dominant_severity === "blocker" || node.dominant_severity === "critical" || count >= 4) {
        return "#ef4444"; // Rose
      }
      return "#f59e0b"; // Amber
    }

    return "#3b82f6";
  };

  const handleNodeClick = (node: TreemapNodeData) => {
    if (node.type === "directory") {
      if (node.name === "root") {
        setCurrentPath([]);
      } else {
        setCurrentPath([...currentPath, node.name]);
      }
    } else {
      setSelectedFile(node);
    }
  };

  const navigateToBreadcrumb = (index: number) => {
    if (index === -1) {
      setCurrentPath([]);
    } else {
      setCurrentPath(currentPath.slice(0, index + 1));
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-slate-900 border border-slate-800 rounded-xl">
        <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-slate-400 text-sm">Computing squarified codebase treemap...</p>
      </div>
    );
  }

  if (error || !rootNode || !currentNode) {
    return (
      <div className="p-8 bg-rose-950/20 border border-rose-900/50 rounded-xl text-center">
        <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto mb-3" />
        <h3 className="text-lg font-semibold text-rose-200 mb-1">Treemap Unavailable</h3>
        <p className="text-rose-400 text-sm">{error || "No data available for treemap."}</p>
      </div>
    );
  }

  return (
    <div className="relative flex flex-col bg-slate-900 border border-slate-800 rounded-xl shadow-xl overflow-hidden">
      {/* Top Header & Navigation Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 border-b border-slate-800 bg-slate-950/60">
        {/* Breadcrumb Navigation */}
        <div className="flex items-center space-x-1.5 overflow-x-auto text-sm py-1">
          <button
            onClick={() => navigateToBreadcrumb(-1)}
            className={`flex items-center px-2.5 py-1 rounded-md font-medium transition ${
              currentPath.length === 0
                ? "bg-slate-800 text-emerald-400"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <Folder className="w-4 h-4 mr-1.5" />
            root
          </button>

          {currentPath.map((seg, idx) => (
            <React.Fragment key={idx}>
              <ChevronRight className="w-4 h-4 text-slate-600 shrink-0" />
              <button
                onClick={() => navigateToBreadcrumb(idx)}
                className={`flex items-center px-2.5 py-1 rounded-md font-medium transition whitespace-nowrap ${
                  idx === currentPath.length - 1
                    ? "bg-slate-800 text-emerald-400"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                }`}
              >
                {seg}
              </button>
            </React.Fragment>
          ))}
        </div>

        {/* Color Mode Switcher */}
        <div className="flex items-center space-x-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Color by:</span>
          <div className="inline-flex rounded-lg p-0.5 bg-slate-800 border border-slate-700">
            <button
              onClick={() => setColorMetric("maintainability")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition ${
                colorMetric === "maintainability"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Maintainability
            </button>
            <button
              onClick={() => setColorMetric("complexity")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition ${
                colorMetric === "complexity"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Complexity
            </button>
            <button
              onClick={() => setColorMetric("issues")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition ${
                colorMetric === "issues"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Issues
            </button>
          </div>
        </div>
      </div>

      {/* Treemap SVG Canvas */}
      <div className="relative w-full h-[620px] bg-slate-950 p-3 overflow-hidden select-none">
        <svg
          viewBox="0 0 1000 1000"
          preserveAspectRatio="none"
          className="w-full h-full rounded-lg"
        >
          {currentNode.children?.map((child, idx) => {
            const rect = child.layout_rect || {
              x: child.x ?? 0,
              y: child.y ?? 0,
              width: child.width ?? 0,
              height: child.height ?? 0,
            };

            const fill = getNodeColor(child);
            const isDir = child.type === "directory";

            return (
              <g
                key={child.path || idx}
                onClick={() => handleNodeClick(child)}
                onMouseEnter={() => setHoveredNode(child)}
                onMouseLeave={() => setHoveredNode(null)}
                className="cursor-pointer transition-opacity duration-200 hover:opacity-90"
              >
                <rect
                  x={rect.x}
                  y={rect.y}
                  width={Math.max(1, rect.width)}
                  height={Math.max(1, rect.height)}
                  fill={fill}
                  stroke="#0f172a"
                  strokeWidth="1.5"
                  rx="3"
                  className="transition-all"
                />

                {/* Display label if rectangle is large enough */}
                {rect.width > 55 && rect.height > 25 && (
                  <text
                    x={rect.x + 6}
                    y={rect.y + 16}
                    fill="#ffffff"
                    fontSize={Math.min(13, Math.max(10, rect.width / 10))}
                    fontWeight={isDir ? "600" : "500"}
                    clipPath={`url(#clip-${idx})`}
                    className="pointer-events-none"
                  >
                    {child.name}
                  </text>
                )}

                {/* Display SLOC if space allows */}
                {rect.width > 60 && rect.height > 45 && (
                  <text
                    x={rect.x + 6}
                    y={rect.y + 32}
                    fill="rgba(255, 255, 255, 0.7)"
                    fontSize="10"
                    className="pointer-events-none"
                  >
                    {child.sloc.toLocaleString()} SLOC
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredNode && (
          <div className="absolute bottom-4 left-4 pointer-events-none z-20 px-3.5 py-2.5 bg-slate-900/95 backdrop-blur-md border border-slate-700 rounded-lg shadow-2xl text-xs text-slate-200 max-w-sm">
            <div className="font-semibold text-slate-100 flex items-center space-x-1.5 mb-1">
              {hoveredNode.type === "directory" ? (
                <Folder className="w-3.5 h-3.5 text-blue-400" />
              ) : (
                <FileCode className="w-3.5 h-3.5 text-emerald-400" />
              )}
              <span className="truncate">{hoveredNode.path}</span>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-slate-300">
              <div>SLOC: <span className="font-medium text-white">{hoveredNode.sloc.toLocaleString()}</span></div>
              {hoveredNode.language && <div>Lang: <span className="font-medium text-white">{hoveredNode.language}</span></div>}
              {hoveredNode.maintainability_score !== null && hoveredNode.maintainability_score !== undefined && (
                <div>MI: <span className="font-medium text-white">{hoveredNode.maintainability_score.toFixed(1)}</span></div>
              )}
              {hoveredNode.max_cyclomatic_complexity !== null && hoveredNode.max_cyclomatic_complexity !== undefined && (
                <div>Max CC: <span className="font-medium text-white">{hoveredNode.max_cyclomatic_complexity}</span></div>
              )}
              <div>Issues: <span className="font-medium text-white">{hoveredNode.issue_count ?? 0}</span></div>
            </div>
          </div>
        )}
      </div>

      {/* Legend & Stats Footer */}
      <div className="flex flex-wrap items-center justify-between px-4 py-3 border-t border-slate-800 bg-slate-950/60 text-xs text-slate-400">
        <div className="flex items-center space-x-4">
          <span className="font-medium text-slate-300">
            {currentNode.name === "root" ? "Total Codebase:" : `${currentNode.name}:`}
          </span>
          <span>{currentNode.sloc.toLocaleString()} SLOC</span>
          <span>{currentNode.file_count ?? currentNode.children?.length ?? 0} files/dirs</span>
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-3">
          <span className="text-slate-500">Legend:</span>
          {colorMetric === "maintainability" && (
            <>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-1" /> ≥70 Good</span>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-amber-500 mr-1" /> 40–69 Moderate</span>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-rose-500 mr-1" /> &lt;40 Low</span>
            </>
          )}
          {colorMetric === "complexity" && (
            <>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-1" /> ≤5 Low</span>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-amber-500 mr-1" /> 6–15 Moderate</span>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-rose-500 mr-1" /> &gt;15 High</span>
            </>
          )}
          {colorMetric === "issues" && (
            <>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-slate-500 mr-1" /> 0 Issues</span>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-amber-500 mr-1" /> 1–3 Issues</span>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-rose-500 mr-1" /> ≥4 or Critical</span>
            </>
          )}
        </div>
      </div>

      {/* File Details Drawer */}
      {selectedFile && (
        <div className="absolute inset-y-0 right-0 w-96 bg-slate-900 border-l border-slate-800 p-5 shadow-2xl z-30 flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center space-x-2">
              <FileCode className="w-5 h-5 text-emerald-400" />
              <h4 className="font-semibold text-slate-100 text-sm truncate max-w-[240px]">
                {selectedFile.name}
              </h4>
            </div>
            <button
              onClick={() => setSelectedFile(null)}
              className="p-1 text-slate-400 hover:text-slate-200 rounded-md hover:bg-slate-800"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="py-4 space-y-4 flex-1 overflow-y-auto">
            <div>
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">File Path</span>
              <p className="text-sm font-mono text-slate-200 break-all bg-slate-950/60 p-2 rounded mt-1 border border-slate-800">
                {selectedFile.path}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                <span className="text-xs text-slate-400">SLOC</span>
                <p className="text-lg font-bold text-white mt-0.5">{selectedFile.sloc.toLocaleString()}</p>
              </div>
              <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                <span className="text-xs text-slate-400">Language</span>
                <p className="text-lg font-bold text-white mt-0.5">{selectedFile.language || "Unknown"}</p>
              </div>
              <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                <span className="text-xs text-slate-400">Maintainability</span>
                <p className="text-lg font-bold text-emerald-400 mt-0.5">
                  {selectedFile.maintainability_score !== null && selectedFile.maintainability_score !== undefined
                    ? selectedFile.maintainability_score.toFixed(1)
                    : "N/A"}
                </p>
              </div>
              <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                <span className="text-xs text-slate-400">Max CC</span>
                <p className="text-lg font-bold text-amber-400 mt-0.5">
                  {selectedFile.max_cyclomatic_complexity ?? "N/A"}
                </p>
              </div>
            </div>

            <div>
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">
                Detected Issues ({selectedFile.issue_count ?? 0})
              </span>
              <div className="mt-2 space-y-2">
                {selectedFile.issue_count === 0 ? (
                  <p className="text-xs text-emerald-400 bg-emerald-950/20 p-2.5 rounded border border-emerald-900/40">
                    No diagnostic issues detected in this file.
                  </p>
                ) : (
                  <p className="text-xs text-amber-400 bg-amber-950/20 p-2.5 rounded border border-amber-900/40">
                    {selectedFile.issue_count} issues detected. Check the Issues tab for line-by-line remediations.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
