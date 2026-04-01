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
 */
const TimeDisplayWidget: React.FC = () => {
  const [selectedTimezone, setSelectedTimezone] = useState<string>('UTC');
  const [currentTime, setCurrentTime] = useState<Date>(new Date());
  const [timezones, setTimezones] = useState<TimezoneInfo[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch timezone list on mount
  useEffect(() => {
    let cancelled = false;

    const fetchTimezones = async () => {
      try {
        const response = await fetch(`${API_BASE}/zones`);
        if (!response.ok) {
          throw new Error(`Failed to fetch timezones: ${response.status}`);
        }
        const data = await response.json();
        if (!cancelled) {
          setTimezones(data.timezones);
          setIsLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load timezones');
          setIsLoading(false);
        }
      }
    };

    fetchTimezones();

    return () => {
      cancelled = true;
    };
  }, []);

  // Tick the clock every second
  useEffect(() => {
    const intervalId = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(intervalId);
  }, []);

  const handleTimezoneChange = useCallback((timezone: string) => {
    setSelectedTimezone(timezone);
  }, []);

  if (error) {
    return (
      <div className="time-display-widget time-display-widget--error" data-testid="time-widget-error">
        <p>Error: {error}</p>
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
