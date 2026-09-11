import React, { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart2,
  Code2,
  FileText,
  ShieldAlert,
} from "lucide-react";
import { apiService } from "../services/api";
import { RepositoryMetricsResponse } from "../types/api";

interface ComplexityDashboardProps {
  analysisId: string;
}

export const ComplexityDashboard: React.FC<ComplexityDashboardProps> = ({ analysisId }) => {
  const [metrics, setMetrics] = useState<RepositoryMetricsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        const data = await apiService.getAnalysisMetrics(analysisId);
        if (isMounted) {
          setMetrics(data);
          setError(null);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.response?.data?.detail || "Failed to load complexity metrics");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchMetrics();
    return () => {
      isMounted = false;
    };
  }, [analysisId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 bg-white rounded-lg border border-slate-200">
        <div className="flex items-center space-x-3 text-indigo-600">
          <Activity className="w-5 h-5 animate-spin" />
          <span className="text-xs font-medium text-slate-700">Loading code complexity & maintainability metrics...</span>
        </div>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="p-6 bg-white rounded-lg border border-slate-200 text-slate-600 text-xs">
        {error || "No complexity metrics available for this repository."}
      </div>
    );
  }

  const { repository_totals, averages, maximums, maintainability, complexity_distribution, quality_summary } = metrics;
  const totalFuncs = (complexity_distribution.low + complexity_distribution.moderate + complexity_distribution.high + complexity_distribution.very_high) || 1;

  const lowPct = Math.round((complexity_distribution.low / totalFuncs) * 100);
  const modPct = Math.round((complexity_distribution.moderate / totalFuncs) * 100);
  const highPct = Math.round((complexity_distribution.high / totalFuncs) * 100);
  const vhighPct = Math.round((complexity_distribution.very_high / totalFuncs) * 100);

  const getMaintainabilityColor = (score: number) => {
    if (score >= 70) return "text-emerald-700 border-emerald-200 bg-emerald-50";
    if (score >= 50) return "text-amber-700 border-amber-200 bg-amber-50";
    return "text-rose-700 border-rose-200 bg-rose-50";
  };

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Source Lines (SLOC)</span>
            <FileText className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-slate-900 font-mono">{repository_totals.total_sloc.toLocaleString()}</div>
          <div className="text-xs text-slate-500 mt-1">{repository_totals.total_files} discovered files</div>
        </div>

        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Avg Complexity (CC)</span>
            <Activity className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900 font-mono">{averages.average_cyclomatic_complexity.toFixed(1)}</div>
          <div className="text-xs text-slate-500 mt-1">Max CC: <span className="text-amber-600 font-semibold font-mono">{maximums.max_cyclomatic_complexity}</span></div>
        </div>

        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Maintainability</span>
            <ShieldAlert className="w-4 h-4 text-slate-400" />
          </div>
          <div className="flex items-baseline space-x-1.5">
            <span className="text-2xl font-bold text-slate-900 font-mono">{maintainability.score.toFixed(1)}</span>
            <span className="text-xs text-slate-400">/ 100</span>
          </div>
          <div className="mt-1.5">
            <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded border ${getMaintainabilityColor(maintainability.score)}`}>
              {maintainability.label}
            </span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Quality Hotspots</span>
            <AlertTriangle className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-bold text-rose-600 font-mono">{quality_summary.total_quality_flags}</div>
          <div className="text-xs text-slate-500 mt-1">
            {quality_summary.flagged_functions_count} functions, {quality_summary.flagged_files_count} files
          </div>
        </div>
      </div>

      {/* Secondary Metrics & Complexity Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Function Scope Metrics */}
        <div className="bg-white border border-slate-200 p-5 rounded-lg shadow-sm space-y-4">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-800 flex items-center space-x-2">
            <Code2 className="w-4 h-4 text-indigo-600" />
            <span>Structural & Scope Metrics</span>
          </h4>
          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
              <span className="text-slate-600">Functions / Methods Analyzed</span>
              <span className="font-semibold text-slate-900 font-mono">{repository_totals.total_functions + repository_totals.total_methods}</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
              <span className="text-slate-600">Average Function Length</span>
              <span className="font-semibold text-slate-900 font-mono">{averages.average_function_size.toFixed(1)} LOC</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
              <span className="text-slate-600">Largest Function</span>
              <span className="font-semibold text-amber-700 font-mono">{maximums.max_function_size} LOC</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
              <span className="text-slate-600">Average Block Nesting</span>
              <span className="font-semibold text-slate-900 font-mono">{averages.average_nesting_depth.toFixed(1)}</span>
            </div>
            <div className="flex justify-between items-center py-1.5">
              <span className="text-slate-600">Maximum Block Nesting</span>
              <span className="font-semibold text-rose-600 font-mono">{maximums.max_nesting_depth}</span>
            </div>
          </div>
        </div>

        {/* Complexity Distribution Breakdown */}
        <div className="lg:col-span-2 bg-white border border-slate-200 p-5 rounded-lg shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-800 flex items-center space-x-2">
              <BarChart2 className="w-4 h-4 text-indigo-600" />
              <span>Cyclomatic Complexity Distribution</span>
            </h4>
            <span className="text-xs text-slate-500 font-mono">{totalFuncs} scopes</span>
          </div>

          {/* Segmented Bar */}
          <div className="h-3.5 w-full bg-slate-100 rounded-full overflow-hidden flex border border-slate-200">
            <div style={{ width: `${lowPct}%` }} className="bg-emerald-500 h-full transition-all duration-500" title={`Low (1-5): ${complexity_distribution.low}`} />
            <div style={{ width: `${modPct}%` }} className="bg-sky-500 h-full transition-all duration-500" title={`Moderate (6-10): ${complexity_distribution.moderate}`} />
            <div style={{ width: `${highPct}%` }} className="bg-amber-500 h-full transition-all duration-500" title={`High (11-20): ${complexity_distribution.high}`} />
            <div style={{ width: `${vhighPct}%` }} className="bg-rose-500 h-full transition-all duration-500" title={`Critical (>20): ${complexity_distribution.very_high}`} />
          </div>

          {/* Legend Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            <div className="bg-slate-50 p-3 rounded-md border border-slate-200">
              <div className="flex items-center space-x-1.5 text-xs text-slate-600">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                <span>Low (1-5)</span>
              </div>
              <div className="text-lg font-bold text-slate-900 font-mono mt-1">{complexity_distribution.low}</div>
              <div className="text-[11px] text-slate-500">{lowPct}% of functions</div>
            </div>

            <div className="bg-slate-50 p-3 rounded-md border border-slate-200">
              <div className="flex items-center space-x-1.5 text-xs text-slate-600">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-500"></span>
                <span>Moderate (6-10)</span>
              </div>
              <div className="text-lg font-bold text-slate-900 font-mono mt-1">{complexity_distribution.moderate}</div>
              <div className="text-[11px] text-slate-500">{modPct}% of functions</div>
            </div>

            <div className="bg-slate-50 p-3 rounded-md border border-slate-200">
              <div className="flex items-center space-x-1.5 text-xs text-slate-600">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                <span>High (11-20)</span>
              </div>
              <div className="text-lg font-bold text-slate-900 font-mono mt-1">{complexity_distribution.high}</div>
              <div className="text-[11px] text-slate-500">{highPct}% of functions</div>
            </div>

            <div className="bg-slate-50 p-3 rounded-md border border-slate-200">
              <div className="flex items-center space-x-1.5 text-xs text-slate-600">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
                <span>Critical (&gt;20)</span>
              </div>
              <div className="text-lg font-bold text-slate-900 font-mono mt-1">{complexity_distribution.very_high}</div>
              <div className="text-[11px] text-slate-500">{vhighPct}% of functions</div>
            </div>
          </div>

          <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded-md border border-slate-200">
            <span className="font-semibold text-slate-800">Maintainability Indicator:</span> Computed deterministically using normalized McCabe Cyclomatic Complexity, average function LOC, and comment density on a 0–100 scale.
          </div>
        </div>
      </div>
    </div>
  );
};
