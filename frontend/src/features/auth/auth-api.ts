import apiClient from "@/lib/api-client";
import type { LoginRequest, LoginResponse } from "./auth-types";

export async function loginApi(data: LoginRequest): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>("/auth/login", data);
  return response.data;
}

export async function logoutApi(): Promise<void> {
  await apiClient.post("/auth/logout");
}

export async function refreshApi(): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>("/auth/refresh");
  return response.data;
}
