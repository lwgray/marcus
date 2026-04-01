import React from 'react';
import { useWeather } from '../hooks/useWeather';
import { WeatherWidgetProps } from '../types/weather';

/**
 * WeatherWidget - Displays current weather data for a configured city.
 *
 * Fetches weather data from the backend API using the useWeather hook and
 * displays temperature, weather condition, icon, humidity, and wind speed.
 * Polls every 5 minutes for updates.
 * Handles loading, error, and stale data states.
 *
 * Props:
 *   city - City name to fetch weather for.
 *   onCityChange - Optional callback when city changes.
 *   units - Temperature units: 'imperial' (default) or 'metric'.
 */
const WeatherWidget: React.FC<WeatherWidgetProps> = ({
  city,
  onCityChange,
  units = 'imperial',
}) => {
  const { data, loading, error, stale } = useWeather(city, units);

  // Loading state (only on initial load, not on refresh)
  if (loading && !data) {
    return (
      <div
        className="weather-widget weather-widget--loading"
        data-testid="weather-loading"
      >
        <h2 className="weather-widget__title">Weather</h2>
        <div className="weather-widget__spinner">Loading weather data...</div>
      </div>
    );
  }

  // Error state (only if no data to show)
  if (error && !data) {
    return (
      <div
        className="weather-widget weather-widget--error"
        data-testid="weather-error"
      >
        <h2 className="weather-widget__title">Weather</h2>
        <p className="weather-widget__error-message">{error}</p>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const unitSymbol = units === 'metric' ? '°C' : '°F';
  const windUnit = units === 'metric' ? 'm/s' : 'mph';

  return (
    <div className="weather-widget" data-testid="weather-widget">
      <h2 className="weather-widget__title">Weather</h2>

      {stale && (
        <div className="weather-widget__stale" data-testid="weather-stale">
          Data may be outdated
        </div>
      )}

      <div className="weather-widget__header">
        <span className="weather-widget__city" data-testid="weather-city">
          {data.city}, {data.country}
        </span>
      </div>

      <div className="weather-widget__main">
        <img
          className="weather-widget__icon"
          data-testid="weather-icon"
          src={data.icon_url}
          alt={data.condition}
          width={64}
          height={64}
        />
        <div className="weather-widget__temp" data-testid="weather-temperature">
          {Math.round(data.temperature)}{unitSymbol}
        </div>
      </div>

      <div className="weather-widget__condition" data-testid="weather-condition">
        {data.condition}
      </div>

      <div className="weather-widget__details">
        <div className="weather-widget__detail">
          Feels like: {Math.round(data.feels_like)}{unitSymbol}
        </div>
        <div className="weather-widget__detail" data-testid="weather-humidity">
          Humidity: {data.humidity}%
        </div>
        <div className="weather-widget__detail" data-testid="weather-wind">
          Wind: {data.wind_speed} {windUnit}
        </div>
        <div className="weather-widget__detail">
          H: {Math.round(data.temp_max)}{unitSymbol} / L: {Math.round(data.temp_min)}{unitSymbol}
        </div>
      </div>
    </div>
  );
};

export default WeatherWidget;
