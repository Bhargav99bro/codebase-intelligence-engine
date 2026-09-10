import React, { useState, useEffect, useRef } from "react";
import {
  Search,
  ExternalLink,
  FolderGit2,
  FileCode2,
  AlertCircle,
  Layers,
  FileText,
  HardDrive,
  GitCommit,
  RefreshCw,
  Play,
  Download,
} from "lucide-react";
import { apiService } from "../services/api";
import { AnalysisJobResponse } from "../types/api";
import { SymbolExplorer } from "./SymbolExplorer";
import { ComplexityDashboard } from "./ComplexityDashboard";
import { FileMetricsTable } from "./FileMetricsTable";
import { HotspotExplorer } from "./HotspotExplorer";
import { DependencyDashboard } from "./DependencyDashboard";
import { HealthDashboard } from "./HealthDashboard";
import { CodebaseTreemap } from "./CodebaseTreemap";
import { HotspotsView } from "./HotspotsView";
import { QualityGateBadge } from "./QualityGateBadge";
import { ExportModal } from "./ExportModal";
import { AnalysisProgressBar } from "./AnalysisProgressBar";
import { AnalysisDiffView } from "./AnalysisDiffView";
import { DuplicationView } from "./DuplicationView";
import { ChurnMatrixView } from "./ChurnMatrixView";
import { TimelineView } from "./TimelineView";

const QUICK_EXAMPLES = [
  "https://github.com/octocat/Hello-World",
  "https://github.com/pallets/flask",
  "https://github.com/tiangolo/fastapi",
];

const LANGUAGE_COLORS: Record<string, string> = {
  Python: "bg-blue-500",
  TypeScript: "bg-indigo-500",
  JavaScript: "bg-amber-400",
  Java: "bg-red-500",
  Go: "bg-cyan-400",
  Rust: "bg-orange-600",
  C: "bg-slate-400",
  "C++": "bg-pink-500",
  HTML: "bg-rose-500",
  CSS: "bg-purple-500",
  JSON: "bg-yellow-500",
  YAML: "bg-emerald-500",
  Markdown: "bg-sky-400",
  Dockerfile: "bg-teal-500",
};

