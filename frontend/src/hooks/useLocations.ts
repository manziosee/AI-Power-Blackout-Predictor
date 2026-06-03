import { useEffect, useState } from "react";
import api from "../services/api";

export interface UserLocation {
  id: string;
  h3_index: string;
  label: string | null;
  is_primary: boolean;
  is_active: boolean;
  alert_threshold: number;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  notify_channels: string[];
}

export interface LocationPayload {
  h3_index: string;
  label?: string;
  is_primary?: boolean;
  alert_threshold?: number;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
  notify_channels?: string[];
}

export function useLocations() {
  const [locations, setLocations] = useState<UserLocation[]>([]);
  const [loading, setLoading] = useState(true);

  const fetch = () => {
    setLoading(true);
    api.get("/users/me/locations").then(r => setLocations(r.data)).finally(() => setLoading(false));
  };

  useEffect(fetch, []);

  const add = async (payload: LocationPayload) => {
    const { data } = await api.post("/users/me/locations", payload);
    setLocations(prev => [...prev, data]);
    return data as UserLocation;
  };

  const update = async (id: string, patch: Partial<LocationPayload> & { is_active?: boolean }) => {
    const { data } = await api.patch(`/users/me/locations/${id}`, patch);
    setLocations(prev => prev.map(l => l.id === id ? data : l));
    return data as UserLocation;
  };

  const remove = async (id: string) => {
    await api.delete(`/users/me/locations/${id}`);
    setLocations(prev => prev.filter(l => l.id !== id));
  };

  return { locations, loading, add, update, remove, refetch: fetch };
}
