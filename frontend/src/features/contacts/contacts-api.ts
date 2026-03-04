import apiClient from "@/lib/api-client";
import type { Contact, CreateContactRequest } from "./contacts-types";

export const contactsApi = {
  list: (params: { limit: number; offset: number }) =>
    apiClient.get<Contact[]>("/contacts", { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Contact>(`/contacts/${id}`).then((r) => r.data),

  create: (data: CreateContactRequest) =>
    apiClient.post<Contact>("/contacts", data).then((r) => r.data),

  update: (id: string, data: CreateContactRequest) =>
    apiClient.put<Contact>(`/contacts/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/contacts/${id}`),
};
