import React, { useState, useEffect } from "react";
import {
  Flame,
  LayoutGrid,
  List,
  Info,
} from "lucide-react";
import { HotspotItem } from "../types/api";
import { apiService } from "../services/api";

interface HotspotsViewProps {
  analysisId: string;
}

export const HotspotsView: React.FC<HotspotsViewProps> = ({ analysisId }) => {
  const [hotspots, setHotspots] = useState<HotspotItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"list" | "scatter">("list");
  const [selectedHotspot, setSelectedHotspot] = useState<HotspotItem | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    apiService
      .getHotspots(analysisId, 10)
      .then((data) => {
        if (isMounted) {
          setHotspots(data.hotspots);
          if (data.hotspots.length > 0) {
            setSelectedHotspot(data.hotspots[0]);
          }
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.response?.data?.detail || "Failed to load codebase hotspots");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [analysisId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-slate-900 border border-slate-800 rounded-xl">
        <div className="w-10 h-10 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-slate-400 text-sm">Evaluating multi-metric hotspot risk scores...</p>
      </div>
    );
  }

  if (error || hotspots.length === 0) {
    return (
      <div className="p-8 bg-slate-900 border border-slate-800 rounded-xl text-center">
        <Flame className="w-10 h-10 text-slate-500 mx-auto mb-3" />
        <h3 className="text-lg font-semibold text-slate-200 mb-1">No Hotspots Found</h3>
        <p className="text-slate-400 text-sm">{error || "No high-risk hotspots detected in this codebase."}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-6">
      {/* Header and Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-5 bg-slate-900 border border-slate-800 rounded-xl">
        <div>
          <div className="flex items-center space-x-2">
            <Flame className="w-6 h-6 text-amber-500" />
            <h2 className="text-xl font-bold text-white">Hotspots Intelligence Matrix</h2>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic risk prioritization combining Complexity Risk (40%), Architectural Centrality (35%), and Issue Severity Burden (25%).
          </p>
        </div>

        {/* View Mode Toggle */}
        <div className="inline-flex rounded-lg p-0.5 bg-slate-800 border border-slate-700">
          <button
            onClick={() => setViewMode("list")}
            className={`flex items-center px-3 py-1.5 text-xs font-medium rounded-md transition ${
              viewMode === "list" ? "bg-amber-500 text-slate-950 font-bold shadow-sm" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <List className="w-3.5 h-3.5 mr-1.5" />
            Top 10 List
          </button>
          <button
            onClick={() => setViewMode("scatter")}
            className={`flex items-center px-3 py-1.5 text-xs font-medium rounded-md transition ${
              viewMode === "scatter" ? "bg-amber-500 text-slate-950 font-bold shadow-sm" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <LayoutGrid className="w-3.5 h-3.5 mr-1.5" />
            2D Risk Matrix
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {viewMode === "list" ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Hotspots List (Left 2 cols) */}
          <div className="lg:col-span-2 space-y-3">
            {hotspots.map((item) => {
              const isSelected = selectedHotspot?.file_path === item.file_path;
              return (
                <div
                  key={item.file_path}
                  onClick={() => setSelectedHotspot(item)}
                  className={`p-4 rounded-xl border transition cursor-pointer ${
                    isSelected
                      ? "bg-slate-800/90 border-amber-500/80 ring-1 ring-amber-500/50"
                      : "bg-slate-900 border-slate-800 hover:bg-slate-800/50 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start space-x-3">
                      <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center shrink-0 mt-0.5">
                        <span className="font-bold text-amber-400 text-xs">#{item.rank}</span>
                      </div>
                      <div>
                        <h4 className="font-semibold text-sm text-slate-100 font-mono break-all">
                          {item.file_path}
                        </h4>
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs text-slate-400">
                          <span>{item.sloc.toLocaleString()} SLOC</span>
                          <span>•</span>
                          <span>Max CC: {item.max_cyclomatic_complexity}</span>
                          <span>•</span>
                          <span>Fan-In: {item.fan_in}</span>
                          <span>•</span>
                          <span>Fan-Out: {item.fan_out}</span>
                          <span>•</span>
                          <span className={item.issues_count > 0 ? "text-rose-400 font-medium" : ""}>
                            {item.issues_count} issues
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Composite Score Badge */}
                    <div className="text-right shrink-0">
                      <span
                        className={`inline-block px-2.5 py-1 rounded-full text-xs font-bold ${
                          item.hotspot_score >= 70
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                            : item.hotspot_score >= 40
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                            : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                        }`}
                      >
                        H: {item.hotspot_score.toFixed(1)}
                      </span>
                    </div>
                  </div>

                  {/* Sub-scores Progress Bars */}
                  <div className="grid grid-cols-3 gap-3 mt-3 pt-3 border-t border-slate-800/80">
                    <div>
                      <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                        <span>Complexity Risk</span>
                        <span className="font-mono text-slate-300">{item.complexity_risk.toFixed(1)}</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-500 rounded-full"
                          style={{ width: `${item.complexity_risk}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                        <span>Centrality</span>
                        <span className="font-mono text-slate-300">{item.architectural_centrality.toFixed(1)}</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-cyan-500 rounded-full"
                          style={{ width: `${item.architectural_centrality}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                        <span>Issue Burden</span>
                        <span className="font-mono text-slate-300">{item.issue_severity_burden.toFixed(1)}</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-rose-500 rounded-full"
                          style={{ width: `${item.issue_severity_burden}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Selected Hotspot Detail Card (Right 1 col) */}
          <div className="space-y-6">
            {selectedHotspot ? (
              <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl sticky top-6 space-y-4">
                <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
                  <Flame className="w-5 h-5 text-amber-500" />
                  <h3 className="font-bold text-white text-base">Hotspot Deep-Dive</h3>
                </div>

                <div>
                  <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">File Path</span>
                  <p className="text-sm font-mono text-slate-200 break-all bg-slate-950 p-2 rounded mt-1 border border-slate-800">
                    {selectedHotspot.file_path}
                  </p>
                </div>

                <div className="bg-slate-950/70 p-3.5 rounded-lg border border-slate-800">
                  <span className="text-xs text-slate-400">Composite Hotspot Score (H)</span>
                  <div className="flex items-baseline space-x-2 mt-1">
                    <span className="text-3xl font-extrabold text-amber-400">
                      {selectedHotspot.hotspot_score.toFixed(1)}
                    </span>
                    <span className="text-xs text-slate-500">/ 100.0</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    Fuses 40% Complexity Risk ({selectedHotspot.complexity_risk.toFixed(1)}), 35% Centrality ({selectedHotspot.architectural_centrality.toFixed(1)}), and 25% Issue Burden ({selectedHotspot.issue_severity_burden.toFixed(1)}).
                  </p>
                </div>

                <div className="space-y-2">
                  <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Diagnostic Burden</span>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2 rounded bg-slate-950 border border-slate-800">
                      <span className="text-slate-400">Blockers:</span>{" "}
                      <span className="font-bold text-rose-400">{selectedHotspot.blocker_count}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-950 border border-slate-800">
                      <span className="text-slate-400">Critical:</span>{" "}
                      <span className="font-bold text-rose-300">{selectedHotspot.critical_count}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-950 border border-slate-800">
                      <span className="text-slate-400">Major:</span>{" "}
                      <span className="font-bold text-amber-400">{selectedHotspot.major_count}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-950 border border-slate-800">
                      <span className="text-slate-400">Minor:</span>{" "}
                      <span className="font-bold text-blue-400">{selectedHotspot.minor_count}</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-2 pt-2 border-t border-slate-800 text-xs text-slate-400">
                  <div className="flex justify-between">
                    <span>Source Lines (SLOC):</span>
                    <span className="font-medium text-slate-200">{selectedHotspot.sloc.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Max Cyclomatic Complexity:</span>
                    <span className="font-medium text-slate-200">{selectedHotspot.max_cyclomatic_complexity}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Max Nesting Depth:</span>
                    <span className="font-medium text-slate-200">{selectedHotspot.max_nesting_depth}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Incoming Dependents (Fan-In):</span>
                    <span className="font-medium text-slate-200">{selectedHotspot.fan_in}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Outgoing Dependencies (Fan-Out):</span>
                    <span className="font-medium text-slate-200">{selectedHotspot.fan_out}</span>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : (
        /* 2D Scatter Matrix View */
        <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center">
              <Info className="w-4 h-4 mr-1 text-slate-500" />
              X = Architectural Centrality ($A_{'{norm}'}$) | Y = Complexity Risk ($C_{'{norm}'}$) | Radius = SLOC
            </span>
            <span className="text-amber-400 font-medium">Upper-Right quadrant indicates highest systemic danger</span>
          </div>

          <div className="relative w-full h-[520px] bg-slate-950 rounded-lg p-8 border border-slate-800">
            {/* SVG Scatter Plot */}
            <svg viewBox="0 0 100 100" className="w-full h-full overflow-visible">
              {/* Quadrant Divider Lines */}
              <line x1="50" y1="0" x2="50" y2="100" stroke="#334155" strokeDasharray="2" strokeWidth="0.5" />
              <line x1="0" y1="50" x2="100" y2="50" stroke="#334155" strokeDasharray="2" strokeWidth="0.5" />

              {/* Axis Labels */}
              <text x="50" y="106" fill="#94a3b8" fontSize="3" textAnchor="middle">
                Architectural Centrality (Fan-In / Fan-Out) →
              </text>
              <text x="-50" y="-4" fill="#94a3b8" fontSize="3" textAnchor="middle" transform="rotate(-90)">
                Complexity Risk (SLOC / CC / Nesting) →
              </text>

              {/* Hotspot Bubbles */}
              {hotspots.map((item) => {
                // Invert Y so 100 is at top
                const cx = item.architectural_centrality;
                const cy = 100 - item.complexity_risk;
                const radius = Math.min(8, Math.max(2.5, Math.sqrt(item.sloc) / 8));
                const isSelected = selectedHotspot?.file_path === item.file_path;

                return (
                  <g
                    key={item.file_path}
                    onClick={() => setSelectedHotspot(item)}
                    className="cursor-pointer transition-transform duration-200 hover:scale-110"
                  >
                    <circle
                      cx={cx}
                      cy={cy}
                      r={radius}
                      fill={
                        item.hotspot_score >= 70
                          ? "#ef4444"
                          : item.hotspot_score >= 40
                          ? "#f59e0b"
                          : "#10b981"
                      }
                      fillOpacity={isSelected ? 0.95 : 0.75}
                      stroke={isSelected ? "#ffffff" : "#0f172a"}
                      strokeWidth={isSelected ? 0.8 : 0.3}
                    />
                    <text
                      x={cx}
                      y={cy - radius - 1}
                      fill="#e2e8f0"
                      fontSize="2.5"
                      textAnchor="middle"
                      className="pointer-events-none font-mono"
                    >
                      {item.file_path.split("/").pop()} (#{item.rank})
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>
      )}
    </div>
  );
};
