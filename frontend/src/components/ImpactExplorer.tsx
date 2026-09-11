import React, { useState, useEffect } from "react";
import {
  GitFork,
  ArrowRight,
  Sliders,
  AlertCircle,
  RefreshCw,
  Search,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import { apiService } from "../services/api";
import { ImpactAnalysisResponse, DependencyGraphNode } from "../types/api";

interface ImpactExplorerProps {
  analysisId: string;
  initialFileId?: string | null;
  nodes?: DependencyGraphNode[];
  onSelectFile?: (fileId: string) => void;
}

export const ImpactExplorer: React.FC<ImpactExplorerProps> = ({
  analysisId,
  initialFileId,
  nodes = [],
  onSelectFile,
}) => {
  const [selectedFileId, setSelectedFileId] = useState<string>(initialFileId || "");
  const [direction, setDirection] = useState<"dependents" | "dependencies">("dependents");
  const [maxDepth, setMaxDepth] = useState<number>(3);
  const [impactData, setImpactData] = useState<ImpactAnalysisResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialFileId) {
      setSelectedFileId(initialFileId);
    } else if (nodes.length > 0 && !selectedFileId) {
      const sorted = [...nodes].sort((a, b) => b.fan_in - a.fan_in);
      if (sorted[0]) {
        setSelectedFileId(sorted[0].id);
      }
    }
  }, [initialFileId, nodes]);

  useEffect(() => {
    if (!selectedFileId) return;

    let isMounted = true;
    const fetchImpact = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiService.getImpactAnalysis(analysisId, selectedFileId, {
          direction,
          max_depth: maxDepth,
        });
        if (isMounted) {
          setImpactData(data);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.response?.data?.detail || "Failed to calculate change impact.");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchImpact();
    return () => {
      isMounted = false;
    };
  }, [analysisId, selectedFileId, direction, maxDepth]);

  return (
    <div className="space-y-6">
      {/* Controls Bar */}
      <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Target File Selector */}
          <div className="space-y-1.5 md:col-span-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-700 flex items-center space-x-1.5">
              <Search className="w-3.5 h-3.5 text-indigo-600" />
              <span>Target File</span>
            </label>
            <select
              value={selectedFileId}
              onChange={(e) => {
                setSelectedFileId(e.target.value);
                if (onSelectFile) onSelectFile(e.target.value);
              }}
              className="w-full bg-white border border-slate-300 rounded-md px-3 py-2 text-xs font-mono text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition"
            >
              {nodes.length === 0 ? (
                <option value="">No files available</option>
              ) : (
                nodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.path} (in: {node.fan_in}, out: {node.fan_out})
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Direction Toggle */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-700 flex items-center space-x-1.5">
              <GitFork className="w-3.5 h-3.5 text-indigo-600" />
              <span>Traversal Direction</span>
            </label>
            <div className="grid grid-cols-2 gap-2 bg-slate-100 p-1 rounded-md border border-slate-200 text-xs">
              <button
                type="button"
                onClick={() => setDirection("dependents")}
                className={`flex items-center justify-center space-x-1 py-1.5 px-2 rounded font-medium transition ${
                  direction === "dependents"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
                title="Upstream blast radius: files that depend on this target"
              >
                <ArrowUpRight className="w-3.5 h-3.5" />
                <span>Blast Radius</span>
              </button>
              <button
                type="button"
                onClick={() => setDirection("dependencies")}
                className={`flex items-center justify-center space-x-1 py-1.5 px-2 rounded font-medium transition ${
                  direction === "dependencies"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
                title="Downstream dependencies: files that this target depends on"
              >
                <ArrowDownRight className="w-3.5 h-3.5" />
                <span>Dependencies</span>
              </button>
            </div>
          </div>

          {/* Max Depth Slider */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-700">
              <span className="flex items-center space-x-1.5">
                <Sliders className="w-3.5 h-3.5 text-slate-500" />
                <span>Max Depth</span>
              </span>
              <span className="font-mono text-indigo-600 font-bold">{maxDepth} levels</span>
            </div>
            <input
              type="range"
              min={1}
              max={10}
              value={maxDepth}
              onChange={(e) => setMaxDepth(Number(e.target.value))}
              className="w-full accent-indigo-600 cursor-pointer h-2 bg-slate-200 rounded-lg appearance-none"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>1 (Direct only)</span>
              <span>5 (Medium)</span>
              <span>10 (Deep)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Loading & Error States */}
      {loading && (
        <div className="flex items-center justify-center p-12 bg-white rounded-lg border border-slate-200">
          <div className="flex items-center space-x-3 text-indigo-600">
            <RefreshCw className="w-5 h-5 animate-spin" />
            <span className="text-xs font-medium text-slate-700">Computing graph traversal blast radius...</span>
          </div>
        </div>
      )}

      {error && !loading && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Impact Results Summary */}
      {impactData && !loading && (
        <div className="space-y-4">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
            <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
              <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold mb-1">
                Total Affected
              </div>
              <div className="text-2xl font-bold font-mono text-slate-900">
                {impactData.affected_files_count}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Files reachable within {impactData.max_depth} hops
              </div>
            </div>

            <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
              <div className="text-[11px] text-amber-700 uppercase tracking-wider font-semibold mb-1">
                Direct (Depth 1)
              </div>
              <div className="text-2xl font-bold font-mono text-amber-800">
                {impactData.direct_count}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Immediate 1-hop dependencies
              </div>
            </div>

            <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
              <div className="text-[11px] text-indigo-700 uppercase tracking-wider font-semibold mb-1">
                Transitive (Depth &gt; 1)
              </div>
              <div className="text-2xl font-bold font-mono text-indigo-800">
                {impactData.transitive_count}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Indirect downstream blast radius
              </div>
            </div>
          </div>

          {/* Impacted Files List */}
          <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Layers className="w-4 h-4 text-indigo-600" />
                <span className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
                  {direction === "dependents"
                    ? `Blast Radius: Files Affected if ${impactData.target_file_path} Changes`
                    : `Dependency Chain: Dependencies Required by ${impactData.target_file_path}`}
                </span>
              </div>
              <span className="text-xs font-mono text-slate-500">
                {impactData.items.length} items
              </span>
            </div>

            {/* Direction Orientation Explanatory Banner */}
            <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 text-[11px] text-slate-600 font-mono flex items-center space-x-2">
              <span className="text-slate-500 font-semibold uppercase tracking-wider">Orientation:</span>
              {direction === "dependents" ? (
                <span>
                  Change Propagation Path:{" "}
                  <span className="text-indigo-700 font-semibold">{impactData.target_file_path} (modified)</span>
                  {" "}&rarr; affects &rarr;{" "}
                  <span className="text-amber-800 font-semibold">Dependent</span>
                  <span className="text-slate-500 ml-2">
                    (Dependency import edge is reversed: Dependent imports Target)
                  </span>
                </span>
              ) : (
                <span>
                  Dependency Path:{" "}
                  <span className="text-indigo-700 font-semibold">{impactData.target_file_path}</span>
                  {" "}&rarr; requires/imports &rarr;{" "}
                  <span className="text-emerald-700 font-semibold">Dependency</span>
                </span>
              )}
            </div>

            {impactData.items.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs">
                {direction === "dependents"
                  ? "No upstream files depend on this module (zero blast radius)."
                  : "This module has no internal dependencies."}
              </div>
            ) : (
              <div className="divide-y divide-slate-100 max-h-[460px] overflow-y-auto font-mono text-xs">
                {impactData.items.map((item, idx) => (
                  <div
                    key={item.file_id || idx}
                    className="p-3.5 hover:bg-slate-50/80 transition flex flex-col md:flex-row md:items-center justify-between gap-2"
                  >
                    <div className="space-y-1.5 flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            item.is_direct
                              ? "bg-amber-50 text-amber-800 border border-amber-200"
                              : "bg-indigo-50 text-indigo-800 border border-indigo-200"
                          }`}
                        >
                          Depth {item.depth} ({item.is_direct ? "Direct" : "Transitive"})
                        </span>
                        <span className="text-slate-900 font-semibold truncate" title={item.file_path}>
                          {item.file_path}
                        </span>
                      </div>

                      {/* Relationship Path Breadcrumb */}
                      {item.relationship_path && item.relationship_path.length > 0 && (
                        <div className="flex items-center flex-wrap gap-1 text-[11px] text-slate-500">
                          <span className="text-slate-500 font-medium">
                            {direction === "dependents" ? "Change Path:" : "Import Path:"}
                          </span>
                          {item.relationship_path.map((segment, sIdx) => (
                            <React.Fragment key={sIdx}>
                              <span className="text-slate-800 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 truncate max-w-[200px]">
                                {segment}
                              </span>
                              {sIdx < item.relationship_path.length - 1 && (
                                <span className="inline-flex items-center space-x-0.5 text-slate-400 text-[10px] font-mono shrink-0">
                                  <ArrowRight className="w-3 h-3 text-slate-400" />
                                  <span>{direction === "dependents" ? "affects" : "requires"}</span>
                                </span>
                              )}
                            </React.Fragment>
                          ))}
                        </div>
                      )}
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        setSelectedFileId(item.file_id);
                        if (onSelectFile) onSelectFile(item.file_id);
                      }}
                      className="shrink-0 px-2.5 py-1 rounded bg-white hover:bg-slate-50 border border-slate-300 text-indigo-600 text-[11px] font-medium transition self-start md:self-auto shadow-sm"
                    >
                      Analyze Impact &rarr;
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
