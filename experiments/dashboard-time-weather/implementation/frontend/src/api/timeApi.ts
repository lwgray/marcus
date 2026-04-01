/**
 * Time Display API Client
 *
 * Provides typed fetch wrappers for the Time Display System backend API.
 *
 * Endpoints:
 * - GET /api/time/zones: List all IANA timezones with region and UTC offset
 * - GET /api/time/now?timezone=X: Get current time in specified timezone
 *
 * @example
 * ```typescript
 * import { fetchTimezones, fetchCurrentTime } from './api/timeApi';
 *
 * // Fetch timezone list
 * const { timezones, count } = await fetchTimezones();
 *
 * // Fetch current time in New York
 * const time = await fetchCurrentTime('America/New_York');
 * console.log(time.formatted.time_24h); // "15:30:45"
 * ```
 */

import { TimezoneListResponse, CurrentTimeResponse } from '../types/time';

const API_BASE = '/api/time';

/**
 * Fetch the list of available timezones.
 *
 * @returns Promise resolving to TimezoneListResponse with timezones grouped by region.
 * @throws Error if the request fails.
 *
 * @example
 * ```typescript
 * const { timezones } = await fetchTimezones();
 * // timezones = [{ name: "America/New_York", utc_offset: "-05:00", region: "Americas", display_name: "New York" }, ...]
 * ```
 */
export async function fetchTimezones(): Promise<TimezoneListResponse> {
  const response = await fetch(`${API_BASE}/zones`);
  if (!response.ok) {
    throw new Error(`Failed to fetch timezones: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch the current time in a given timezone.
 *
 * @param timezone - IANA timezone identifier (e.g., "America/New_York"). Defaults to "UTC".
 * @returns Promise resolving to CurrentTimeResponse with formatted time strings.
 * @throws Error if the request fails or timezone is invalid.
 *
 * @example
 * ```typescript
 * const time = await fetchCurrentTime('Asia/Tokyo');
 * console.log(time.formatted.time_24h); // "00:30:45"
 * console.log(time.formatted.date); // "April 01, 2026"
 * console.log(time.utc_offset); // "+09:00"
 * ```
 */
export async function fetchCurrentTime(
  timezone: string = 'UTC'
): Promise<CurrentTimeResponse> {
  const params = new URLSearchParams({ timezone });
  const response = await fetch(`${API_BASE}/now?${params}`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || `Failed to fetch time: ${response.status}`);
  }
  return response.json();
}
