import React, { useState, useEffect } from "react";
import {
  History,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  GitCommit,
  Calendar,
  AlertCircle,
} from "lucide-react";
import { TimelineResponse } from "../types/api";
import { apiService } from "../services/api";

interface TimelineViewProps {
  repositoryId: string;
}

export const TimelineView: React.FC<TimelineViewProps> = ({ repositoryId }) => {
  const [data, setData] = useState<TimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    apiService
      .getRepositoryTimeline(repositoryId)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.response?.data?.detail || "Failed to load repository timeline");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [repositoryId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-white border border-slate-200 rounded-lg shadow-sm">
        <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-slate-600 text-xs">Loading longitudinal health and debt trajectory...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-white border border-slate-200 rounded-lg text-center text-xs text-rose-600 shadow-sm">
        <p>{error || "No timeline data available"}</p>
      </div>
    );
  }

  const timeline = data.timeline;
  const initialPoint = timeline.length > 0 ? timeline[0] : null;
  const latestPoint = timeline.length > 0 ? timeline[timeline.length - 1] : null;

  const scoreDelta =
    initialPoint && latestPoint ? Math.round((latestPoint.overall_score - initialPoint.overall_score) * 10) / 10 : 0;
  const debtDelta =
    initialPoint && latestPoint ? latestPoint.technical_debt_minutes - initialPoint.technical_debt_minutes : 0;

  return (
    <div className="space-y-6">
      {/* Header and Trajectory Summary */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <History className="w-5 h-5 text-indigo-600" />
              Longitudinal Health & Debt Timeline
            </h2>
            <p className="text-slate-500 text-xs mt-0.5">
              Tracking code quality trajectory across commits for <span className="font-mono text-slate-700">{data.repository_name}</span>
            </p>
          </div>

          <div className="text-xs text-slate-600 bg-slate-100 px-2.5 py-1 rounded border border-slate-200 font-mono">
            {timeline.length} analyses recorded
          </div>
        </div>

        {timeline.length > 1 && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-5 pt-5 border-t border-slate-100">
            <div className="bg-slate-50 border border-slate-200 rounded-md p-3">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Total Score Delta</div>
              <div className="flex items-center gap-1 mt-1">
                {scoreDelta > 0 ? (
                  <TrendingUp className="w-4 h-4 text-emerald-600" />
                ) : scoreDelta < 0 ? (
                  <TrendingDown className="w-4 h-4 text-rose-600" />
                ) : (
                  <Minus className="w-4 h-4 text-slate-400" />
                )}
                <span
                  className={`text-xl font-bold font-mono ${
                    scoreDelta > 0 ? "text-emerald-700" : scoreDelta < 0 ? "text-rose-700" : "text-slate-900"
                  }`}
                >
                  {scoreDelta > 0 ? `+${scoreDelta}` : scoreDelta} pts
                </span>
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-md p-3">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Debt Burndown</div>
              <div className="flex items-center gap-1 mt-1">
                <Clock className="w-4 h-4 text-slate-400" />
                <span
                  className={`text-xl font-bold font-mono ${
                    debtDelta < 0 ? "text-emerald-700" : debtDelta > 0 ? "text-rose-700" : "text-slate-900"
                  }`}
                >
                  {debtDelta > 0 ? `+${debtDelta}` : debtDelta} min
                </span>
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-md p-3">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Current Health Grade</div>
              <div className="text-xl font-bold font-mono text-indigo-700 mt-1">
                {latestPoint?.grade} ({latestPoint?.overall_score.toFixed(1)})
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Chronological Timeline Stream */}
      {timeline.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center shadow-sm">
          <AlertCircle className="w-10 h-10 text-slate-400 mx-auto mb-2" />
          <h3 className="text-sm font-semibold text-slate-900">No Completed Analyses</h3>
          <p className="text-xs text-slate-500 mt-1">
            Run analyses to build up historical health and technical debt trajectory.
          </p>
        </div>
      ) : (
        <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
          {timeline.map((point) => {
            const commitDateStr = point.commit_date
              ? new Date(point.commit_date).toLocaleString()
              : point.created_at
              ? new Date(point.created_at).toLocaleString()
              : "Unknown date";

            return (
              <div key={point.analysis_id} className="relative">
                {/* Node marker */}
                <div className="absolute -left-6 top-3 w-4 h-4 rounded-full border-2 border-white bg-indigo-600 ring-2 ring-indigo-100 shadow-sm" />

                {/* Card */}
                <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1.5 text-xs font-mono text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200 font-semibold">
                        <GitCommit className="w-3.5 h-3.5" />
                        {point.commit_hash ? point.commit_hash.slice(0, 8) : "Initial"}
                      </div>
                      <span className="text-xs text-slate-600 font-medium">{point.commit_author || "System"}</span>
                    </div>

                    <div className="flex items-center gap-1.5 text-xs text-slate-500">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>{commitDateStr}</span>
                    </div>
                  </div>

                  {/* Score & Debt Row */}
                  <div className="grid grid-cols-2 sm:grid-cols-6 gap-2.5 mt-3">
                    <div className="bg-slate-50 border border-slate-200 rounded p-2.5">
                      <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Health Score</div>
                      <div className="text-base font-bold font-mono text-slate-900 mt-0.5">
                        {point.overall_score.toFixed(1)}{" "}
                        <span className="text-xs text-indigo-600">({point.grade})</span>
                      </div>
                    </div>

                    <div className="bg-slate-50 border border-slate-200 rounded p-2.5">
                      <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Debt</div>
                      <div className="text-base font-bold font-mono text-slate-900 mt-0.5">
                        {point.technical_debt_minutes}m
                      </div>
                    </div>

                    <div className="bg-slate-50 border border-slate-200 rounded p-2.5">
                      <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Issues</div>
                      <div className="text-base font-bold font-mono text-slate-900 mt-0.5">
                        {point.total_issues_count}
                      </div>
                    </div>

                    <div className="bg-slate-50 border border-slate-200 rounded p-2.5">
                      <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Maintainability</div>
                      <div className="text-sm font-semibold font-mono text-slate-800 mt-1">
                        {point.maintainability_score.toFixed(1)}
                      </div>
                    </div>

                    <div className="bg-slate-50 border border-slate-200 rounded p-2.5">
                      <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Complexity</div>
                      <div className="text-sm font-semibold font-mono text-slate-800 mt-1">
                        {point.complexity_score.toFixed(1)}
                      </div>
                    </div>

                    <div className="bg-slate-50 border border-slate-200 rounded p-2.5">
                      <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Duplication</div>
                      <div className="text-sm font-semibold font-mono text-slate-800 mt-1">
                        {point.duplication_score.toFixed(1)}
                      </div>
                    </div>
                  </div>

                  {point.commit_message && (
                    <p className="text-xs text-slate-600 mt-2.5 italic truncate font-mono">
                      "{point.commit_message}"
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
