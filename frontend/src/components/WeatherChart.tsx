import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { WeatherObservation } from "../types/weather";
import { tempValue, tempUnitLabel } from "../utils/units";
import type { UnitSystem } from "../utils/units";

interface Props {
  history: WeatherObservation[];
  units: UnitSystem;
}

interface ChartPoint {
  time: string;
  temperature: number | null;
  apparent_temperature: number | null;
}

function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function WeatherChart({ history, units }: Props) {
  const unitLabel = tempUnitLabel(units);

  // History arrives newest-first from the API; reverse for chronological chart
  const data: ChartPoint[] = [...history].reverse().map((obs) => ({
    time: formatTime(obs.observed_at),
    temperature: tempValue(obs.temperature_c, units),
    apparent_temperature: tempValue(obs.apparent_temperature_c, units),
  }));

  if (data.length === 0) {
    return (
      <div className="card chart-card">
        <h3>Temperature History</h3>
        <p className="empty-state">No history yet. Trigger a few pipeline runs.</p>
      </div>
    );
  }

  return (
    <div className="card chart-card">
      <h3>Temperature History (last {data.length} observations)</h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            tickFormatter={(v) => `${v}${unitLabel}`}
            domain={["auto", "auto"]}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "6px",
              color: "#f1f5f9",
            }}
            formatter={(value, name) => [
              typeof value === "number" ? `${value.toFixed(1)}${unitLabel}` : "—",
              name === "temperature" ? "Temp" : "Feels like",
            ]}
          />
          <Line
            type="monotone"
            dataKey="temperature"
            stroke="#38bdf8"
            strokeWidth={2}
            dot={false}
            name="temperature"
          />
          <Line
            type="monotone"
            dataKey="apparent_temperature"
            stroke="#818cf8"
            strokeWidth={1.5}
            strokeDasharray="4 2"
            dot={false}
            name="apparent_temperature"
          />
        </LineChart>
      </ResponsiveContainer>
      <div className="chart-legend">
        <span className="legend-item temp">— Temperature</span>
        <span className="legend-item feels">- - Feels like</span>
      </div>
    </div>
  );
}
