import { CurrentWeatherCard } from "./components/CurrentWeather";
import { PipelineStatus } from "./components/PipelineStatus";
import { WeatherChart } from "./components/WeatherChart";
import { useWeather } from "./hooks/useWeather";
import "./index.css";

export default function App() {
  const {
    current,
    history,
    runs,
    loading,
    triggering,
    error,
    lastRefreshed,
    fetchAll,
    triggerRefresh,
  } = useWeather();

  if (loading && !current) {
    return (
      <div className="app">
        <div className="loading-state">Loading weather data…</div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Weather App</h1>
        <p className="app-subtitle">Data engineering portfolio project</p>
      </header>

      {error && (
        <div className="error-banner">
          <strong>Error:</strong> {error}
          {error.includes("404") && (
            <span>
              {" "}
              — No data yet. Click <strong>Refresh Data</strong> below to run
              the pipeline.
            </span>
          )}
        </div>
      )}

      <main className="app-main">
        {current ? (
          <CurrentWeatherCard data={current} />
        ) : (
          !error && (
            <div className="card empty-card">
              <p>No weather data yet. Use the Refresh Data button below.</p>
            </div>
          )
        )}

        <WeatherChart history={history} />

        <PipelineStatus
          runs={runs}
          triggering={triggering}
          lastRefreshed={lastRefreshed}
          onTrigger={triggerRefresh}
          onRefresh={fetchAll}
        />
      </main>
    </div>
  );
}
