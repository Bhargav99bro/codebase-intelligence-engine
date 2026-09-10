import React, { useState, useEffect, useRef } from "react";
import {
  RefreshCw,
  AlertCircle,
  XOctagon,
  Terminal,
} from "lucide-react";
import { AnalysisJobResponse } from "../types/api";
import { apiService } from "../services/api";

interface AnalysisProgressBarProps {
  analysisId: string;
  initialJob: AnalysisJobResponse | null;
  onComplete: (job: AnalysisJobResponse) => void;
  onError: (errorMsg: string) => void;
  onCancelled: () => void;
}

export const AnalysisProgressBar: React.FC<AnalysisProgressBarProps> = ({
  analysisId,
  initialJob,
  onComplete,
  onError,
  onCancelled,
}) => {
  const [job, setJob] = useState<AnalysisJobResponse | null>(initialJob);
  const [cancelling, setCancelling] = useState(false);
  const [cancelMessage, setCancelMessage] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollTimerRef = useRef<number | null>(null);

  // Stop all streaming and polling
  const cleanup = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (pollTimerRef.current) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  // Polling fallback
  const startPolling = () => {
    if (pollTimerRef.current) return;
    pollTimerRef.current = window.setInterval(async () => {
      try {
        const data = await apiService.getAnalysis(analysisId);
        setJob(data);
        if (data.status === "completed") {
          cleanup();
          onComplete(data);
        } else if (data.status === "failed") {
          cleanup();
          onError(data.error_message || "Analysis failed");
        } else if (data.status === "cancelled") {
          cleanup();
          onCancelled();
        }
      } catch (err) {
        console.error("Polling error", err);
      }
    }, 1500);
  };

  useEffect(() => {
    let active = true;

    // Connect to Server-Sent Events (SSE)
    const baseApi = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : "/api/v1";
    const sseUrl = `${baseApi}/analyses/${analysisId}/events`;

    try {
      const es = new EventSource(sseUrl);
      eventSourceRef.current = es;

      es.addEventListener("stage", (event) => {
        if (!active) return;
        try {
          const parsed = JSON.parse(event.data);
          setJob((prev) => (prev ? { ...prev, ...parsed } : (parsed as any)));
        } catch (e) {
          console.error("Error parsing SSE stage event", e);
        }
      });

      es.addEventListener("log", (event) => {
        if (!active) return;
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.message) {
            setLogs((prev) => [...prev.slice(-4), parsed.message]);
          }
        } catch (e) {
          console.error("Error parsing SSE log event", e);
        }
      });

      es.addEventListener("complete", (_event) => {
        if (!active) return;
        cleanup();
        // Fetch full complete job
        apiService.getAnalysis(analysisId).then((data) => {
          if (active) onComplete(data);
        });
      });

      es.addEventListener("cancelled", (_event) => {
        if (!active) return;
        cleanup();
        onCancelled();
      });

      es.addEventListener("error", (_event) => {
        if (!active) return;
        // If SSE fails or disconnects, fall back to polling
        if (es.readyState === EventSource.CLOSED) {
          es.close();
          startPolling();
        }
      });
    } catch (e) {
      console.warn("SSE not available, falling back to polling", e);
      startPolling();
    }

    return () => {
      active = false;
      cleanup();
    };
  }, [analysisId]);

  const handleCancel = async () => {
    if (cancelling) return;
    const confirm = window.confirm("Are you sure you want to cancel the analysis? Workspace data will be cleaned up safely.");
    if (!confirm) return;

    setCancelling(true);
    setCancelMessage("Requesting cancellation...");

    try {
      const res = await apiService.cancelAnalysis(analysisId);
      setCancelMessage(res.message);
    } catch (err: any) {
      setCancelling(false);
      const detail = err.response?.data?.detail || "Failed to cancel analysis.";
      setCancelMessage(`Cancel rejected: ${detail}`);
    }
  };

  const getStageBadge = (stage?: string) => {
    switch (stage) {
      case "cloning":
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">CLONING REPOSITORY</span>;
      case "file_discovery":
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">FILE DISCOVERY</span>;
      case "parsing":
      case "parsing_symbols":
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-purple-500/20 text-purple-400 border border-purple-500/30">EXTRACTING AST</span>;
      case "analyzing_metrics":
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-amber-500/20 text-amber-400 border border-amber-500/30">CODE METRICS</span>;
      case "analyzing_dependencies":
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">DEPENDENCIES</span>;
      case "evaluating_health":
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-pink-500/20 text-pink-400 border border-pink-500/30">HEALTH & QUALITY GATES</span>;
      case "persisting":
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-amber-500/20 text-amber-400 border border-amber-500/30">PERSISTING METADATA</span>;
      case "cancellation_requested":
      case "cancelling":
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse">CANCELLATION REQUESTED</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-slate-800 text-slate-400 border border-slate-700">ANALYZING</span>;
    }
  };

  const progressPct = Math.max(job?.progress ?? 5, 5);

  return (
    <div className="p-5 rounded-xl bg-slate-950/70 border border-indigo-500/30 space-y-4 shadow-xl animate-in fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <RefreshCw className="w-4 h-4 text-indigo-400 animate-spin" />
          <span className="text-sm font-semibold text-white">Live Ingestion & Analysis Stream</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
            SSE Live
          </span>
        </div>

        <div className="flex items-center space-x-3">
          {getStageBadge(job?.stage)}

          {/* Cancel Analysis Button */}
          <button
            onClick={handleCancel}
            disabled={cancelling}
            className="flex items-center px-2.5 py-1 text-xs font-medium rounded-md bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 transition disabled:opacity-50"
            title="Cooperatively cancel this analysis job"
          >
            <XOctagon className="w-3.5 h-3.5 mr-1 text-rose-400" />
            {cancelling ? "Cancelling..." : "Cancel Analysis"}
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs font-mono text-slate-400">
          <span className="truncate pr-4">{job?.message || "Running pipeline stages..."}</span>
          <span className="font-bold text-indigo-400">{progressPct}%</span>
        </div>
        <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 rounded-full ${
              cancelling
                ? "bg-rose-500"
                : "bg-gradient-to-r from-indigo-500 via-cyan-400 to-emerald-400"
            }`}
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Real-time Status Logs */}
      {logs.length > 0 && (
        <div className="p-2.5 rounded-lg bg-slate-900/90 border border-slate-800 text-[11px] font-mono text-slate-400 space-y-1">
          <div className="flex items-center text-slate-500 text-[10px] mb-0.5">
            <Terminal className="w-3 h-3 mr-1" />
            <span>Telemetry stream</span>
          </div>
          {logs.map((log, i) => (
            <div key={i} className="truncate text-slate-300">
              &gt; {log}
            </div>
          ))}
        </div>
      )}

      {/* Cancellation Banner */}
      {cancelMessage && (
        <div className="p-2.5 rounded-lg bg-rose-950/30 border border-rose-900/50 text-xs text-rose-300 flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{cancelMessage}</span>
        </div>
      )}
    </div>
  );
};