export const RepositoryIngestion: React.FC = () => {
  const [repoUrl, setRepoUrl] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [job, setJob] = useState<AnalysisJobResponse | null>(null);
  const [runningAnalysisId, setRunningAnalysisId] = useState<string | null>(null);
  const [showExportModal, setShowExportModal] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<
    | "health"
    | "diff"
    | "duplication"
    | "churn"
    | "timeline"
    | "treemap"
    | "hotspots_qg"
    | "dependencies"
    | "quality"
    | "files"
    | "hotspots"
    | "symbols"
  >("health");

  const pollTimerRef = useRef<number | null>(null);

  const clearPolling = () => {
    if (pollTimerRef.current) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  useEffect(() => {
    return () => clearPolling();
  }, []);

  const startPolling = (id: string) => {
    clearPolling();
    const poll = async () => {
      try {
        const data = await apiService.getAnalysis(id);
        setJob(data);

        if (data.status === "completed" || data.status === "failed") {
          setLoading(false);
          clearPolling();
        }
      } catch (err: any) {
        clearPolling();
        setLoading(false);
        setError("Failed to fetch analysis progress.");
      }
    };

    // Poll immediately, then every 1.5s
    poll();
    pollTimerRef.current = window.setInterval(poll, 1500);
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = repoUrl.trim();
    if (!trimmed) {
      setError("Please provide a valid GitHub repository URL.");
      return;
    }

    if (!trimmed.toLowerCase().startsWith("https://github.com/")) {
      setError("Only public HTTPS GitHub URLs (https://github.com/owner/repo) are supported.");
      return;
    }

    setError(null);
    setLoading(true);
    setJob(null);

    try {
      const initialJob = await apiService.analyzeRepository({ repository_url: trimmed });
      setRunningAnalysisId(initialJob.analysis_id);
      startPolling(initialJob.analysis_id);
    } catch (err: any) {
      setLoading(false);
      const detail = err.response?.data?.detail || err.message || "Failed to submit repository for ingestion.";
      setError(detail);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };


  return (
    <div className="bg-slate-900/40 border border-slate-800/80 rounded-lg p-5 space-y-5">
      <div className="border-b border-slate-800/80 pb-3">
        <div className="flex items-center space-x-2">
          <FolderGit2 className="w-4 h-4 text-indigo-400" />
          <h2 className="text-base font-semibold text-slate-100 tracking-tight">Repository Ingestion & Pipeline</h2>
          <span className="text-[11px] px-2 py-0.5 rounded bg-slate-850 text-slate-400 border border-slate-750 font-mono">
            Static AST Engine
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Submit a public GitHub or GitLab repository. The engine performs an isolated shallow clone, enforces resource quotas, discovers files, and executes multilingual AST parsing.
        </p>
      </div>

      {/* URL Input Form */}
      <form onSubmit={handleAnalyze} className="space-y-3">
        <div className="flex flex-col sm:flex-row gap-2.5">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/owner/repository"
              disabled={loading}
              className="w-full bg-slate-950 border border-slate-800 rounded pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 font-mono transition"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !repoUrl.trim()}
            className="flex items-center justify-center space-x-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded transition shrink-0"
          >
            {loading ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Ingesting...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Analyze</span>
              </>
            )}
          </button>
        </div>

        {/* Quick Example Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-0.5 text-xs text-slate-400">
          <span className="font-mono text-[11px] text-slate-500">Quick test:</span>
          {QUICK_EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setRepoUrl(ex)}
              disabled={loading}
              className="px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-850 text-slate-400 hover:text-slate-200 border border-slate-800 font-mono transition text-[11px]"
            >
              {ex.replace("https://github.com/", "")}
            </button>
          ))}
        </div>
      </form>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-semibold text-rose-200">Ingestion Error</div>
            <div className="text-xs text-rose-300 leading-relaxed font-mono">{error}</div>
          </div>
        </div>
      )}

      {/* In-Progress Pipeline Card with SSE & Cancellation */}
      {loading && (runningAnalysisId || (job && job.status !== "completed" && job.status !== "failed")) && (
        <AnalysisProgressBar
          analysisId={runningAnalysisId || job!.id}
          initialJob={job}
          onComplete={(completedJob) => {
            setJob(completedJob);
            setLoading(false);
            setRunningAnalysisId(null);
          }}
          onError={(msg) => {
            setError(msg);
            setLoading(false);
            setRunningAnalysisId(null);
          }}
          onCancelled={() => {
            setError("Analysis was cancelled by user. Workspace has been safely cleaned up.");
            setLoading(false);
            setRunningAnalysisId(null);
          }}
        />
      )}

      {/* Completed Ingestion Result Card */}
      {job && job.status === "completed" && (
        <div className="p-6 rounded-xl bg-slate-950/70 border border-emerald-500/30 space-y-6 animate-in fade-in">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-2">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono uppercase text-slate-400">Repository</span>
                <span className="text-xs px-2 py-0.5 rounded font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Ready for Analysis
                </span>
              </div>
              <div className="flex items-center space-x-2 mt-1">
                <h3 className="text-xl font-bold text-white font-mono">
                  {job.owner} / {job.name}
                </h3>
                <a
                  href={job.repository_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-slate-400 hover:text-indigo-400 transition"
                  title="Open on GitHub"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 self-start sm:self-center">
              <QualityGateBadge analysisId={job.id} />

              <button
                onClick={() => setShowExportModal(true)}
                className="flex items-center px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-sm transition"
              >
                <Download className="w-3.5 h-3.5 mr-1.5" />
                Export
              </button>

              <button
                onClick={() => {
                  setJob(null);
                  setRepoUrl("");
                }}
                className="text-xs font-mono text-indigo-400 hover:text-indigo-300 ml-1"
              >
                Analyze Another &rarr;
              </button>
            </div>
          </div>

          <ExportModal
            isOpen={showExportModal}
            onClose={() => setShowExportModal(false)}
            analysisId={job.id}
          />

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
            <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
              <div className="text-xs text-slate-400 flex items-center space-x-1.5 mb-1">
                <FileCode2 className="w-3.5 h-3.5 text-indigo-400" />
                <span>Total Files</span>
              </div>
              <div className="text-xl font-bold font-mono text-white">{job.total_files}</div>
              <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                {job.analyzable_files} analyzable
              </div>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
              <div className="text-xs text-slate-400 flex items-center space-x-1.5 mb-1">
                <FileText className="w-3.5 h-3.5 text-cyan-400" />
                <span>Lines of Code</span>
              </div>
              <div className="text-xl font-bold font-mono text-white">
                {job.total_lines.toLocaleString()}
              </div>
              <div className="text-[11px] text-slate-500 font-mono mt-0.5">Discovered source</div>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
              <div className="text-xs text-slate-400 flex items-center space-x-1.5 mb-1">
                <HardDrive className="w-3.5 h-3.5 text-amber-400" />
                <span>Repository Size</span>
              </div>
              <div className="text-xl font-bold font-mono text-white">
                {formatBytes(job.total_bytes)}
              </div>
              <div className="text-[11px] text-slate-500 font-mono mt-0.5">Uncompressed disk</div>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
              <div className="text-xs text-slate-400 flex items-center space-x-1.5 mb-1">
                <GitCommit className="w-3.5 h-3.5 text-rose-400" />
                <span>HEAD Commit</span>
              </div>
              <div className="text-sm font-bold font-mono text-slate-200 truncate" title={job.commit_hash || ""}>
                {job.commit_hash ? job.commit_hash.substring(0, 8) : "N/A"}
              </div>
              <div className="text-[11px] text-slate-500 font-mono mt-0.5 truncate">
                {job.metadata_json?.branch || "main"} branch
              </div>
            </div>
          </div>

          {/* Language Distribution */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between text-xs font-mono text-slate-300">
              <span className="flex items-center space-x-1.5">
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                <span>Language Distribution ({Object.keys(job.language_distribution).length} detected)</span>
              </span>
            </div>

            {/* Segmented Progress Bar */}
            <div className="h-3 w-full bg-slate-900 rounded-full flex overflow-hidden border border-slate-800">
              {Object.entries(job.language_distribution).map(([lang, pct]) => (
                <div
                  key={lang}
                  className={`${LANGUAGE_COLORS[lang] || "bg-slate-500"} transition-all duration-500`}
                  style={{ width: `${pct}%` }}
                  title={`${lang}: ${pct}%`}
                />
              ))}
            </div>

            {/* Language Pills */}
            <div className="flex flex-wrap gap-2 pt-1">
              {Object.entries(job.language_distribution).map(([lang, pct]) => (
                <div
                  key={lang}
                  className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-xs font-mono"
                >
                  <span className={`w-2 h-2 rounded-full ${LANGUAGE_COLORS[lang] || "bg-slate-500"}`} />
                  <span className="text-slate-300 font-medium">{lang}</span>
                  <span className="text-slate-500">{pct}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* Analysis View Tabs */}
          <div className="pt-4 border-t border-slate-800">
            <div className="flex border-b border-slate-800 gap-2 mb-6 overflow-x-auto pb-1">
              <button
                onClick={() => setActiveTab("health")}
                className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === "health"
                    ? "border-cyan-400 text-cyan-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                <span>Health & Issues</span>
                {job.health_summary && (
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                    {job.health_summary.grade} ({job.health_summary.overall_score?.toFixed(0)})
                  </span>
                )}
              </button>
              <button
                onClick={() => setActiveTab("diff")}
                className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === "diff"
                    ? "border-indigo-400 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Diff & PR Gate
              </button>
              <button
                onClick={() => setActiveTab("duplication")}
                className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === "duplication"
                    ? "border-purple-400 text-purple-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Duplication
                {job.health_summary?.duplication_ratio !== undefined && (
                  <span className="ml-1.5 px-1.5 py-0.2 rounded text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    {job.health_summary.duplication_ratio.toFixed(1)}%
                  </span>
                )}
              </button>
              <button
                onClick={() => setActiveTab("churn")}
                className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === "churn"
                    ? "border-orange-400 text-orange-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Git Churn
              </button>
              <button
                onClick={() => setActiveTab("timeline")}
                className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === "timeline"
                    ? "border-blue-400 text-blue-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Timeline
              </button>
              <button
                onClick={() => setActiveTab("treemap")}
                className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === "treemap"
                    ? "border-emerald-400 text-emerald-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Codebase Treemap
              </button>
              <button
                onClick={() => setActiveTab("hotspots_qg")}
                className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === "hotspots_qg"
                    ? "border-amber-400 text-amber-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Hotspots Matrix
              </button>
              <button
                onClick={() => setActiveTab("dependencies")}
                className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === "dependencies"
                    ? "border-indigo-400 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Dependencies & Architecture
              </button>
              <button
                onClick={() => setActiveTab("quality")}
                className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === "quality"
                    ? "border-cyan-400 text-cyan-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Complexity & Maintainability
              </button>
              <button
                onClick={() => setActiveTab("files")}
                className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === "files"
                    ? "border-cyan-400 text-cyan-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                File Metrics Table
              </button>
              <button
                onClick={() => setActiveTab("hotspots")}
                className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === "hotspots"
                    ? "border-rose-400 text-rose-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Quality Hotspots
              </button>
              <button
                onClick={() => setActiveTab("symbols")}
                className={`pb-2.5 px-3 text-xs font-semibold tracking-wide border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === "symbols"
                    ? "border-indigo-400 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Structural Symbols ({job.total_symbols || 0})
              </button>
            </div>

            {/* Tab Views */}
            {activeTab === "health" && <HealthDashboard analysisId={job.id} />}
            {activeTab === "diff" && (
              <AnalysisDiffView
                currentAnalysisId={job.id}
                defaultBaseAnalysisId={job.base_analysis_id}
              />
            )}
            {activeTab === "duplication" && <DuplicationView analysisId={job.id} />}
            {activeTab === "churn" && <ChurnMatrixView analysisId={job.id} />}
            {activeTab === "timeline" && <TimelineView repositoryId={job.repository_id} />}
            {activeTab === "treemap" && <CodebaseTreemap analysisId={job.id} />}
            {activeTab === "hotspots_qg" && <HotspotsView analysisId={job.id} />}
            {activeTab === "dependencies" && <DependencyDashboard analysisId={job.id} />}
            {activeTab === "quality" && <ComplexityDashboard analysisId={job.id} />}
            {activeTab === "files" && <FileMetricsTable analysisId={job.id} />}
            {activeTab === "hotspots" && <HotspotExplorer analysisId={job.id} />}
            {activeTab === "symbols" && (
              <SymbolExplorer
                analysisId={job.id}
                totalSymbols={job.total_symbols}
                symbolDistribution={job.symbol_distribution}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};
