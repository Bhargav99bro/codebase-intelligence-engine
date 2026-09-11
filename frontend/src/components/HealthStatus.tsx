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
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            Operational
          </span>
        );
      case "degraded":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3 h-3 mr-1" />
            Degraded
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
            <XCircle className="w-3 h-3 mr-1" />
            Disconnected
          </span>
        );
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
        <div>
          <div className="flex items-center space-x-2.5">
            <h2 className="text-base font-semibold text-slate-900 tracking-tight">System & Infrastructure Status</h2>
            {health && renderStatusBadge(health.status)}
            {error && renderStatusBadge("disconnected")}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Live health probes monitoring FastAPI ASGI, PostgreSQL 16 pool, and Redis 7 broker.
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          {latencyMs !== null && (
            <span className="text-[11px] font-mono text-slate-600 flex items-center bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
              <Clock className="w-3 h-3 mr-1 text-slate-500" />
              {latencyMs}ms RTT
            </span>
          )}
          <button
            onClick={fetchStatus}
            disabled={loading}
            className="flex items-center space-x-1 px-2.5 py-1 text-xs font-mono text-slate-700 bg-slate-100 hover:bg-slate-200/70 border border-slate-200 rounded transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 text-slate-500 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="my-4 p-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start space-x-3">
          <XCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-rose-900">Backend Unreachable</div>
            <div className="text-xs text-rose-700 mt-0.5">{error}</div>
            <div className="text-xs text-slate-600 mt-2">
              Ensure the FastAPI backend is running at <code className="bg-rose-100 px-1 py-0.5 rounded text-rose-800 font-mono">http://localhost:8000</code> or via Docker Compose.
            </div>
          </div>
        </div>
      )}

      {/* Grid of Subsystems */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        {/* API Card */}
        <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 hover:border-slate-300 transition">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2 text-indigo-600">
              <Server className="w-4 h-4" />
              <span className="text-sm font-semibold text-slate-800">FastAPI ASGI Engine</span>
            </div>
            {health ? renderStatusBadge(health.services.api.status) : renderStatusBadge("disconnected")}
          </div>
          <div className="text-xs text-slate-600 space-y-1 font-mono">
            <div>Version: <span className="text-slate-800">{health?.version || "—"}</span></div>
            <div>Env: <span className="text-slate-800">{health?.environment || "—"}</span></div>
            <div className="text-[11px] text-slate-500 truncate">{health?.services.api.details || "Awaiting connection..."}</div>
          </div>
        </div>

        {/* PostgreSQL Card */}
        <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 hover:border-slate-300 transition">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2 text-slate-700">
              <Database className="w-4 h-4" />
              <span className="text-sm font-semibold text-slate-800">PostgreSQL 16</span>
            </div>
            {health ? renderStatusBadge(health.services.database.status) : renderStatusBadge("disconnected")}
          </div>
          <div className="text-xs text-slate-600 space-y-1 font-mono">
            <div>Driver: <span className="text-slate-800">asyncpg / SQLAlchemy 2.0</span></div>
            <div>Pool: <span className="text-slate-800">Async Pool Active</span></div>
            <div className="text-[11px] text-slate-500 truncate">{health?.services.database.details || "Awaiting probe..."}</div>
          </div>
        </div>

        {/* Redis Card */}
        <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 hover:border-slate-300 transition">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2 text-slate-700">
              <Cpu className="w-4 h-4" />
              <span className="text-sm font-semibold text-slate-800">Redis 7 Broker</span>
            </div>
            {health ? renderStatusBadge(health.services.redis.status) : renderStatusBadge("disconnected")}
          </div>
          <div className="text-xs text-slate-600 space-y-1 font-mono">
            <div>Client: <span className="text-slate-800">redis.asyncio</span></div>
            <div>Purpose: <span className="text-slate-800">Celery Broker / State</span></div>
            <div className="text-[11px] text-slate-500 truncate">{health?.services.redis.details || "Awaiting probe..."}</div>
          </div>
        </div>
      </div>

      {/* Raw Payload Accordion */}
      <div className="mt-6 pt-4 border-t border-slate-200">
        <button
          onClick={() => setShowRaw(!showRaw)}
          className="text-xs font-mono text-indigo-600 hover:text-indigo-700 flex items-center space-x-1"
        >
          <Terminal className="w-3.5 h-3.5 mr-1" />
          <span>{showRaw ? "Hide Raw Health Payload" : "View Raw Health API Payload"}</span>
        </button>

        {showRaw && (
          <pre className="mt-3 p-3 bg-slate-50 rounded-lg text-xs font-mono text-slate-800 overflow-x-auto border border-slate-200">
            {JSON.stringify(health || { error: error || "No data" }, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
};
