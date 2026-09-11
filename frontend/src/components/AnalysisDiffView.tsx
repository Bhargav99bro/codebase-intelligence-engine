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
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-700 font-semibold text-xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>PR GATE PASSED</span>
        </div>
      );
    }
    if (gate.status === "WARNING") {
      return (
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-amber-50 border border-amber-200 text-amber-800 font-semibold text-xs">
          <AlertTriangle className="w-4 h-4 text-amber-600" />
          <span>PR GATE WARNING</span>
        </div>
      );
    }
    return (
      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-rose-50 border border-rose-200 text-rose-700 font-semibold text-xs">
        <XCircle className="w-4 h-4 text-rose-600" />
        <span>PR GATE FAILED</span>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header & Base Analysis Selector */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <GitCompare className="w-5 h-5 text-indigo-600" />
              Analysis Diff & PR Quality Gate
            </h2>
            <p className="text-slate-500 text-xs mt-1">
              Compare this analysis against a baseline commit to evaluate regressions and gate eligibility.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <input
              type="text"
              placeholder="Enter Baseline Analysis UUID..."
              value={baseAnalysisId}
              onChange={(e) => setBaseAnalysisId(e.target.value)}
              className="bg-white border border-slate-300 rounded-md px-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 w-72"
            />
            <button
              onClick={() => fetchDiff(baseAnalysisId)}
              disabled={loading || !baseAnalysisId.trim()}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-md text-xs font-medium transition shadow-sm"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              Compare
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-rose-50 border border-rose-200 rounded-md text-rose-700 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center p-12 bg-white border border-slate-200 rounded-lg shadow-sm">
          <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin mb-3" />
          <p className="text-slate-500 text-xs">Evaluating diff metrics, cycle shifts, and gate rules...</p>
        </div>
      )}

      {!loading && diffData && (
        <>
          {/* Quality Gate Banner */}
          <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">Quality Gate Verdict</h3>
                <p className="text-xs text-slate-500">Automated evaluation against regression thresholds</p>
              </div>
              {renderGateBadge(diffData.quality_gate)}
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  Evaluation Rationales
                </span>
                <ul className="space-y-1.5">
                  {diffData.quality_gate.reasons.map((r, i) => (
                    <li key={i} className="text-xs text-slate-700 flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 flex-shrink-0" />
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-50 border border-slate-200 rounded-md p-3 text-center">
                  <div className="text-[11px] font-medium text-slate-500">New Blocker/Crit</div>
                  <div className={`text-xl font-bold font-mono mt-1 ${diffData.quality_gate.new_blocker_critical_count > 0 ? "text-rose-600" : "text-emerald-600"}`}>
                    {diffData.quality_gate.new_blocker_critical_count}
                  </div>
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-md p-3 text-center">
                  <div className="text-[11px] font-medium text-slate-500">New Major</div>
                  <div className={`text-xl font-bold font-mono mt-1 ${diffData.quality_gate.new_major_count > 0 ? "text-amber-600" : "text-slate-800"}`}>
                    {diffData.quality_gate.new_major_count}
                  </div>
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-md p-3 text-center">
                  <div className="text-[11px] font-medium text-slate-500">New Cycles</div>
                  <div className={`text-xl font-bold font-mono mt-1 ${diffData.quality_gate.new_cycles_count > 0 ? "text-rose-600" : "text-emerald-600"}`}>
                    {diffData.quality_gate.new_cycles_count}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Delta Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Overall Health Delta</div>
              <div className="flex items-center gap-2 mt-2">
                {diffData.delta_health_score > 0 ? (
                  <TrendingUp className="w-5 h-5 text-emerald-600" />
                ) : diffData.delta_health_score < 0 ? (
                  <TrendingDown className="w-5 h-5 text-rose-600" />
                ) : (
                  <Minus className="w-5 h-5 text-slate-400" />
                )}
                <span
                  className={`text-2xl font-bold font-mono ${
                    diffData.delta_health_score > 0
                      ? "text-emerald-600"
                      : diffData.delta_health_score < 0
                      ? "text-rose-600"
                      : "text-slate-800"
                  }`}
                >
                  {diffData.delta_health_score > 0 ? `+${diffData.delta_health_score}` : diffData.delta_health_score} pts
                </span>
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Technical Debt Delta</div>
              <div className="flex items-center gap-2 mt-2">
                <Clock className="w-5 h-5 text-slate-500" />
                <span
                  className={`text-2xl font-bold font-mono ${
                    diffData.delta_debt_minutes < 0
                      ? "text-emerald-600"
                      : diffData.delta_debt_minutes > 0
                      ? "text-rose-600"
                      : "text-slate-800"
                  }`}
                >
                  {diffData.delta_debt_minutes > 0 ? `+${diffData.delta_debt_minutes}` : diffData.delta_debt_minutes} min
                </span>
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Duplication Ratio Delta</div>
              <div className="flex items-center gap-2 mt-2">
                <Repeat className="w-5 h-5 text-indigo-600" />
                <span
                  className={`text-2xl font-bold font-mono ${
                    diffData.quality_gate.delta_duplication_ratio > 0
                      ? "text-rose-600"
                      : diffData.quality_gate.delta_duplication_ratio < 0
                      ? "text-emerald-600"
                      : "text-slate-800"
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
          <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
            <h4 className="text-xs font-semibold text-slate-800 uppercase tracking-wider mb-3">Pillar Performance Deltas</h4>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {Object.entries(diffData.pillar_deltas).map(([pillar, val]) => (
                <div key={pillar} className="bg-slate-50 border border-slate-200 rounded-md p-3">
                  <div className="text-[11px] font-medium text-slate-600 capitalize truncate">
                    {pillar.replace(/_/g, " ")}
                  </div>
                  <div
                    className={`text-base font-bold font-mono mt-1 ${
                      val > 0 ? "text-emerald-600" : val < 0 ? "text-rose-600" : "text-slate-500"
                    }`}
                  >
                    {val > 0 ? `+${val}` : val}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Issue Lifecycle Section */}
          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm">
            <div className="flex items-center border-b border-slate-200 bg-slate-50 px-4">
              <button
                onClick={() => setActiveIssueTab("new")}
                className={`py-2.5 px-3.5 text-xs font-semibold border-b-2 transition ${
                  activeIssueTab === "new"
                    ? "border-rose-600 text-rose-700 bg-white"
                    : "border-transparent text-slate-600 hover:text-slate-900"
                }`}
              >
                New Issues ({diffData.new_issues_count})
              </button>
              <button
                onClick={() => setActiveIssueTab("fixed")}
                className={`py-2.5 px-3.5 text-xs font-semibold border-b-2 transition ${
                  activeIssueTab === "fixed"
                    ? "border-emerald-600 text-emerald-700 bg-white"
                    : "border-transparent text-slate-600 hover:text-slate-900"
                }`}
              >
                Fixed Issues ({diffData.fixed_issues_count})
              </button>
              <button
                onClick={() => setActiveIssueTab("persistent")}
                className={`py-2.5 px-3.5 text-xs font-semibold border-b-2 transition ${
                  activeIssueTab === "persistent"
                    ? "border-indigo-600 text-indigo-700 bg-white"
                    : "border-transparent text-slate-600 hover:text-slate-900"
                }`}
              >
                Persistent Issues ({diffData.persistent_issues_count})
              </button>
            </div>

            <div className="p-4 space-y-2.5">
              {activeIssueTab === "new" &&
                (diffData.new_issues.length === 0 ? (
                  <p className="text-xs text-slate-500 text-center py-6">No new issues introduced.</p>
                ) : (
                  diffData.new_issues.map((iss, idx) => (
                    <div
                      key={idx}
                      className="bg-slate-50 border border-slate-200 rounded-md p-3 flex items-start justify-between gap-4"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-100 text-rose-700 border border-rose-200 uppercase">
                            {iss.severity}
                          </span>
                          <span className="text-xs font-mono text-slate-500">{iss.rule_id}</span>
                          <span className="text-xs font-semibold text-slate-900">{iss.title}</span>
                        </div>
                        <p className="text-xs font-mono text-slate-500 mt-1">{iss.file_path}</p>
                      </div>
                      <span className="text-xs font-mono text-slate-500 whitespace-nowrap">
                        +{iss.remediation_effort_minutes} min debt
                      </span>
                    </div>
                  ))
                ))}

              {activeIssueTab === "fixed" &&
                (diffData.fixed_issues.length === 0 ? (
                  <p className="text-xs text-slate-500 text-center py-6">No issues resolved in this analysis.</p>
                ) : (
                  diffData.fixed_issues.map((iss, idx) => (
                    <div
                      key={idx}
                      className="bg-slate-50 border border-slate-200 rounded-md p-3 flex items-start justify-between gap-4"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-700 border border-emerald-200 uppercase">
                            RESOLVED
                          </span>
                          <span className="text-xs font-mono text-slate-500">{iss.rule_id}</span>
                          <span className="text-xs font-semibold text-slate-900">{iss.title}</span>
                        </div>
                        <p className="text-xs font-mono text-slate-500 mt-1">{iss.file_path}</p>
                      </div>
                      <span className="text-xs font-mono text-emerald-600 font-semibold whitespace-nowrap">
                        -{iss.remediation_effort_minutes} min debt
                      </span>
                    </div>
                  ))
                ))}

              {activeIssueTab === "persistent" &&
                (diffData.persistent_issues.length === 0 ? (
                  <p className="text-xs text-slate-500 text-center py-6">No persistent issues.</p>
                ) : (
                  diffData.persistent_issues.slice(0, 50).map((iss, idx) => (
                    <div
                      key={idx}
                      className="bg-slate-50 border border-slate-200 rounded-md p-3 flex items-start justify-between gap-4 opacity-90"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-200 text-slate-700 uppercase">
                            {iss.severity}
                          </span>
                          <span className="text-xs font-mono text-slate-500">{iss.rule_id}</span>
                          <span className="text-xs font-semibold text-slate-800">{iss.title}</span>
                        </div>
                        <p className="text-xs font-mono text-slate-500 mt-1">{iss.file_path}</p>
                      </div>
                      <span className="text-xs font-mono text-slate-500 whitespace-nowrap">
                        {iss.remediation_effort_minutes} min debt
                      </span>
                    </div>
                  ))
                ))}
            </div>
          </div>

          {/* Cycle Shifts */}
          {(diffData.new_cycles.length > 0 || diffData.resolved_cycles.length > 0) && (
            <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-4">
              <h4 className="text-xs font-semibold text-slate-900 flex items-center gap-2 uppercase tracking-wider">
                <ShieldAlert className="w-4 h-4 text-amber-600" />
                Circular Dependency Cycle Transitions
              </h4>

              {diffData.new_cycles.length > 0 && (
                <div>
                  <span className="text-[11px] font-semibold text-rose-700 uppercase tracking-wider">
                    New Cycles Introduced ({diffData.new_cycles.length})
                  </span>
                  <div className="mt-2 space-y-2">
                    {diffData.new_cycles.map((cycle, i) => (
                      <div key={i} className="bg-rose-50 border border-rose-200 rounded-md p-2.5 text-xs font-mono text-rose-800">
                        {cycle.join(" -> ")}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {diffData.resolved_cycles.length > 0 && (
                <div>
                  <span className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider">
                    Resolved Cycles ({diffData.resolved_cycles.length})
                  </span>
                  <div className="mt-2 space-y-2">
                    {diffData.resolved_cycles.map((cycle, i) => (
                      <div key={i} className="bg-emerald-50 border border-emerald-200 rounded-md p-2.5 text-xs font-mono text-emerald-800">
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

