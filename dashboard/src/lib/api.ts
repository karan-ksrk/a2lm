const BASE = "/api/admin";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("a2lm_token");
}

export function setToken(token: string) {
  localStorage.setItem("a2lm_token", token);
}

export function clearToken() {
  localStorage.removeItem("a2lm_token");
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const login = (username: string, password: string) =>
  request<{ access_token: string; token_type: string }>("POST", "/login", {
    username,
    password,
  });

// ── Providers ─────────────────────────────────────────────────────────────────

export interface Provider {
  id: string;
  display_name: string;
  adapter_class: string;
  base_url: string | null;
  is_active: boolean;
  requires_account_id: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProviderIn {
  id: string;
  display_name: string;
  adapter_class: string;
  base_url?: string;
  is_active?: boolean;
  requires_account_id?: boolean;
}

export const listProviders = () => request<Provider[]>("GET", "/providers");
export const createProvider = (body: ProviderIn) =>
  request<Provider>("POST", "/providers", body);
export const updateProvider = (id: string, body: Partial<ProviderIn>) =>
  request<Provider>("PUT", `/providers/${id}`, body);
export const deleteProvider = (id: string) =>
  request<{ deleted: boolean }>("DELETE", `/providers/${id}`);

// ── Models ────────────────────────────────────────────────────────────────────

export interface Model {
  id: string;
  provider_id: string;
  native_id: string;
  display_name: string | null;
  context_len: number;
  supports_streaming: boolean;
  supports_vision: boolean;
  weight: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ModelIn {
  id: string;
  provider_id: string;
  native_id: string;
  display_name?: string;
  context_len?: number;
  supports_streaming?: boolean;
  supports_vision?: boolean;
  weight?: number;
  is_active?: boolean;
}

export const listModels = () => request<Model[]>("GET", "/models");
export const createModel = (body: ModelIn) =>
  request<Model>("POST", "/models", body);
export const updateModel = (id: string, body: Partial<ModelIn>) =>
  request<Model>("PUT", `/models/${id}`, body);
export const deleteModel = (id: string) =>
  request<{ deleted: boolean }>("DELETE", `/models/${id}`);

// ── Aliases ───────────────────────────────────────────────────────────────────

export interface Alias {
  id: number;
  alias_name: string;
  provider_id: string;
  native_id: string;
  priority: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AliasIn {
  alias_name: string;
  provider_id: string;
  native_id: string;
  priority: number;
  is_active?: boolean;
}

export const listAliases = () => request<Alias[]>("GET", "/aliases");
export const createAlias = (body: AliasIn) =>
  request<Alias>("POST", "/aliases", body);
export const updateAlias = (
  id: number,
  body: { priority?: number; is_active?: boolean }
) => request<Alias>("PUT", `/aliases/${id}`, body);
export const deleteAlias = (id: number) =>
  request<{ deleted: boolean }>("DELETE", `/aliases/${id}`);

// ── Rate Limits ───────────────────────────────────────────────────────────────

export interface RateLimit {
  id: number;
  provider_id: string;
  native_id: string;
  rpm: number;
  daily: number;
  notes: string | null;
  updated_at: string;
}

export interface RateLimitIn {
  rpm: number;
  daily: number;
  notes?: string;
}

export const listRateLimits = () => request<RateLimit[]>("GET", "/rate-limits");
export const upsertRateLimit = (
  provider_id: string,
  native_id: string,
  body: RateLimitIn
) =>
  request<RateLimit>(
    "PUT",
    `/rate-limits/${encodeURIComponent(provider_id)}/${encodeURIComponent(native_id)}`,
    body
  );
export const deleteRateLimit = (provider_id: string, native_id: string) =>
  request<{ deleted: boolean }>(
    "DELETE",
    `/rate-limits/${encodeURIComponent(provider_id)}/${encodeURIComponent(native_id)}`
  );
