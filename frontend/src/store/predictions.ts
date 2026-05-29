import { create } from "zustand";

export interface Prediction {
  id: string;
  h3_index: string;
  probability: number;
  risk_level: "low" | "medium" | "high" | "critical";
  window_start: string;
  window_end: string;
}

export interface HeatmapCell {
  h3_index: string;
  probability: number;
  risk_level: string;
  center_lat: number;
  center_lng: number;
}

interface PredictionsStore {
  predictions: Record<string, Prediction[]>;
  heatmap: HeatmapCell[];
  loading: boolean;
  setPredictions: (h3_index: string, data: Prediction[]) => void;
  setHeatmap: (data: HeatmapCell[]) => void;
  setLoading: (v: boolean) => void;
}

export const usePredictionsStore = create<PredictionsStore>((set) => ({
  predictions: {},
  heatmap: [],
  loading: false,
  setPredictions: (h3_index, data) =>
    set((s) => ({ predictions: { ...s.predictions, [h3_index]: data } })),
  setHeatmap: (data) => set({ heatmap: data }),
  setLoading: (v) => set({ loading: v }),
}));
