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
      <div className="flex flex-col items-center justify-center p-12 bg-slate-900 border border-slate-800 rounded-xl">
        <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-slate-400 text-sm">Scanning codebase for Type-1 and Type-2 duplicates...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl text-center">
        <p className="text-rose-400 text-sm">{error || "No duplication data available"}</p>
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-emerald-400";
    if (score >= 75) return "text-amber-400";
    return "text-rose-400";
  };

  return (
    <div className="space-y-6">
      {/* Top Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-400">Duplication Health Score</div>
          <div className={`text-3xl font-bold mt-2 ${getScoreColor(data.duplication_score)}`}>
            {data.duplication_score.toFixed(1)} / 100
          </div>
          <div className="text-xs text-slate-500 mt-1">Dedicated duplication pillar</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-400">Duplication Ratio</div>
          <div className={`text-3xl font-bold mt-2 ${data.duplication_ratio > 10 ? "text-rose-400" : "text-slate-200"}`}>
            {data.duplication_ratio.toFixed(1)}%
          </div>
          <div className="text-xs text-slate-500 mt-1">Duplicate SLOC / Total SLOC</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-400">Duplicate Blocks</div>
          <div className="text-3xl font-bold text-slate-200 mt-2">
            {data.duplicate_blocks_count}
          </div>
          <div className="text-xs text-slate-500 mt-1">Detected clone pairs</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-400">Duplicated Lines</div>
          <div className="text-3xl font-bold text-slate-200 mt-2">
            {data.duplicate_lines_count}
          </div>
          <div className="text-xs text-slate-500 mt-1">Lines in duplicate blocks</div>
        </div>
      </div>

      {/* Filter and Actions bar */}
      <div className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Filter className="w-4 h-4" />
          <span>Clone Type:</span>
          <div className="flex gap-1 ml-2">
            {["ALL", "TYPE_1", "TYPE_2"].map((t) => (
              <button
                key={t}
                onClick={() => setCloneTypeFilter(t)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  cloneTypeFilter === t
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                {t === "ALL" ? "All Clones" : t === "TYPE_1" ? "Type-1 (Exact)" : "Type-2 (Renamed)"}
              </button>
            ))}
          </div>
        </div>

        <span className="text-xs text-slate-400">
          Showing {data.duplicates.length} of {data.total_matches} clone blocks
        </span>
      </div>

      {/* Duplicate Pairs List */}
      {data.duplicates.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
          <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-white">Zero Duplication Detected</h3>
          <p className="text-sm text-slate-400 mt-1">
            No duplicated blocks meeting the minimum thresholds (10 lines, 40 tokens) were found.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {data.duplicates.map((dup) => {
            const isExpanded = expandedBlockId === dup.id;
            return (
              <div
                key={dup.id}
                className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm transition-all"
              >
                <div
                  onClick={() => setExpandedBlockId(isExpanded ? null : dup.id)}
                  className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-800/40 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown className="w-5 h-5 text-slate-400" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-slate-400" />
                    )}
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${
                        dup.clone_type === "TYPE_1"
                          ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                          : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                      }`}
                    >
                      {dup.clone_type === "TYPE_1" ? "Type-1 Exact" : "Type-2 Renamed"}
                    </span>
                    <span className="text-sm font-medium text-white">
                      {dup.line_count} lines ({dup.token_count} tokens)
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-slate-400">
                    <span className="font-mono text-slate-300">
                      {dup.source_file_path}:{dup.source_start_line}-{dup.source_end_line}
                    </span>
                    <span>⟷</span>
                    <span className="font-mono text-slate-300">
                      {dup.target_file_path}:{dup.target_start_line}-{dup.target_end_line}
                    </span>
                  </div>
                </div>

                {isExpanded && (
                  <div className="border-t border-slate-800 p-4 bg-slate-950/60">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {/* Source snippet */}
                      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3">
                        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-xs">
                          <span className="font-mono text-indigo-300 truncate">{dup.source_file_path}</span>
                          {dup.source_url ? (
                            <a
                              href={dup.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-slate-400 hover:text-indigo-400 flex items-center gap-1"
                            >
                              Lines {dup.source_start_line}-{dup.source_end_line}
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          ) : (
                            <span className="text-slate-500">
                              Lines {dup.source_start_line}-{dup.source_end_line}
                            </span>
                          )}
                        </div>
                        <pre className="text-xs font-mono text-slate-300 overflow-x-auto p-2 bg-slate-950 rounded max-h-60">
                          {dup.source_snippet || "(Snippet not stored)"}
                        </pre>
                      </div>

                      {/* Target snippet */}
                      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3">
                        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-xs">
                          <span className="font-mono text-indigo-300 truncate">{dup.target_file_path}</span>
                          {dup.target_url ? (
                            <a
                              href={dup.target_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-slate-400 hover:text-indigo-400 flex items-center gap-1"
                            >
                              Lines {dup.target_start_line}-{dup.target_end_line}
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          ) : (
                            <span className="text-slate-500">
                              Lines {dup.target_start_line}-{dup.target_end_line}
                            </span>
                          )}
                        </div>
                        <pre className="text-xs font-mono text-slate-300 overflow-x-auto p-2 bg-slate-950 rounded max-h-60">
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
