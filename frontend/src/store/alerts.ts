import { create } from "zustand";

export interface Subscription {
  id: string;
  h3_index: string;
  threshold_probability: number;
  channels: string[];
  is_active: boolean;
}

interface AlertsStore {
  subscriptions: Subscription[];
  setSubscriptions: (data: Subscription[]) => void;
  addSubscription: (sub: Subscription) => void;
  removeSubscription: (id: string) => void;
}

export const useAlertsStore = create<AlertsStore>((set) => ({
  subscriptions: [],
  setSubscriptions: (data) => set({ subscriptions: data }),
  addSubscription: (sub) => set((s) => ({ subscriptions: [...s.subscriptions, sub] })),
  removeSubscription: (id) =>
    set((s) => ({ subscriptions: s.subscriptions.filter((x) => x.id !== id) })),
}));
