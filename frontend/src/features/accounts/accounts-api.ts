import apiClient from "@/lib/api-client";
import type { Account, CreateAccountRequest } from "./accounts-types";

export const accountsApi = {
  list: (params: { limit: number; offset: number }) =>
    apiClient.get<Account[]>("/accounts", { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Account>(`/accounts/${id}`).then((r) => r.data),

  create: (data: CreateAccountRequest) =>
    apiClient.post<Account>("/accounts", data).then((r) => r.data),

  update: (id: string, data: CreateAccountRequest) =>
    apiClient.put<Account>(`/accounts/${id}`, data).then((r) => r.data),

  deactivate: (id: string) =>
    apiClient.post<Account>(`/accounts/${id}/deactivate`).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/accounts/${id}`),
};
