/**
 * Typed API client for the weather app backend.
 *
 * All backend communication goes through this module. Benefits:
 *  - One place to change the base URL (dev vs prod)
 *  - Typed return values — TypeScript catches mismatches at compile time
 *  - Error handling in one place, not scattered across components
 */
import type {
  CurrentWeather,
  PipelineRun,
  TriggerResponse,
  WeatherObservation,
} from "../types/weather";

const BASE_URL = "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, options);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  /** Fetch the most recent weather observation. */
  getCurrentWeather(): Promise<CurrentWeather> {
    return request<CurrentWeather>("/api/weather/current");
  },

  /** Fetch recent observation history (newest first). */
  getWeatherHistory(limit = 48): Promise<WeatherObservation[]> {
    return request<WeatherObservation[]>(
      `/api/weather/history?limit=${limit}`
    );
  },

  /** Fetch pipeline run history (newest first). */
  getPipelineRuns(limit = 10): Promise<PipelineRun[]> {
    return request<PipelineRun[]>(`/api/pipeline/runs?limit=${limit}`);
  },

  /** Trigger the ETL pipeline immediately. */
  triggerPipeline(): Promise<TriggerResponse> {
    return request<TriggerResponse>("/api/pipeline/trigger", {
      method: "POST",
    });
  },
};
