import React, { useEffect, useState, useMemo } from "react";
import { apiService } from "../services/api";
import { SymbolItem } from "../types/api";

interface SymbolExplorerProps {
  analysisId: string;
  totalSymbols?: number;
  symbolDistribution?: Record<string, number>;
}

const SYMBOL_TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  function: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" },
  class: { bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200" },
  method: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  import: { bg: "bg-amber-50", text: "text-amber-800", border: "border-amber-200" },
  export: { bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200" },
  interface: { bg: "bg-indigo-50", text: "text-indigo-700", border: "border-indigo-200" },
  type: { bg: "bg-cyan-50", text: "text-cyan-800", border: "border-cyan-200" },
};

export const SymbolExplorer: React.FC<SymbolExplorerProps> = ({
  analysisId,
  totalSymbols = 0,
  symbolDistribution = {},
}) => {
  const [symbols, setSymbols] = useState<SymbolItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedType, setSelectedType] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(0);
  const pageSize = 50;

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    apiService
      .getAnalysisSymbols(analysisId, {
        skip: currentPage * pageSize,
        limit: pageSize,
        symbol_type: selectedType || undefined,
        search: searchQuery.trim() || undefined,
      })
      .then((res) => {
        if (isMounted) {
          setSymbols(res.items);
          setTotalCount(res.total);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.response?.data?.detail || "Failed to load symbols");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [analysisId, selectedType, searchQuery, currentPage]);

  // Group symbols by file path
  const groupedByFile = useMemo(() => {
    const map: Record<string, SymbolItem[]> = {};
    for (const sym of symbols) {
      const fileKey = sym.file_path || "Unknown File";
      if (!map[fileKey]) {
        map[fileKey] = [];
      }
      map[fileKey].push(sym);
    }
    return map;
  }, [symbols]);

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-5 border-b border-slate-200 gap-4">
        <div>
          <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
            <svg
              className="w-4 h-4 text-indigo-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
              />
            </svg>
            Code Structure & Symbols
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Static structural AST extracted symbols across functions, classes, interfaces, and types.
          </p>
        </div>

        <div className="flex items-center gap-2.5 bg-slate-50 px-3 py-1.5 rounded-md border border-slate-200">
          <span className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">Total Symbols</span>
          <span className="text-sm font-mono font-bold text-slate-900">{totalSymbols || totalCount}</span>
        </div>
      </div>

      {/* Symbol Distribution Summary Pills */}
      {Object.keys(symbolDistribution).length > 0 && (
        <div className="mt-5 flex flex-wrap gap-1.5">
          {Object.entries(symbolDistribution).map(([type, count]) => {
            const colors = SYMBOL_TYPE_COLORS[type.toLowerCase()] || {
              bg: "bg-slate-100",
              text: "text-slate-700",
              border: "border-slate-200",
            };
            const isFilterActive = selectedType === type;
            return (
              <button
                key={type}
                onClick={() => {
                  setSelectedType(isFilterActive ? "" : type);
                  setCurrentPage(0);
                }}
                className={`px-2.5 py-1 rounded border text-xs font-mono font-medium transition flex items-center gap-1.5 ${colors.bg} ${colors.text} ${colors.border} ${
                  isFilterActive ? "ring-2 ring-indigo-500 shadow-sm" : "hover:opacity-85"
                }`}
              >
                <span className="capitalize">{type}s</span>
                <span className="bg-white/80 border border-slate-200/60 px-1 py-0.2 rounded text-[10px] font-bold">
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Controls: Search and Filter */}
      <div className="mt-4 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <input
            type="text"
            placeholder="Search symbols by name or signature..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(0);
            }}
            className="w-full bg-white border border-slate-300 rounded-md px-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
          />
          {searchQuery && (
            <button
              onClick={() => {
                setSearchQuery("");
                setCurrentPage(0);
              }}
              className="absolute right-2.5 top-2 text-xs text-slate-400 hover:text-slate-600"
            >
              ✕
            </button>
          )}
        </div>

        <select
          value={selectedType}
          onChange={(e) => {
            setSelectedType(e.target.value);
            setCurrentPage(0);
          }}
          className="bg-white border border-slate-300 rounded-md px-3 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="">All Symbol Types</option>
          <option value="class">Classes</option>
          <option value="function">Functions</option>
          <option value="method">Methods</option>
          <option value="interface">Interfaces</option>
          <option value="type">Types</option>
          <option value="import">Imports</option>
          <option value="export">Exports</option>
        </select>
      </div>

      {/* Symbol Explorer Tree Content */}
      <div className="mt-5 space-y-3">
        {loading && (
          <div className="p-8 text-center text-slate-500 text-xs animate-pulse">
            Loading extracted symbols...
          </div>
        )}

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-md text-rose-700 text-xs">
            {error}
          </div>
        )}

        {!loading && !error && Object.keys(groupedByFile).length === 0 && (
          <div className="p-8 text-center text-slate-500 text-xs bg-slate-50 rounded-md border border-slate-200">
            No symbols found matching your filter criteria.
          </div>
        )}

        {!loading &&
          !error &&
          Object.entries(groupedByFile).map(([filePath, fileSymbols]) => {
            // Organize into tree: roots and their nested children
            const idMap = new Map<string, SymbolItem>();
            fileSymbols.forEach((s) => idMap.set(s.id, s));

            const roots: SymbolItem[] = [];
            const childrenByParent = new Map<string, SymbolItem[]>();

            fileSymbols.forEach((s) => {
              if (s.parent_symbol_id && idMap.has(s.parent_symbol_id)) {
                const arr = childrenByParent.get(s.parent_symbol_id) || [];
                arr.push(s);
                childrenByParent.set(s.parent_symbol_id, arr);
              } else {
                roots.push(s);
              }
            });

            return (
              <div
                key={filePath}
                className="bg-white border border-slate-200 rounded-md overflow-hidden"
              >
                {/* File Header */}
                <div className="px-3.5 py-2 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                  <div className="flex items-center gap-2 font-mono text-xs text-slate-700">
                    <svg
                      className="w-3.5 h-3.5 text-slate-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                      />
                    </svg>
                    <span className="font-semibold text-slate-900">{filePath}</span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-600 bg-white border border-slate-200 px-2 py-0.5 rounded">
                    {fileSymbols.length} symbol{fileSymbols.length === 1 ? "" : "s"}
                  </span>
                </div>

                {/* File Symbols List */}
                <div className="p-2.5 space-y-0.5">
                  {roots.map((rootSym) => {
                    const children = childrenByParent.get(rootSym.id) || [];
                    const rootColors = SYMBOL_TYPE_COLORS[rootSym.symbol_type.toLowerCase()] || {
                      bg: "bg-slate-100",
                      text: "text-slate-700",
                      border: "border-slate-200",
                    };

                    return (
                      <div key={rootSym.id} className="space-y-0.5">
                        {/* Root Symbol Line */}
                        <div className="flex items-center justify-between py-1 px-2 rounded hover:bg-slate-50 transition group font-mono text-xs">
                          <div className="flex items-center gap-2 overflow-hidden">
                            <span
                              className={`px-1.5 py-0.2 rounded text-[9px] uppercase font-bold border ${rootColors.bg} ${rootColors.text} ${rootColors.border}`}
                            >
                              {rootSym.symbol_type}
                            </span>
                            <span className="text-slate-900 font-semibold truncate group-hover:text-indigo-600">
                              {rootSym.name}
                            </span>
                            {rootSym.signature && (
                              <span className="text-slate-400 text-[11px] truncate hidden sm:inline">
                                {rootSym.signature}
                              </span>
                            )}
                          </div>

                          <span className="text-[11px] text-slate-400 shrink-0 ml-2">
                            L{rootSym.start_line}
                            {rootSym.end_line > rootSym.start_line ? ` - L${rootSym.end_line}` : ""}
                          </span>
                        </div>

                        {/* Indented Children (e.g. Class Methods) */}
                        {children.length > 0 && (
                          <div className="ml-5 pl-2.5 border-l border-slate-200 space-y-0.5">
                            {children.map((childSym, idx) => {
                              const isLast = idx === children.length - 1;
                              const childColors = SYMBOL_TYPE_COLORS[childSym.symbol_type.toLowerCase()] || {
                                bg: "bg-slate-100",
                                text: "text-slate-700",
                                border: "border-slate-200",
                              };

                              return (
                                <div
                                  key={childSym.id}
                                  className="flex items-center justify-between py-0.5 px-1.5 rounded hover:bg-slate-50 transition group font-mono text-xs relative"
                                >
                                  <div className="flex items-center gap-1.5 overflow-hidden">
                                    <span className="text-slate-400 select-none text-[10px]">
                                      {isLast ? "└──" : "├──"}
                                    </span>
                                    <span
                                      className={`px-1 py-0.2 rounded text-[9px] uppercase font-bold border ${childColors.bg} ${childColors.text} ${childColors.border}`}
                                    >
                                      {childSym.symbol_type}
                                    </span>
                                    <span className="text-slate-700 font-medium truncate group-hover:text-indigo-600">
                                      {childSym.name}
                                    </span>
                                    {childSym.signature && (
                                      <span className="text-slate-400 text-[11px] truncate hidden md:inline">
                                        {childSym.signature}
                                      </span>
                                    )}
                                  </div>

                                  <span className="text-[10px] text-slate-400 shrink-0 ml-2">
                                    L{childSym.start_line}
                                    {childSym.end_line > childSym.start_line ? ` - L${childSym.end_line}` : ""}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="mt-5 flex items-center justify-between pt-3 border-t border-slate-200 text-xs text-slate-600 font-mono">
          <span>
            Showing page {currentPage + 1} of {totalPages} ({totalCount} symbols)
          </span>

          <div className="flex items-center gap-2">
            <button
              disabled={currentPage === 0}
              onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
              className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-300 disabled:opacity-40 disabled:hover:bg-white rounded text-slate-700 transition"
            >
              Previous
            </button>
            <button
              disabled={currentPage >= totalPages - 1}
              onClick={() => setCurrentPage((p) => Math.min(totalPages - 1, p + 1))}
              className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-300 disabled:opacity-40 disabled:hover:bg-white rounded text-slate-700 transition"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

