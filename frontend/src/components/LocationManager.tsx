import { useState } from "react";
import type { BackfillResponse, CatalogCity } from "../types/weather";

interface Props {
  catalog: CatalogCity[];
  onAddFavorite: (locationKey: string) => Promise<void>;
  onRemoveFavorite: (locationKey: string) => Promise<void>;
  onBackfill: (locationKey: string, startDate: string, endDate: string) => Promise<BackfillResponse>;
  backfilling: boolean;
}

// Get today's date as YYYY-MM-DD
function today(): string {
  return new Date().toISOString().slice(0, 10);
}

// Get date N days ago as YYYY-MM-DD
function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

export function LocationManager({
  catalog,
  onAddFavorite,
  onRemoveFavorite,
  onBackfill,
  backfilling,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"catalog" | "backfill">("catalog");
  const [pendingKey, setPendingKey] = useState<string | null>(null);

  // Backfill state
  const [backfillLocation, setBackfillLocation] = useState("");
  const [backfillStart, setBackfillStart] = useState(daysAgo(30));
  const [backfillEnd, setBackfillEnd] = useState(today());
  const [backfillResult, setBackfillResult] = useState<BackfillResponse | null>(null);
  const [backfillError, setBackfillError] = useState<string | null>(null);

  async function handleToggleFavorite(city: CatalogCity) {
    setPendingKey(city.location_key);
    try {
      if (city.is_favorite) {
        await onRemoveFavorite(city.location_key);
      } else {
        await onAddFavorite(city.location_key);
      }
    } finally {
      setPendingKey(null);
    }
  }

  async function handleBackfill() {
    if (!backfillLocation) return;
    setBackfillResult(null);
    setBackfillError(null);
    try {
      const result = await onBackfill(backfillLocation, backfillStart, backfillEnd);
      setBackfillResult(result);
    } catch (err) {
      setBackfillError(err instanceof Error ? err.message : "Backfill failed");
    }
  }

  // Group catalog by country
  const byCountry: Record<string, CatalogCity[]> = {};
  for (const city of catalog) {
    (byCountry[city.country] ??= []).push(city);
  }
  const countries = Object.keys(byCountry).sort();

  return (
    <div className="card location-manager-card">
      <div className="location-manager-header">
        <h3>Locations</h3>
        <button
          className="btn btn-secondary"
          onClick={() => setIsOpen((o) => !o)}
        >
          {isOpen ? "Close" : "Manage"}
        </button>
      </div>

      {isOpen && (
        <div className="location-manager-body">
          <div className="tab-bar">
            <button
              className={`tab-btn ${activeTab === "catalog" ? "tab-active" : ""}`}
              onClick={() => setActiveTab("catalog")}
            >
              Browse Cities
            </button>
            <button
              className={`tab-btn ${activeTab === "backfill" ? "tab-active" : ""}`}
              onClick={() => setActiveTab("backfill")}
            >
              Backfill History
            </button>
          </div>

          {activeTab === "catalog" && (
            <div className="catalog-list">
              {countries.map((country) => (
                <div key={country} className="catalog-country-group">
                  <div className="catalog-country-label">{country}</div>
                  {byCountry[country].map((city) => (
                    <div key={city.location_key} className="catalog-row">
                      <span className="catalog-city-name">{city.name}</span>
                      <button
                        className={`btn favorite-btn ${city.is_favorite ? "btn-favorite-active" : "btn-secondary"}`}
                        onClick={() => handleToggleFavorite(city)}
                        disabled={pendingKey === city.location_key}
                        title={city.is_favorite ? "Remove from favorites" : "Add to favorites"}
                      >
                        {pendingKey === city.location_key
                          ? "…"
                          : city.is_favorite
                          ? "★ Favorited"
                          : "☆ Add"}
                      </button>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}

          {activeTab === "backfill" && (
            <div className="backfill-panel">
              <p className="backfill-description">
                Load historical hourly data from the Open-Meteo archive for any city.
                Backfill is idempotent — running it twice for the same range is safe.
              </p>

              <div className="backfill-form">
                <div className="form-group">
                  <label className="form-label">City</label>
                  <select
                    className="location-select"
                    value={backfillLocation}
                    onChange={(e) => setBackfillLocation(e.target.value)}
                  >
                    <option value="">— select a city —</option>
                    {catalog.map((city) => (
                      <option key={city.location_key} value={city.location_key}>
                        {city.name}, {city.country}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Start date</label>
                    <input
                      type="date"
                      className="date-input"
                      value={backfillStart}
                      max={backfillEnd}
                      onChange={(e) => setBackfillStart(e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">End date</label>
                    <input
                      type="date"
                      className="date-input"
                      value={backfillEnd}
                      max={today()}
                      onChange={(e) => setBackfillEnd(e.target.value)}
                    />
                  </div>
                </div>

                <button
                  className="btn btn-primary"
                  onClick={handleBackfill}
                  disabled={!backfillLocation || backfilling}
                >
                  {backfilling ? "Running backfill…" : "Run Backfill"}
                </button>
              </div>

              {backfillError && (
                <div className="backfill-error">{backfillError}</div>
              )}

              {backfillResult && (
                <div className="backfill-result">
                  <strong>Backfill complete</strong> — {backfillResult.location_name}{" "}
                  {backfillResult.start_date} to {backfillResult.end_date}
                  <div className="backfill-stats">
                    <span>Written: {backfillResult.rows_written}</span>
                    <span>Skipped: {backfillResult.rows_skipped}</span>
                    <span>Transformed: {backfillResult.rows_transformed}</span>
                    {backfillResult.rows_failed > 0 && (
                      <span className="failed-count">Failed: {backfillResult.rows_failed}</span>
                    )}
                    <span>{backfillResult.duration_seconds.toFixed(1)}s</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
