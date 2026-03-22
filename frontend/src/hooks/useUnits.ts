/**
 * Hook for managing the user's unit preference (metric / imperial).
 *
 * Persists to localStorage so the choice survives page reloads.
 * Defaults to imperial.
 */
import { useState } from "react";
import type { UnitSystem } from "../utils/units";

const STORAGE_KEY = "weather-units";

export function useUnits() {
  const [units, setUnits] = useState<UnitSystem>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "metric" || stored === "imperial") return stored;
    return "imperial"; // default
  });

  function toggleUnits() {
    setUnits((u) => {
      const next: UnitSystem = u === "imperial" ? "metric" : "imperial";
      localStorage.setItem(STORAGE_KEY, next);
      return next;
    });
  }

  return { units, toggleUnits };
}
