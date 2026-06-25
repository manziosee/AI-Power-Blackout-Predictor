import axios from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";

const BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface Prediction {
  h3_index: string;
  probability: number;
  risk_level: "low" | "medium" | "high" | "critical";
  window_start: string;
  window_end: string;
}

export interface OutageReport {
  id: string;
  h3_index: string;
  verified: boolean;
  created_at: string;
}

export const getPrediction = (h3Index: string) =>
  api.get<Prediction>(`/api/v1/predictions/cell/${h3Index}`).then((r) => r.data);

export const getHeatmap = () =>
  api.get(`/api/v1/predictions/heatmap`).then((r) => r.data);

export const getRecentOutages = (h3Index: string, limit = 20) =>
  api.get<OutageReport[]>(`/api/v1/outages/${h3Index}?limit=${limit}`).then((r) => r.data);

export const reportOutage = (h3Index: string, description?: string) =>
  api.post("/api/v1/outages", { h3_index: h3Index, description }).then((r) => r.data);

export const getHealth = () => api.get("/health").then((r) => r.data);

export const login = async (phone: string, otp: string): Promise<string> => {
  const resp = await api.post<{ access_token: string }>("/api/v1/users/verify-otp", {
    phone,
    otp_code: otp,
  });
  const token = resp.data.access_token;
  await AsyncStorage.setItem("access_token", token);
  return token;
};

export const logout = async () => {
  await AsyncStorage.removeItem("access_token");
};
