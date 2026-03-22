/**
 * Custom React hook that manages weather data fetching.
 *
 * Encapsulates: loading state, error state, data, and the refresh trigger.
 * Components stay clean — they just call useWeather() and render what they get.
 */
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type {
  CatalogCity,
  CurrentWeather,
  FavoriteLocation,
  PipelineRun,
  WeatherObservation,
} from "../types/weather";

interface WeatherState {
  current: CurrentWeather | null;
  history: WeatherObservation[];
  runs: PipelineRun[];
  favorites: FavoriteLocation[];
  catalog: CatalogCity[];
  loading: boolean;
  triggering: boolean;
  backfilling: boolean;
  error: string | null;
  lastRefreshed: Date | null;
}

export function useWeather(selectedLocationKey: string | null) {
  const [state, setState] = useState<WeatherState>({
    current: null,
    history: [],
    runs: [],
    favorites: [],
    catalog: [],
    loading: true,
    triggering: false,
    backfilling: false,
    error: null,
    lastRefreshed: null,
  });

  const fetchAll = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const [current, history, runs, favorites, catalog] = await Promise.all([
        api.getCurrentWeather(selectedLocationKey ?? undefined),
        api.getWeatherHistory(selectedLocationKey ?? undefined, 48),
        api.getPipelineRuns(10),
        api.getFavorites(),
        api.getCatalog(),
      ]);
      setState({
        current,
        history,
        runs,
        favorites,
        catalog,
        loading: false,
        triggering: false,
        backfilling: false,
        error: null,
        lastRefreshed: new Date(),
      });
    } catch (err) {
      setState((s) => ({
        ...s,
        loading: false,
        error: err instanceof Error ? err.message : "Unknown error",
      }));
    }
  }, [selectedLocationKey]);

  // Trigger the pipeline then refresh all data once it completes
  const triggerRefresh = useCallback(async () => {
    setState((s) => ({ ...s, triggering: true, error: null }));
    try {
      await api.triggerPipeline(selectedLocationKey ?? undefined);
      await fetchAll();
    } catch (err) {
      setState((s) => ({
        ...s,
        triggering: false,
        error: err instanceof Error ? err.message : "Trigger failed",
      }));
    }
  }, [fetchAll, selectedLocationKey]);

  const addFavorite = useCallback(async (locationKey: string) => {
    await api.addFavorite(locationKey);
    await fetchAll();
  }, [fetchAll]);

  const removeFavorite = useCallback(async (locationKey: string) => {
    await api.removeFavorite(locationKey);
    await fetchAll();
  }, [fetchAll]);

  const runBackfill = useCallback(async (
    locationKey: string,
    startDate: string,
    endDate: string,
  ) => {
    setState((s) => ({ ...s, backfilling: true, error: null }));
    try {
      const result = await api.runBackfill({ location_key: locationKey, start_date: startDate, end_date: endDate });
      await fetchAll();
      return result;
    } catch (err) {
      setState((s) => ({
        ...s,
        backfilling: false,
        error: err instanceof Error ? err.message : "Backfill failed",
      }));
      throw err;
    }
  }, [fetchAll]);

  // Load data on mount and when selected location changes
  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return { ...state, fetchAll, triggerRefresh, addFavorite, removeFavorite, runBackfill };
}
