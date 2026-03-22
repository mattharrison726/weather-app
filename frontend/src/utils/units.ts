/**
 * Unit conversion utilities.
 *
 * Data is stored in metric (what Open-Meteo returns). Conversion to imperial
 * happens here, at the presentation layer — the database and API stay metric.
 *
 * This separation is correct: unit preference is a display concern, not a
 * data storage concern. Storing imperial would make re-conversion lossy and
 * would break the "units in column names" convention.
 */

export type UnitSystem = "imperial" | "metric";

/** °C → °F */
function cToF(c: number): number {
  return (c * 9) / 5 + 32;
}

/** km/h → mph */
function kmhToMph(kmh: number): number {
  return kmh * 0.621371;
}

/** mm → inches */
function mmToIn(mm: number): number {
  return mm * 0.0393701;
}

export function tempValue(c: number | null, units: UnitSystem): number | null {
  if (c === null) return null;
  return units === "metric" ? c : cToF(c);
}

export function tempDisplay(c: number | null, units: UnitSystem): string {
  const v = tempValue(c, units);
  if (v === null) return "—";
  return `${v.toFixed(1)}${tempUnitLabel(units)}`;
}

export function tempUnitLabel(units: UnitSystem): string {
  return units === "metric" ? "°C" : "°F";
}

export function windDisplay(kmh: number | null, units: UnitSystem): string {
  if (kmh === null) return "—";
  if (units === "metric") return `${kmh.toFixed(1)} km/h`;
  return `${kmhToMph(kmh).toFixed(1)} mph`;
}

export function precipDisplay(mm: number | null, units: UnitSystem): string {
  if (mm === null) return "—";
  if (units === "metric") return `${mm.toFixed(1)} mm`;
  return `${mmToIn(mm).toFixed(2)} in`;
}

export function windSpeedValue(kmh: number | null, units: UnitSystem): number | null {
  if (kmh === null) return null;
  return units === "metric" ? kmh : kmhToMph(kmh);
}
