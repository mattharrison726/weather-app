/**
 * Custom React hook that manages weather data fetching.
 *
 * Encapsulates: loading state, error state, data, and the refresh trigger.
 * Components stay clean — they just call useWeather() and render what they get.
 */
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type {
  CurrentWeather,
  PipelineRun,
  WeatherObservation,
} from "../types/weather";

interface WeatherState {
  current: CurrentWeather | null;
  history: WeatherObservation[];
  runs: PipelineRun[];
  loading: boolean;
  triggering: boolean;
  error: string | null;
  lastRefreshed: Date | null;
}

export function useWeather() {
  const [state, setState] = useState<WeatherState>({
    current: null,
    history: [],
    runs: [],
    loading: true,
    triggering: false,
    error: null,
    lastRefreshed: null,
  });

  const fetchAll = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const [current, history, runs] = await Promise.all([
        api.getCurrentWeather(),
        api.getWeatherHistory(48),
        api.getPipelineRuns(10),
      ]);
      setState({
        current,
        history,
        runs,
        loading: false,
        triggering: false,
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
  }, []);

  // Trigger the pipeline then refresh all data once it completes
  const triggerRefresh = useCallback(async () => {
    setState((s) => ({ ...s, triggering: true, error: null }));
    try {
      await api.triggerPipeline();
      await fetchAll();
    } catch (err) {
      setState((s) => ({
        ...s,
        triggering: false,
        error: err instanceof Error ? err.message : "Trigger failed",
      }));
    }
  }, [fetchAll]);

  // Load data on mount
  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return { ...state, fetchAll, triggerRefresh };
}
