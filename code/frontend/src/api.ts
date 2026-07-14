// SubTrack API client.
// In dev, requests go to "/api" which Vite proxies to the backend (:8000).
// In prod, set VITE_API_BASE (e.g. "https://api.subtrack.app") so calls hit the
// backend on its own origin / through the same host.

const RAW_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || "";
const BASE = RAW_BASE.replace(/\/$/, "");

const TOKEN_KEY = "subtrack_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// Called when the backend rejects our token (401) so the app can force re-auth.
let onUnauthorized: (() => void) | null = null;
export function setOnUnauthorized(cb: (() => void) | null) {
  onUnauthorized = cb;
}

async function req(path: string, opts: RequestInit = {}) {
  const headers: Record<string, string> = { ...(opts.headers as any) };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (opts.body) headers["Content-Type"] = "application/json";
  const url = `${BASE}/api${path}`;
  const res = await fetch(url, { ...opts, headers });
  if (!res.ok) {
    const text = await res.text();
    if (res.status === 401) {
      clearToken();
      onUnauthorized?.();
    }
    throw new Error(`${res.status}: ${text}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export interface Subscription {
  id: number;
  merchant_name: string;
  amount: string;
  currency: string;
  billing_cycle: string;
  status: string;
  trial_end_date: string | null;
  next_renewal_date: string | null;
  notes: string | null;
  source: string;
}

export interface CalendarItem {
  subscription_id: number;
  merchant_name: string;
  kind: string;
  date: string;
}

export interface Prefs {
  email_alerts: boolean;
  sms_alerts: boolean;
  phone_verified: boolean;
  phone_number: string | null;
}

export const api = {
  register: (email: string, password: string) =>
    req("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    req("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => req("/auth/me"),
  createSub: (data: any) => req("/subscriptions", { method: "POST", body: JSON.stringify(data) }),
  updateSub: (id: number, data: any) =>
    req(`/subscriptions/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteSub: (id: number) => req(`/subscriptions/${id}`, { method: "DELETE" }),
  listSubs: (params: Record<string, string> = {}) => {
    const q = new URLSearchParams(params).toString();
    return req(`/subscriptions${q ? "?" + q : ""}`);
  },
  calendar: () => req("/subscriptions/calendar"),
  getPrefs: () => req("/alerts/preferences"),
  updatePrefs: (data: any) => req("/alerts/preferences", { method: "PUT", body: JSON.stringify(data) }),
  requestOtp: (phone_number: string) =>
    req("/auth/phone/request-otp", { method: "POST", body: JSON.stringify({ phone_number }) }),
  verifyOtp: (code: string) =>
    req("/auth/phone/verify-otp", { method: "POST", body: JSON.stringify({ code }) }),
  // Gmail auto-import (Phase 2)
  gmailStatus: () => req("/gmail/status"),
  gmailConnect: () => req("/gmail/connect"),
  gmailIngest: () => req("/gmail/ingest", { method: "POST" }),
  // Test alert (verify comms instantly)
  testAlert: () => req("/alerts/test", { method: "POST" }),
};
