import { renderHook, act, waitFor } from '@testing-library/react';
import { useWeather } from '../hooks/useWeather';
import { WeatherResponse } from '../types/weather';

const mockWeatherResponse: WeatherResponse = {
  success: true,
  data: {
    city: 'New York',
    country: 'US',
    temperature: 72.5,
    feels_like: 70.1,
    temp_min: 68.0,
    temp_max: 75.0,
    humidity: 55,
    pressure: 1013,
    wind_speed: 8.5,
    wind_direction: 220,
    condition: 'clear sky',
    condition_code: 800,
    icon: '01d',
    icon_url: 'https://openweathermap.org/img/wn/01d@2x.png',
    visibility: 10000,
    timestamp: '2026-03-31T20:30:00Z',
    sunrise: '2026-03-31T10:45:00Z',
    sunset: '2026-03-31T23:15:00Z',
  },
  stale: false,
  cached_at: '2026-03-31T20:30:00Z',
};

beforeEach(() => {
  jest.useFakeTimers();
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(mockWeatherResponse),
  }) as jest.Mock;
});

afterEach(() => {
  jest.useRealTimers();
  jest.restoreAllMocks();
});

describe('useWeather', () => {
  it('starts in loading state with no data', () => {
    const { result } = renderHook(() => useWeather('New York'));
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.stale).toBe(false);
  });

  it('fetches weather data on mount', async () => {
    const { result } = renderHook(() => useWeather('New York'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).not.toBeNull();
    expect(result.current.data?.city).toBe('New York');
    expect(result.current.error).toBeNull();
  });

  it('constructs correct API URL with city and units', async () => {
    const { result } = renderHook(() => useWeather('London', 'metric'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/weather?city=London&units=metric'
    );
  });

  it('defaults to imperial units', async () => {
    const { result } = renderHook(() => useWeather('New York'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/weather?city=New+York&units=imperial'
    );
  });

  it('sets error when fetch fails', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(
      new Error('Network error')
    );

    const { result } = renderHook(() => useWeather('New York'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('Network error');
    expect(result.current.data).toBeNull();
  });

  it('sets error when API returns error response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          success: false,
          error: { code: 'CITY_NOT_FOUND', message: "City not found" },
        }),
    });

    const { result } = renderHook(() => useWeather('Faketown'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('City not found');
  });

  it('sets stale flag when response is stale', async () => {
    const staleResponse = { ...mockWeatherResponse, stale: true };
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(staleResponse),
    });

    const { result } = renderHook(() => useWeather('New York'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.stale).toBe(true);
  });

  it('refetches when city changes', async () => {
    const { result, rerender } = renderHook(
      ({ city }) => useWeather(city),
      { initialProps: { city: 'New York' } }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    rerender({ city: 'London' });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });

  it('refetches when units change', async () => {
    const { result, rerender } = renderHook(
      ({ city, units }: { city: string; units: 'imperial' | 'metric' }) =>
        useWeather(city, units),
      { initialProps: { city: 'New York', units: 'imperial' as const } }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    rerender({ city: 'New York', units: 'metric' as const });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });

  it('exposes a refetch function', async () => {
    const { result } = renderHook(() => useWeather('New York'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);

    await act(async () => {
      await result.current.refetch();
    });

    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  it('keeps previous data on fetch error', async () => {
    const { result } = renderHook(() => useWeather('New York'));

    // Wait for successful load
    await waitFor(() => {
      expect(result.current.data).not.toBeNull();
    });

    // Next fetch fails
    (global.fetch as jest.Mock).mockRejectedValueOnce(
      new Error('Network error')
    );

    await act(async () => {
      await result.current.refetch();
    });

    // Data should still be there
    expect(result.current.data?.city).toBe('New York');
    expect(result.current.stale).toBe(true);
  });

  it('polls on interval', async () => {
    renderHook(() => useWeather('New York'));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    // Advance 5 minutes
    act(() => {
      jest.advanceTimersByTime(300_000);
    });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });

  it('cleans up interval on unmount', async () => {
    const clearIntervalSpy = jest.spyOn(global, 'clearInterval');

    const { unmount } = renderHook(() => useWeather('New York'));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
  });
});
