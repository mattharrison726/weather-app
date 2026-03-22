/**
 * TypeScript types mirroring the backend Pydantic response schemas.
 *
 * Keeping these in sync with schemas/weather.py, schemas/pipeline.py, and
 * schemas/locations.py is a manual contract right now. In a larger project
 * you'd generate these automatically from the OpenAPI spec (e.g. with
 * openapi-typescript).
 */

export interface WeatherObservation {
  id: number;
  location_key: string;
  observed_at: string; // ISO 8601
  temperature_c: number | null;
  apparent_temperature_c: number | null;
  relative_humidity_pct: number | null;
  precipitation_mm: number | null;
  wind_speed_kmh: number | null;
  wind_direction_deg: number | null;
  weather_code: number | null;
  weather_description: string | null;
  is_day: boolean | null;
  data_quality_flag: string;
}

export interface CurrentWeather {
  location_name: string;
  latitude: number;
  longitude: number;
  observation: WeatherObservation;
}

export interface PipelineRun {
  run_id: string;
  pipeline_name: string;
  triggered_by: string;
  location_key: string | null;
  started_at: string; // ISO 8601
  completed_at: string | null;
  status: string; // 'success' | 'failed' | 'partial' | 'running'
  rows_fetched: number;
  rows_transformed: number;
  rows_failed: number;
  error_message: string | null;
  duration_seconds: number | null;
}

export interface TriggerResponse {
  message: string;
  run_id: string;
  status: string;
  rows_fetched: number;
  rows_transformed: number;
  rows_failed: number;
  duration_seconds: number | null;
  error_message: string | null;
}

// --- Location types ---

export interface FavoriteLocation {
  location_key: string;
  name: string;
  country: string;
  latitude: number;
  longitude: number;
  added_at: string; // ISO 8601
}

export interface CatalogCity {
  location_key: string;
  name: string;
  country: string;
  latitude: number;
  longitude: number;
  is_favorite: boolean;
}

export interface BackfillRequest {
  location_key: string;
  start_date: string; // YYYY-MM-DD
  end_date: string;   // YYYY-MM-DD
}

export interface BackfillResponse {
  location_key: string;
  location_name: string;
  start_date: string;
  end_date: string;
  rows_written: number;
  rows_skipped: number;
  rows_transformed: number;
  rows_failed: number;
  duration_seconds: number;
}
