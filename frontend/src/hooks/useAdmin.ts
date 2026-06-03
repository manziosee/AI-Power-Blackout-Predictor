import { useEffect, useState } from "react";
import api from "../services/api";

export interface PlatformStats {
  users: { total: number; new_today: number; new_week: number; new_month: number };
  sms: { total_30d: number; delivered: number; failed: number; queued: number; delivery_rate: number | null };
  outages: { reports_today: number; reports_week: number };
  predictions: { run_today: number };
  fraud: { open_flags: number };
}

export interface SmppConnector {
  id: string;
  operator: string;
  country: string;
  host: string;
  configured: boolean;
}

export interface CeleryHealth {
  status: string;
  worker_count: number;
  workers: string[];
  active_tasks: number;
  scheduled_tasks: number;
  detail?: string;
}

export interface FraudFlag {
  id: string;
  user_id: string | null;
  report_id: string | null;
  rule: string;
  detail: string | null;
  severity: string;
  resolved: boolean;
  created_at: string;
}

export interface AdminUser {
  id: string;
  phone: string;
  country_code: string;
  language: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface AccuracyRow {
  country_code: string;
  regions: number;
  avg_accuracy: number | null;
  avg_f1: number | null;
  total_predictions: number;
}

export function useAdminStats() {
  const [data, setData] = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);
  const fetch = () => {
    setLoading(true);
    api.get("/admin/stats").then(r => setData(r.data)).finally(() => setLoading(false));
  };
  useEffect(fetch, []);
  return { data, loading, refetch: fetch };
}

export function useSmppStatus() {
  const [connectors, setConnectors] = useState<SmppConnector[]>([]);
  useEffect(() => {
    api.get("/admin/smpp-status").then(r => setConnectors(r.data.connectors)).catch(() => {});
  }, []);
  return connectors;
}

export function useCeleryHealth() {
  const [data, setData] = useState<CeleryHealth | null>(null);
  const fetch = () => api.get("/admin/celery-health").then(r => setData(r.data)).catch(() => {});
  useEffect(() => { fetch(); }, []);
  return { data, refetch: fetch };
}

export function useFraudFlags(resolved = false) {
  const [flags, setFlags] = useState<FraudFlag[]>([]);
  const fetch = () => api.get("/admin/fraud/flags", { params: { resolved } }).then(r => setFlags(r.data)).catch(() => {});
  useEffect(fetch, [resolved]);

  const resolve = async (id: string) => {
    await api.patch(`/admin/fraud/flags/${id}`, {});
    setFlags(prev => prev.filter(f => f.id !== id));
  };

  return { flags, resolve, refetch: fetch };
}

export function useAdminUsers(search = "") {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const fetch = () => api.get("/admin/users", { params: { search: search || undefined } }).then(r => setUsers(r.data)).catch(() => {});
  useEffect(fetch, [search]);

  const toggleBan = async (id: string) => {
    const { data } = await api.patch(`/admin/users/${id}/ban`);
    setUsers(prev => prev.map(u => u.id === id ? { ...u, is_active: data.is_active } : u));
  };

  return { users, toggleBan, refetch: fetch };
}

export function useAccuracy() {
  const [rows, setRows] = useState<AccuracyRow[]>([]);
  useEffect(() => {
    api.get("/admin/accuracy").then(r => setRows(r.data)).catch(() => {});
  }, []);
  return rows;
}
