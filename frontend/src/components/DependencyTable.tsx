import React, { useState, useEffect } from "react";
import {
  Search,
  ArrowRight,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  FileCode,
} from "lucide-react";
import { apiService } from "../services/api";
import { DependenciesListResponse, DependencyItem } from "../types/api";

interface DependencyTableProps {
  analysisId: string;
  onSelectFile?: (fileId: string) => void;
}

export const DependencyTable: React.FC<DependencyTableProps> = ({
  analysisId,
  onSelectFile,
}) => {
  const [data, setData] = useState<DependenciesListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter & Pagination state
  const [skip, setSkip] = useState<number>(0);
  const limit = 25;
  const [resolutionStatus, setResolutionStatus] = useState<string>("");
  const [dependencyType, setDependencyType] = useState<string>("");
  const [search, setSearch] = useState<string>("");
  const [debouncedSearch, setDebouncedSearch] = useState<string>("");

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setSkip(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    let isMounted = true;
    const fetchEdges = async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await apiService.getDependencyEdges(analysisId, {
          skip,
          limit,
          resolution_status: resolutionStatus || undefined,
          dependency_type: dependencyType || undefined,
          search: debouncedSearch || undefined,
        });
        if (isMounted) {
          setData(res);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.response?.data?.detail || "Failed to load dependencies table.");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchEdges();
    return () => {
      isMounted = false;
    };
  }, [analysisId, skip, resolutionStatus, dependencyType, debouncedSearch]);

  const totalPages = data ? Math.ceil(data.total / limit) : 0;
  const currentPage = Math.floor(skip / limit) + 1;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "internal":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            INTERNAL
          </span>
        );
      case "external":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-sky-500/20 text-sky-300 border border-sky-500/30">
            EXTERNAL
          </span>
        );
      case "unresolved":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-rose-500/20 text-rose-300 border border-rose-500/30">
            UNRESOLVED
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-slate-800 text-slate-400">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-4">
      {/* Search & Filter Toolbar */}
      <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-xl flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search source file or target module..."
            className="w-full bg-slate-950/80 border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono transition"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={resolutionStatus}
            onChange={(e) => {
              setResolutionStatus(e.target.value);
              setSkip(0);
            }}
            className="bg-slate-950/80 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500 font-mono"
          >
            <option value="">All Statuses</option>
            <option value="internal">Internal Only</option>
            <option value="external">External Only</option>
            <option value="unresolved">Unresolved Only</option>
          </select>

          <select
            value={dependencyType}
            onChange={(e) => {
              setDependencyType(e.target.value);
              setSkip(0);
            }}
            className="bg-slate-950/80 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500 font-mono"
          >
            <option value="">All Types</option>
            <option value="import">import</option>
            <option value="import_from">import_from</option>
            <option value="require">require</option>
            <option value="dynamic_import">dynamic_import</option>
            <option value="export_from">export_from</option>
            <option value="type_import">type_import</option>
          </select>
        </div>
      </div>

      {/* Table Container */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center p-12 text-cyan-400">
            <RefreshCw className="w-5 h-5 animate-spin mr-2" />
            <span className="text-xs font-medium">Loading dependency edges...</span>
          </div>
        ) : error ? (
          <div className="p-6 text-center text-rose-400 text-xs">{error}</div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs font-mono">
            No dependency relationships found matching the selected filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/90 text-slate-400 text-[11px] uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-4">Source File</th>
                  <th className="py-2.5 px-4">Target Module / Path</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-4">Imported Symbols</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {data.items.map((item: DependencyItem) => (
                  <tr
                    key={item.id}
                    className="hover:bg-slate-800/40 transition group"
                  >
                    {/* Source File */}
                    <td className="py-2.5 px-4">
                      <div className="flex items-center space-x-1.5">
                        <FileCode className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400 transition shrink-0" />
                        <span
                          className="text-slate-200 font-medium truncate max-w-[240px]"
                          title={item.source_file_path}
                        >
                          {item.source_file_path}
                        </span>
                        <span className="text-slate-500 text-[10px]">
                          :{item.line_number}
                        </span>
                      </div>
                    </td>

                    {/* Target Module */}
                    <td className="py-2.5 px-4">
                      <div className="flex items-center space-x-1.5">
                        <ArrowRight className="w-3 h-3 text-slate-600 shrink-0" />
                        <span
                          className={`truncate max-w-[260px] ${
                            item.resolution_status === "internal"
                              ? "text-emerald-300 font-medium cursor-pointer hover:underline"
                              : item.resolution_status === "external"
                              ? "text-sky-300"
                              : "text-rose-300"
                          }`}
                          title={item.target_file_path || item.target_module}
                          onClick={() => {
                            if (item.target_file_id && onSelectFile) {
                              onSelectFile(item.target_file_id);
                            }
                          }}
                        >
                          {item.target_file_path || item.target_module}
                        </span>
                      </div>
                    </td>

                    {/* Type */}
                    <td className="py-2.5 px-3">
                      <span className="text-slate-400 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800 text-[10px]">
                        {item.dependency_type}
                      </span>
                    </td>

                    {/* Status */}
                    <td className="py-2.5 px-3">
                      <div className="flex items-center space-x-1">
                        {getStatusBadge(item.resolution_status)}
                        {item.is_type_only && (
                          <span className="px-1 py-0.5 rounded text-[9px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                            TS-TYPE
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Imported Symbols */}
                    <td className="py-2.5 px-4">
                      {item.imported_symbols && item.imported_symbols.length > 0 ? (
                        <div className="flex flex-wrap gap-1 max-w-[280px]">
                          {item.imported_symbols.slice(0, 4).map((sym, idx) => (
                            <span
                              key={idx}
                              className="text-[10px] bg-slate-950 text-slate-300 px-1.5 py-0.5 rounded border border-slate-800 truncate max-w-[100px]"
                              title={sym}
                            >
                              {sym}
                            </span>
                          ))}
                          {item.imported_symbols.length > 4 && (
                            <span className="text-[10px] text-slate-500 self-center">
                              +{item.imported_symbols.length - 4} more
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-slate-600 text-[11px]">&mdash;</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {data && data.total > limit && (
          <div className="px-4 py-3 bg-slate-950/80 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <div>
              Showing {skip + 1} to {Math.min(skip + limit, data.total)} of{" "}
              <span className="font-semibold text-slate-200">{data.total}</span> edges
            </div>
            <div className="flex items-center space-x-2">
              <button
                type="button"
                disabled={skip === 0}
                onClick={() => setSkip(Math.max(0, skip - limit))}
                className="p-1 rounded bg-slate-900 border border-slate-700 disabled:opacity-30 hover:bg-slate-800 transition"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="font-mono text-slate-300">
                {currentPage} / {totalPages}
              </span>
              <button
                type="button"
                disabled={skip + limit >= data.total}
                onClick={() => setSkip(skip + limit)}
                className="p-1 rounded bg-slate-900 border border-slate-700 disabled:opacity-30 hover:bg-slate-800 transition"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
