/**
 * TypeScript types mirroring the backend Pydantic response schemas.
 *
 * Keeping these in sync with schemas/weather.py and schemas/pipeline.py is
 * a manual contract right now. In a larger project you'd generate these
 * automatically from the OpenAPI spec (e.g. with openapi-typescript).
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
