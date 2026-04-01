/** IANA timezone metadata from GET /api/time/zones */
export interface TimezoneInfo {
  name: string;
  utc_offset: string;
  region: string;
  display_name: string;
}

/** Response from GET /api/time/zones */
export interface TimezoneListResponse {
  timezones: TimezoneInfo[];
  count: number;
}

/** Pre-formatted time strings from GET /api/time/now */
export interface FormattedTime {
  time_24h: string;
  time_12h: string;
  date: string;
  day_of_week: string;
}

/** Response from GET /api/time/now */
export interface CurrentTimeResponse {
  datetime_str: string;
  timezone: string;
  utc_offset: string;
  unix_timestamp: number;
  formatted: FormattedTime;
}

/** Clock widget internal state */
export interface ClockState {
  selectedTimezone: string;
  currentTime: Date;
  timezones: TimezoneInfo[];
  isLoading: boolean;
  error: string | null;
}
