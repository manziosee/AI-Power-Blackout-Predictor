import {
  CarbonImpact,
  ClientOptions,
  HealthResponse,
  HeatmapResponse,
  OutageReport,
  Prediction,
  PredictionExplanation,
  WeatherCurrent,
} from "./types.js";
import { BlackoutApiError, BlackoutAuthError, BlackoutNetworkError } from "./errors.js";

const DEFAULT_BASE_URL = "http://localhost:8000";
const DEFAULT_TIMEOUT_MS = 30_000;

export class BlackoutClient {
  private readonly baseUrl: string;
  private readonly headers: Record<string, string>;
  private readonly timeout: number;

  constructor(options: ClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/$/, "");
    this.timeout = options.timeout ?? DEFAULT_TIMEOUT_MS;
    this.headers = {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(options.apiKey ? { Authorization: `Bearer ${options.apiKey}` } : {}),
    };
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);
    try {
      const resp = await fetch(url, {
        ...init,
        headers: { ...this.headers, ...(init.headers as Record<string, string> | undefined) },
        signal: controller.signal,
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({ detail: resp.statusText }));
        const detail: string = body?.detail ?? resp.statusText;
        if (resp.status === 401 || resp.status === 403) throw new BlackoutAuthError(resp.status, detail, url);
        throw new BlackoutApiError(resp.status, detail, url);
      }
      return (await resp.json()) as T;
    } catch (err) {
      if (err instanceof BlackoutApiError) throw err;
      throw new BlackoutNetworkError(`Request to ${url} failed`, err);
    } finally {
      clearTimeout(timer);
    }
  }

  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  async getPrediction(h3Index: string): Promise<Prediction> {
    return this.request<Prediction>(`/api/v1/predictions/cell/${h3Index}`);
  }

  async explainPrediction(h3Index: string): Promise<PredictionExplanation> {
    return this.request<PredictionExplanation>(`/api/v1/predictions/cell/${h3Index}/explain`);
  }

  async getHeatmap(bounds?: { north: number; south: number; east: number; west: number }): Promise<HeatmapResponse> {
    const q = bounds
      ? `?north=${bounds.north}&south=${bounds.south}&east=${bounds.east}&west=${bounds.west}`
      : "";
    return this.request<HeatmapResponse>(`/api/v1/predictions/heatmap${q}`);
  }

  async getOutageReports(h3Index: string, limit = 20): Promise<OutageReport[]> {
    return this.request<OutageReport[]>(`/api/v1/outages/${h3Index}?limit=${limit}`);
  }

  async getCarbonImpact(hours = 2, loadMw = 0.5): Promise<CarbonImpact> {
    return this.request<CarbonImpact>(`/api/v1/carbon/impact?hours=${hours}&load_mw=${loadMw}`);
  }

  async getCurrentWeather(h3Index: string): Promise<{ current: WeatherCurrent }> {
    return this.request(`/api/v1/weather/current/${h3Index}`);
  }

  async askAssistant(question: string, h3Index?: string): Promise<{ answer: string }> {
    return this.request("/api/v1/assistant/ask", {
      method: "POST",
      body: JSON.stringify({ question, h3_index: h3Index }),
    });
  }
}
