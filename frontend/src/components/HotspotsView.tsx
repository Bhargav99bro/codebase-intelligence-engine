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
      <div className="flex flex-col items-center justify-center p-12 bg-white border border-slate-200 rounded-lg shadow-sm">
        <div className="w-8 h-8 border-3 border-amber-500 border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-slate-600 text-xs">Evaluating multi-metric hotspot risk scores...</p>
      </div>
    );
  }

  if (error || hotspots.length === 0) {
    return (
      <div className="p-8 bg-white border border-slate-200 rounded-lg text-center shadow-sm">
        <Flame className="w-8 h-8 text-slate-400 mx-auto mb-2" />
        <h3 className="text-sm font-semibold text-slate-900 mb-1">No Hotspots Found</h3>
        <p className="text-slate-500 text-xs">{error || "No high-risk hotspots detected in this codebase."}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-6">
      {/* Header and Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-white border border-slate-200 rounded-lg shadow-sm">
        <div>
          <div className="flex items-center space-x-2">
            <Flame className="w-5 h-5 text-amber-500" />
            <h2 className="text-base font-bold text-slate-900">Hotspots Intelligence Matrix</h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Deterministic risk prioritization combining Complexity Risk (40%), Architectural Centrality (35%), and Issue Severity Burden (25%).
          </p>
        </div>

        {/* View Mode Toggle */}
        <div className="inline-flex rounded-md p-0.5 bg-slate-100 border border-slate-200">
          <button
            onClick={() => setViewMode("list")}
            className={`flex items-center px-3 py-1 text-xs font-medium rounded transition ${
              viewMode === "list" ? "bg-white text-slate-900 font-bold shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <List className="w-3.5 h-3.5 mr-1.5" />
            Top 10 List
          </button>
          <button
            onClick={() => setViewMode("scatter")}
            className={`flex items-center px-3 py-1 text-xs font-medium rounded transition ${
              viewMode === "scatter" ? "bg-white text-slate-900 font-bold shadow-sm" : "text-slate-600 hover:text-slate-900"
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
                  className={`p-4 rounded-lg border transition cursor-pointer shadow-sm ${
                    isSelected
                      ? "bg-amber-50/40 border-amber-400 ring-1 ring-amber-300"
                      : "bg-white border-slate-200 hover:bg-slate-50/80 hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start space-x-3">
                      <div className="w-6 h-6 rounded bg-amber-50 border border-amber-200 flex items-center justify-center shrink-0 mt-0.5">
                        <span className="font-bold text-amber-700 text-xs">#{item.rank}</span>
                      </div>
                      <div>
                        <h4 className="font-semibold text-xs text-slate-900 font-mono break-all">
                          {item.file_path}
                        </h4>
                        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 mt-1 text-[11px] text-slate-500 font-mono">
                          <span>{item.sloc.toLocaleString()} SLOC</span>
                          <span>&bull;</span>
                          <span>Max CC: {item.max_cyclomatic_complexity}</span>
                          <span>&bull;</span>
                          <span>Fan-In: {item.fan_in}</span>
                          <span>&bull;</span>
                          <span>Fan-Out: {item.fan_out}</span>
                          <span>&bull;</span>
                          <span className={item.issues_count > 0 ? "text-rose-600 font-semibold" : ""}>
                            {item.issues_count} issues
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Composite Score Badge */}
                    <div className="text-right shrink-0">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded text-xs font-bold font-mono ${
                          item.hotspot_score >= 70
                            ? "bg-rose-50 text-rose-700 border border-rose-200"
                            : item.hotspot_score >= 40
                            ? "bg-amber-50 text-amber-700 border border-amber-200"
                            : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        }`}
                      >
                        H: {item.hotspot_score.toFixed(1)}
                      </span>
                    </div>
                  </div>

                  {/* Sub-scores Progress Bars */}
                  <div className="grid grid-cols-3 gap-3 mt-3 pt-3 border-t border-slate-100">
                    <div>
                      <div className="flex justify-between text-[10px] text-slate-500 uppercase font-semibold mb-1">
                        <span>Complexity</span>
                        <span className="font-mono text-slate-700">{item.complexity_risk.toFixed(1)}</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200">
                        <div
                          className="h-full bg-indigo-600 rounded-full"
                          style={{ width: `${item.complexity_risk}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[10px] text-slate-500 uppercase font-semibold mb-1">
                        <span>Centrality</span>
                        <span className="font-mono text-slate-700">{item.architectural_centrality.toFixed(1)}</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200">
                        <div
                          className="h-full bg-sky-600 rounded-full"
                          style={{ width: `${item.architectural_centrality}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[10px] text-slate-500 uppercase font-semibold mb-1">
                        <span>Issue Burden</span>
                        <span className="font-mono text-slate-700">{item.issue_severity_burden.toFixed(1)}</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200">
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
              <div className="p-4 bg-white border border-slate-200 rounded-lg sticky top-6 space-y-3.5 shadow-sm">
                <div className="flex items-center space-x-2 pb-2.5 border-b border-slate-100">
                  <Flame className="w-4 h-4 text-amber-500" />
                  <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wider">Hotspot Deep-Dive</h3>
                </div>

                <div>
                  <span className="text-[11px] text-slate-500 font-semibold uppercase tracking-wider">File Path</span>
                  <p className="text-xs font-mono text-slate-800 break-all bg-slate-50 p-2 rounded mt-1 border border-slate-200">
                    {selectedHotspot.file_path}
                  </p>
                </div>

                <div className="bg-slate-50 p-3 rounded-md border border-slate-200">
                  <span className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Composite Hotspot Score (H)</span>
                  <div className="flex items-baseline space-x-1 mt-0.5">
                    <span className="text-2xl font-bold font-mono text-amber-600">
                      {selectedHotspot.hotspot_score.toFixed(1)}
                    </span>
                    <span className="text-xs text-slate-400">/ 100.0</span>
                  </div>
                  <p className="text-[11px] text-slate-600 mt-1.5 leading-relaxed">
                    Fuses 40% Complexity Risk ({selectedHotspot.complexity_risk.toFixed(1)}), 35% Centrality ({selectedHotspot.architectural_centrality.toFixed(1)}), and 25% Issue Burden ({selectedHotspot.issue_severity_burden.toFixed(1)}).
                  </p>
                </div>

                <div className="space-y-1.5">
                  <span className="text-[11px] text-slate-500 font-semibold uppercase tracking-wider">Diagnostic Burden</span>
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="p-2 rounded bg-slate-50 border border-slate-200">
                      <span className="text-slate-500">Blockers:</span>{" "}
                      <span className="font-bold text-rose-700">{selectedHotspot.blocker_count}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-50 border border-slate-200">
                      <span className="text-slate-500">Critical:</span>{" "}
                      <span className="font-bold text-rose-600">{selectedHotspot.critical_count}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-50 border border-slate-200">
                      <span className="text-slate-500">Major:</span>{" "}
                      <span className="font-bold text-amber-700">{selectedHotspot.major_count}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-50 border border-slate-200">
                      <span className="text-slate-500">Minor:</span>{" "}
                      <span className="font-bold text-indigo-700">{selectedHotspot.minor_count}</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5 pt-2 border-t border-slate-100 text-xs text-slate-600">
                  <div className="flex justify-between">
                    <span>Source Lines (SLOC):</span>
                    <span className="font-medium font-mono text-slate-900">{selectedHotspot.sloc.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Max Cyclomatic Complexity:</span>
                    <span className="font-medium font-mono text-slate-900">{selectedHotspot.max_cyclomatic_complexity}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Max Nesting Depth:</span>
                    <span className="font-medium font-mono text-slate-900">{selectedHotspot.max_nesting_depth}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Incoming Dependents (Fan-In):</span>
                    <span className="font-medium font-mono text-slate-900">{selectedHotspot.fan_in}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Outgoing Dependencies (Fan-Out):</span>
                    <span className="font-medium font-mono text-slate-900">{selectedHotspot.fan_out}</span>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : (
        /* 2D Scatter Matrix View */
        <div className="p-5 bg-white border border-slate-200 rounded-lg space-y-4 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center">
              <Info className="w-4 h-4 mr-1 text-slate-400" />
              X = Architectural Centrality ($A_{'{norm}'}$) | Y = Complexity Risk ($C_{'{norm}'}$) | Radius = SLOC
            </span>
            <span className="text-amber-700 font-medium">Upper-Right quadrant indicates highest systemic danger</span>
          </div>

          <div className="relative w-full h-[520px] bg-slate-50 rounded-lg p-8 border border-slate-200">
            {/* SVG Scatter Plot */}
            <svg viewBox="0 0 100 100" className="w-full h-full overflow-visible">
              {/* Quadrant Divider Lines */}
              <line x1="50" y1="0" x2="50" y2="100" stroke="#cbd5e1" strokeDasharray="2" strokeWidth="0.5" />
              <line x1="0" y1="50" x2="100" y2="50" stroke="#cbd5e1" strokeDasharray="2" strokeWidth="0.5" />

              {/* Axis Labels */}
              <text x="50" y="106" fill="#64748b" fontSize="3" textAnchor="middle" fontWeight="500">
                Architectural Centrality (Fan-In / Fan-Out) &rarr;
              </text>
              <text x="-50" y="-4" fill="#64748b" fontSize="3" textAnchor="middle" fontWeight="500" transform="rotate(-90)">
                Complexity Risk (SLOC / CC / Nesting) &rarr;
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
                      fillOpacity={isSelected ? 0.95 : 0.8}
                      stroke={isSelected ? "#0f172a" : "#ffffff"}
                      strokeWidth={isSelected ? 0.8 : 0.4}
                    />
                    <text
                      x={cx}
                      y={cy - radius - 1}
                      fill="#1e293b"
                      fontSize="2.5"
                      fontWeight="600"
                      textAnchor="middle"
                      className="pointer-events-none font-mono select-none"
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
