import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import WeatherWidget from '../components/WeatherWidget';
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
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(mockWeatherResponse),
  }) as jest.Mock;
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('WeatherWidget', () => {
  it('renders the widget container', async () => {
    render(<WeatherWidget city="New York" />);
    await waitFor(() => {
      expect(screen.getByTestId('weather-widget')).toBeInTheDocument();
    });
  });

  it('fetches weather data on mount', async () => {
    render(<WeatherWidget city="New York" />);
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/weather?city=New+York&units=imperial'
      );
    });
  });

  it('displays city name', async () => {
    render(<WeatherWidget city="New York" />);
    await waitFor(() => {
      expect(screen.getByTestId('weather-city')).toHaveTextContent('New York');
    });
  });

  it('displays temperature', async () => {
    render(<WeatherWidget city="New York" />);
    await waitFor(() => {
      expect(screen.getByTestId('weather-temperature')).toHaveTextContent('73');
    });
  });

  it('displays weather condition description', async () => {
    render(<WeatherWidget city="New York" />);
    await waitFor(() => {
      expect(screen.getByTestId('weather-condition')).toHaveTextContent(
        'clear sky'
      );
    });
  });

  it('displays weather icon', async () => {
    render(<WeatherWidget city="New York" />);
    await waitFor(() => {
      const icon = screen.getByTestId('weather-icon');
      expect(icon).toBeInTheDocument();
      expect(icon).toHaveAttribute(
        'src',
        'https://openweathermap.org/img/wn/01d@2x.png'
      );
    });
  });

  it('displays humidity', async () => {
    render(<WeatherWidget city="New York" />);
    await waitFor(() => {
      expect(screen.getByTestId('weather-humidity')).toHaveTextContent('55%');
    });
  });

  it('displays wind speed', async () => {
    render(<WeatherWidget city="New York" />);
    await waitFor(() => {
      expect(screen.getByTestId('weather-wind')).toHaveTextContent('8.5');
    });
  });

  it('shows loading state initially', () => {
    render(<WeatherWidget city="New York" />);
    expect(screen.getByTestId('weather-loading')).toBeInTheDocument();
  });

  it('shows error state when fetch fails', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(
      new Error('Network error')
    );

    render(<WeatherWidget city="New York" />);
    await waitFor(() => {
      expect(screen.getByTestId('weather-error')).toBeInTheDocument();
    });
  });

  it('shows error when API returns error response', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          success: false,
          error: { code: 'CITY_NOT_FOUND', message: "City 'Faketown' not found" },
        }),
    });

    render(<WeatherWidget city="Faketown" />);
    await waitFor(() => {
      expect(screen.getByTestId('weather-error')).toBeInTheDocument();
    });
  });

  it('shows stale indicator when data is stale', async () => {
    const staleResponse = { ...mockWeatherResponse, stale: true };
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(staleResponse),
    });

    render(<WeatherWidget city="New York" />);
    await waitFor(() => {
      expect(screen.getByTestId('weather-stale')).toBeInTheDocument();
    });
  });

  it('uses metric units when specified', async () => {
    render(<WeatherWidget city="London" units="metric" />);
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/weather?city=London&units=metric'
      );
    });
  });

  it('refetches when city prop changes', async () => {
    const { rerender } = render(<WeatherWidget city="New York" />);
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    rerender(<WeatherWidget city="London" />);
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });
});
