import type { FavoriteLocation } from "../types/weather";

interface Props {
  favorites: FavoriteLocation[];
  selectedKey: string | null;
  onSelect: (locationKey: string) => void;
}

export function LocationPicker({ favorites, selectedKey, onSelect }: Props) {
  if (favorites.length === 0) return null;

  return (
    <div className="location-picker">
      <select
        value={selectedKey ?? ""}
        onChange={(e) => onSelect(e.target.value)}
        className="location-select"
        aria-label="Select location"
      >
        {favorites.map((loc) => (
          <option key={loc.location_key} value={loc.location_key}>
            {loc.name}, {loc.country}
          </option>
        ))}
      </select>
    </div>
  );
}
