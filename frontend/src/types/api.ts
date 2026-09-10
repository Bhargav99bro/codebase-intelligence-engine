export interface ServiceComponentStatus {
  status: string;
  details?: string | null;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy" | string;
  project: string;
  version: string;
  environment: string;
  timestamp: string;
  services: {
    api: ServiceComponentStatus;
    database: ServiceComponentStatus;
    redis: ServiceComponentStatus;
    [key: string]: ServiceComponentStatus;
  };
}

export interface RepositoryAnalyzeRequest {
  repository_url: string;
}

export interface RepositoryAnalyzeResponse {
  analysis_id: string;
  status: "queued" | string;
  repository_url: string;
  message: string;
}

export interface AnalysisJobResponse {
  id: string;
  repository_id: string;
  repository_url: string;
  owner: string;
  name: string;
  status: "queued" | "cloning" | "discovering" | "completed" | "failed" | "cancellation_requested" | "cancelled" | string;
  stage: string;
  progress: number;
  message: string;
  error_message?: string | null;
  commit_hash?: string | null;
  total_files: number;
  analyzable_files: number;
  total_lines: number;
  total_bytes: number;
  language_distribution: Record<string, number>;
  total_symbols?: number;
  symbol_distribution?: Record<string, number>;
  metadata_json?: Record<string, any>;
  health_summary?: {
    overall_score?: number;
    grade?: string;
    maintainability_score?: number;
    complexity_score?: number;
    architecture_score?: number;
    hygiene_score?: number;
    duplication_score?: number;
    duplication_ratio?: number;
    duplicate_blocks_count?: number;
    duplicate_lines_count?: number;
    total_issues_count?: number;
    technical_debt_minutes?: number;
  } | null;
  commit_date?: string | null;
  base_analysis_id?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface SymbolItem {
  id: string;
  analysis_id: string;
  file_id: string;
  file_path?: string;
  name: string;
  symbol_type: "function" | "class" | "method" | "import" | "export" | "interface" | "type" | string;
  qualified_name?: string | null;
  start_line: number;
  start_column: number;
  end_line: number;
  end_column: number;
  parent_symbol_id?: string | null;
  signature?: string | null;
  metadata_json: Record<string, any>;
  created_at: string;
}

export interface SymbolListResponse {
  items: SymbolItem[];
  total: number;
  skip: number;
  limit: number;
}

export interface QualityFlagItem {
  flag: string;
  description: string;
  metric_value: number;
  threshold: number;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | string;
  location: string;
}

export interface RepositoryMetricsResponse {
  analysis_id: string;
  repository_totals: {
    total_sloc: number;
    total_files: number;
    total_symbols: number;
    total_functions: number;
    total_classes: number;
    total_methods: number;
  };
  averages: {
    average_cyclomatic_complexity: number;
    average_function_size: number;
    average_nesting_depth: number;
  };
  maximums: {
    max_cyclomatic_complexity: number;
    max_function_size: number;
    max_nesting_depth: number;
  };
  maintainability: {
    score: number;
    rating: "good" | "moderate" | "poor" | string;
    label: string;
  };
  complexity_distribution: {
    low: number;
    moderate: number;
    high: number;
    very_high: number;
  };
  quality_summary: {
    total_quality_flags: number;
    flagged_files_count: number;
    flagged_functions_count: number;
    severity_counts: Record<string, number>;
    top_hotspots: QualityFlagItem[];
  };
}

export interface FileMetricItem {
  id: string;
  file_id: string;
  file_path: string;
  language?: string | null;
  total_lines: number;
  sloc: number;
  comment_lines: number;
  blank_lines: number;
  statement_count: number;
  symbol_count: number;
  function_count: number;
  class_count: number;
  method_count: number;
  import_count: number;
  export_count: number;
  max_nesting_depth: number;
  average_nesting_depth: number;
  total_cyclomatic_complexity: number;
  average_cyclomatic_complexity: number;
  max_cyclomatic_complexity: number;
  maintainability_score: number;
  metric_status: string;
  metric_error?: string | null;
  quality_flags: QualityFlagItem[];
}

export interface FileMetricsListResponse {
  analysis_id: string;
  items: FileMetricItem[];
  total: number;
  skip: number;
  limit: number;
}

export interface SymbolMetricItem {
  id: string;
  symbol_id: string;
  file_id: string;
  symbol_name: string;
  symbol_type: string;
  signature?: string | null;
  file_path: string;
  start_line: number;
  lines_of_code: number;
  cyclomatic_complexity: number;
  nesting_depth: number;
  parameter_count: number;
  return_count: number;
  branch_count: number;
  loop_count: number;
  exception_handler_count: number;
  boolean_condition_count: number;
  quality_flags: QualityFlagItem[];
  metric_status: string;
  metric_error?: string | null;
}

export interface SymbolMetricsListResponse {
  analysis_id: string;
  items: SymbolMetricItem[];
  total: number;
  skip: number;
  limit: number;
}

export interface DependencyItem {
  id: string;
  source_file_id: string;
  source_file_path: string;
  target_file_id?: string | null;
  target_file_path?: string | null;
  target_module: string;
  dependency_type: string;
  imported_symbols: string[];
  line_number: number;
  resolution_status: "internal" | "external" | "unresolved" | string;
  is_type_only: boolean;
  created_at: string;
}

export interface DependenciesListResponse {
  analysis_id: string;
  items: DependencyItem[];
  total: number;
  skip: number;
  limit: number;
}

export interface DependencyGraphNode {
  id: string;
  label: string;
  path: string;
  language?: string | null;
  fan_in: number;
  fan_out: number;
  instability: number;
  in_cycle: boolean;
  cycle_count: number;
}

export interface DependencyGraphEdge {
  id: string;
  source: string;
  target: string;
  source_path: string;
  target_path: string;
  type: string;
  symbols: string[];
  line_number: number;
}

export interface DependencyGraphResponse {
  analysis_id: string;
  nodes: DependencyGraphNode[];
  edges: DependencyGraphEdge[];
  total_nodes: number;
  total_edges: number;
}

export interface CycleItem {
  cycle_id: number;
  length: number;
  files: string[];
  edges: Array<{ source: string; target: string }>;
}

export interface CyclesListResponse {
  analysis_id: string;
  total_cycles: number;
  cycle_cap_reached: boolean;
  cycles: CycleItem[];
}

export interface ImpactedItem {
  file_id: string;
  file_path: string;
  depth: number;
  is_direct: boolean;
  relationship_path: string[];
}

export interface ImpactAnalysisResponse {
  analysis_id: string;
  target_file_id: string;
  target_file_path: string;
  direction: "dependents" | "dependencies" | string;
  max_depth: number;
  affected_files_count: number;
  direct_count: number;
  transitive_count: number;
  items: ImpactedItem[];
}

export interface TopNodeMetric {
  file_id: string;
  file_path: string;
  fan_in: number;
  fan_out: number;
  instability: number;
}

export interface ArchitectureHotspots {
  core_foundation: string[];
  high_coupling: string[];
  cyclic_modules: string[];
  isolated_modules: string[];
}

export interface DependencySummaryResponse {
  analysis_id: string;
  total_dependencies: number;
  internal_dependencies: number;
  external_dependencies: number;
  unresolved_dependencies: number;
  analyzed_files: number;
  isolated_files_count: number;
  average_fan_in: number;
  average_fan_out: number;
  max_fan_in: number;
  max_fan_out: number;
  average_instability: number;
  circular_dependency_count: number;
  cycle_cap_reached: boolean;
  top_fan_in: TopNodeMetric[];
  top_fan_out: TopNodeMetric[];
  architecture_hotspots: ArchitectureHotspots;
}

export interface IssueItem {
  id: string;
  analysis_id: string;
  file_id?: string | null;
  file_path?: string | null;
  rule_id: string;
  rule_name: string;
  category: "architecture" | "complexity" | "maintainability" | "hygiene" | "security" | string;
  severity: "blocker" | "critical" | "major" | "minor" | "info" | string;
  title: string;
  description: string;
  line_number?: number | null;
  end_line_number?: number | null;
  symbol_name?: string | null;
  remediation_effort_minutes: number;
  metadata_json: Record<string, any>;
  created_at: string;
}

export interface IssuesListResponse {
  analysis_id: string;
  items: IssueItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  severity_counts: Record<string, number>;
  category_counts: Record<string, number>;
}

export interface TopRuleViolation {
  rule_id: string;
  rule_name: string;
  category: string;
  severity: string;
  count: number;
}

export interface IssuesSummaryResponse {
  analysis_id: string;
  total_issues: number;
  severity_counts: Record<string, number>;
  category_counts: Record<string, number>;
  total_technical_debt_minutes: number;
  top_violated_rules: TopRuleViolation[];
}

export interface RecommendationItem {
  id: string;
  target_type: "file" | "symbol" | "cycle" | string;
  target_id?: string | null;
  target_name: string;
  file_id?: string | null;
  file_path?: string | null;
  title: string;
  summary: string;
  rationale: string;
  effort_hours: number;
  current_health_impact: number;
  expected_score_recovery?: number | null;
  action_type: string;
  primary_category: string;
  related_issue_ids: string[];
  modeled_metric_changes: Record<string, any>;
  qualitative: boolean;
}

export interface HealthScoreResponse {
  analysis_id: string;
  overall_score: number;
  grade: string;
  maintainability_score: number;
  complexity_score: number;
  architecture_score: number;
  hygiene_score: number;
  technical_debt_minutes: number;
  debt_ratio_hours_per_ksloc: number;
  total_issues_count: number;
  blocker_count: number;
  critical_count: number;
  major_count: number;
  minor_count: number;
  info_count: number;
  category_scores: Record<string, any>;
  recommendations: RecommendationItem[];
  created_at: string;
}

// Treemap & Hotspot Visualizer Types
export interface TreemapNodeData {
  name: string;
  path: string;
  type: "directory" | "file";
  node_type?: "directory" | "file";
  sloc: number;
  total_lines?: number;
  file_count?: number;
  language?: string | null;
  maintainability_score?: number | null;
  max_cyclomatic_complexity?: number | null;
  total_cyclomatic_complexity?: number | null;
  issue_count?: number;
  dominant_severity?: string | null;
  children?: TreemapNodeData[];
  layout_rect?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  x?: number;
  y?: number;
  width?: number;
  height?: number;
}

export interface TreemapResponse {
  root: TreemapNodeData;
}

export interface HotspotItem {
  rank: number;
  file_path: string;
  hotspot_score: number;
  complexity_risk: number;
  architectural_centrality: number;
  issue_severity_burden: number;
  sloc: number;
  max_cyclomatic_complexity: number;
  max_nesting_depth: number;
  fan_in: number;
  fan_out: number;
  issues_count: number;
  blocker_count: number;
  critical_count: number;
  major_count: number;
  minor_count: number;
}

export interface HotspotsResponse {
  total_analyzed_files: number;
  hotspots: HotspotItem[];
}

export interface QualityGateCondition {
  condition_id: string;
  metric: string;
  actual_value: number;
  threshold: number;
  operator: string;
  severity: "fail" | "warn";
  passed: boolean;
  message: string;
}

export interface QualityGateResponse {
  status: "PASSED" | "WARNING" | "FAILED";
  passed: boolean;
  overall_score: number;
  total_conditions: number;
  passed_count: number;
  failed_count: number;
  warning_count: number;
  conditions: QualityGateCondition[];
}

export interface CustomQualityGateParams {
  min_score?: number;
  max_blockers?: number;
  max_cycles?: number;
  max_criticals?: number;
  min_mi?: number;
  max_crit_funcs?: number;
}

// Duplication, Git Churn, Timeline & Diff Types

export interface CodeDuplicateItem {
  id: string;
  analysis_id: string;
  clone_type: "TYPE_1" | "TYPE_2" | string;
  line_count: number;
  token_count: number;
  source_file_path: string;
  source_start_line: number;
  source_end_line: number;
  target_file_path: string;
  target_start_line: number;
  target_end_line: number;
  similarity_score: number;
  fragment_hash: string;
  source_url?: string;
  target_url?: string;
  source_snippet?: string;
  target_snippet?: string;
}

export interface DuplicationResponse {
  analysis_id: string;
  duplication_score: number;
  duplication_ratio: number;
  duplicate_blocks_count: number;
  duplicate_lines_count: number;
  total_matches: number;
  limit: number;
  offset: number;
  duplicates: CodeDuplicateItem[];
}

export interface GitChurnMetricItem {
  id: string;
  analysis_id: string;
  file_id?: string | null;
  file_path: string;
  commit_count: number;
  insertions: number;
  deletions: number;
  churn_lines: number;
  author_count: number;
  churn_score: number;
  last_modified_date?: string | null;
}

export interface ChurnResponse {
  analysis_id: string;
  has_git_history: boolean;
  max_churn: number;
  total_files: number;
  limit: number;
  offset: number;
  churn_metrics: GitChurnMetricItem[];
}

export interface PRQualityGate {
  status: "PASSED" | "WARNING" | "FAILED";
  passed?: boolean;
  reasons: string[];
  new_blocker_count?: number;
  new_critical_count?: number;
  new_blocker_critical_count: number;
  new_major_count: number;
  new_cycles_count: number;
  delta_health: number;
  delta_duplication_ratio: number;
}

export interface AnalysisDiffResponse {
  base_id?: string;
  head_id?: string;
  base_analysis_id: string;
  current_analysis_id: string;
  delta_health_score: number;
  delta_debt_minutes: number;
  pillar_deltas: {
    maintainability: number;
    complexity: number;
    architecture: number;
    hygiene_and_reliability: number;
    duplication: number;
  };
  new_issues_count: number;
  fixed_issues_count: number;
  persistent_issues_count: number;
  new_issues: any[];
  fixed_issues: any[];
  persistent_issues: any[];
  new_cycles: string[][];
  resolved_cycles: string[][];
  persistent_cycles: string[][];
  quality_gate: PRQualityGate;
}

export interface TimelinePoint {
  analysis_id: string;
  commit_hash?: string | null;
  commit_author?: string | null;
  commit_message?: string | null;
  commit_date?: string | null;
  created_at?: string | null;
  overall_score: number;
  grade: string;
  maintainability_score: number;
  complexity_score: number;
  architecture_score: number;
  hygiene_score: number;
  duplication_score: number;
  duplication_ratio: number;
  duplicate_blocks_count: number;
  duplicate_lines_count: number;
  technical_debt_minutes: number;
  debt_ratio_hours_per_ksloc: number;
  total_issues_count: number;
}

export interface TimelineResponse {
  repository_id: string;
  repository_name: string;
  default_branch?: string;
  timeline_count: number;
  timeline: TimelinePoint[];
}
