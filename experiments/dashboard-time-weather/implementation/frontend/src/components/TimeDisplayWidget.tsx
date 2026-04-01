import React, { useCallback, useEffect, useState } from 'react';
import { TimezoneInfo } from '../types/time';
import LiveClock from './LiveClock';
import TimezoneSelector from './TimezoneSelector';

const API_BASE = '/api/time';

/**
 * TimeDisplayWidget - Container component for the live clock and timezone selector.
 *
 * Manages state for timezone selection and real-time clock updates.
 * Fetches timezone list from backend on mount, then ticks every 1 second
 * using client-side Date for zero-latency updates.
 *
 * Timezone change flow:
 * 1. User selects new timezone in TimezoneSelector
 * 2. handleTimezoneChange updates selectedTimezone state
 * 3. React re-renders LiveClock with new timezone prop
 * 4. LiveClock uses Intl.DateTimeFormat(timezone) to format the display
 * 5. Clock continues ticking every 1s with the new timezone applied
 */
const TimeDisplayWidget: React.FC = () => {
  const [selectedTimezone, setSelectedTimezone] = useState<string>('UTC');
  const [currentTime, setCurrentTime] = useState<Date>(new Date());
  const [timezones, setTimezones] = useState<TimezoneInfo[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch timezone list from backend API with error handling
  const fetchTimezones = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/zones`);
      if (!response.ok) {
        throw new Error(
          `Failed to fetch timezones: HTTP ${response.status} ${response.statusText}`
        );
      }
      const data = await response.json();
      if (!data.timezones || !Array.isArray(data.timezones)) {
        throw new Error('Invalid response format from timezone API');
      }
      setTimezones(data.timezones);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to load timezones'
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch timezone list on mount
  useEffect(() => {
    fetchTimezones();
  }, [fetchTimezones]);

  // Tick the clock every second - this drives real-time updates
  // When selectedTimezone changes, LiveClock immediately shows the
  // new timezone on the next tick (no API call needed)
  useEffect(() => {
    const intervalId = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(intervalId);
  }, []);

  // When user selects a new timezone, update state immediately.
  // LiveClock re-renders with the new timezone prop and uses
  // Intl.DateTimeFormat to display the correct time.
  const handleTimezoneChange = useCallback((timezone: string) => {
    setSelectedTimezone(timezone);
  }, []);

  if (error) {
    return (
      <div
        className="time-display-widget time-display-widget--error"
        data-testid="time-widget-error"
      >
        <p>Error: {error}</p>
        <button
          onClick={fetchTimezones}
          className="time-display-widget__retry"
          data-testid="retry-button"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="time-display-widget" data-testid="time-display-widget">
      <h2 className="time-display-widget__title">Clock</h2>
      <LiveClock timezone={selectedTimezone} currentTime={currentTime} />
      <TimezoneSelector
        timezones={timezones}
        selected={selectedTimezone}
        onChange={handleTimezoneChange}
        isLoading={isLoading}
      />
    </div>
  );
};

export default TimeDisplayWidget;
