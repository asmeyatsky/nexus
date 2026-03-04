import apiClient from "@/lib/api-client";
import type { Opportunity, CreateOpportunityRequest, UpdateStageRequest } from "./opportunities-types";

export const opportunitiesApi = {
  list: (params: { limit: number; offset: number }) =>
    apiClient.get<Opportunity[]>("/opportunities", { params }).then((r) => r.data),

  listOpen: (params: { limit: number; offset: number }) =>
    apiClient.get<Opportunity[]>("/opportunities/open", { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Opportunity>(`/opportunities/${id}`).then((r) => r.data),

  create: (data: CreateOpportunityRequest) =>
    apiClient.post<Opportunity>("/opportunities", data).then((r) => r.data),

  update: (id: string, data: CreateOpportunityRequest) =>
    apiClient.put<Opportunity>(`/opportunities/${id}`, data).then((r) => r.data),

  updateStage: (id: string, data: UpdateStageRequest) =>
    apiClient.patch<Opportunity>(`/opportunities/${id}/stage`, data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/opportunities/${id}`),
};
