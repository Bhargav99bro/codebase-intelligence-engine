import React, { useEffect, useState, useCallback } from "react";
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw, Database, Server, Cpu, Clock, Terminal } from "lucide-react";
import { apiService } from "../services/api";
import { HealthResponse } from "../types/api";

export const HealthStatus: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [showRaw, setShowRaw] = useState<boolean>(false);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    const start = performance.now();
    try {
      const data = await apiService.getHealth();
      setLatencyMs(Math.round(performance.now() - start));
      setHealth(data);
    } catch (err: any) {
      setLatencyMs(Math.round(performance.now() - start));
      const message = err.response?.data?.detail || err.message || "Failed to reach backend API";
      setError(message);
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    // Auto-poll health every 15 seconds
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case "connected":
      case "healthy":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            Operational
          </span>
        );
      case "degraded":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3 h-3 mr-1" />
            Degraded
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3 h-3 mr-1" />
            Disconnected
          </span>
        );
    }
  };

  return (
    <div className="bg-slate-900/40 border border-slate-800/80 rounded-lg p-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800/80 gap-3">
        <div>
          <div className="flex items-center space-x-2.5">
            <h2 className="text-base font-semibold text-slate-100 tracking-tight">System & Infrastructure Status</h2>
            {health && renderStatusBadge(health.status)}
            {error && renderStatusBadge("disconnected")}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Live health probes monitoring FastAPI ASGI, PostgreSQL 16 pool, and Redis 7 broker.
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          {latencyMs !== null && (
            <span className="text-[11px] font-mono text-slate-400 flex items-center bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
              <Clock className="w-3 h-3 mr-1 text-slate-500" />
              {latencyMs}ms RTT
            </span>
          )}
          <button
            onClick={fetchStatus}
            disabled={loading}
            className="flex items-center space-x-1 px-2.5 py-1 text-xs font-mono text-slate-300 bg-slate-900 hover:bg-slate-850 border border-slate-800 rounded transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 text-slate-400 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="my-4 p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-start space-x-3">
          <XCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold">Backend Unreachable</div>
            <div className="text-xs text-rose-400/90 mt-0.5">{error}</div>
            <div className="text-xs text-slate-400 mt-2">
              Ensure the FastAPI backend is running at <code className="bg-rose-950/60 px-1 py-0.5 rounded text-rose-200">http://localhost:8000</code> or via Docker Compose.
            </div>
          </div>
        </div>
      )}

      {/* Grid of Subsystems */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        {/* API Card */}
        <div className="p-4 rounded-lg bg-slate-950/50 border border-slate-800 hover:border-slate-700 transition">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2 text-indigo-400">
              <Server className="w-4 h-4" />
              <span className="text-sm font-semibold text-slate-200">FastAPI ASGI Engine</span>
            </div>
            {health ? renderStatusBadge(health.services.api.status) : renderStatusBadge("disconnected")}
          </div>
          <div className="text-xs text-slate-400 space-y-1 font-mono">
            <div>Version: <span className="text-slate-300">{health?.version || "—"}</span></div>
            <div>Env: <span className="text-slate-300">{health?.environment || "—"}</span></div>
            <div className="text-[11px] text-slate-500 truncate">{health?.services.api.details || "Awaiting connection..."}</div>
          </div>
        </div>

        {/* PostgreSQL Card */}
        <div className="p-4 rounded-lg bg-slate-950/50 border border-slate-800 hover:border-slate-700 transition">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2 text-cyan-400">
              <Database className="w-4 h-4" />
              <span className="text-sm font-semibold text-slate-200">PostgreSQL 16</span>
            </div>
            {health ? renderStatusBadge(health.services.database.status) : renderStatusBadge("disconnected")}
          </div>
          <div className="text-xs text-slate-400 space-y-1 font-mono">
            <div>Driver: <span className="text-slate-300">asyncpg / SQLAlchemy 2.0</span></div>
            <div>Pool: <span className="text-slate-300">Async Pool Active</span></div>
            <div className="text-[11px] text-slate-500 truncate">{health?.services.database.details || "Awaiting probe..."}</div>
          </div>
        </div>

        {/* Redis Card */}
        <div className="p-4 rounded-lg bg-slate-950/50 border border-slate-800 hover:border-slate-700 transition">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2 text-rose-400">
              <Cpu className="w-4 h-4" />
              <span className="text-sm font-semibold text-slate-200">Redis 7 Broker</span>
            </div>
            {health ? renderStatusBadge(health.services.redis.status) : renderStatusBadge("disconnected")}
          </div>
          <div className="text-xs text-slate-400 space-y-1 font-mono">
            <div>Client: <span className="text-slate-300">redis.asyncio</span></div>
            <div>Purpose: <span className="text-slate-300">Celery Broker / State</span></div>
            <div className="text-[11px] text-slate-500 truncate">{health?.services.redis.details || "Awaiting probe..."}</div>
          </div>
        </div>
      </div>

      {/* Raw Payload Accordion */}
      <div className="mt-6 pt-4 border-t border-slate-800/60">
        <button
          onClick={() => setShowRaw(!showRaw)}
          className="text-xs font-mono text-indigo-400 hover:text-indigo-300 flex items-center space-x-1"
        >
          <Terminal className="w-3.5 h-3.5 mr-1" />
          <span>{showRaw ? "Hide Raw Health Payload" : "View Raw Health API Payload"}</span>
        </button>

        {showRaw && (
          <pre className="mt-3 p-3 bg-slate-950 rounded-lg text-xs font-mono text-slate-300 overflow-x-auto border border-slate-800">
            {JSON.stringify(health || { error: error || "No data" }, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
};
