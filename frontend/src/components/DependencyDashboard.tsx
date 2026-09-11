import React, { useState, useEffect } from "react";
import {
  GitFork,
  Activity,
  RotateCcw,
  ShieldCheck,
  AlertTriangle,
  Flame,
  Anchor,
  Box,
  Share2,
  RefreshCw,
} from "lucide-react";
import { apiService } from "../services/api";
import {
  DependencySummaryResponse,
  DependencyGraphResponse,
} from "../types/api";
import { DependencyGraphView } from "./DependencyGraphView";
import { ImpactExplorer } from "./ImpactExplorer";
import { CircularDependenciesView } from "./CircularDependenciesView";
import { DependencyTable } from "./DependencyTable";

interface DependencyDashboardProps {
  analysisId: string;
}

export const DependencyDashboard: React.FC<DependencyDashboardProps> = ({
  analysisId,
}) => {
  const [summary, setSummary] = useState<DependencySummaryResponse | null>(null);
  const [graphData, setGraphData] = useState<DependencyGraphResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Active sub-tab
  const [subTab, setSubTab] = useState<"graph" | "impact" | "cycles" | "edges">("graph");
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [sumRes, graphRes] = await Promise.all([
          apiService.getDependencySummary(analysisId),
          apiService.getDependencyGraph(analysisId),
        ]);
        if (isMounted) {
          setSummary(sumRes);
          setGraphData(graphRes);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(
            err.response?.data?.detail || "Failed to load dependency and architecture data."
          );
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchData();
    return () => {
      isMounted = false;
    };
  }, [analysisId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 bg-white rounded-lg border border-slate-200">
        <div className="flex items-center space-x-3 text-indigo-600">
          <RefreshCw className="w-5 h-5 animate-spin" />
          <span className="text-xs font-medium text-slate-700">
            Loading dependency & architecture intelligence...
          </span>
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="p-6 bg-white rounded-lg border border-slate-200 text-slate-600 text-xs">
        {error || "No dependency intelligence available for this repository."}
      </div>
    );
  }

  const handleSelectFile = (fileId: string) => {
    setSelectedFileId(fileId);
  };

  const handleFocusImpact = (fileId: string) => {
    setSelectedFileId(fileId);
    setSubTab("impact");
  };

  return (
    <div className="space-y-6">
      {/* Overview Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Total Dependencies */}
        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">
              Total Dependencies
            </span>
            <Share2 className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-900">
            {summary.total_dependencies.toLocaleString()}
          </div>
          <div className="text-xs text-slate-500 mt-1 flex items-center space-x-2">
            <span className="text-emerald-700 font-medium">{summary.internal_dependencies} internal</span>
            <span>&bull;</span>
            <span className="text-indigo-600 font-medium">{summary.external_dependencies} external</span>
          </div>
        </div>

        {/* Fan-In / Foundation */}
        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">
              Coupling Metrics
            </span>
            <GitFork className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-900">
            {summary.average_fan_in.toFixed(1)} <span className="text-xs font-normal text-slate-500">avg in</span>
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Max in: <span className="text-slate-900 font-bold font-mono">{summary.max_fan_in}</span> | Max out:{" "}
            <span className="text-slate-900 font-bold font-mono">{summary.max_fan_out}</span>
          </div>
        </div>

        {/* Instability */}
        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">
              Avg Instability (I)
            </span>
            <Activity className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-900">
            {summary.average_instability.toFixed(2)}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {summary.average_instability > 0.7
              ? "Volatile / Client-heavy"
              : summary.average_instability < 0.3
              ? "Stable Foundation"
              : "Balanced Architecture"}
          </div>
        </div>

        {/* Cycles */}
        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">
              Circular Deps
            </span>
            {summary.circular_dependency_count > 0 ? (
              <AlertTriangle className="w-4 h-4 text-rose-500" />
            ) : (
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
            )}
          </div>
          <div
            className={`text-2xl font-bold font-mono ${
              summary.circular_dependency_count > 0 ? "text-rose-600" : "text-emerald-700"
            }`}
          >
            {summary.circular_dependency_count}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {summary.circular_dependency_count === 0
              ? "Strict DAG hierarchy"
              : summary.cycle_cap_reached
              ? "Cap reached (100+)"
              : "Cyclical coupling detected"}
          </div>
        </div>
      </div>

      {/* Architecture Hotspot Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Core Foundation */}
        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm space-y-2">
          <div className="flex items-center space-x-1.5 text-xs font-semibold text-emerald-700 uppercase tracking-wider">
            <Anchor className="w-3.5 h-3.5" />
            <span>Core Foundation</span>
          </div>
          <p className="text-[11px] text-slate-500">
            Highly depended on by other files (High Fan-In, Low Instability).
          </p>
          <div className="space-y-1 max-h-28 overflow-y-auto">
            {summary.architecture_hotspots?.core_foundation?.length ? (
              summary.architecture_hotspots.core_foundation.map((path, idx) => (
                <div
                  key={idx}
                  onClick={() => {
                    const node = graphData?.nodes.find((n) => n.path === path);
                    if (node) handleFocusImpact(node.id);
                  }}
                  className="text-xs font-mono text-emerald-800 truncate cursor-pointer hover:underline"
                  title={`${path} — Click to analyze blast radius`}
                >
                  {path}
                </div>
              ))
            ) : (
              <span className="text-[11px] text-slate-400 font-mono">None identified</span>
            )}
          </div>
        </div>

        {/* High Coupling */}
        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm space-y-2">
          <div className="flex items-center space-x-1.5 text-xs font-semibold text-amber-700 uppercase tracking-wider">
            <Flame className="w-3.5 h-3.5" />
            <span>High Coupling</span>
          </div>
          <p className="text-[11px] text-slate-500">
            Both high fan-in and high fan-out. Prime candidates for refactoring.
          </p>
          <div className="space-y-1 max-h-28 overflow-y-auto">
            {summary.architecture_hotspots?.high_coupling?.length ? (
              summary.architecture_hotspots.high_coupling.map((path, idx) => (
                <div
                  key={idx}
                  onClick={() => {
                    const node = graphData?.nodes.find((n) => n.path === path);
                    if (node) handleFocusImpact(node.id);
                  }}
                  className="text-xs font-mono text-amber-800 truncate cursor-pointer hover:underline"
                  title={`${path} — Click to analyze blast radius`}
                >
                  {path}
                </div>
              ))
            ) : (
              <span className="text-[11px] text-slate-400 font-mono">None identified</span>
            )}
          </div>
        </div>

        {/* Cyclic Modules */}
        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm space-y-2">
          <div className="flex items-center space-x-1.5 text-xs font-semibold text-rose-700 uppercase tracking-wider">
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Cyclic Modules</span>
          </div>
          <p className="text-[11px] text-slate-500">
            Modules entangled in recursive or mutual circular imports.
          </p>
          <div className="space-y-1 max-h-28 overflow-y-auto">
            {summary.architecture_hotspots?.cyclic_modules?.length ? (
              summary.architecture_hotspots.cyclic_modules.map((path, idx) => (
                <div
                  key={idx}
                  onClick={() => setSubTab("cycles")}
                  className="text-xs font-mono text-rose-800 truncate cursor-pointer hover:underline"
                  title={`${path} — View cycles`}
                >
                  {path}
                </div>
              ))
            ) : (
              <span className="text-[11px] text-emerald-700 font-mono">0 cyclic modules</span>
            )}
          </div>
        </div>

        {/* Isolated Modules */}
        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm space-y-2">
          <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-700 uppercase tracking-wider">
            <Box className="w-3.5 h-3.5 text-slate-500" />
            <span>Isolated Modules ({summary.isolated_files_count})</span>
          </div>
          <p className="text-[11px] text-slate-500">
            Files with 0 internal incoming or outgoing dependencies.
          </p>
          <div className="space-y-1 max-h-28 overflow-y-auto">
            {summary.architecture_hotspots?.isolated_modules?.length ? (
              summary.architecture_hotspots.isolated_modules.slice(0, 5).map((path, idx) => (
                <div key={idx} className="text-xs font-mono text-slate-600 truncate" title={path}>
                  {path}
                </div>
              ))
            ) : (
              <span className="text-[11px] text-slate-400 font-mono">None identified</span>
            )}
          </div>
        </div>
      </div>

      {/* Subtab Navigation Bar */}
      <div className="border-b border-slate-200 flex items-center space-x-1">
        <button
          onClick={() => setSubTab("graph")}
          className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors ${
            subTab === "graph"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-600 hover:text-slate-900"
          }`}
        >
          Interactive Graph ({graphData?.nodes.length || 0} nodes)
        </button>

        <button
          onClick={() => setSubTab("impact")}
          className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors ${
            subTab === "impact"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-600 hover:text-slate-900"
          }`}
        >
          Change Impact & Blast Radius
        </button>

        <button
          onClick={() => setSubTab("cycles")}
          className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors ${
            subTab === "cycles"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-600 hover:text-slate-900"
          }`}
        >
          Circular Dependencies ({summary.circular_dependency_count})
        </button>

        <button
          onClick={() => setSubTab("edges")}
          className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors ${
            subTab === "edges"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-600 hover:text-slate-900"
          }`}
        >
          Dependency Edges Table
        </button>
      </div>

      {/* Subtab Content Panels */}
      {subTab === "graph" && graphData && (
        <DependencyGraphView
          nodes={graphData.nodes}
          edges={graphData.edges}
          selectedFileId={selectedFileId}
          onSelectFile={handleSelectFile}
        />
      )}

      {subTab === "impact" && (
        <ImpactExplorer
          analysisId={analysisId}
          initialFileId={selectedFileId}
          nodes={graphData?.nodes || []}
          onSelectFile={handleSelectFile}
        />
      )}

      {subTab === "cycles" && (
        <CircularDependenciesView
          analysisId={analysisId}
          onSelectFile={(filePath) => {
            const node = graphData?.nodes.find((n) => n.path === filePath);
            if (node) {
              setSelectedFileId(node.id);
              setSubTab("graph");
            }
          }}
        />
      )}

      {subTab === "edges" && (
        <DependencyTable
          analysisId={analysisId}
          onSelectFile={(fileId) => {
            setSelectedFileId(fileId);
            setSubTab("graph");
          }}
        />
      )}
    </div>
  );
};
