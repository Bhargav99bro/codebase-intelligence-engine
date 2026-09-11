import React, { useState, useEffect } from "react";
import {
  RotateCcw,
  AlertTriangle,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import { apiService } from "../services/api";
import { CyclesListResponse, CycleItem } from "../types/api";

interface CircularDependenciesViewProps {
  analysisId: string;
  onSelectFile?: (filePath: string) => void;
}

export const CircularDependenciesView: React.FC<CircularDependenciesViewProps> = ({
  analysisId,
  onSelectFile,
}) => {
  const [data, setData] = useState<CyclesListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedCycle, setExpandedCycle] = useState<number | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchCycles = async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await apiService.getDependencyCycles(analysisId);
        if (isMounted) {
          setData(res);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.response?.data?.detail || "Failed to load circular dependencies.");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchCycles();
    return () => {
      isMounted = false;
    };
  }, [analysisId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 bg-white rounded-lg border border-slate-200">
        <div className="flex items-center space-x-3 text-rose-600">
          <RefreshCw className="w-5 h-5 animate-spin" />
          <span className="text-xs font-medium text-slate-700">Analyzing dependency cycles (Tarjan SCC)...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-white rounded-lg border border-slate-200 text-slate-600 text-xs">
        {error || "No circular dependency data available."}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Cap Reached Warning Alert */}
      {data.cycle_cap_reached && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start space-x-3 text-amber-900 shadow-sm">
          <AlertTriangle className="w-5 h-5 shrink-0 text-amber-600 mt-0.5" />
          <div className="text-xs space-y-1">
            <span className="font-semibold block text-xs text-amber-900 uppercase tracking-wider">
              Cycle Detection Cap Reached (100 cycles)
            </span>
            <span className="text-amber-800">
              This repository contains dense cyclical relationships. Cycle enumeration was capped at 100 to prevent exponential path explosion and guarantee predictable response times.
            </span>
          </div>
        </div>
      )}

      {/* Zero Cycles Clean State */}
      {data.total_cycles === 0 ? (
        <div className="p-8 bg-white border border-emerald-200 rounded-lg text-center space-y-3 shadow-sm">
          <div className="w-10 h-10 bg-emerald-50 border border-emerald-200 rounded-full flex items-center justify-center mx-auto text-emerald-600">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-semibold text-slate-900">
            Clean Architecture: No Circular Dependencies Detected
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            The internal module graph is a strictly Directed Acyclic Graph (DAG). There are no mutual or transitive circular dependencies between files.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Header Bar */}
          <div className="flex items-center justify-between bg-white border border-slate-200 px-4 py-3 rounded-lg shadow-sm">
            <div className="flex items-center space-x-2 text-rose-600">
              <RotateCcw className="w-4 h-4" />
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-900">
                {data.total_cycles} Circular {data.total_cycles === 1 ? "Dependency" : "Dependencies"} Detected
              </span>
            </div>
            <span className="text-xs font-mono text-slate-500">
              Elementary directed cycles
            </span>
          </div>

          {/* Cycles List */}
          <div className="space-y-3">
            {data.cycles.map((cycle: CycleItem) => {
              const isExpanded = expandedCycle === cycle.cycle_id;
              return (
                <div
                  key={cycle.cycle_id}
                  className="bg-white border border-slate-200 hover:border-slate-300 rounded-lg p-4 transition shadow-sm space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold font-mono bg-rose-50 text-rose-700 border border-rose-200">
                        Cycle #{cycle.cycle_id}
                      </span>
                      <span className="text-xs text-slate-500 font-mono">
                        {cycle.length}-file loop
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => setExpandedCycle(isExpanded ? null : cycle.cycle_id)}
                      className="text-xs text-slate-600 hover:text-slate-900 font-mono font-medium"
                    >
                      {isExpanded ? "Collapse" : "Details"}
                    </button>
                  </div>

                  {/* Visual Loop Chain */}
                  <div className="flex items-center flex-wrap gap-2 pt-1 font-mono text-xs">
                    {cycle.files.map((filePath, idx) => (
                      <React.Fragment key={idx}>
                        <button
                          type="button"
                          onClick={() => onSelectFile && onSelectFile(filePath)}
                          className="px-2.5 py-1 rounded bg-slate-50 border border-slate-200 text-slate-800 hover:bg-slate-100 transition text-[11px] truncate max-w-[260px]"
                          title={filePath}
                        >
                          {filePath}
                        </button>
                        <ArrowRight className="w-3.5 h-3.5 text-rose-500 shrink-0" />
                      </React.Fragment>
                    ))}
                    <span className="px-2 py-0.5 rounded bg-rose-50 border border-rose-200 text-rose-700 text-[10px] font-bold">
                      LOOP CLOSED
                    </span>
                  </div>

                  {/* Expanded Edges View */}
                  {isExpanded && cycle.edges && (
                    <div className="mt-3 pt-3 border-t border-slate-100 text-[11px] font-mono space-y-1.5 text-slate-600 bg-slate-50 p-2.5 rounded">
                      <span className="text-xs text-slate-700 font-semibold uppercase tracking-wider block mb-1">
                        Coupled Edges:
                      </span>
                      {cycle.edges.map((edge, eIdx) => (
                        <div key={eIdx} className="flex items-center space-x-2 pl-2">
                          <span className="text-slate-800 truncate max-w-[240px]">{edge.source}</span>
                          <span className="text-rose-600 font-bold">&rarr;</span>
                          <span className="text-slate-800 truncate max-w-[240px]">{edge.target}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
