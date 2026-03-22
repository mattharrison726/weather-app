/**
 * Typed API client for the weather app backend.
 *
 * All backend communication goes through this module. Benefits:
 *  - One place to change the base URL (dev vs prod)
 *  - Typed return values — TypeScript catches mismatches at compile time
 *  - Error handling in one place, not scattered across components
 */
import type {
  BackfillRequest,
  BackfillResponse,
  CatalogCity,
  CurrentWeather,
  FavoriteLocation,
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
  // 204 No Content has no body
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  // --- Weather ---

  /** Fetch the most recent weather observation for a location. */
  getCurrentWeather(locationKey?: string): Promise<CurrentWeather> {
    const qs = locationKey ? `?location_key=${encodeURIComponent(locationKey)}` : "";
    return request<CurrentWeather>(`/api/weather/current${qs}`);
  },

  /** Fetch recent observation history (newest first). */
  getWeatherHistory(locationKey?: string, limit = 48): Promise<WeatherObservation[]> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (locationKey) params.set("location_key", locationKey);
    return request<WeatherObservation[]>(`/api/weather/history?${params}`);
  },

  // --- Pipeline ---

  /** Fetch pipeline run history (newest first). */
  getPipelineRuns(limit = 10): Promise<PipelineRun[]> {
    return request<PipelineRun[]>(`/api/pipeline/runs?limit=${limit}`);
  },

  /** Trigger the ETL pipeline for all favorites (or a specific location). */
  triggerPipeline(locationKey?: string): Promise<TriggerResponse[]> {
    const qs = locationKey ? `?location_key=${encodeURIComponent(locationKey)}` : "";
    return request<TriggerResponse[]>(`/api/pipeline/trigger${qs}`, {
      method: "POST",
    });
  },

  /** Run a historical backfill for a location. */
  runBackfill(body: BackfillRequest): Promise<BackfillResponse> {
    return request<BackfillResponse>("/api/pipeline/backfill", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },

  // --- Locations ---

  /** Get the full catalog of available cities. */
  getCatalog(): Promise<CatalogCity[]> {
    return request<CatalogCity[]>("/api/locations/catalog");
  },

  /** Get the user's favorited locations. */
  getFavorites(): Promise<FavoriteLocation[]> {
    return request<FavoriteLocation[]>("/api/locations/favorites");
  },

  /** Add a catalog city to favorites. */
  addFavorite(locationKey: string): Promise<FavoriteLocation> {
    return request<FavoriteLocation>(
      `/api/locations/favorites/${encodeURIComponent(locationKey)}`,
      { method: "POST" }
    );
  },

  /** Remove a location from favorites. */
  removeFavorite(locationKey: string): Promise<void> {
    return request<void>(
      `/api/locations/favorites/${encodeURIComponent(locationKey)}`,
      { method: "DELETE" }
    );
  },
};
