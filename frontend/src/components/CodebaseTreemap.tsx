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
      return "#e2e8f0"; // Slate-200
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
      if (count === 0) return "#94a3b8"; // Slate-400 (clean)
      if (node.dominant_severity === "blocker" || node.dominant_severity === "critical" || count >= 4) {
        return "#ef4444"; // Rose
      }
      return "#f59e0b"; // Amber
    }

    return "#6366f1";
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
      <div className="flex flex-col items-center justify-center p-12 bg-white border border-slate-200 rounded-lg shadow-sm">
        <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-slate-600 text-xs">Computing squarified codebase treemap...</p>
      </div>
    );
  }

  if (error || !rootNode || !currentNode) {
    return (
      <div className="p-8 bg-white border border-rose-200 rounded-lg text-center shadow-sm">
        <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
        <h3 className="text-sm font-semibold text-slate-900 mb-1">Treemap Unavailable</h3>
        <p className="text-rose-600 text-xs">{error || "No data available for treemap."}</p>
      </div>
    );
  }

  return (
    <div className="relative flex flex-col bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
      {/* Top Header & Navigation Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 border-b border-slate-200 bg-slate-50">
        {/* Breadcrumb Navigation */}
        <div className="flex items-center space-x-1 overflow-x-auto text-xs py-0.5">
          <button
            onClick={() => navigateToBreadcrumb(-1)}
            className={`flex items-center px-2 py-1 rounded font-medium transition ${
              currentPath.length === 0
                ? "bg-white text-indigo-700 border border-slate-200 shadow-sm"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60"
            }`}
          >
            <Folder className="w-3.5 h-3.5 mr-1 text-slate-500" />
            root
          </button>

          {currentPath.map((seg, idx) => (
            <React.Fragment key={idx}>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <button
                onClick={() => navigateToBreadcrumb(idx)}
                className={`flex items-center px-2 py-1 rounded font-medium transition whitespace-nowrap ${
                  idx === currentPath.length - 1
                    ? "bg-white text-indigo-700 border border-slate-200 shadow-sm"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60"
                }`}
              >
                {seg}
              </button>
            </React.Fragment>
          ))}
        </div>

        {/* Color Mode Switcher */}
        <div className="flex items-center space-x-2">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Color by:</span>
          <div className="inline-flex rounded-md p-0.5 bg-slate-200/80 border border-slate-300/80">
            <button
              onClick={() => setColorMetric("maintainability")}
              className={`px-2.5 py-0.5 text-xs font-medium rounded transition ${
                colorMetric === "maintainability"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Maintainability
            </button>
            <button
              onClick={() => setColorMetric("complexity")}
              className={`px-2.5 py-0.5 text-xs font-medium rounded transition ${
                colorMetric === "complexity"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Complexity
            </button>
            <button
              onClick={() => setColorMetric("issues")}
              className={`px-2.5 py-0.5 text-xs font-medium rounded transition ${
                colorMetric === "issues"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Issues
            </button>
          </div>
        </div>
      </div>

      {/* Treemap SVG Canvas */}
      <div className="relative w-full h-[620px] bg-slate-100 p-2.5 overflow-hidden select-none">
        <svg
          viewBox="0 0 1000 1000"
          preserveAspectRatio="none"
          className="w-full h-full rounded border border-slate-200 bg-white"
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
                  stroke="#ffffff"
                  strokeWidth="1.5"
                  rx="2"
                  className="transition-all"
                />

                {/* Display label if rectangle is large enough */}
                {rect.width > 55 && rect.height > 25 && (
                  <text
                    x={rect.x + 6}
                    y={rect.y + 16}
                    fill={isDir ? "#334155" : "#ffffff"}
                    fontSize={Math.min(13, Math.max(10, rect.width / 10))}
                    fontWeight={isDir ? "600" : "500"}
                    className="pointer-events-none font-sans"
                  >
                    {child.name}
                  </text>
                )}

                {/* Display SLOC if space allows */}
                {rect.width > 60 && rect.height > 45 && (
                  <text
                    x={rect.x + 6}
                    y={rect.y + 30}
                    fill={isDir ? "#64748b" : "rgba(255, 255, 255, 0.85)"}
                    fontSize="9"
                    className="pointer-events-none font-mono"
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
          <div className="absolute bottom-4 left-4 pointer-events-none z-20 px-3.5 py-2.5 bg-white border border-slate-200 rounded-lg shadow-xl text-xs text-slate-700 max-w-sm">
            <div className="font-semibold text-slate-900 flex items-center space-x-1.5 mb-1">
              {hoveredNode.type === "directory" ? (
                <Folder className="w-3.5 h-3.5 text-indigo-600" />
              ) : (
                <FileCode className="w-3.5 h-3.5 text-indigo-600" />
              )}
              <span className="truncate font-mono">{hoveredNode.path}</span>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-slate-600 font-mono text-[11px] pt-1 border-t border-slate-100">
              <div>SLOC: <span className="font-bold text-slate-900">{hoveredNode.sloc.toLocaleString()}</span></div>
              {hoveredNode.language && <div>Lang: <span className="font-bold text-slate-900">{hoveredNode.language}</span></div>}
              {hoveredNode.maintainability_score !== null && hoveredNode.maintainability_score !== undefined && (
                <div>MI: <span className="font-bold text-slate-900">{hoveredNode.maintainability_score.toFixed(1)}</span></div>
              )}
              {hoveredNode.max_cyclomatic_complexity !== null && hoveredNode.max_cyclomatic_complexity !== undefined && (
                <div>Max CC: <span className="font-bold text-slate-900">{hoveredNode.max_cyclomatic_complexity}</span></div>
              )}
              <div>Issues: <span className="font-bold text-slate-900">{hoveredNode.issue_count ?? 0}</span></div>
            </div>
          </div>
        )}
      </div>

      {/* Legend & Stats Footer */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2.5 border-t border-slate-200 bg-slate-50 text-xs text-slate-600">
        <div className="flex items-center space-x-4">
          <span className="font-semibold text-slate-800">
            {currentNode.name === "root" ? "Total Codebase:" : `${currentNode.name}:`}
          </span>
          <span className="font-mono">{currentNode.sloc.toLocaleString()} SLOC</span>
          <span className="font-mono">{currentNode.file_count ?? currentNode.children?.length ?? 0} files/dirs</span>
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-3 text-xs">
          <span className="text-slate-500 font-medium">Legend:</span>
          {colorMetric === "maintainability" && (
            <>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-1" /> &ge;70 Good</span>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-amber-500 mr-1" /> 40–69 Moderate</span>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-rose-500 mr-1" /> &lt;40 Low</span>
            </>
          )}
          {colorMetric === "complexity" && (
            <>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-1" /> &le;5 Low</span>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-amber-500 mr-1" /> 6–15 Moderate</span>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-rose-500 mr-1" /> &gt;15 High</span>
            </>
          )}
          {colorMetric === "issues" && (
            <>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-slate-400 mr-1" /> 0 Issues</span>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-amber-500 mr-1" /> 1–3 Issues</span>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-rose-500 mr-1" /> &ge;4 or Critical</span>
            </>
          )}
        </div>
      </div>

      {/* File Details Drawer */}
      {selectedFile && (
        <div className="absolute inset-y-0 right-0 w-96 bg-white border-l border-slate-200 p-5 shadow-2xl z-30 flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200">
            <div className="flex items-center space-x-2">
              <FileCode className="w-4 h-4 text-indigo-600" />
              <h4 className="font-semibold text-slate-900 text-sm truncate max-w-[240px]">
                {selectedFile.name}
              </h4>
            </div>
            <button
              onClick={() => setSelectedFile(null)}
              className="p-1 text-slate-400 hover:text-slate-600 rounded-md hover:bg-slate-100"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="py-4 space-y-4 flex-1 overflow-y-auto">
            <div>
              <span className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">File Path</span>
              <p className="text-xs font-mono text-slate-800 break-all bg-slate-50 p-2.5 rounded mt-1 border border-slate-200">
                {selectedFile.path}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">SLOC</span>
                <p className="text-lg font-bold font-mono text-slate-900 mt-0.5">{selectedFile.sloc.toLocaleString()}</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Language</span>
                <p className="text-lg font-bold font-mono text-slate-900 mt-0.5">{selectedFile.language || "Unknown"}</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Maintainability</span>
                <p className="text-lg font-bold font-mono text-emerald-700 mt-0.5">
                  {selectedFile.maintainability_score !== null && selectedFile.maintainability_score !== undefined
                    ? selectedFile.maintainability_score.toFixed(1)
                    : "N/A"}
                </p>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Max CC</span>
                <p className="text-lg font-bold font-mono text-amber-700 mt-0.5">
                  {selectedFile.max_cyclomatic_complexity ?? "N/A"}
                </p>
              </div>
            </div>

            <div>
              <span className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">
                Detected Issues ({selectedFile.issue_count ?? 0})
              </span>
              <div className="mt-2 space-y-2">
                {selectedFile.issue_count === 0 ? (
                  <p className="text-xs text-emerald-800 bg-emerald-50 p-2.5 rounded border border-emerald-200">
                    No diagnostic issues detected in this file.
                  </p>
                ) : (
                  <p className="text-xs text-amber-800 bg-amber-50 p-2.5 rounded border border-amber-200">
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
