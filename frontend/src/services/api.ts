import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1",
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Auth ─────────────────────────────────────────────────────────────────────
export const registerUser = (data: { phone: string; country_code: string; language: string; password?: string }) =>
  api.post("/users/register", data);

export const loginUser = (data: { phone: string; password: string }) =>
  api.post("/users/login", data);

export const getMe = () => api.get("/users/me");

// ── Predictions ───────────────────────────────────────────────────────────────
export const getCellPredictions = (h3_index: string) =>
  api.get(`/predictions/cell/${h3_index}`);

export const getHeatmap = (country_code: string) =>
  api.get(`/predictions/heatmap`, { params: { country_code } });

// ── Outages ───────────────────────────────────────────────────────────────────
export const reportOutage = (data: { h3_index?: string; lat?: number; lng?: number; source?: string }) =>
  api.post("/outages/report", data);

export const getCellOutages = (h3_index: string) =>
  api.get(`/outages/cell/${h3_index}`);

export const confirmOutage = (report_id: string) =>
  api.post(`/outages/${report_id}/confirm`);

// ── Alerts ────────────────────────────────────────────────────────────────────
export const getSubscriptions = () => api.get("/alerts/subscriptions");

export const createSubscription = (data: { h3_index: string; threshold_probability: number; channels: string[] }) =>
  api.post("/alerts/subscriptions", data);

export const deleteSubscription = (id: string) =>
  api.delete(`/alerts/subscriptions/${id}`);

export const getAlertHistory = () => api.get("/alerts/history");

// ── Neighborhoods ─────────────────────────────────────────────────────────────
export const lookupCell = (lat: number, lng: number) =>
  api.get("/neighborhoods/lookup", { params: { lat, lng } });

export default api;
