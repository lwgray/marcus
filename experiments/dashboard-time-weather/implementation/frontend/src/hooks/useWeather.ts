import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiResponse, WeatherData } from '../types/weather';

const API_BASE = '/api/weather';
const POLL_INTERVAL = 300_000; // 5 minutes

/**
 * useWeather - Custom hook for fetching and managing weather data.
 *
 * Fetches weather data from the backend API for a given city,
 * manages loading/error/stale states, and polls every 5 minutes.
 *
 * Parameters
 * ----------
 * city : string
 *     City name to fetch weather for.
 * units : 'imperial' | 'metric'
 *     Temperature units. Defaults to 'imperial'.
 *
 * Returns
 * -------
 * Object with:
 *   data - WeatherData or null if not loaded.
 *   loading - True while fetching.
 *   error - Error message or null.
 *   stale - True if data is from expired cache.
 *   refetch - Function to manually trigger a refetch.
 */
export function useWeather(
  city: string,
  units: 'imperial' | 'metric' = 'imperial'
) {
  const [data, setData] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState<boolean>(false);
  const dataRef = useRef<WeatherData | null>(null);

  const fetchWeather = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ city, units });
      const response = await fetch(`${API_BASE}?${params.toString()}`);
      const json: ApiResponse = await response.json();

      if (json.success) {
        setData(json.data);
        dataRef.current = json.data;
        setStale(json.stale);
        setError(null);
      } else {
        setError(json.error.message);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to connect to weather service'
      );
      // Keep previous data and mark as stale
      if (dataRef.current !== null) {
        setStale(true);
      }
    } finally {
      setLoading(false);
    }
  }, [city, units]);

  useEffect(() => {
    fetchWeather();
    const interval = setInterval(fetchWeather, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchWeather]);

  return { data, loading, error, stale, refetch: fetchWeather };
}
