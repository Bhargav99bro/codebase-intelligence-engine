import React, { useState, useEffect } from "react";
import {
  Activity,
  Info,
} from "lucide-react";
import { ChurnResponse } from "../types/api";
import { apiService } from "../services/api";

interface ChurnMatrixViewProps {
  analysisId: string;
}

export const ChurnMatrixView: React.FC<ChurnMatrixViewProps> = ({ analysisId }) => {
  const [data, setData] = useState<ChurnResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    apiService
      .getAnalysisChurn(analysisId, 100, 0)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.response?.data?.detail || "Failed to load git churn metrics");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [analysisId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-slate-900 border border-slate-800 rounded-xl">
        <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-slate-400 text-sm">Parsing git log history and calculating relative churn scores...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl text-center">
        <p className="text-rose-400 text-sm">{error || "No churn metrics available"}</p>
      </div>
    );
  }

  const filteredMetrics = data.churn_metrics.filter((m) =>
    m.file_path.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-400">Git History Status</div>
          <div className="flex items-center gap-2 mt-2">
            <span
              className={`inline-block w-2.5 h-2.5 rounded-full ${
                data.has_git_history ? "bg-emerald-400" : "bg-slate-500"
              }`}
            />
            <span className="text-lg font-bold text-white">
              {data.has_git_history ? "100-Commit History Available" : "Zero-State (No History)"}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {data.has_git_history
              ? "Machine-readable numstat churn active"
              : "Defect hotspot fallback to static hotspot"}
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-400">Tracked Files in History</div>
          <div className="text-3xl font-bold text-slate-200 mt-2">{data.total_files}</div>
          <p className="text-xs text-slate-500 mt-1">Files modified in shallow history window</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-400">Max Relative Churn</div>
          <div className="text-3xl font-bold text-indigo-400 mt-2">{data.max_churn.toFixed(1)}%</div>
          <p className="text-xs text-slate-500 mt-1">Peak file volatility score</p>
        </div>
      </div>

      {/* Filter and Search */}
      <div className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-indigo-400" />
          <h3 className="text-sm font-semibold text-white">Git Churn Volatility Matrix</h3>
        </div>

        <input
          type="text"
          placeholder="Filter files..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-64"
        />
      </div>

      {/* Churn Table */}
      {filteredMetrics.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
          <Info className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-white">No File Churn Recorded</h3>
          <p className="text-sm text-slate-400 mt-1">
            No git modification activity was recorded for the selected filter or repository.
          </p>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase font-semibold">
                <tr>
                  <th className="px-4 py-3">File Path</th>
                  <th className="px-4 py-3 text-center">Commits</th>
                  <th className="px-4 py-3 text-right">Additions</th>
                  <th className="px-4 py-3 text-right">Deletions</th>
                  <th className="px-4 py-3 text-right">Net Churn</th>
                  <th className="px-4 py-3">Relative Churn (C_churn)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredMetrics.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 font-mono text-slate-200">{item.file_path}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 font-semibold text-slate-300">
                        {item.commit_count}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-emerald-400 font-mono">
                      +{item.insertions}
                    </td>
                    <td className="px-4 py-3 text-right text-rose-400 font-mono">
                      -{item.deletions}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-300 font-mono font-semibold">
                      {item.churn_lines}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                          <div
                            className={`h-full rounded-full ${
                              item.churn_score > 70
                                ? "bg-rose-500"
                                : item.churn_score > 40
                                ? "bg-amber-500"
                                : "bg-indigo-500"
                            }`}
                            style={{ width: `${Math.min(100, item.churn_score)}%` }}
                          />
                        </div>
                        <span className="font-semibold text-slate-300">{item.churn_score.toFixed(1)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
