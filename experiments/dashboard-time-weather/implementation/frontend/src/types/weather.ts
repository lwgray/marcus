/**
 * TypeScript interfaces for the Weather Information Service.
 *
 * These types match the backend Pydantic models defined in
 * backend/app/models/weather.py and the OpenAPI contract
 * at docs/api/weather-api-contract.yaml.
 */

export interface WeatherData {
  city: string;
  country: string;
  temperature: number;
  feels_like: number;
  temp_min: number;
  temp_max: number;
  humidity: number;
  pressure: number;
  wind_speed: number;
  wind_direction: number;
  condition: string;
  condition_code: number;
  icon: string;
  icon_url: string;
  visibility: number;
  timestamp: string;
  sunrise: string;
  sunset: string;
}

export interface WeatherResponse {
  success: true;
  data: WeatherData;
  stale: boolean;
  cached_at: string;
}

export interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
  };
}

export type ApiResponse = WeatherResponse | ErrorResponse;

export interface WeatherWidgetProps {
  city: string;
  onCityChange?: (city: string) => void;
  units?: 'imperial' | 'metric';
}

export interface WeatherState {
  data: WeatherData | null;
  loading: boolean;
  error: string | null;
  stale: boolean;
}
