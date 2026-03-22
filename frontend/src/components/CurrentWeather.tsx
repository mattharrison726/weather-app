import type { CurrentWeather } from "../types/weather";
import {
  tempDisplay,
  tempUnitLabel,
  windDisplay,
  precipDisplay,
} from "../utils/units";
import type { UnitSystem } from "../utils/units";

interface Props {
  data: CurrentWeather;
  units: UnitSystem;
}

/** Maps wind degrees to a compass direction label. */
function windDirection(deg: number | null): string {
  if (deg === null) return "—";
  const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return dirs[Math.round(deg / 45) % 8];
}

export function CurrentWeatherCard({ data, units }: Props) {
  const obs = data.observation;
  const isDay = obs.is_day ?? true;

  return (
    <div className="card current-weather">
      <div className="card-header">
        <h2>{data.location_name}</h2>
        <span className="coords">
          {data.latitude}°, {data.longitude}°
        </span>
      </div>

      <div className="weather-primary">
        <div className="temperature">
          {obs.temperature_c !== null ? (
            <>
              <span className="temp-value">
                {units === "imperial"
                  ? ((obs.temperature_c * 9) / 5 + 32).toFixed(1)
                  : obs.temperature_c.toFixed(1)}
              </span>
              <span className="temp-unit">{tempUnitLabel(units)}</span>
            </>
          ) : (
            <span className="temp-value">—</span>
          )}
        </div>
        <div className="weather-description">
          <div className="condition">{obs.weather_description ?? "Unknown"}</div>
          {obs.apparent_temperature_c !== null && (
            <div className="feels-like">
              Feels like {tempDisplay(obs.apparent_temperature_c, units)}
            </div>
          )}
          <div className="day-night">{isDay ? "Daytime" : "Night"}</div>
        </div>
      </div>

      <div className="weather-details">
        <div className="detail">
          <span className="detail-label">Humidity</span>
          <span className="detail-value">
            {obs.relative_humidity_pct !== null
              ? `${obs.relative_humidity_pct}%`
              : "—"}
          </span>
        </div>
        <div className="detail">
          <span className="detail-label">Precipitation</span>
          <span className="detail-value">
            {precipDisplay(obs.precipitation_mm, units)}
          </span>
        </div>
        <div className="detail">
          <span className="detail-label">Wind</span>
          <span className="detail-value">
            {obs.wind_speed_kmh !== null
              ? `${windDisplay(obs.wind_speed_kmh, units)} ${windDirection(obs.wind_direction_deg)}`
              : "—"}
          </span>
        </div>
        <div className="detail">
          <span className="detail-label">Quality</span>
          <span className={`detail-value quality-${obs.data_quality_flag}`}>
            {obs.data_quality_flag}
          </span>
        </div>
      </div>

      <div className="observed-at">
        Observed {new Date(obs.observed_at).toLocaleString()}
      </div>
    </div>
  );
}
