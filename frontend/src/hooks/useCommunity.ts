import { useEffect, useState } from "react";
import api from "../services/api";

export interface Badge {
  key: string;
  name: string;
  emoji: string;
  description: string;
  earned_at: string;
}

export interface Level {
  name: string;
  emoji: string;
  next_at: number | null;
  progress_pct: number | null;
}

export interface UserStats {
  total_points: number;
  weekly_points: number;
  monthly_points: number;
  report_count: number;
  confirm_count: number;
  note_count: number;
  current_streak_days: number;
  level: Level;
  badges: Badge[];
}

export interface LeaderboardEntry {
  rank: number;
  phone_masked: string;
  country_code: string;
  points: number;
  total_points: number;
  report_count: number;
  confirm_count: number;
  streak: number;
  level: string;
}

export interface CommunityNote {
  id: string;
  h3_index: string;
  body: string;
  upvotes: number;
  created_at: string;
  expires_at: string;
  is_mine: boolean;
}

export function useMyStats() {
  const [data, setData] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);

  const refetch = () => {
    setLoading(true);
    api.get("/community/stats/me")
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { refetch(); }, []);
  return { data, loading, refetch };
}

export function useLeaderboard(country_code: string, period: "weekly" | "monthly" = "weekly") {
  const [data, setData] = useState<LeaderboardEntry[]>([]);
  useEffect(() => {
    if (!country_code) return;
    api.get("/community/leaderboard", { params: { country_code, period } })
      .then(r => setData(r.data)).catch(() => {});
  }, [country_code, period]);
  return data;
}

export function useCommunityNotes(h3_index: string) {
  const [notes, setNotes] = useState<CommunityNote[]>([]);
  const [loading, setLoading] = useState(false);

  const fetch = async () => {
    if (!h3_index) return;
    setLoading(true);
    try {
      const { data } = await api.get(`/community/notes/${h3_index}`);
      setNotes(data);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetch(); }, [h3_index]);

  const addNote = async (body: string) => {
    const { data } = await api.post("/community/notes", { h3_index, body });
    setNotes(prev => [data, ...prev]);
  };

  const upvote = async (note_id: string) => {
    const { data } = await api.post(`/community/notes/${note_id}/upvote`);
    setNotes(prev => prev.map(n => n.id === note_id ? { ...n, upvotes: data.upvotes } : n));
  };

  const remove = async (note_id: string) => {
    await api.delete(`/community/notes/${note_id}`);
    setNotes(prev => prev.filter(n => n.id !== note_id));
  };

  return { notes, loading, addNote, upvote, remove, refetch: fetch };
}
