import { useEffect, useState } from "react";
import api from "../services/api";

export interface DurationPrediction {
  min_minutes: number;
  median_minutes: number;
  max_minutes: number;
  label: string;
  confidence: "low" | "medium" | "high";
  sample_size: number;
}

export interface AccuracyMetrics {
  accuracy_pct: number | null;
  grade: string;
  verdict: string;
  total_predictions: number;
  true_positives: number;
  false_positives: number;
  true_negatives: number;
  false_negatives: number;
  period_days: number;
}

export interface RankingEntry {
  rank: number;
  h3_index: string;
  city: string;
  country_code: string;
  outages_7d: number;
  outages_30d: number;
  avg_duration_minutes: number | null;
}

export interface CalendarDay {
  day: number;
  date: string;
  outage_count: number;
  total_duration_minutes: number;
  max_probability: number;
  risk_level: string;
  is_future: boolean;
}

export interface CalendarData {
  h3_index: string;
  year: number;
  month: number;
  month_name: string;
  days_in_month: number;
  total_outages: number;
  days: CalendarDay[];
}

export interface CellRank {
  rank_in_country: number | null;
  total_ranked_cells: number;
  percentile: number | null;
  city: string;
  outages_30d: number;
}

export function useDuration(h3_index: string, country_code: string) {
  const [data, setData] = useState<DurationPrediction | null>(null);
  useEffect(() => {
    if (!h3_index) return;
    api.get(`/analytics/duration/${h3_index}`, { params: { country_code } })
      .then(r => setData(r.data)).catch(() => {});
  }, [h3_index, country_code]);
  return data;
}

export function useAccuracy(h3_index: string, days = 30) {
  const [data, setData] = useState<AccuracyMetrics | null>(null);
  useEffect(() => {
    if (!h3_index) return;
    api.get(`/analytics/accuracy/${h3_index}`, { params: { days } })
      .then(r => setData(r.data)).catch(() => {});
  }, [h3_index, days]);
  return data;
}

export function useRankings(country_code: string, limit = 20) {
  const [data, setData] = useState<RankingEntry[]>([]);
  useEffect(() => {
    if (!country_code) return;
    api.get("/analytics/rankings", { params: { country_code, limit } })
      .then(r => setData(r.data)).catch(() => {});
  }, [country_code, limit]);
  return data;
}

export function useCellRank(h3_index: string) {
  const [data, setData] = useState<CellRank | null>(null);
  useEffect(() => {
    if (!h3_index) return;
    api.get(`/analytics/rankings/cell/${h3_index}`)
      .then(r => setData(r.data)).catch(() => {});
  }, [h3_index]);
  return data;
}

export function useCalendar(h3_index: string, year?: number, month?: number) {
  const [data, setData] = useState<CalendarData | null>(null);
  const now = new Date();
  const y = year ?? now.getFullYear();
  const m = month ?? now.getMonth() + 1;

  useEffect(() => {
    if (!h3_index) return;
    api.get(`/analytics/calendar/${h3_index}`, { params: { year: y, month: m } })
      .then(r => setData(r.data)).catch(() => {});
  }, [h3_index, y, m]);

  return data;
}
