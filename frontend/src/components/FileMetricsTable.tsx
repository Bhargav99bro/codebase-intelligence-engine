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
      <ArrowDown className="w-3.5 h-3.5 text-indigo-600 ml-1 inline" />
    ) : (
      <ArrowUp className="w-3.5 h-3.5 text-indigo-600 ml-1 inline" />
    );
  };

  const getMiBadge = (score: number) => {
    if (score >= 70) {
      return <span className="px-1.5 py-0.5 text-xs font-semibold font-mono rounded bg-emerald-50 text-emerald-700 border border-emerald-200">{score.toFixed(1)}</span>;
    }
    if (score >= 50) {
      return <span className="px-1.5 py-0.5 text-xs font-semibold font-mono rounded bg-amber-50 text-amber-700 border border-amber-200">{score.toFixed(1)}</span>;
    }
    return <span className="px-1.5 py-0.5 text-xs font-semibold font-mono rounded bg-rose-50 text-rose-700 border border-rose-200">{score.toFixed(1)}</span>;
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm">
      {/* Table Header & Controls */}
      <div className="p-4 border-b border-slate-200 flex flex-col md:flex-row gap-3 justify-between items-center bg-slate-50">
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-900">File Complexity & Maintainability</h4>
          <p className="text-xs text-slate-500 mt-0.5">Showing <span className="font-mono text-slate-700">{items.length}</span> of <span className="font-mono text-slate-700">{total}</span> source files</p>
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
            className="bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-slate-900 w-24 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 font-mono transition"
          />

          <select
            value={language}
            onChange={(e) => {
              setLanguage(e.target.value);
              setPage(0);
            }}
            className="bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 font-mono"
          >
            <option value="">All Languages</option>
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
          </select>

          <label className="flex items-center space-x-1.5 text-slate-700 cursor-pointer bg-white border border-slate-300 px-2.5 py-1.5 rounded-md shadow-sm">
            <input
              type="checkbox"
              checked={flaggedOnly}
              onChange={(e) => {
                setFlaggedOnly(e.target.checked);
                setPage(0);
              }}
              className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-xs font-medium">Hotspots only</span>
          </label>
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse font-mono">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold select-none text-[11px] uppercase tracking-wider">
              <th className="py-2.5 px-4 font-sans">File Path</th>
              <th className="py-2.5 px-3 font-sans">Lang</th>
              <th className="py-2.5 px-3 font-sans cursor-pointer hover:text-slate-900" onClick={() => toggleSort("sloc")}>
                SLOC {getSortIcon("sloc")}
              </th>
              <th className="py-2.5 px-3 font-sans cursor-pointer hover:text-slate-900" onClick={() => toggleSort("function_count")}>
                Funcs {getSortIcon("function_count")}
              </th>
              <th className="py-2.5 px-3 font-sans cursor-pointer hover:text-slate-900" onClick={() => toggleSort("total_cyclomatic_complexity")}>
                Total CC {getSortIcon("total_cyclomatic_complexity")}
              </th>
              <th className="py-2.5 px-3 font-sans">Avg CC</th>
              <th className="py-2.5 px-3 font-sans cursor-pointer hover:text-slate-900" onClick={() => toggleSort("max_nesting_depth")}>
                Max Nest {getSortIcon("max_nesting_depth")}
              </th>
              <th className="py-2.5 px-3 font-sans cursor-pointer hover:text-slate-900" onClick={() => toggleSort("maintainability_score")}>
                Maintainability {getSortIcon("maintainability_score")}
              </th>
              <th className="py-2.5 px-4 font-sans">Quality Flags</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td colSpan={9} className="text-center py-8 text-slate-500 text-xs">
                  <Activity className="w-5 h-5 animate-spin mx-auto text-indigo-600 mb-2" />
                  Loading file metrics...
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={9} className="text-center py-8 text-rose-600 text-xs">
                  {error}
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={9} className="text-center py-8 text-slate-500 text-xs">
                  No files match the specified filters.
                </td>
              </tr>
            ) : (
              items.map((file) => (
                <tr key={file.id} className="hover:bg-slate-50/80 transition">
                  <td className="py-2.5 px-4 font-mono text-slate-800 truncate max-w-xs" title={file.file_path}>
                    <div className="flex items-center space-x-1.5">
                      <FileCode className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span className="truncate">{file.file_path}</span>
                    </div>
                  </td>
                  <td className="py-2.5 px-3 text-slate-500 font-sans">{file.language || "—"}</td>
                  <td className="py-2.5 px-3 font-semibold text-slate-900">{file.sloc}</td>
                  <td className="py-2.5 px-3 text-slate-700">{file.function_count + file.method_count}</td>
                  <td className="py-2.5 px-3 font-bold text-slate-900">{file.total_cyclomatic_complexity}</td>
                  <td className="py-2.5 px-3 text-slate-700">{file.average_cyclomatic_complexity.toFixed(1)}</td>
                  <td className="py-2.5 px-3 text-slate-700">
                    <span className={file.max_nesting_depth > 4 ? "text-rose-600 font-bold" : ""}>
                      {file.max_nesting_depth}
                    </span>
                  </td>
                  <td className="py-2.5 px-3">{getMiBadge(file.maintainability_score)}</td>
                  <td className="py-2.5 px-4">
                    {file.quality_flags && file.quality_flags.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {file.quality_flags.map((q, idx) => (
                          <span
                            key={idx}
                            title={q.description}
                            className={`px-1.5 py-0.5 text-[10px] font-bold rounded ${
                              q.severity === "CRITICAL" || q.severity === "HIGH"
                                ? "bg-rose-50 text-rose-700 border border-rose-200"
                                : "bg-amber-50 text-amber-700 border border-amber-200"
                            }`}
                          >
                            {q.flag}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-emerald-700 flex items-center space-x-1 font-sans">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span className="text-[11px] font-medium">Clean</span>
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
        <div className="p-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-600">
          <div>
            Page {page + 1} of {totalPages}
          </div>
          <div className="flex space-x-2">
            <button
              disabled={page === 0}
              onClick={() => setPage(page - 1)}
              className="px-2.5 py-1 bg-white border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed text-slate-700 shadow-sm"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages - 1}
              onClick={() => setPage(page + 1)}
              className="px-2.5 py-1 bg-white border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed text-slate-700 shadow-sm"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
