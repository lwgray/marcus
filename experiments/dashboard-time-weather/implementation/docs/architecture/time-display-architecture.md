# Time Display System - Architecture Design

## Overview
The Time Display System is a dashboard widget consisting of a live clock with timezone selection. It uses a React frontend for real-time display and a FastAPI backend for timezone data and server time.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                   Dashboard App                      │
│  ┌───────────────────────────────────────────────┐  │
│  │           TimeDisplayWidget (Container)         │  │
│  │  ┌─────────────────┐  ┌─────────────────────┐ │  │
│  │  │  LiveClock       │  │  TimezoneSelector    │ │  │
│  │  │                  │  │                      │ │  │
│  │  │  - Displays      │  │  - Dropdown of       │ │  │
│  │  │    HH:MM:SS      │  │    IANA timezones    │ │  │
│  │  │  - Updates every │  │  - Grouped by region │ │  │
│  │  │    1 second       │  │  - Search/filter     │ │  │
│  │  │  - Shows date    │  │  - Shows UTC offset  │ │  │
│  │  │  - Shows TZ name │  │                      │ │  │
│  │  └─────────────────┘  └─────────────────────┘ │  │
│  │                                                 │  │
│  │  State: { selectedTimezone, currentTime }       │  │
│  └───────────────────────────────────────────────┘  │
│                         │                            │
│                         │ GET /api/time/zones        │
│                         │ GET /api/time/now?tz=X     │
│                         ▼                            │
│  ┌───────────────────────────────────────────────┐  │
│  │              FastAPI Backend                    │  │
│  │                                                │  │
│  │  /api/time/zones  → List available timezones   │  │
│  │  /api/time/now    → Current time in timezone   │  │
│  │                                                │  │
│  │  Uses: Python zoneinfo (stdlib, IANA db)       │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Frontend Components

#### 1. TimeDisplayWidget (Container)
- **Responsibility**: Orchestrates clock and timezone selector
- **State Management**: React useState/useEffect hooks
- **State**: `{ selectedTimezone: string, currentTime: Date }`
- **Behavior**:
  - On mount: fetches timezone list from API, starts 1s interval timer
  - On timezone change: updates selectedTimezone state
  - On unmount: clears interval timer

#### 2. LiveClock (Presentational)
- **Props**: `{ timezone: string, currentTime: Date }`
- **Responsibility**: Renders formatted time display
- **Display Format**: `HH:MM:SS` (24h) with date and timezone name
- **Update Mechanism**: Parent re-renders every 1s via setInterval
- **Formatting**: Uses `Intl.DateTimeFormat` with timezone parameter

#### 3. TimezoneSelector (Interactive)
- **Props**: `{ timezones: TimezoneInfo[], selected: string, onChange: (tz: string) => void }`
- **Responsibility**: Dropdown for timezone selection
- **Features**: Grouped by region (Americas, Europe, Asia, etc.), shows UTC offset
- **Behavior**: Calls onChange callback when user selects a timezone

### Backend Endpoints

#### 1. GET /api/time/zones
- Returns list of available IANA timezones with metadata
- Cached response (timezone list is static)

#### 2. GET /api/time/now
- Returns current server time in requested timezone
- Used for initial sync and periodic drift correction

## Data Flow

```
1. App loads → TimeDisplayWidget mounts
2. TimeDisplayWidget → GET /api/time/zones → populates TimezoneSelector
3. TimeDisplayWidget starts setInterval(1000ms)
4. Every 1s: new Date() → format with Intl.DateTimeFormat(selectedTimezone) → LiveClock re-renders
5. User selects timezone → TimezoneSelector.onChange → TimeDisplayWidget updates state
6. LiveClock immediately shows time in new timezone (client-side conversion)
```

## Key Design Decisions

1. **Client-side time updates**: The clock ticks client-side using `setInterval` + `Intl.DateTimeFormat`. No need to poll the server every second. Server endpoint exists for initial sync and drift correction.

2. **IANA timezones via Python zoneinfo**: Uses Python 3.9+ stdlib `zoneinfo` module backed by the IANA timezone database. No external dependencies needed.

3. **No database**: Timezone data is static (from IANA). No persistence layer needed for the time display system.

4. **Intl.DateTimeFormat for formatting**: Browser-native timezone conversion. No need for moment.js or similar libraries.
