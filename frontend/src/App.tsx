import { useState } from "react";
import { CurrentWeatherCard } from "./components/CurrentWeather";
import { LocationManager } from "./components/LocationManager";
import { LocationPicker } from "./components/LocationPicker";
import { PipelineStatus } from "./components/PipelineStatus";
import { UnitToggle } from "./components/UnitToggle";
import { WeatherChart } from "./components/WeatherChart";
import { useUnits } from "./hooks/useUnits";
import { useWeather } from "./hooks/useWeather";
import "./index.css";

export default function App() {
  const { units, toggleUnits } = useUnits();
  const [selectedLocationKey, setSelectedLocationKey] = useState<string | null>(null);

  const {
    current,
    history,
    runs,
    favorites,
    catalog,
    loading,
    triggering,
    backfilling,
    error,
    lastRefreshed,
    fetchAll,
    triggerRefresh,
    addFavorite,
    removeFavorite,
    runBackfill,
  } = useWeather(selectedLocationKey);

  // Once favorites load, auto-select the first one if nothing is selected
  const effectiveKey =
    selectedLocationKey ?? (favorites.length > 0 ? favorites[0].location_key : null);

  function handleSelectLocation(key: string) {
    setSelectedLocationKey(key);
  }

  if (loading && !current && !error) {
    return (
      <div className="app">
        <div className="loading-state">Loading weather data…</div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <h1>Weather App</h1>
          <p className="app-subtitle">Data engineering portfolio project</p>
        </div>
        <div className="header-right">
          <LocationPicker
            favorites={favorites}
            selectedKey={effectiveKey}
            onSelect={handleSelectLocation}
          />
          <UnitToggle units={units} onToggle={toggleUnits} />
        </div>
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
          <CurrentWeatherCard data={current} units={units} />
        ) : (
          !error && (
            <div className="card empty-card">
              <p>No weather data yet. Use the Refresh Data button below.</p>
            </div>
          )
        )}

        <WeatherChart history={history} units={units} />

        <PipelineStatus
          runs={runs}
          triggering={triggering}
          lastRefreshed={lastRefreshed}
          onTrigger={triggerRefresh}
          onRefresh={fetchAll}
        />

        <LocationManager
          catalog={catalog}
          onAddFavorite={addFavorite}
          onRemoveFavorite={removeFavorite}
          onBackfill={runBackfill}
          backfilling={backfilling}
        />
      </main>
    </div>
  );
}
