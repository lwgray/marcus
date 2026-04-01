import React, { useMemo } from 'react';
import { TimezoneInfo } from '../types/time';

interface TimezoneSelectorProps {
  /** Available timezones from API */
  timezones: TimezoneInfo[];
  /** Currently selected timezone IANA identifier */
  selected: string;
  /** Callback when timezone selection changes */
  onChange: (timezone: string) => void;
  /** Whether the timezone list is loading */
  isLoading?: boolean;
}

/**
 * TimezoneSelector - Dropdown for selecting a timezone.
 *
 * Groups timezones by region and shows UTC offset.
 * Calls onChange with the IANA timezone string when user selects.
 */
const TimezoneSelector: React.FC<TimezoneSelectorProps> = ({
  timezones,
  selected,
  onChange,
  isLoading = false,
}) => {
  // Group timezones by region
  const groupedTimezones = useMemo(() => {
    const groups: Record<string, TimezoneInfo[]> = {};
    for (const tz of timezones) {
      if (!groups[tz.region]) {
        groups[tz.region] = [];
      }
      groups[tz.region].push(tz);
    }
    // Sort regions alphabetically
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
  }, [timezones]);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange(e.target.value);
  };

  return (
    <div className="timezone-selector" data-testid="timezone-selector">
      <label htmlFor="timezone-select" className="timezone-selector__label">
        Timezone
      </label>
      <select
        id="timezone-select"
        className="timezone-selector__select"
        value={selected}
        onChange={handleChange}
        disabled={isLoading}
        data-testid="timezone-select"
      >
        {isLoading ? (
          <option>Loading timezones...</option>
        ) : (
          groupedTimezones.map(([region, tzList]) => (
            <optgroup key={region} label={region}>
              {tzList.map((tz) => (
                <option key={tz.name} value={tz.name}>
                  {tz.display_name} ({tz.utc_offset})
                </option>
              ))}
            </optgroup>
          ))
        )}
      </select>
    </div>
  );
};

export default TimezoneSelector;
