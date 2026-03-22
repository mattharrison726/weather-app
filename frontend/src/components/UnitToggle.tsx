import type { UnitSystem } from "../utils/units";

interface Props {
  units: UnitSystem;
  onToggle: () => void;
}

export function UnitToggle({ units, onToggle }: Props) {
  return (
    <button
      className="unit-toggle"
      onClick={onToggle}
      title="Switch between imperial and metric units"
    >
      <span className={units === "imperial" ? "unit-active" : "unit-inactive"}>°F</span>
      <span className="unit-sep">/</span>
      <span className={units === "metric" ? "unit-active" : "unit-inactive"}>°C</span>
    </button>
  );
}
