import React, { useEffect, useState } from "react";
import {
  Activity,
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  CheckCircle2,
  FileCode,
} from "lucide-react";
import { apiService } from "../services/api";
import { FileMetricItem } from "../types/api";

interface FileMetricsTableProps {
  analysisId: string;
}

export const FileMetricsTable: React.FC<FileMetricsTableProps> = ({ analysisId }) => {
  const [items, setItems] = useState<FileMetricItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & sorting state
  const [page, setPage] = useState<number>(0);
  const [limit] = useState<number>(20);
  const [sortBy, setSortBy] = useState<string>("total_cyclomatic_complexity");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [minComplexity, setMinComplexity] = useState<string>("");
  const [language, setLanguage] = useState<string>("");
  const [flaggedOnly, setFlaggedOnly] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    const fetchFiles = async () => {
      try {
        setLoading(true);
        const data = await apiService.getFileMetrics(analysisId, {
          skip: page * limit,
          limit,
          sort_by: sortBy,
          order,
          min_complexity: minComplexity ? parseInt(minComplexity, 10) : undefined,
          language: language || undefined,
          flagged_only: flaggedOnly,
        });
        if (isMounted) {
          setItems(data.items);
          setTotal(data.total);
          setError(null);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.response?.data?.detail || "Failed to load file metrics");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchFiles();
    return () => {
      isMounted = false;
    };
  }, [analysisId, page, sortBy, order, minComplexity, language, flaggedOnly]);

  const toggleSort = (field: string) => {
    if (sortBy === field) {
      setOrder(order === "desc" ? "asc" : "desc");
    } else {
      setSortBy(field);
      setOrder("desc");
    }
    setPage(0);
  };

  const getSortIcon = (field: string) => {
    if (sortBy !== field) return <ArrowUpDown className="w-3.5 h-3.5 opacity-40 ml-1 inline" />;
    return order === "desc" ? (
      <ArrowDown className="w-3.5 h-3.5 text-cyan-400 ml-1 inline" />
    ) : (
      <ArrowUp className="w-3.5 h-3.5 text-cyan-400 ml-1 inline" />
    );
  };

  const getMiBadge = (score: number) => {
    if (score >= 70) {
      return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">{score.toFixed(1)}</span>;
    }
    if (score >= 50) {
      return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">{score.toFixed(1)}</span>;
    }
    return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-rose-500/10 text-rose-400 border border-rose-500/30">{score.toFixed(1)}</span>;
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      {/* Table Header & Controls */}
      <div className="p-4 border-b border-slate-800 flex flex-col md:flex-row gap-3 justify-between items-center">
        <div>
          <h4 className="text-sm font-semibold text-slate-200">File Complexity & Maintainability</h4>
          <p className="text-xs text-slate-400 mt-0.5">Showing {items.length} of {total} source files</p>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <input
            type="number"
            placeholder="Min CC..."
            value={minComplexity}
            onChange={(e) => {
              setMinComplexity(e.target.value);
              setPage(0);
            }}
            className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 w-24 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />

          <select
            value={language}
            onChange={(e) => {
              setLanguage(e.target.value);
              setPage(0);
            }}
            className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="">All Languages</option>
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
          </select>

          <label className="flex items-center space-x-1.5 text-slate-300 cursor-pointer bg-slate-950 border border-slate-700 px-2.5 py-1.5 rounded-lg">
            <input
              type="checkbox"
              checked={flaggedOnly}
              onChange={(e) => {
                setFlaggedOnly(e.target.checked);
                setPage(0);
              }}
              className="rounded bg-slate-800 border-slate-600 text-cyan-500 focus:ring-0"
            />
            <span>Hotspots only</span>
          </label>
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-950/60 border-b border-slate-800 text-slate-400 font-semibold select-none">
              <th className="py-3 px-4">File Path</th>
              <th className="py-3 px-3">Lang</th>
              <th className="py-3 px-3 cursor-pointer hover:text-slate-200" onClick={() => toggleSort("sloc")}>
                SLOC {getSortIcon("sloc")}
              </th>
              <th className="py-3 px-3 cursor-pointer hover:text-slate-200" onClick={() => toggleSort("function_count")}>
                Funcs {getSortIcon("function_count")}
              </th>
              <th className="py-3 px-3 cursor-pointer hover:text-slate-200" onClick={() => toggleSort("total_cyclomatic_complexity")}>
                Total CC {getSortIcon("total_cyclomatic_complexity")}
              </th>
              <th className="py-3 px-3">Avg CC</th>
              <th className="py-3 px-3 cursor-pointer hover:text-slate-200" onClick={() => toggleSort("max_nesting_depth")}>
                Max Nest {getSortIcon("max_nesting_depth")}
              </th>
              <th className="py-3 px-3 cursor-pointer hover:text-slate-200" onClick={() => toggleSort("maintainability_score")}>
                Maintainability {getSortIcon("maintainability_score")}
              </th>
              <th className="py-3 px-4">Quality Flags</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {loading ? (
              <tr>
                <td colSpan={9} className="text-center py-8 text-slate-400">
                  <Activity className="w-5 h-5 animate-spin mx-auto text-cyan-400 mb-2" />
                  Loading file metrics...
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={9} className="text-center py-8 text-rose-400">
                  {error}
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={9} className="text-center py-8 text-slate-500">
                  No files match the specified filters.
                </td>
              </tr>
            ) : (
              items.map((file) => (
                <tr key={file.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-3 px-4 font-mono text-slate-200 truncate max-w-xs" title={file.file_path}>
                    <div className="flex items-center space-x-1.5">
                      <FileCode className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                      <span className="truncate">{file.file_path}</span>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-slate-400">{file.language || "—"}</td>
                  <td className="py-3 px-3 font-semibold text-slate-200">{file.sloc}</td>
                  <td className="py-3 px-3 text-slate-300">{file.function_count + file.method_count}</td>
                  <td className="py-3 px-3 font-bold text-cyan-400">{file.total_cyclomatic_complexity}</td>
                  <td className="py-3 px-3 text-slate-300">{file.average_cyclomatic_complexity.toFixed(1)}</td>
                  <td className="py-3 px-3 text-slate-300">
                    <span className={file.max_nesting_depth > 4 ? "text-rose-400 font-bold" : ""}>
                      {file.max_nesting_depth}
                    </span>
                  </td>
                  <td className="py-3 px-3">{getMiBadge(file.maintainability_score)}</td>
                  <td className="py-3 px-4">
                    {file.quality_flags && file.quality_flags.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {file.quality_flags.map((q, idx) => (
                          <span
                            key={idx}
                            title={q.description}
                            className={`px-1.5 py-0.5 text-[10px] font-bold rounded ${
                              q.severity === "CRITICAL" || q.severity === "HIGH"
                                ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                                : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                            }`}
                          >
                            {q.flag}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-emerald-400/80 flex items-center space-x-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span className="text-[11px]">Clean</span>
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
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
