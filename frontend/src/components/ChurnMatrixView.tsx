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
      <div className="flex flex-col items-center justify-center p-12 bg-white border border-slate-200 rounded-lg shadow-sm">
        <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-slate-600 text-xs">Parsing git log history and calculating relative churn scores...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-white border border-slate-200 rounded-lg text-center text-xs text-rose-600 shadow-sm">
        <p>{error || "No churn metrics available"}</p>
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
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Git History Status</div>
          <div className="flex items-center gap-2 mt-1.5">
            <span
              className={`inline-block w-2.5 h-2.5 rounded-full ${
                data.has_git_history ? "bg-emerald-500" : "bg-slate-400"
              }`}
            />
            <span className="text-base font-bold text-slate-900">
              {data.has_git_history ? "100-Commit History Available" : "Zero-State (No History)"}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {data.has_git_history
              ? "Machine-readable numstat churn active"
              : "Defect hotspot fallback to static hotspot"}
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Tracked Files in History</div>
          <div className="text-2xl font-bold font-mono text-slate-900 mt-1">{data.total_files}</div>
          <p className="text-xs text-slate-500 mt-1">Files modified in shallow history window</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Max Relative Churn</div>
          <div className="text-2xl font-bold font-mono text-indigo-600 mt-1">{data.max_churn.toFixed(1)}%</div>
          <p className="text-xs text-slate-500 mt-1">Peak file volatility score</p>
        </div>
      </div>

      {/* Filter and Search */}
      <div className="flex items-center justify-between bg-white border border-slate-200 rounded-lg p-3 shadow-sm">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-indigo-600" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-800">Git Churn Volatility Matrix</h3>
        </div>

        <input
          type="text"
          placeholder="Filter files..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="bg-white border border-slate-300 rounded-md px-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 font-mono w-64 transition"
        />
      </div>

      {/* Churn Table */}
      {filteredMetrics.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center shadow-sm">
          <Info className="w-10 h-10 text-slate-400 mx-auto mb-2" />
          <h3 className="text-sm font-semibold text-slate-900">No File Churn Recorded</h3>
          <p className="text-xs text-slate-500 mt-1">
            No git modification activity was recorded for the selected filter or repository.
          </p>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 uppercase font-semibold text-[11px] tracking-wider">
                <tr>
                  <th className="px-4 py-2.5">File Path</th>
                  <th className="px-4 py-2.5 text-center">Commits</th>
                  <th className="px-4 py-2.5 text-right">Additions</th>
                  <th className="px-4 py-2.5 text-right">Deletions</th>
                  <th className="px-4 py-2.5 text-right">Net Churn</th>
                  <th className="px-4 py-2.5">Relative Churn (C_churn)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredMetrics.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/80 transition">
                    <td className="px-4 py-2.5 font-mono text-slate-800">{item.file_path}</td>
                    <td className="px-4 py-2.5 text-center">
                      <span className="bg-slate-100 px-2 py-0.5 rounded border border-slate-200 font-semibold text-slate-700">
                        {item.commit_count}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right text-emerald-700 font-mono font-medium">
                      +{item.insertions}
                    </td>
                    <td className="px-4 py-2.5 text-right text-rose-700 font-mono font-medium">
                      -{item.deletions}
                    </td>
                    <td className="px-4 py-2.5 text-right text-slate-900 font-mono font-semibold">
                      {item.churn_lines}
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
                          <div
                            className={`h-full rounded-full ${
                              item.churn_score > 70
                                ? "bg-rose-500"
                                : item.churn_score > 40
                                ? "bg-amber-500"
                                : "bg-indigo-600"
                            }`}
                            style={{ width: `${Math.min(100, item.churn_score)}%` }}
                          />
                        </div>
                        <span className="font-semibold text-slate-800">{item.churn_score.toFixed(1)}%</span>
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
