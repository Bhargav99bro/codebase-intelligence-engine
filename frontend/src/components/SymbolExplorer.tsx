import React, { useEffect, useState, useMemo } from "react";
import { apiService } from "../services/api";
import { SymbolItem } from "../types/api";

interface SymbolExplorerProps {
  analysisId: string;
  totalSymbols?: number;
  symbolDistribution?: Record<string, number>;
}

const SYMBOL_TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  function: { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/30" },
  class: { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/30" },
  method: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/30" },
  import: { bg: "bg-amber-500/10", text: "text-amber-400", border: "border-amber-500/30" },
  export: { bg: "bg-rose-500/10", text: "text-rose-400", border: "border-rose-500/30" },
  interface: { bg: "bg-indigo-500/10", text: "text-indigo-400", border: "border-indigo-500/30" },
  type: { bg: "bg-cyan-500/10", text: "text-cyan-400", border: "border-cyan-500/30" },
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
    <div className="mt-8 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <svg
              className="w-5 h-5 text-indigo-400"
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
          <p className="text-sm text-slate-400 mt-1">
            Static structural analysis extracted using Tree-sitter & AST parsers.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-950 px-4 py-2 rounded-lg border border-slate-800">
          <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">Total Symbols</span>
          <span className="text-lg font-mono font-bold text-indigo-400">{totalSymbols || totalCount}</span>
        </div>
      </div>

      {/* Symbol Distribution Summary Pills */}
      {Object.keys(symbolDistribution).length > 0 && (
        <div className="mt-6 flex flex-wrap gap-2">
          {Object.entries(symbolDistribution).map(([type, count]) => {
            const colors = SYMBOL_TYPE_COLORS[type.toLowerCase()] || {
              bg: "bg-slate-800",
              text: "text-slate-300",
              border: "border-slate-700",
            };
            const isFilterActive = selectedType === type;
            return (
              <button
                key={type}
                onClick={() => {
                  setSelectedType(isFilterActive ? "" : type);
                  setCurrentPage(0);
                }}
                className={`px-3 py-1.5 rounded-lg border text-xs font-mono font-medium transition flex items-center gap-2 ${colors.bg} ${colors.text} ${colors.border} ${
                  isFilterActive ? "ring-2 ring-indigo-400 shadow-md" : "hover:opacity-80"
                }`}
              >
                <span className="capitalize">{type}s</span>
                <span className="bg-slate-950/60 px-1.5 py-0.5 rounded text-[11px] font-bold">
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Controls: Search and Filter */}
      <div className="mt-6 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <input
            type="text"
            placeholder="Search symbols by name or signature..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(0);
            }}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
          {searchQuery && (
            <button
              onClick={() => {
                setSearchQuery("");
                setCurrentPage(0);
              }}
              className="absolute right-3 top-2.5 text-xs text-slate-400 hover:text-white"
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
          className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
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
      <div className="mt-6 space-y-4">
        {loading && (
          <div className="p-8 text-center text-slate-400 animate-pulse">
            Loading extracted symbols...
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-sm">
            {error}
          </div>
        )}

        {!loading && !error && Object.keys(groupedByFile).length === 0 && (
          <div className="p-8 text-center text-slate-500 text-sm bg-slate-950/40 rounded-lg border border-slate-800">
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
                className="bg-slate-950/60 border border-slate-800/80 rounded-xl overflow-hidden"
              >
                {/* File Header */}
                <div className="px-4 py-2.5 bg-slate-900/80 border-b border-slate-800/80 flex items-center justify-between">
                  <div className="flex items-center gap-2 font-mono text-xs text-slate-300">
                    <svg
                      className="w-4 h-4 text-slate-500"
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
                    <span className="font-semibold text-slate-200">{filePath}</span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400 bg-slate-800/60 px-2 py-0.5 rounded">
                    {fileSymbols.length} symbol{fileSymbols.length === 1 ? "" : "s"}
                  </span>
                </div>

                {/* File Symbols List */}
                <div className="p-3 space-y-1">
                  {roots.map((rootSym) => {
                    const children = childrenByParent.get(rootSym.id) || [];
                    const rootColors = SYMBOL_TYPE_COLORS[rootSym.symbol_type.toLowerCase()] || {
                      bg: "bg-slate-800",
                      text: "text-slate-300",
                      border: "border-slate-700",
                    };

                    return (
                      <div key={rootSym.id} className="space-y-1">
                        {/* Root Symbol Line */}
                        <div className="flex items-center justify-between py-1.5 px-2.5 rounded-lg hover:bg-slate-800/40 transition group font-mono text-xs">
                          <div className="flex items-center gap-2.5 overflow-hidden">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${rootColors.bg} ${rootColors.text} ${rootColors.border}`}
                            >
                              {rootSym.symbol_type}
                            </span>
                            <span className="text-slate-100 font-semibold truncate group-hover:text-indigo-300">
                              {rootSym.name}
                            </span>
                            {rootSym.signature && (
                              <span className="text-slate-500 text-[11px] truncate hidden sm:inline">
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
                          <div className="ml-6 pl-3 border-l border-slate-800 space-y-1">
                            {children.map((childSym, idx) => {
                              const isLast = idx === children.length - 1;
                              const childColors = SYMBOL_TYPE_COLORS[childSym.symbol_type.toLowerCase()] || {
                                bg: "bg-slate-800",
                                text: "text-slate-300",
                                border: "border-slate-700",
                              };

                              return (
                                <div
                                  key={childSym.id}
                                  className="flex items-center justify-between py-1 px-2 rounded hover:bg-slate-800/40 transition group font-mono text-xs relative"
                                >
                                  <div className="flex items-center gap-2 overflow-hidden">
                                    <span className="text-slate-600 select-none">
                                      {isLast ? "└──" : "├──"}
                                    </span>
                                    <span
                                      className={`px-1.5 py-0.5 rounded text-[9px] uppercase font-bold border ${childColors.bg} ${childColors.text} ${childColors.border}`}
                                    >
                                      {childSym.symbol_type}
                                    </span>
                                    <span className="text-slate-200 font-medium truncate group-hover:text-emerald-300">
                                      {childSym.name}
                                    </span>
                                    {childSym.signature && (
                                      <span className="text-slate-500 text-[11px] truncate hidden md:inline">
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
        <div className="mt-6 flex items-center justify-between pt-4 border-t border-slate-800 text-xs text-slate-400 font-mono">
          <span>
            Showing page {currentPage + 1} of {totalPages} ({totalCount} symbols)
          </span>

          <div className="flex items-center gap-2">
            <button
              disabled={currentPage === 0}
              onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:hover:bg-slate-800 rounded text-slate-200 transition"
            >
              Previous
            </button>
            <button
              disabled={currentPage >= totalPages - 1}
              onClick={() => setCurrentPage((p) => Math.min(totalPages - 1, p + 1))}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:hover:bg-slate-800 rounded text-slate-200 transition"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
