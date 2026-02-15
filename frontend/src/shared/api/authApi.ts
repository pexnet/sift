import { ApiError, apiClient } from "./client";
import { parseAuthUser } from "../../entities/user/model";
import type { AuthUser, LoginRequest, RegisterRequest } from "../types/contracts";

const AUTH_BASE = "/api/v1/auth";

export async function getCurrentUser(): Promise<AuthUser | null> {
  try {
    const payload = await apiClient.get<unknown>(`${AUTH_BASE}/me`);
    return parseAuthUser(payload);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

export async function login(payload: LoginRequest): Promise<AuthUser> {
  const response = await apiClient.post<LoginRequest, unknown>(`${AUTH_BASE}/login`, payload);
  return parseAuthUser(response);
}

export async function register(payload: RegisterRequest): Promise<AuthUser> {
  const response = await apiClient.post<RegisterRequest, unknown>(`${AUTH_BASE}/register`, payload);
  return parseAuthUser(response);
}

export async function logout(): Promise<void> {
  await apiClient.post<Record<string, never>, null>(`${AUTH_BASE}/logout`, {});
}
