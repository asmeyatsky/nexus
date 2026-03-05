import apiClient from "@/lib/api-client";
import type { Lead, CreateLeadRequest, ConvertLeadRequest } from "./leads-types";
import type { PaginatedResponse } from "@/lib/types";

export const leadsApi = {
  list: (params: Record<string, string | number>) =>
    apiClient.get<PaginatedResponse<Lead>>("/leads", { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Lead>(`/leads/${id}`).then((r) => r.data),

  create: (data: CreateLeadRequest) =>
    apiClient.post<Lead>("/leads", data).then((r) => r.data),

  qualify: (id: string) =>
    apiClient.post<Lead>(`/leads/${id}/qualify`).then((r) => r.data),

  convert: (id: string, data: ConvertLeadRequest) =>
    apiClient.post<Lead>(`/leads/${id}/convert`, data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/leads/${id}`),
};
