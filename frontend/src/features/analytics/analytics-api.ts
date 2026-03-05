import apiClient from "@/lib/api-client";

export const analyticsApi = {
  revenueForecast: (ownerId?: string) =>
    apiClient.get("/analytics/revenue-forecast", { params: ownerId ? { owner_id: ownerId } : {} }).then((r) => r.data),

  leadScores: (ownerId?: string) =>
    apiClient.get("/analytics/lead-scores", { params: ownerId ? { owner_id: ownerId } : {} }).then((r) => r.data),

  trends: (entity: string, period: string, groupBy?: string, ownerId?: string) =>
    apiClient.get("/analytics/trends", {
      params: { entity, period, ...(groupBy ? { group_by: groupBy } : {}), ...(ownerId ? { owner_id: ownerId } : {}) },
    }).then((r) => r.data),

  winLoss: (ownerId?: string) =>
    apiClient.get("/analytics/win-loss", { params: ownerId ? { owner_id: ownerId } : {} }).then((r) => r.data),
};
