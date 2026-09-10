import axios from "axios";
import {
  AnalysisJobResponse,
  HealthResponse,
  RepositoryAnalyzeRequest,
  RepositoryAnalyzeResponse,
  SymbolListResponse,
} from "../types/api";

// When running Vite dev server, /api is proxied to backend:8000 or localhost:8000
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : "/api/v1",
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

export const apiService = {
  async getHealth(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>("/health");
    return response.data;
  },

  async analyzeRepository(payload: RepositoryAnalyzeRequest): Promise<RepositoryAnalyzeResponse> {
    const response = await apiClient.post<RepositoryAnalyzeResponse>("/repositories/analyze", payload);
    return response.data;
  },

  async getAnalysis(analysisId: string): Promise<AnalysisJobResponse> {
    const response = await apiClient.get<AnalysisJobResponse>(`/analyses/${analysisId}`);
    return response.data;
  },

  async getAnalysisSymbols(
    analysisId: string,
    params?: { skip?: number; limit?: number; symbol_type?: string; search?: string }
  ): Promise<SymbolListResponse> {
    const response = await apiClient.get<SymbolListResponse>(`/analyses/${analysisId}/symbols`, {
      params,
    });
    return response.data;
  },

  async getAnalysisMetrics(analysisId: string): Promise<import("../types/api").RepositoryMetricsResponse> {
    const response = await apiClient.get<import("../types/api").RepositoryMetricsResponse>(`/analyses/${analysisId}/metrics`);
    return response.data;
  },

  async getFileMetrics(
    analysisId: string,
    params?: {
      skip?: number;
      limit?: number;
      sort_by?: string;
      order?: string;
      min_complexity?: number;
      language?: string;
      flagged_only?: boolean;
    }
  ): Promise<import("../types/api").FileMetricsListResponse> {
    const response = await apiClient.get<import("../types/api").FileMetricsListResponse>(
      `/analyses/${analysisId}/metrics/files`,
      { params }
    );
    return response.data;
  },

  async getSymbolMetrics(
    analysisId: string,
    params?: {
      skip?: number;
      limit?: number;
      sort_by?: string;
      order?: string;
      min_complexity?: number;
      symbol_type?: string;
      file_id?: string;
      search?: string;
      flagged_only?: boolean;
    }
  ): Promise<import("../types/api").SymbolMetricsListResponse> {
    const response = await apiClient.get<import("../types/api").SymbolMetricsListResponse>(
      `/analyses/${analysisId}/metrics/symbols`,
      { params }
    );
    return response.data;
  },

  async getDependencySummary(
    analysisId: string
  ): Promise<import("../types/api").DependencySummaryResponse> {
    const response = await apiClient.get<import("../types/api").DependencySummaryResponse>(
      `/analyses/${analysisId}/dependencies`
    );
    return response.data;
  },

  async getDependencyEdges(
    analysisId: string,
    params?: {
      skip?: number;
      limit?: number;
      source_file_id?: string;
      target_file_id?: string;
      resolution_status?: string;
      dependency_type?: string;
      search?: string;
      sort_by?: string;
      order?: string;
    }
  ): Promise<import("../types/api").DependenciesListResponse> {
    const response = await apiClient.get<import("../types/api").DependenciesListResponse>(
      `/analyses/${analysisId}/dependencies/edges`,
      { params }
    );
    return response.data;
  },

  async getDependencyGraph(
    analysisId: string,
    params?: {
      max_nodes?: number;
      min_degree?: number;
      focus_file_id?: string;
    }
  ): Promise<import("../types/api").DependencyGraphResponse> {
    const response = await apiClient.get<import("../types/api").DependencyGraphResponse>(
      `/analyses/${analysisId}/dependencies/graph`,
      { params }
    );
    return response.data;
  },

  async getDependencyCycles(
    analysisId: string
  ): Promise<import("../types/api").CyclesListResponse> {
    const response = await apiClient.get<import("../types/api").CyclesListResponse>(
      `/analyses/${analysisId}/dependencies/cycles`
    );
    return response.data;
  },

  async getImpactAnalysis(
    analysisId: string,
    fileId: string,
    params?: {
      direction?: string;
      max_depth?: number;
    }
  ): Promise<import("../types/api").ImpactAnalysisResponse> {
    const response = await apiClient.get<import("../types/api").ImpactAnalysisResponse>(
      `/analyses/${analysisId}/dependencies/impact/${fileId}`,
      { params }
    );
    return response.data;
  },

  async getHealthScore(analysisId: string): Promise<import("../types/api").HealthScoreResponse> {
    const response = await apiClient.get<import("../types/api").HealthScoreResponse>(
      `/analyses/${analysisId}/health`
    );
    return response.data;
  },

  async getIssues(
    analysisId: string,
    params?: {
      page?: number;
      page_size?: number;
      category?: string;
      severity?: string;
      rule_id?: string;
      file_id?: string;
      search?: string;
    }
  ): Promise<import("../types/api").IssuesListResponse> {
    const response = await apiClient.get<import("../types/api").IssuesListResponse>(
      `/analyses/${analysisId}/issues`,
      { params }
    );
    return response.data;
  },

  async getIssuesSummary(analysisId: string): Promise<import("../types/api").IssuesSummaryResponse> {
    const response = await apiClient.get<import("../types/api").IssuesSummaryResponse>(
      `/analyses/${analysisId}/issues/summary`
    );
    return response.data;
  },

  async getRootInfo(): Promise<{ name: string; version: string; status: string }> {
    const rootClient = axios.create({
      baseURL: import.meta.env.VITE_API_URL || "",
      timeout: 5000,
    });
    const response = await rootClient.get("/");
    return response.data;
  },

  // Treemap, Hotspots, Quality Gate, Exports & Cancel
  async getTreemap(analysisId: string): Promise<import("../types/api").TreemapResponse> {
    const response = await apiClient.get<import("../types/api").TreemapResponse>(
      `/analyses/${analysisId}/treemap`
    );
    return response.data;
  },

  async getHotspots(analysisId: string, limit: number = 10): Promise<import("../types/api").HotspotsResponse> {
    const response = await apiClient.get<import("../types/api").HotspotsResponse>(
      `/analyses/${analysisId}/hotspots`,
      { params: { limit } }
    );
    return response.data;
  },

  async getQualityGate(
    analysisId: string,
    params?: import("../types/api").CustomQualityGateParams
  ): Promise<import("../types/api").QualityGateResponse> {
    const response = await apiClient.get<import("../types/api").QualityGateResponse>(
      `/analyses/${analysisId}/quality-gate`,
      { params }
    );
    return response.data;
  },

  async cancelAnalysis(analysisId: string): Promise<{ status: string; message: string }> {
    const response = await apiClient.post<{ status: string; message: string }>(
      `/analyses/${analysisId}/cancel`
    );
    return response.data;
  },

  async getMarkdownReport(analysisId: string): Promise<string> {
    const response = await apiClient.get<string>(`/analyses/${analysisId}/export/markdown`, {
      responseType: "text",
    });
    return response.data;
  },

  getExportUrl(analysisId: string, format: "sarif" | "markdown" | "json"): string {
    const base = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : "/api/v1";
    return `${base}/analyses/${analysisId}/export/${format}`;
  },

  // Longitudinal Analytics, Diff Engine, Duplication & Churn
  async compareAnalyses(
    baseId: string,
    headId: string
  ): Promise<import("../types/api").AnalysisDiffResponse> {
    const response = await apiClient.get<import("../types/api").AnalysisDiffResponse>(
      "/analyses/compare",
      {
        params: {
          base_id: baseId,
          head_id: headId,
        },
      }
    );
    return response.data;
  },

  async getAnalysisDuplication(
    analysisId: string,
    limit: number = 100,
    offset: number = 0,
    cloneType?: string
  ): Promise<import("../types/api").DuplicationResponse> {
    const response = await apiClient.get<import("../types/api").DuplicationResponse>(
      `/analyses/${analysisId}/duplication`,
      {
        params: {
          limit,
          offset,
          clone_type: cloneType,
        },
      }
    );
    return response.data;
  },

  async getAnalysisChurn(
    analysisId: string,
    limit: number = 100,
    offset: number = 0
  ): Promise<import("../types/api").ChurnResponse> {
    const response = await apiClient.get<import("../types/api").ChurnResponse>(
      `/analyses/${analysisId}/churn`,
      {
        params: {
          limit,
          offset,
        },
      }
    );
    return response.data;
  },

  async getRepositoryTimeline(
    repositoryId: string
  ): Promise<import("../types/api").TimelineResponse> {
    const response = await apiClient.get<import("../types/api").TimelineResponse>(
      `/repositories/${repositoryId}/timeline`
    );
    return response.data;
  },
};
