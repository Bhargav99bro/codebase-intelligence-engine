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
      <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Target File Selector */}
          <div className="space-y-1.5 md:col-span-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
              <Search className="w-3.5 h-3.5 text-cyan-400" />
              <span>Target File</span>
            </label>
            <select
              value={selectedFileId}
              onChange={(e) => {
                setSelectedFileId(e.target.value);
                if (onSelectFile) onSelectFile(e.target.value);
              }}
              className="w-full bg-slate-950/90 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500 transition"
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
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
              <GitFork className="w-3.5 h-3.5 text-indigo-400" />
              <span>Traversal Direction</span>
            </label>
            <div className="grid grid-cols-2 gap-2 bg-slate-950/60 p-1 rounded-lg border border-slate-800 text-xs">
              <button
                type="button"
                onClick={() => setDirection("dependents")}
                className={`flex items-center justify-center space-x-1 py-1.5 px-2 rounded-md font-medium transition ${
                  direction === "dependents"
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="Upstream blast radius: files that depend on this target"
              >
                <ArrowUpRight className="w-3.5 h-3.5" />
                <span>Blast Radius</span>
              </button>
              <button
                type="button"
                onClick={() => setDirection("dependencies")}
                className={`flex items-center justify-center space-x-1 py-1.5 px-2 rounded-md font-medium transition ${
                  direction === "dependencies"
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
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
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400">
              <span className="flex items-center space-x-1.5">
                <Sliders className="w-3.5 h-3.5 text-amber-400" />
                <span>Max Depth</span>
              </span>
              <span className="font-mono text-cyan-400 font-bold">{maxDepth} levels</span>
            </div>
            <input
              type="range"
              min={1}
              max={10}
              value={maxDepth}
              onChange={(e) => setMaxDepth(Number(e.target.value))}
              className="w-full accent-cyan-400 cursor-pointer h-2 bg-slate-800 rounded-lg appearance-none"
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
        <div className="flex items-center justify-center p-12 bg-slate-900/60 rounded-xl border border-slate-800">
          <div className="flex items-center space-x-3 text-cyan-400">
            <RefreshCw className="w-5 h-5 animate-spin" />
            <span className="text-sm font-medium">Computing graph traversal blast radius...</span>
          </div>
        </div>
      )}

      {error && !loading && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Impact Results Summary */}
      {impactData && !loading && (
        <div className="space-y-4">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
            <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold mb-1">
                Total Affected
              </div>
              <div className="text-2xl font-bold font-mono text-white">
                {impactData.affected_files_count}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Files reachable within {impactData.max_depth} hops
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-amber-400 uppercase tracking-wider font-semibold mb-1">
                Direct (Depth 1)
              </div>
              <div className="text-2xl font-bold font-mono text-amber-300">
                {impactData.direct_count}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Immediate 1-hop dependencies
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-indigo-400 uppercase tracking-wider font-semibold mb-1">
                Transitive (Depth &gt; 1)
              </div>
              <div className="text-2xl font-bold font-mono text-indigo-300">
                {impactData.transitive_count}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Indirect downstream blast radius
              </div>
            </div>
          </div>

          {/* Impacted Files List */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Layers className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
                  {direction === "dependents"
                    ? `Blast Radius: Files Affected if ${impactData.target_file_path} Changes`
                    : `Dependency Chain: Dependencies Required by ${impactData.target_file_path}`}
                </span>
              </div>
              <span className="text-xs font-mono text-slate-400">
                {impactData.items.length} items
              </span>
            </div>

            {/* Direction Orientation Explanatory Banner */}
            <div className="px-4 py-2 bg-slate-950/60 border-b border-slate-800 text-[11px] text-slate-400 font-mono flex items-center space-x-2">
              <span className="text-slate-500 font-semibold uppercase tracking-wider">Orientation:</span>
              {direction === "dependents" ? (
                <span>
                  Change Propagation Path:{" "}
                  <span className="text-cyan-300 font-semibold">{impactData.target_file_path} (modified)</span>
                  {" "}&rarr; affects &rarr;{" "}
                  <span className="text-amber-300 font-semibold">Dependent</span>
                  <span className="text-slate-500 ml-2">
                    (Dependency import edge is reversed: Dependent imports Target)
                  </span>
                </span>
              ) : (
                <span>
                  Dependency Path:{" "}
                  <span className="text-cyan-300 font-semibold">{impactData.target_file_path}</span>
                  {" "}&rarr; requires/imports &rarr;{" "}
                  <span className="text-emerald-300 font-semibold">Dependency</span>
                </span>
              )}
            </div>

            {impactData.items.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                {direction === "dependents"
                  ? "No upstream files depend on this module (zero blast radius)."
                  : "This module has no internal dependencies."}
              </div>
            ) : (
              <div className="divide-y divide-slate-800/60 max-h-[460px] overflow-y-auto font-mono text-xs">
                {impactData.items.map((item, idx) => (
                  <div
                    key={item.file_id || idx}
                    className="p-3.5 hover:bg-slate-800/40 transition flex flex-col md:flex-row md:items-center justify-between gap-2"
                  >
                    <div className="space-y-1.5 flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            item.is_direct
                              ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                              : "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                          }`}
                        >
                          Depth {item.depth} ({item.is_direct ? "Direct" : "Transitive"})
                        </span>
                        <span className="text-slate-200 font-semibold truncate" title={item.file_path}>
                          {item.file_path}
                        </span>
                      </div>

                      {/* Relationship Path Breadcrumb */}
                      {item.relationship_path && item.relationship_path.length > 0 && (
                        <div className="flex items-center flex-wrap gap-1 text-[11px] text-slate-400">
                          <span className="text-slate-500 font-medium">
                            {direction === "dependents" ? "Change Path:" : "Import Path:"}
                          </span>
                          {item.relationship_path.map((segment, sIdx) => (
                            <React.Fragment key={sIdx}>
                              <span className="text-slate-300 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800 truncate max-w-[200px]">
                                {segment}
                              </span>
                              {sIdx < item.relationship_path.length - 1 && (
                                <span className="inline-flex items-center space-x-0.5 text-slate-500 text-[10px] font-mono shrink-0">
                                  <ArrowRight className="w-3 h-3 text-slate-500" />
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
                      className="shrink-0 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-400 text-[11px] font-medium transition self-start md:self-auto"
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
