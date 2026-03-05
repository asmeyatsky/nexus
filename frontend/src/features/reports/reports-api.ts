import apiClient from "@/lib/api-client";

export const reportsApi = {
  pipelineSummary: (ownerId?: string) =>
    apiClient.get("/reports/pipeline-summary", { params: ownerId ? { owner_id: ownerId } : {} }).then((r) => r.data),

  leadFunnel: (ownerId?: string) =>
    apiClient.get("/reports/lead-funnel", { params: ownerId ? { owner_id: ownerId } : {} }).then((r) => r.data),

  caseMetrics: (ownerId?: string) =>
    apiClient.get("/reports/case-metrics", { params: ownerId ? { owner_id: ownerId } : {} }).then((r) => r.data),

  activitySummary: (period: string = "day", ownerId?: string) =>
    apiClient.get("/reports/activity-summary", { params: { period, ...(ownerId ? { owner_id: ownerId } : {}) } }).then((r) => r.data),
};
