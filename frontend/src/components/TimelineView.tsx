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
      <div className="flex flex-col items-center justify-center p-12 bg-slate-900 border border-slate-800 rounded-xl">
        <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-slate-400 text-sm">Loading longitudinal health and debt trajectory...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl text-center">
        <p className="text-rose-400 text-sm">{error || "No timeline data available"}</p>
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
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <History className="w-6 h-6 text-indigo-400" />
              Longitudinal Health & Debt Timeline
            </h2>
            <p className="text-slate-400 text-sm mt-1">
              Tracking code quality trajectory across commits for {data.repository_name}
            </p>
          </div>

          <div className="text-xs text-slate-400 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
            {timeline.length} analyses recorded
          </div>
        </div>

        {timeline.length > 1 && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6 pt-6 border-t border-slate-800">
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3">
              <div className="text-xs text-slate-400">Total Score Delta</div>
              <div className="flex items-center gap-1 mt-1">
                {scoreDelta > 0 ? (
                  <TrendingUp className="w-5 h-5 text-emerald-400" />
                ) : scoreDelta < 0 ? (
                  <TrendingDown className="w-5 h-5 text-rose-400" />
                ) : (
                  <Minus className="w-5 h-5 text-slate-400" />
                )}
                <span
                  className={`text-xl font-bold ${
                    scoreDelta > 0 ? "text-emerald-400" : scoreDelta < 0 ? "text-rose-400" : "text-slate-200"
                  }`}
                >
                  {scoreDelta > 0 ? `+${scoreDelta}` : scoreDelta} pts
                </span>
              </div>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3">
              <div className="text-xs text-slate-400">Debt Burndown</div>
              <div className="flex items-center gap-1 mt-1">
                <Clock className="w-5 h-5 text-slate-400" />
                <span
                  className={`text-xl font-bold ${
                    debtDelta < 0 ? "text-emerald-400" : debtDelta > 0 ? "text-rose-400" : "text-slate-200"
                  }`}
                >
                  {debtDelta > 0 ? `+${debtDelta}` : debtDelta} min
                </span>
              </div>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3">
              <div className="text-xs text-slate-400">Current Health Grade</div>
              <div className="text-xl font-bold text-indigo-400 mt-1">
                {latestPoint?.grade} ({latestPoint?.overall_score.toFixed(1)})
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Chronological Timeline Stream */}
      {timeline.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
          <AlertCircle className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-white">No Completed Analyses</h3>
          <p className="text-sm text-slate-400 mt-1">
            Run analyses to build up historical health and technical debt trajectory.
          </p>
        </div>
      ) : (
        <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
          {timeline.map((point) => {
            const commitDateStr = point.commit_date
              ? new Date(point.commit_date).toLocaleString()
              : point.created_at
              ? new Date(point.created_at).toLocaleString()
              : "Unknown date";

            return (
              <div key={point.analysis_id} className="relative">
                {/* Node marker */}
                <div className="absolute -left-6 top-3 w-4 h-4 rounded-full border-2 border-slate-900 bg-indigo-500 ring-4 ring-slate-900" />

                {/* Card */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800/80">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1.5 text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                        <GitCommit className="w-3.5 h-3.5" />
                        {point.commit_hash ? point.commit_hash.slice(0, 8) : "Initial"}
                      </div>
                      <span className="text-xs text-slate-400">{point.commit_author || "System"}</span>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>{commitDateStr}</span>
                    </div>
                  </div>

                  {/* Score & Debt Row */}
                  <div className="grid grid-cols-2 sm:grid-cols-6 gap-3 mt-4">
                    <div className="bg-slate-950 rounded-lg p-2.5">
                      <div className="text-xs text-slate-400">Health Score</div>
                      <div className="text-lg font-bold text-white mt-0.5">
                        {point.overall_score.toFixed(1)}{" "}
                        <span className="text-xs text-indigo-400">({point.grade})</span>
                      </div>
                    </div>

                    <div className="bg-slate-950 rounded-lg p-2.5">
                      <div className="text-xs text-slate-400">Debt</div>
                      <div className="text-lg font-bold text-slate-200 mt-0.5">
                        {point.technical_debt_minutes}m
                      </div>
                    </div>

                    <div className="bg-slate-950 rounded-lg p-2.5">
                      <div className="text-xs text-slate-400">Issues</div>
                      <div className="text-lg font-bold text-slate-200 mt-0.5">
                        {point.total_issues_count}
                      </div>
                    </div>

                    <div className="bg-slate-950 rounded-lg p-2.5">
                      <div className="text-xs text-slate-400">Maintainability</div>
                      <div className="text-sm font-semibold text-slate-300 mt-1">
                        {point.maintainability_score.toFixed(1)}
                      </div>
                    </div>

                    <div className="bg-slate-950 rounded-lg p-2.5">
                      <div className="text-xs text-slate-400">Complexity</div>
                      <div className="text-sm font-semibold text-slate-300 mt-1">
                        {point.complexity_score.toFixed(1)}
                      </div>
                    </div>

                    <div className="bg-slate-950 rounded-lg p-2.5">
                      <div className="text-xs text-slate-400">Duplication</div>
                      <div className="text-sm font-semibold text-slate-300 mt-1">
                        {point.duplication_score.toFixed(1)}
                      </div>
                    </div>
                  </div>

                  {point.commit_message && (
                    <p className="text-xs text-slate-400 mt-3 italic truncate">
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
