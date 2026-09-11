import React, { useState, useEffect } from "react";
import {
  ExternalLink,
  Filter,
  CheckCircle,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { DuplicationResponse } from "../types/api";
import { apiService } from "../services/api";

interface DuplicationViewProps {
  analysisId: string;
}

export const DuplicationView: React.FC<DuplicationViewProps> = ({ analysisId }) => {
  const [data, setData] = useState<DuplicationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cloneTypeFilter, setCloneTypeFilter] = useState<string>("ALL");
  const [expandedBlockId, setExpandedBlockId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    const typeParam = cloneTypeFilter === "ALL" ? undefined : cloneTypeFilter;
    apiService
      .getAnalysisDuplication(analysisId, 100, 0, typeParam)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
          if (res.duplicates.length > 0) {
            setExpandedBlockId(res.duplicates[0].id);
          }
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.response?.data?.detail || "Failed to load duplication metrics");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [analysisId, cloneTypeFilter]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-white border border-slate-200 rounded-lg shadow-sm">
        <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-slate-600 text-xs">Scanning codebase for Type-1 and Type-2 duplicates...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-white border border-slate-200 rounded-lg text-center text-xs text-rose-600 shadow-sm">
        {error || "No duplication data available"}
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-emerald-700";
    if (score >= 75) return "text-amber-700";
    return "text-rose-700";
  };

  return (
    <div className="space-y-6">
      {/* Top Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Duplication Health Score</div>
          <div className={`text-2xl font-bold font-mono mt-1 ${getScoreColor(data.duplication_score)}`}>
            {data.duplication_score.toFixed(1)} <span className="text-xs font-normal text-slate-400">/ 100</span>
          </div>
          <div className="text-xs text-slate-500 mt-1">Dedicated duplication pillar</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Duplication Ratio</div>
          <div className={`text-2xl font-bold font-mono mt-1 ${data.duplication_ratio > 10 ? "text-rose-600" : "text-slate-900"}`}>
            {data.duplication_ratio.toFixed(1)}%
          </div>
          <div className="text-xs text-slate-500 mt-1">Duplicate SLOC / Total SLOC</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Duplicate Blocks</div>
          <div className="text-2xl font-bold font-mono text-slate-900 mt-1">
            {data.duplicate_blocks_count}
          </div>
          <div className="text-xs text-slate-500 mt-1">Detected clone pairs</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Duplicated Lines</div>
          <div className="text-2xl font-bold font-mono text-slate-900 mt-1">
            {data.duplicate_lines_count}
          </div>
          <div className="text-xs text-slate-500 mt-1">Lines in duplicate blocks</div>
        </div>
      </div>

      {/* Filter and Actions bar */}
      <div className="flex items-center justify-between bg-white border border-slate-200 rounded-lg p-3 shadow-sm">
        <div className="flex items-center gap-2 text-xs text-slate-700">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-semibold">Clone Type:</span>
          <div className="flex gap-1 ml-2">
            {["ALL", "TYPE_1", "TYPE_2"].map((t) => (
              <button
                key={t}
                onClick={() => setCloneTypeFilter(t)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                  cloneTypeFilter === t
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200"
                }`}
              >
                {t === "ALL" ? "All Clones" : t === "TYPE_1" ? "Type-1 (Exact)" : "Type-2 (Renamed)"}
              </button>
            ))}
          </div>
        </div>

        <span className="text-xs text-slate-500 font-mono">
          Showing {data.duplicates.length} of {data.total_matches} clone blocks
        </span>
      </div>

      {/* Duplicate Pairs List */}
      {data.duplicates.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center shadow-sm">
          <CheckCircle className="w-10 h-10 text-emerald-600 mx-auto mb-2" />
          <h3 className="text-sm font-semibold text-slate-900">Zero Duplication Detected</h3>
          <p className="text-xs text-slate-500 mt-1">
            No duplicated blocks meeting the minimum thresholds (10 lines, 40 tokens) were found.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.duplicates.map((dup) => {
            const isExpanded = expandedBlockId === dup.id;
            return (
              <div
                key={dup.id}
                className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm transition"
              >
                <div
                  onClick={() => setExpandedBlockId(isExpanded ? null : dup.id)}
                  className="p-3.5 flex items-center justify-between cursor-pointer hover:bg-slate-50/80 transition"
                >
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-slate-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-slate-500" />
                    )}
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        dup.clone_type === "TYPE_1"
                          ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                          : "bg-sky-50 text-sky-700 border border-sky-200"
                      }`}
                    >
                      {dup.clone_type === "TYPE_1" ? "Type-1 Exact" : "Type-2 Renamed"}
                    </span>
                    <span className="text-xs font-semibold text-slate-900 font-mono">
                      {dup.line_count} lines ({dup.token_count} tokens)
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-xs text-slate-600">
                    <span className="font-mono text-slate-800">
                      {dup.source_file_path}:{dup.source_start_line}-{dup.source_end_line}
                    </span>
                    <span className="text-slate-400">&harr;</span>
                    <span className="font-mono text-slate-800">
                      {dup.target_file_path}:{dup.target_start_line}-{dup.target_end_line}
                    </span>
                  </div>
                </div>

                {isExpanded && (
                  <div className="border-t border-slate-100 p-4 bg-slate-50">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {/* Source snippet */}
                      <div className="bg-white border border-slate-200 rounded-md p-3 shadow-sm">
                        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100 text-xs">
                          <span className="font-mono text-indigo-700 font-medium truncate">{dup.source_file_path}</span>
                          {dup.source_url ? (
                            <a
                              href={dup.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-slate-500 hover:text-indigo-600 flex items-center gap-1 font-mono"
                            >
                              Lines {dup.source_start_line}-{dup.source_end_line}
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          ) : (
                            <span className="text-slate-500 font-mono">
                              Lines {dup.source_start_line}-{dup.source_end_line}
                            </span>
                          )}
                        </div>
                        <pre className="text-xs font-mono text-slate-800 overflow-x-auto p-2.5 bg-slate-50 border border-slate-200 rounded max-h-60 leading-relaxed">
                          {dup.source_snippet || "(Snippet not stored)"}
                        </pre>
                      </div>

                      {/* Target snippet */}
                      <div className="bg-white border border-slate-200 rounded-md p-3 shadow-sm">
                        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100 text-xs">
                          <span className="font-mono text-indigo-700 font-medium truncate">{dup.target_file_path}</span>
                          {dup.target_url ? (
                            <a
                              href={dup.target_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-slate-500 hover:text-indigo-600 flex items-center gap-1 font-mono"
                            >
                              Lines {dup.target_start_line}-{dup.target_end_line}
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          ) : (
                            <span className="text-slate-500 font-mono">
                              Lines {dup.target_start_line}-{dup.target_end_line}
                            </span>
                          )}
                        </div>
                        <pre className="text-xs font-mono text-slate-800 overflow-x-auto p-2.5 bg-slate-50 border border-slate-200 rounded max-h-60 leading-relaxed">
                          {dup.target_snippet || "(Snippet not stored)"}
                        </pre>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
