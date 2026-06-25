export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface Prediction {
  h3_index: string;
  probability: number;
  risk_level: RiskLevel;
  window_start: string;
  window_end: string;
  model_version: string;
}

export interface PredictionExplanation {
  h3_index: string;
  probability: number;
  risk_level: RiskLevel;
  model_version: string;
  top_factor: string;
  feature_weights: Record<string, number>;
}

export interface OutageReport {
  id: string;
  h3_index: string;
  verified: boolean;
  description: string | null;
  created_at: string;
}

export interface HeatmapFeature {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: { h3_index: string; probability: number; risk_level: RiskLevel };
}

export interface HeatmapResponse {
  type: "FeatureCollection";
  features: HeatmapFeature[];
}

export interface HealthResponse {
  status: string;
  db: string;
  redis: string;
  ws_connections: number;
}

export interface CarbonImpact {
  affected_cells: number;
  duration_hours: number;
  kwh_lost: number;
  co2_kg_avoided: number;
  co2_tonnes_avoided: number;
  load_mw_per_cell: number;
}

export interface WeatherCurrent {
  time: string;
  temperature_c: number | null;
  humidity_pct: number | null;
  precipitation_mm: number | null;
  wind_speed_ms: number | null;
  cloud_cover_pct: number | null;
  weather_code: number | null;
}

export interface ClientOptions {
  baseUrl?: string;
  apiKey?: string;
  timeout?: number;
}
