import React, { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Flame,
  Search,
} from "lucide-react";
import { apiService } from "../services/api";
import { SymbolMetricItem } from "../types/api";

interface HotspotExplorerProps {
  analysisId: string;
}

export const HotspotExplorer: React.FC<HotspotExplorerProps> = ({ analysisId }) => {
  const [items, setItems] = useState<SymbolMetricItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState<number>(0);
  const [limit] = useState<number>(20);
  const [search, setSearch] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("cyclomatic_complexity");
  const [flaggedOnly, setFlaggedOnly] = useState<boolean>(false);
  const [minComplexity, setMinComplexity] = useState<string>("");

  useEffect(() => {
    let isMounted = true;
    const fetchSymbols = async () => {
      try {
        setLoading(true);
        const data = await apiService.getSymbolMetrics(analysisId, {
          skip: page * limit,
          limit,
          sort_by: sortBy,
          order: "desc",
          search: search || undefined,
          flagged_only: flaggedOnly,
          min_complexity: minComplexity ? parseInt(minComplexity, 10) : undefined,
        });
        if (isMounted) {
          setItems(data.items);
          setTotal(data.total);
          setError(null);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.response?.data?.detail || "Failed to load symbol metrics");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchSymbols();
    return () => {
      isMounted = false;
    };
  }, [analysisId, page, sortBy, search, flaggedOnly, minComplexity]);

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      {/* Header & Controls */}
      <div className="p-4 border-b border-slate-800 flex flex-col md:flex-row gap-3 justify-between items-center">
        <div className="flex items-center space-x-2">
          <Flame className="w-5 h-5 text-rose-500" />
          <div>
            <h4 className="text-sm font-semibold text-slate-200">Function & Method Complexity Hotspots</h4>
            <p className="text-xs text-slate-400 mt-0.5">Discovered {total} executable function scopes</p>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search functions..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
              className="bg-slate-950 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-slate-200 w-44 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <select
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value);
              setPage(0);
            }}
            className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="cyclomatic_complexity">Sort by Complexity</option>
            <option value="lines_of_code">Sort by Length (LOC)</option>
            <option value="nesting_depth">Sort by Max Nesting</option>
            <option value="parameter_count">Sort by Parameters</option>
          </select>

          <input
            type="number"
            placeholder="Min CC..."
            value={minComplexity}
            onChange={(e) => {
              setMinComplexity(e.target.value);
              setPage(0);
            }}
            className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 w-20 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />

          <label className="flex items-center space-x-1.5 text-slate-300 cursor-pointer bg-slate-950 border border-slate-700 px-2.5 py-1.5 rounded-lg">
            <input
              type="checkbox"
              checked={flaggedOnly}
              onChange={(e) => {
                setFlaggedOnly(e.target.checked);
                setPage(0);
              }}
              className="rounded bg-slate-800 border-slate-600 text-rose-500 focus:ring-0"
            />
            <span>Hotspots only</span>
          </label>
        </div>
      </div>

      {/* Hotspots List */}
      <div className="divide-y divide-slate-800/60">
        {loading ? (
          <div className="py-12 text-center text-slate-400">
            <Activity className="w-5 h-5 animate-spin mx-auto text-cyan-400 mb-2" />
            Loading function complexity metrics...
          </div>
        ) : error ? (
          <div className="py-12 text-center text-rose-400 text-xs">
            {error}
          </div>
        ) : items.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-xs">
            No functions or methods match the active filter criteria.
          </div>
        ) : (
          items.map((item) => {
            const isHighCC = item.cyclomatic_complexity > 10;
            const isVeryHighCC = item.cyclomatic_complexity > 20;

            return (
              <div key={item.id} className="p-4 hover:bg-slate-800/30 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
                {/* Function Details */}
                <div className="space-y-1 max-w-xl">
                  <div className="flex items-center space-x-2">
                    <span className="px-1.5 py-0.5 rounded font-mono text-[10px] uppercase font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                      {item.symbol_type}
                    </span>
                    <span className="font-semibold text-slate-100 font-mono text-sm">{item.symbol_name}</span>
                    <span className="text-slate-500 font-mono text-[11px] truncate">
                      {item.file_path}:{item.start_line}
                    </span>
                  </div>

                  {item.signature && (
                    <div className="font-mono text-slate-400 text-[11px] bg-slate-950/60 px-2 py-1 rounded border border-slate-800/80 truncate">
                      {item.signature}
                    </div>
                  )}

                  {/* Quality Flags / Findings */}
                  {item.quality_flags && item.quality_flags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {item.quality_flags.map((flag, fIdx) => (
                        <span
                          key={fIdx}
                          title={flag.description}
                          className={`flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                            flag.severity === "CRITICAL"
                              ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                              : flag.severity === "HIGH"
                              ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                              : "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                          }`}
                        >
                          <AlertTriangle className="w-3 h-3" />
                          <span>{flag.flag}: {flag.description}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Metric Badges */}
                <div className="flex items-center space-x-3 self-start md:self-auto shrink-0 pt-2 md:pt-0">
                  <div className="text-center px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 min-w-[64px]">
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">Complexity</div>
                    <div
                      className={`text-base font-bold ${
                        isVeryHighCC
                          ? "text-rose-400"
                          : isHighCC
                          ? "text-amber-400"
                          : "text-emerald-400"
                      }`}
                    >
                      {item.cyclomatic_complexity}
                    </div>
                  </div>

                  <div className="text-center px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-800 min-w-[56px]">
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">LOC</div>
                    <div className="text-sm font-semibold text-slate-200">{item.lines_of_code}</div>
                  </div>

                  <div className="text-center px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-800 min-w-[56px]">
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">Nesting</div>
                    <div className="text-sm font-semibold text-slate-200">{item.nesting_depth}</div>
                  </div>

                  <div className="text-center px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-800 min-w-[56px]">
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">Params</div>
                    <div className="text-sm font-semibold text-slate-200">{item.parameter_count}</div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="p-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <div>
            Page {page + 1} of {totalPages}
          </div>
          <div className="flex space-x-2">
            <button
              disabled={page === 0}
              onClick={() => setPage(page - 1)}
              className="px-2.5 py-1 bg-slate-800 rounded hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed text-slate-200"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages - 1}
              onClick={() => setPage(page + 1)}
              className="px-2.5 py-1 bg-slate-800 rounded hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed text-slate-200"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
