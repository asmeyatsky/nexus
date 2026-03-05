import apiClient from "@/lib/api-client";
import type { Case, CreateCaseRequest, ResolveCaseRequest } from "./cases-types";
import type { PaginatedResponse } from "@/lib/types";

export const casesApi = {
  list: (params: Record<string, string | number>) =>
    apiClient.get<PaginatedResponse<Case>>("/cases", { params }).then((r) => r.data),

  listOpen: (params: { limit: number; offset: number }) =>
    apiClient.get<Case[]>("/cases/open", { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Case>(`/cases/${id}`).then((r) => r.data),

  create: (data: CreateCaseRequest) =>
    apiClient.post<Case>("/cases", data).then((r) => r.data),

  updateStatus: (id: string, status: string) =>
    apiClient.patch<Case>(`/cases/${id}/status`, { status }).then((r) => r.data),

  resolve: (id: string, data: ResolveCaseRequest) =>
    apiClient.post<Case>(`/cases/${id}/resolve`, data).then((r) => r.data),

  close: (id: string) =>
    apiClient.post<Case>(`/cases/${id}/close`).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/cases/${id}`),
};
