import React, { useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Cpu,
  FileCode,
  Flame,
  Info,
  Layers,
  Search,
  Shield,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import { apiService } from "../services/api";
import {
  HealthScoreResponse,
  IssueItem,
  IssuesListResponse,
  RecommendationItem,
} from "../types/api";

interface HealthDashboardProps {
  analysisId: string;
}

export const HealthDashboard: React.FC<HealthDashboardProps> = ({ analysisId }) => {
  // Main Health Score & Recs
  const [healthData, setHealthData] = useState<HealthScoreResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  // Issues List & Filter
  const [issuesData, setIssuesData] = useState<IssuesListResponse | null>(null);
  const [loadingIssues, setLoadingIssues] = useState<boolean>(true);
  const [issuesError, setIssuesError] = useState<string | null>(null);

  // Filters & Pagination
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(25);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [debouncedSearch, setDebouncedSearch] = useState<string>("");

  // UI state
  const [expandedIssueId, setExpandedIssueId] = useState<string | null>(null);
  const [showFormulaModal, setShowFormulaModal] = useState<boolean>(false);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Fetch Health Score
  useEffect(() => {
    let isMounted = true;
    const fetchHealth = async () => {
      try {
        setLoadingHealth(true);
        const data = await apiService.getHealthScore(analysisId);
        if (isMounted) {
          setHealthData(data);
          setHealthError(null);
        }
      } catch (err: any) {
        if (isMounted) {
          setHealthError(err.response?.data?.detail || "Failed to load health score");
        }
      } finally {
        if (isMounted) setLoadingHealth(false);
      }
    };

    fetchHealth();
    return () => {
      isMounted = false;
    };
  }, [analysisId]);

  // Fetch Issues
  useEffect(() => {
    let isMounted = true;
    const fetchIssues = async () => {
      try {
        setLoadingIssues(true);
        const params: any = {
          page,
          page_size: pageSize,
        };
        if (selectedCategory) params.category = selectedCategory;
        if (selectedSeverity) params.severity = selectedSeverity;
        if (debouncedSearch) params.search = debouncedSearch;

        const data = await apiService.getIssues(analysisId, params);
        if (isMounted) {
          setIssuesData(data);
          setIssuesError(null);
        }
      } catch (err: any) {
        if (isMounted) {
          setIssuesError(err.response?.data?.detail || "Failed to load diagnostic issues");
        }
      } finally {
        if (isMounted) setLoadingIssues(false);
      }
    };

    fetchIssues();
    return () => {
      isMounted = false;
    };
  }, [analysisId, page, pageSize, selectedCategory, selectedSeverity, debouncedSearch]);

  const getGradeBadge = (grade: string) => {
    switch (grade) {
      case "A+":
      case "A":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      case "B":
        return "bg-blue-50 text-blue-700 border-blue-200";
      case "C":
        return "bg-amber-50 text-amber-700 border-amber-200";
      case "D":
        return "bg-orange-50 text-orange-700 border-orange-200";
      case "F":
      default:
        return "bg-rose-50 text-rose-700 border-rose-200";
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-emerald-700";
    if (score >= 80) return "text-blue-700";
    if (score >= 70) return "text-amber-700";
    if (score >= 60) return "text-orange-700";
    return "text-rose-700";
  };

  const getScoreBarColor = (score: number) => {
    if (score >= 90) return "bg-emerald-600";
    if (score >= 80) return "bg-blue-600";
    if (score >= 70) return "bg-amber-500";
    if (score >= 60) return "bg-orange-500";
    return "bg-rose-500";
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "blocker":
        return "bg-rose-100 text-rose-800 border-rose-300 font-bold";
      case "critical":
        return "bg-rose-50 text-rose-700 border-rose-200";
      case "major":
        return "bg-orange-50 text-orange-700 border-orange-200";
      case "minor":
        return "bg-amber-50 text-amber-700 border-amber-200";
      case "info":
      default:
        return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  const getCategoryBadge = (category: string) => {
    switch (category.toLowerCase()) {
      case "architecture":
        return "bg-purple-50 text-purple-700 border-purple-200";
      case "complexity":
        return "bg-amber-50 text-amber-700 border-amber-200";
      case "maintainability":
        return "bg-blue-50 text-blue-700 border-blue-200";
      case "hygiene":
        return "bg-teal-50 text-teal-700 border-teal-200";
      case "security":
        return "bg-rose-50 text-rose-700 border-rose-200";
      default:
        return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  if (loadingHealth && !healthData) {
    return (
      <div className="flex items-center justify-center p-16 bg-white rounded-lg border border-slate-200 shadow-sm">
        <div className="flex items-center space-x-3 text-indigo-600">
          <Activity className="w-6 h-6 animate-spin" />
          <span className="text-sm font-medium text-slate-700">Computing deterministic health score and diagnostic rules...</span>
        </div>
      </div>
    );
  }

  if (healthError || !healthData) {
    return (
      <div className="p-6 bg-white rounded-lg border border-slate-200 text-slate-600 text-sm shadow-sm">
        {healthError || "Health score data not available for this analysis job."}
      </div>
    );
  }

  const {
    overall_score,
    grade,
    maintainability_score,
    complexity_score,
    architecture_score,
    hygiene_score,
    technical_debt_minutes,
    debt_ratio_hours_per_ksloc,
    total_issues_count,
    blocker_count,
    critical_count,
    major_count,
    minor_count,
    info_count,
    recommendations,
  } = healthData;

  const debtHours = (technical_debt_minutes / 60).toFixed(1);

  return (
    <div className="space-y-8">
      {/* 1. HERO CODEBASE HEALTH SCORE */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm relative overflow-hidden">
        <div className="relative z-10 flex flex-col lg:flex-row items-center justify-between gap-8">
          {/* Left: Score Gauge & Grade */}
          <div className="flex items-center gap-6">
            <div className="relative flex items-center justify-center w-32 h-32 rounded-full bg-slate-50 border-4 border-slate-200 shadow-inner">
              <div className="text-center">
                <span className={`text-3xl font-extrabold tracking-tight ${getScoreColor(overall_score)}`}>
                  {overall_score.toFixed(1)}
                </span>
                <span className="block text-[11px] font-semibold text-slate-500 uppercase tracking-widest mt-0.5">
                  / 100
                </span>
              </div>
            </div>

            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Codebase Health Score</h2>
                <span
                  className={`px-3 py-1 rounded-full text-sm font-bold border ${getGradeBadge(
                    grade
                  )} shadow-sm`}
                >
                  Grade {grade}
                </span>
              </div>
              <p className="text-slate-600 text-sm mt-1 max-w-md leading-relaxed">
                Aggregated deterministic health score across Maintainability, Complexity, Architecture, and Reliability pillars.
              </p>
              <button
                onClick={() => setShowFormulaModal(!showFormulaModal)}
                className="mt-2 text-xs text-indigo-600 hover:text-indigo-800 underline font-medium flex items-center gap-1"
              >
                <Info className="w-3.5 h-3.5" />
                {showFormulaModal ? "Hide scoring formula breakdown" : "View transparent scoring formulas"}
              </button>
            </div>
          </div>

          {/* Right: Key Health Metrics Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 w-full lg:w-auto">
            <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
              <div className="flex items-center justify-between text-slate-500 mb-1">
                <span className="text-xs font-medium uppercase tracking-wider">Tech Debt</span>
                <Clock className="w-4 h-4 text-amber-600" />
              </div>
              <div className="text-xl font-bold text-slate-900">{debtHours}h</div>
              <span className="text-xs text-slate-500">{technical_debt_minutes} min effort</span>
            </div>

            <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
              <div className="flex items-center justify-between text-slate-500 mb-1">
                <span className="text-xs font-medium uppercase tracking-wider">Debt Ratio</span>
                <Flame className="w-4 h-4 text-orange-600" />
              </div>
              <div className="text-xl font-bold text-slate-900">{debt_ratio_hours_per_ksloc.toFixed(1)}</div>
              <span className="text-xs text-slate-500">hours / kSLOC</span>
            </div>

            <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
              <div className="flex items-center justify-between text-slate-500 mb-1">
                <span className="text-xs font-medium uppercase tracking-wider">Total Issues</span>
                <AlertCircle className="w-4 h-4 text-rose-600" />
              </div>
              <div className="text-xl font-bold text-slate-900">{total_issues_count}</div>
              <span className="text-xs text-slate-500">detected smells</span>
            </div>

            <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
              <div className="flex items-center justify-between text-slate-500 mb-1">
                <span className="text-xs font-medium uppercase tracking-wider">Severities</span>
                <ShieldAlert className="w-4 h-4 text-purple-600" />
              </div>
              <div className="flex items-center gap-1.5 mt-1">
                {blocker_count > 0 && (
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
                    {blocker_count} B
                  </span>
                )}
                {critical_count > 0 && (
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                    {critical_count} C
                  </span>
                )}
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-orange-50 text-orange-700 border border-orange-200">
                  {major_count} M
                </span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                  {minor_count} m
                </span>
              </div>
              <span className="text-[10px] text-slate-500 block mt-1">{info_count} info notes</span>
            </div>
          </div>
        </div>

        {/* Scoring Formula Transparency Details (Collapsible) */}
        {showFormulaModal && (
          <div className="mt-6 pt-5 border-t border-slate-200 text-xs text-slate-700 space-y-3 bg-slate-50 p-4 rounded-lg">
            <h4 className="font-semibold text-slate-900 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-indigo-600" />
              Deterministic Scoring Formula Specifications
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <span className="font-semibold text-slate-900">Overall Health Score:</span>
                <p className="text-slate-600 mt-0.5">
                  <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 font-mono text-slate-800">
                    Score = 0.25 × (Maintainability + Complexity + Architecture + Hygiene)
                  </code>
                </p>
                <p className="text-slate-500 mt-1">
                  Grades: A+ (≥95), A (≥90), B (≥80), C (≥70), D (≥60), F (&lt;60). Clamped to [0, 100].
                </p>
              </div>
              <div>
                <span className="font-semibold text-slate-900">Technical Debt Calculation:</span>
                <p className="text-slate-600 mt-0.5">
                  Remediation effort minutes mapped per rule severity and code size.
                </p>
                <p className="text-slate-500 mt-1">
                  Debt ratio = (Total Remediation Hours) / (Total kSLOC).
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 2. FOUR PILLAR SCORE CARDS */}
      <div>
        <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
          <Layers className="w-4 h-4 text-slate-700" />
          Health Pillars (0–100 Scale)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Maintainability */}
          <div className="bg-white rounded-lg p-5 border border-slate-200 hover:border-slate-300 transition-colors shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Maintainability</span>
              <FileCode className="w-4 h-4 text-blue-600" />
            </div>
            <div className="flex items-baseline justify-between mb-2">
              <span className={`text-2xl font-bold ${getScoreColor(maintainability_score)}`}>
                {maintainability_score.toFixed(1)}
              </span>
              <span className="text-xs text-slate-500">Weight: 25%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
              <div
                className={`h-full ${getScoreBarColor(maintainability_score)} rounded-full transition-all duration-500`}
                style={{ width: `${Math.min(100, Math.max(0, maintainability_score))}%` }}
              />
            </div>
            <p className="text-[11px] text-slate-500 mt-2">
              Composite of average MI, low-MI toxic file penalty, and comment ratio health.
            </p>
          </div>

          {/* Complexity */}
          <div className="bg-white rounded-lg p-5 border border-slate-200 hover:border-slate-300 transition-colors shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Complexity</span>
              <Cpu className="w-4 h-4 text-amber-600" />
            </div>
            <div className="flex items-baseline justify-between mb-2">
              <span className={`text-2xl font-bold ${getScoreColor(complexity_score)}`}>
                {complexity_score.toFixed(1)}
              </span>
              <span className="text-xs text-slate-500">Weight: 25%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
              <div
                className={`h-full ${getScoreBarColor(complexity_score)} rounded-full transition-all duration-500`}
                style={{ width: `${Math.min(100, Math.max(0, complexity_score))}%` }}
              />
            </div>
            <p className="text-[11px] text-slate-500 mt-2">
              Evaluates cyclomatic complexity density, high-CC functions, and nesting depth.
            </p>
          </div>

          {/* Architecture */}
          <div className="bg-white rounded-lg p-5 border border-slate-200 hover:border-slate-300 transition-colors shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Architecture</span>
              <Layers className="w-4 h-4 text-purple-600" />
            </div>
            <div className="flex items-baseline justify-between mb-2">
              <span className={`text-2xl font-bold ${getScoreColor(architecture_score)}`}>
                {architecture_score.toFixed(1)}
              </span>
              <span className="text-xs text-slate-500">Weight: 25%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
              <div
                className={`h-full ${getScoreBarColor(architecture_score)} rounded-full transition-all duration-500`}
                style={{ width: `${Math.min(100, Math.max(0, architecture_score))}%` }}
              />
            </div>
            <p className="text-[11px] text-slate-500 mt-2">
              Penalizes cyclic dependencies, God modules, and unstable dependency violations.
            </p>
          </div>

          {/* Hygiene & Reliability */}
          <div className="bg-white rounded-lg p-5 border border-slate-200 hover:border-slate-300 transition-colors shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Hygiene & Reliability</span>
              <Shield className="w-4 h-4 text-teal-600" />
            </div>
            <div className="flex items-baseline justify-between mb-2">
              <span className={`text-2xl font-bold ${getScoreColor(hygiene_score)}`}>
                {hygiene_score.toFixed(1)}
              </span>
              <span className="text-xs text-slate-500">Weight: 25%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
              <div
                className={`h-full ${getScoreBarColor(hygiene_score)} rounded-full transition-all duration-500`}
                style={{ width: `${Math.min(100, Math.max(0, hygiene_score))}%` }}
              />
            </div>
            <p className="text-[11px] text-slate-500 mt-2">
              Weighted penalty for empty handlers, dead code, secrets, and dangerous sinks.
            </p>
          </div>
        </div>
      </div>

      {/* 3. PRIORITIZED ACTION PLAN / TOP RECOMMENDATIONS */}
      {recommendations && recommendations.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-600" />
              Prioritized Action Plan (Top Modeled Interventions)
            </h3>
            <span className="text-xs text-slate-500">
              Counterfactual metric simulation: bounded to top 5 impactful refactorings
            </span>
          </div>

          <div className="space-y-3">
            {recommendations.map((rec: RecommendationItem, index: number) => (
              <div
                key={rec.id || index}
                className="bg-white rounded-lg p-5 border border-slate-200 hover:border-slate-300 transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-slate-100 text-[11px] font-bold text-slate-700">
                      {index + 1}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-semibold border uppercase tracking-wider ${getCategoryBadge(
                        rec.primary_category
                      )}`}
                    >
                      {rec.primary_category}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                      {rec.target_type}: {rec.target_name}
                    </span>
                    {rec.file_path && (
                      <span className="text-xs font-mono text-slate-600 truncate max-w-xs">
                        {rec.file_path}
                      </span>
                    )}
                  </div>

                  <h4 className="text-sm font-semibold text-slate-900">{rec.title}</h4>
                  <p className="text-xs text-slate-600 leading-relaxed">{rec.summary}</p>
                  <p className="text-[11px] text-slate-500 italic">{rec.rationale}</p>
                </div>

                {/* Score Recovery & Effort */}
                <div className="flex items-center gap-4 shrink-0 self-end md:self-center">
                  <div className="text-right">
                    <span className="text-[10px] uppercase font-semibold text-slate-500 block">
                      Modeled Score Recovery
                    </span>
                    {rec.expected_score_recovery !== null && rec.expected_score_recovery !== undefined ? (
                      <span className="text-base font-extrabold text-emerald-600 flex items-center justify-end gap-0.5">
                        <TrendingUp className="w-3.5 h-3.5" />
                        +{rec.expected_score_recovery.toFixed(1)} pts
                      </span>
                    ) : (
                      <span className="text-xs font-semibold text-slate-700">Qualitative fix</span>
                    )}
                  </div>

                  <div className="h-8 w-px bg-slate-200 hidden sm:block" />

                  <div className="text-right">
                    <span className="text-[10px] uppercase font-semibold text-slate-500 block">Effort</span>
                    <span className="text-sm font-bold text-slate-900">{rec.effort_hours.toFixed(1)}h</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. FILTERABLE ISSUE EXPLORER */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-5 shadow-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-purple-600" />
              Diagnostic Code Smells & Architectural Issues
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Deterministic rule violations detected across complexity, architecture, maintainability, hygiene, and security.
            </p>
          </div>

          <span className="text-xs text-slate-600 bg-slate-100 px-3 py-1.5 rounded-md border border-slate-200 font-mono">
            {issuesData?.total ?? 0} total issues
          </span>
        </div>

        {/* Filter Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search rule, symbol, or file path..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-md pl-9 pr-4 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          {/* Category Filter */}
          <div className="relative">
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setPage(1);
              }}
              className="w-full bg-white border border-slate-300 rounded-md px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 appearance-none"
            >
              <option value="">All Categories</option>
              <option value="architecture">Architecture</option>
              <option value="complexity">Complexity</option>
              <option value="maintainability">Maintainability</option>
              <option value="hygiene">Hygiene & Reliability</option>
              <option value="security">Security Heuristics</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-3 top-3 pointer-events-none" />
          </div>

          {/* Severity Filter */}
          <div className="relative">
            <select
              value={selectedSeverity}
              onChange={(e) => {
                setSelectedSeverity(e.target.value);
                setPage(1);
              }}
              className="w-full bg-white border border-slate-300 rounded-md px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 appearance-none"
            >
              <option value="">All Severities</option>
              <option value="blocker">Blocker</option>
              <option value="critical">Critical</option>
              <option value="major">Major</option>
              <option value="minor">Minor</option>
              <option value="info">Info</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-3 top-3 pointer-events-none" />
          </div>
        </div>

        {/* Issues List / Table */}
        {loadingIssues ? (
          <div className="flex items-center justify-center p-12 text-indigo-600 space-x-2">
            <Activity className="w-5 h-5 animate-spin" />
            <span className="text-xs font-medium text-slate-600">Loading filtered issues...</span>
          </div>
        ) : issuesError ? (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs">
            {issuesError}
          </div>
        ) : issuesData?.items.length === 0 ? (
          <div className="p-8 text-center bg-slate-50 rounded-lg border border-slate-200">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2 opacity-80" />
            <p className="text-sm text-slate-800 font-medium">No diagnostic issues match your filter</p>
            <p className="text-xs text-slate-500 mt-1">Try clearing filters or search query to see all detected smells.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {issuesData?.items.map((issue: IssueItem) => {
              const isExpanded = expandedIssueId === issue.id;
              return (
                <div
                  key={issue.id}
                  className="bg-white border border-slate-200 rounded-md overflow-hidden transition-all hover:border-slate-300 shadow-sm"
                >
                  <div
                    onClick={() => setExpandedIssueId(isExpanded ? null : issue.id)}
                    className="p-3.5 flex items-start sm:items-center justify-between gap-3 cursor-pointer select-none"
                  >
                    <div className="flex items-start sm:items-center gap-3 flex-1 min-w-0">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-slate-400 shrink-0 mt-0.5 sm:mt-0" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-slate-400 shrink-0 mt-0.5 sm:mt-0" />
                      )}

                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase tracking-wider shrink-0 ${getSeverityBadge(
                          issue.severity
                        )}`}
                      >
                        {issue.severity}
                      </span>

                      <span className="font-mono text-xs font-semibold text-indigo-700 shrink-0">
                        {issue.rule_id}
                      </span>

                      <div className="min-w-0 flex-1">
                        <span className="text-xs font-semibold text-slate-900 truncate block">
                          {issue.title}
                        </span>
                        <div className="flex items-center gap-2 mt-0.5 text-[11px] text-slate-500 truncate">
                          {issue.file_path && (
                            <span className="font-mono truncate">{issue.file_path}</span>
                          )}
                          {issue.line_number && (
                            <span className="font-mono text-slate-400">L{issue.line_number}</span>
                          )}
                          {issue.symbol_name && (
                            <span className="text-slate-600">({issue.symbol_name})</span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-medium border uppercase ${getCategoryBadge(
                          issue.category
                        )}`}
                      >
                        {issue.category}
                      </span>
                      <span className="text-[11px] text-slate-500 font-mono font-medium">
                        {issue.remediation_effort_minutes}m
                      </span>
                    </div>
                  </div>

                  {/* Expanded Detail Panel */}
                  {isExpanded && (
                    <div className="px-4 pb-4 pt-3 border-t border-slate-200 bg-slate-50/70 space-y-3">
                      <div>
                        <span className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider block">
                          Detailed Description
                        </span>
                        <p className="text-xs text-slate-700 mt-1 leading-relaxed">{issue.description}</p>
                      </div>

                      {issue.metadata_json && Object.keys(issue.metadata_json).length > 0 && (
                        <div>
                          <span className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider block">
                            Diagnostic Attributes & Metadata
                          </span>
                          <div className="mt-1.5 p-2.5 rounded bg-white border border-slate-200 font-mono text-[11px] text-slate-800 overflow-x-auto">
                            <pre>{JSON.stringify(issue.metadata_json, null, 2)}</pre>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination Bar */}
        {issuesData && issuesData.total_pages > 1 && (
          <div className="flex items-center justify-between pt-3 border-t border-slate-200 text-xs text-slate-600">
            <div>
              Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, issuesData.total)} of{" "}
              {issuesData.total} issues
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 rounded bg-white border border-slate-300 hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none text-slate-700 font-medium shadow-sm transition"
              >
                Previous
              </button>
              <span className="text-slate-500 font-mono">
                Page {page} of {issuesData.total_pages}
              </span>
              <button
                disabled={page >= issuesData.total_pages}
                onClick={() => setPage((p) => Math.min(issuesData.total_pages, p + 1))}
                className="px-3 py-1 rounded bg-white border border-slate-300 hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none text-slate-700 font-medium shadow-sm transition"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
