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
      <div className="flex items-center justify-center p-12 bg-slate-900/60 rounded-xl border border-slate-800">
        <div className="flex items-center space-x-3 text-rose-400">
          <RefreshCw className="w-5 h-5 animate-spin" />
          <span className="text-sm font-medium">Analyzing dependency cycles (Tarjan SCC)...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-slate-900/60 rounded-xl border border-slate-800 text-slate-400 text-sm">
        {error || "No circular dependency data available."}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Cap Reached Warning Alert */}
      {data.cycle_cap_reached && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-start space-x-3 text-amber-300">
          <AlertTriangle className="w-5 h-5 shrink-0 text-amber-400 mt-0.5" />
          <div className="text-xs space-y-1">
            <span className="font-semibold block text-sm text-amber-200">
              Cycle Detection Cap Reached (100 cycles)
            </span>
            <span>
              This repository contains dense cyclical relationships. Cycle enumeration was capped at 100 to prevent exponential path explosion and guarantee predictable response times.
            </span>
          </div>
        </div>
      )}

      {/* Zero Cycles Clean State */}
      {data.total_cycles === 0 ? (
        <div className="p-8 bg-slate-900/80 border border-emerald-500/30 rounded-xl text-center space-y-3">
          <div className="w-12 h-12 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto text-emerald-400">
            <ShieldCheck className="w-7 h-7" />
          </div>
          <h3 className="text-base font-semibold text-slate-100">
            Clean Architecture: No Circular Dependencies Detected
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            The internal module graph is a strictly Directed Acyclic Graph (DAG). There are no mutual or transitive circular dependencies between files.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Header Bar */}
          <div className="flex items-center justify-between bg-slate-900/80 border border-slate-800 px-4 py-3 rounded-xl">
            <div className="flex items-center space-x-2 text-rose-400">
              <RotateCcw className="w-4 h-4" />
              <span className="text-sm font-semibold text-slate-200">
                {data.total_cycles} Circular {data.total_cycles === 1 ? "Dependency" : "Dependencies"} Detected
              </span>
            </div>
            <span className="text-xs font-mono text-slate-400">
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
                  className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-xl p-4 transition space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold font-mono bg-rose-500/20 text-rose-300 border border-rose-500/30">
                        Cycle #{cycle.cycle_id}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">
                        {cycle.length}-file loop
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => setExpandedCycle(isExpanded ? null : cycle.cycle_id)}
                      className="text-xs text-slate-400 hover:text-slate-200 font-mono"
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
                          className="px-2.5 py-1 rounded bg-slate-950 border border-rose-500/30 text-rose-200 hover:bg-rose-500/10 hover:border-rose-500/60 transition text-[11px] truncate max-w-[260px]"
                          title={filePath}
                        >
                          {filePath}
                        </button>
                        <ArrowRight className="w-3.5 h-3.5 text-rose-400/80 shrink-0" />
                      </React.Fragment>
                    ))}
                    <span className="px-2 py-0.5 rounded bg-rose-950/60 border border-rose-500/40 text-rose-300 text-[10px] font-bold">
                      LOOP CLOSED
                    </span>
                  </div>

                  {/* Expanded Edges View */}
                  {isExpanded && cycle.edges && (
                    <div className="mt-3 pt-3 border-t border-slate-800 text-[11px] font-mono space-y-1.5 text-slate-400">
                      <span className="text-xs text-slate-300 font-semibold uppercase tracking-wider block mb-1">
                        Coupled Edges:
                      </span>
                      {cycle.edges.map((edge, eIdx) => (
                        <div key={eIdx} className="flex items-center space-x-2 pl-2">
                          <span className="text-slate-300 truncate max-w-[240px]">{edge.source}</span>
                          <span className="text-rose-400 font-bold">&rarr;</span>
                          <span className="text-slate-300 truncate max-w-[240px]">{edge.target}</span>
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
