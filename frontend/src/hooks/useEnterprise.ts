import { useEffect, useState } from "react";
import api from "../services/api";

export interface UtilityStats {
  company: string;
  country_code: string;
  plan: string;
  stats: {
    outages_last_24h: number;
    active_unresolved: number;
    verified_last_7d: number;
    total_last_30d: number;
    avg_duration_minutes: number | null;
    high_risk_areas_now: number;
  };
}

export interface LiveOutage {
  id: string;
  h3_index: string;
  lat: number | null;
  lng: number | null;
  reported_at: string;
  resolved_at: string | null;
  duration_minutes: number | null;
  verification_count: number;
  verified: boolean;
  source: string;
}

export interface ImpactScore {
  business_type: string;
  business_type_label: string;
  direct_loss_usd: number;
  expected_loss_usd: number;
  monthly_risk_usd: number;
  recommendation: string;
  using_custom_revenue: boolean;
  duration_hours: number;
  probability: number;
}

export interface WebhookSub {
  id: string;
  h3_index: string;
  url: string;
  secret: string;
  threshold_probability: number;
  events: string[];
  is_active: boolean;
  last_triggered_at: string | null;
}

export interface WebhookEvent {
  id: string;
  event_type: string;
  success: boolean;
  response_status: number | null;
  attempt: number;
  fired_at: string;
  error: string | null;
}

// Utility API key auth header helper
export function utilityHeaders(apiKey: string) {
  return { "X-Utility-API-Key": apiKey };
}

export function useUtilityDashboard(apiKey: string) {
  const [data, setData] = useState<UtilityStats | null>(null);
  const [error, setError] = useState("");

  const fetch = () => {
    if (!apiKey) return;
    api.get("/utility/dashboard", { headers: utilityHeaders(apiKey) })
      .then(r => { setData(r.data); setError(""); })
      .catch(() => setError("Invalid API key or server error"));
  };

  useEffect(fetch, [apiKey]);
  return { data, error, refetch: fetch };
}

export function useLiveOutages(apiKey: string, hours = 24) {
  const [outages, setOutages] = useState<LiveOutage[]>([]);
  useEffect(() => {
    if (!apiKey) return;
    api.get("/utility/outages/live", { headers: utilityHeaders(apiKey), params: { hours } })
      .then(r => setOutages(r.data)).catch(() => {});
  }, [apiKey, hours]);
  return outages;
}

export function useMyImpact(durationHours = 2, probability = 0.7) {
  const [data, setData] = useState<ImpactScore[] | null>(null);
  useEffect(() => {
    api.get("/business/impact/me", { params: { duration_hours: durationHours, probability } })
      .then(r => setData(Array.isArray(r.data) ? r.data : null)).catch(() => {});
  }, [durationHours, probability]);
  return data;
}

export function useWebhooks() {
  const [subs, setSubs] = useState<WebhookSub[]>([]);

  const fetch = () => {
    api.get("/webhooks/").then(r => setSubs(r.data)).catch(() => {});
  };

  useEffect(fetch, []);

  const create = async (payload: { h3_index: string; url: string; threshold_probability: number; events: string[] }) => {
    const { data } = await api.post("/webhooks/", payload);
    setSubs(prev => [...prev, data]);
    return data;
  };

  const remove = async (id: string) => {
    await api.delete(`/webhooks/${id}`);
    setSubs(prev => prev.filter(s => s.id !== id));
  };

  const test = async (id: string) => {
    const { data } = await api.post(`/webhooks/${id}/test`);
    return data;
  };

  return { subs, create, remove, test, refetch: fetch };
}
