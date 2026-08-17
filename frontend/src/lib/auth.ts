import { api } from "./api";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RoleOut {
  id: string;
  name: string;
}

export interface MeResponse {
  id: string;
  email: string;
  full_name: string;
  tenant_id: string | null;
  is_superadmin: boolean;
  roles: RoleOut[];
  permission_modules: string[];
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/login", { email, password });
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  return data;
}

/** Consumes an invite-email link's token, sets the account's real
 * password, and logs the user straight in. */
export async function setPassword(token: string, newPassword: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/set-password", { token, new_password: newPassword });
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  return data;
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "/login";
}

export async function fetchMe(): Promise<MeResponse> {
  const { data } = await api.get<MeResponse>("/auth/me");
  return data;
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(localStorage.getItem("access_token"));
}
