import React, { useState, useEffect } from "react";
import {
  GitCompare,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Clock,
  ShieldAlert,
  Repeat,
} from "lucide-react";
import { AnalysisDiffResponse, PRQualityGate } from "../types/api";
import { apiService } from "../services/api";

interface AnalysisDiffViewProps {
  currentAnalysisId: string;
  defaultBaseAnalysisId?: string | null;
}

export const AnalysisDiffView: React.FC<AnalysisDiffViewProps> = ({
  currentAnalysisId,
  defaultBaseAnalysisId,
}) => {
  const [baseAnalysisId, setBaseAnalysisId] = useState<string>(defaultBaseAnalysisId || "");
  const [diffData, setDiffData] = useState<AnalysisDiffResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeIssueTab, setActiveIssueTab] = useState<"new" | "fixed" | "persistent">("new");

  const fetchDiff = (baseId: string) => {
    if (!baseId.trim()) return;
    setLoading(true);
    setError(null);

    apiService
      .compareAnalyses(baseId.trim(), currentAnalysisId)
      .then((data) => {
        setDiffData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.response?.data?.detail || "Failed to compare analyses");
        setLoading(false);
      });
  };

  useEffect(() => {
    if (defaultBaseAnalysisId) {
      setBaseAnalysisId(defaultBaseAnalysisId);
      fetchDiff(defaultBaseAnalysisId);
    }
  }, [defaultBaseAnalysisId, currentAnalysisId]);

  const renderGateBadge = (gate: PRQualityGate) => {
    if (gate.status === "PASSED") {
      return (
        <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold">
          <CheckCircle2 className="w-5 h-5" />
          <span>PR GATE PASSED</span>
        </div>
      );
    }
    if (gate.status === "WARNING") {
      return (
        <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 font-semibold">
          <AlertTriangle className="w-5 h-5" />
          <span>PR GATE WARNING</span>
        </div>
      );
    }
    return (
      <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 font-semibold">
        <XCircle className="w-5 h-5" />
        <span>PR GATE FAILED</span>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header & Base Analysis Selector */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <GitCompare className="w-6 h-6 text-indigo-400" />
              Analysis Diff & PR Quality Gate
            </h2>
            <p className="text-slate-400 text-sm mt-1">
              Compare this analysis against a baseline commit to evaluate regressions and gate eligibility.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder="Enter Baseline Analysis UUID..."
              value={baseAnalysisId}
              onChange={(e) => setBaseAnalysisId(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-72"
            />
            <button
              onClick={() => fetchDiff(baseAnalysisId)}
              disabled={loading || !baseAnalysisId.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              Compare
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-rose-950/40 border border-rose-800/60 rounded-lg text-rose-300 text-sm flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center p-12 bg-slate-900 border border-slate-800 rounded-xl">
          <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-slate-400 text-sm">Evaluating diff metrics, cycle shifts, and gate rules...</p>
        </div>
      )}

      {!loading && diffData && (
        <>
          {/* Quality Gate Banner */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <h3 className="text-lg font-semibold text-white">Quality Gate Verdict</h3>
                <p className="text-xs text-slate-400">Automated evaluation against regression thresholds</p>
              </div>
              {renderGateBadge(diffData.quality_gate)}
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Evaluation Rationales
                </span>
                <ul className="space-y-1">
                  {diffData.quality_gate.reasons.map((r, i) => (
                    <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-2 flex-shrink-0" />
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-center">
                  <div className="text-xs text-slate-400">New Blocker/Crit</div>
                  <div className={`text-xl font-bold mt-1 ${diffData.quality_gate.new_blocker_critical_count > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                    {diffData.quality_gate.new_blocker_critical_count}
                  </div>
                </div>
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-center">
                  <div className="text-xs text-slate-400">New Major</div>
                  <div className={`text-xl font-bold mt-1 ${diffData.quality_gate.new_major_count > 0 ? "text-amber-400" : "text-slate-300"}`}>
                    {diffData.quality_gate.new_major_count}
                  </div>
                </div>
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-center">
                  <div className="text-xs text-slate-400">New Cycles</div>
                  <div className={`text-xl font-bold mt-1 ${diffData.quality_gate.new_cycles_count > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                    {diffData.quality_gate.new_cycles_count}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Delta Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="text-xs font-medium text-slate-400">Overall Health Delta</div>
              <div className="flex items-center gap-2 mt-2">
                {diffData.delta_health_score > 0 ? (
                  <TrendingUp className="w-6 h-6 text-emerald-400" />
                ) : diffData.delta_health_score < 0 ? (
                  <TrendingDown className="w-6 h-6 text-rose-400" />
                ) : (
                  <Minus className="w-6 h-6 text-slate-400" />
                )}
                <span
                  className={`text-2xl font-bold ${
                    diffData.delta_health_score > 0
                      ? "text-emerald-400"
                      : diffData.delta_health_score < 0
                      ? "text-rose-400"
                      : "text-slate-300"
                  }`}
                >
                  {diffData.delta_health_score > 0 ? `+${diffData.delta_health_score}` : diffData.delta_health_score} pts
                </span>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="text-xs font-medium text-slate-400">Technical Debt Delta</div>
              <div className="flex items-center gap-2 mt-2">
                <Clock className="w-6 h-6 text-slate-400" />
                <span
                  className={`text-2xl font-bold ${
                    diffData.delta_debt_minutes < 0
                      ? "text-emerald-400"
                      : diffData.delta_debt_minutes > 0
                      ? "text-rose-400"
                      : "text-slate-300"
                  }`}
                >
                  {diffData.delta_debt_minutes > 0 ? `+${diffData.delta_debt_minutes}` : diffData.delta_debt_minutes} min
                </span>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="text-xs font-medium text-slate-400">Duplication Ratio Delta</div>
              <div className="flex items-center gap-2 mt-2">
                <Repeat className="w-6 h-6 text-indigo-400" />
                <span
                  className={`text-2xl font-bold ${
                    diffData.quality_gate.delta_duplication_ratio > 0
                      ? "text-rose-400"
                      : diffData.quality_gate.delta_duplication_ratio < 0
                      ? "text-emerald-400"
                      : "text-slate-300"
                  }`}
                >
                  {diffData.quality_gate.delta_duplication_ratio > 0
                    ? `+${diffData.quality_gate.delta_duplication_ratio}%`
                    : `${diffData.quality_gate.delta_duplication_ratio}%`}
                </span>
              </div>
            </div>
          </div>

          {/* Pillar Deltas Grid */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h4 className="text-sm font-semibold text-slate-300 mb-3">Pillar Performance Deltas</h4>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {Object.entries(diffData.pillar_deltas).map(([pillar, val]) => (
                <div key={pillar} className="bg-slate-950 border border-slate-800/80 rounded-lg p-3">
                  <div className="text-xs text-slate-400 capitalize truncate">
                    {pillar.replace(/_/g, " ")}
                  </div>
                  <div
                    className={`text-lg font-bold mt-1 ${
                      val > 0 ? "text-emerald-400" : val < 0 ? "text-rose-400" : "text-slate-400"
                    }`}
                  >
                    {val > 0 ? `+${val}` : val}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Issue Lifecycle Section */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="flex items-center border-b border-slate-800 bg-slate-950/60 px-4">
              <button
                onClick={() => setActiveIssueTab("new")}
                className={`py-3 px-4 text-sm font-medium border-b-2 transition-colors ${
                  activeIssueTab === "new"
                    ? "border-rose-500 text-rose-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                New Issues ({diffData.new_issues_count})
              </button>
              <button
                onClick={() => setActiveIssueTab("fixed")}
                className={`py-3 px-4 text-sm font-medium border-b-2 transition-colors ${
                  activeIssueTab === "fixed"
                    ? "border-emerald-500 text-emerald-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Fixed Issues ({diffData.fixed_issues_count})
              </button>
              <button
                onClick={() => setActiveIssueTab("persistent")}
                className={`py-3 px-4 text-sm font-medium border-b-2 transition-colors ${
                  activeIssueTab === "persistent"
                    ? "border-indigo-500 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Persistent Issues ({diffData.persistent_issues_count})
              </button>
            </div>

            <div className="p-4 space-y-3">
              {activeIssueTab === "new" &&
                (diffData.new_issues.length === 0 ? (
                  <p className="text-sm text-slate-400 text-center py-6">No new issues introduced.</p>
                ) : (
                  diffData.new_issues.map((iss, idx) => (
                    <div
                      key={idx}
                      className="bg-slate-950 border border-slate-800 rounded-lg p-3 flex items-start justify-between gap-4"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30 uppercase">
                            {iss.severity}
                          </span>
                          <span className="text-xs font-mono text-slate-400">{iss.rule_id}</span>
                          <span className="text-sm font-medium text-white">{iss.title}</span>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">{iss.file_path}</p>
                      </div>
                      <span className="text-xs text-slate-500 whitespace-nowrap">
                        +{iss.remediation_effort_minutes} min debt
                      </span>
                    </div>
                  ))
                ))}

              {activeIssueTab === "fixed" &&
                (diffData.fixed_issues.length === 0 ? (
                  <p className="text-sm text-slate-400 text-center py-6">No issues resolved in this analysis.</p>
                ) : (
                  diffData.fixed_issues.map((iss, idx) => (
                    <div
                      key={idx}
                      className="bg-slate-950 border border-slate-800 rounded-lg p-3 flex items-start justify-between gap-4"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 uppercase">
                            RESOLVED
                          </span>
                          <span className="text-xs font-mono text-slate-400">{iss.rule_id}</span>
                          <span className="text-sm font-medium text-white">{iss.title}</span>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">{iss.file_path}</p>
                      </div>
                      <span className="text-xs text-emerald-400 whitespace-nowrap">
                        -{iss.remediation_effort_minutes} min debt
                      </span>
                    </div>
                  ))
                ))}

              {activeIssueTab === "persistent" &&
                (diffData.persistent_issues.length === 0 ? (
                  <p className="text-sm text-slate-400 text-center py-6">No persistent issues.</p>
                ) : (
                  diffData.persistent_issues.slice(0, 50).map((iss, idx) => (
                    <div
                      key={idx}
                      className="bg-slate-950 border border-slate-800 rounded-lg p-3 flex items-start justify-between gap-4 opacity-85"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-300 uppercase">
                            {iss.severity}
                          </span>
                          <span className="text-xs font-mono text-slate-400">{iss.rule_id}</span>
                          <span className="text-sm font-medium text-white">{iss.title}</span>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">{iss.file_path}</p>
                      </div>
                      <span className="text-xs text-slate-500 whitespace-nowrap">
                        {iss.remediation_effort_minutes} min debt
                      </span>
                    </div>
                  ))
                ))}
            </div>
          </div>

          {/* Cycle Shifts */}
          {(diffData.new_cycles.length > 0 || diffData.resolved_cycles.length > 0) && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                Circular Dependency Cycle Transitions
              </h4>

              {diffData.new_cycles.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider">
                    New Cycles Introduced ({diffData.new_cycles.length})
                  </span>
                  <div className="mt-2 space-y-2">
                    {diffData.new_cycles.map((cycle, i) => (
                      <div key={i} className="bg-rose-950/20 border border-rose-800/40 rounded-lg p-3 text-xs font-mono text-rose-300">
                        {cycle.join(" -> ")}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {diffData.resolved_cycles.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                    Resolved Cycles ({diffData.resolved_cycles.length})
                  </span>
                  <div className="mt-2 space-y-2">
                    {diffData.resolved_cycles.map((cycle, i) => (
                      <div key={i} className="bg-emerald-950/20 border border-emerald-800/40 rounded-lg p-3 text-xs font-mono text-emerald-300">
                        {cycle.join(" -> ")}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};
