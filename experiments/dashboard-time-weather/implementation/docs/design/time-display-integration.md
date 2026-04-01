# Time Display System - Integration Specification

## Component Communication

### 1. TimezoneSelector → TimeDisplayWidget → LiveClock

```
TimezoneSelector
  │  onChange(timezone: string)
  ▼
TimeDisplayWidget (state update)
  │  props: { timezone, currentTime }
  ▼
LiveClock (re-renders with new timezone)
```

**Mechanism**: React props/callbacks (standard unidirectional data flow)
- TimezoneSelector calls `onChange` prop with IANA timezone string
- TimeDisplayWidget updates `selectedTimezone` state via `useState` setter
- React re-renders LiveClock with new timezone prop
- LiveClock uses `Intl.DateTimeFormat` with new timezone to format display

### 2. Frontend → Backend (API Calls)

#### On Widget Mount
```
TimeDisplayWidget.useEffect(() => {
  // 1. Fetch timezone list (one-time)
  GET /api/time/zones → populate TimezoneSelector options

  // 2. Fetch initial server time for sync
  GET /api/time/now?timezone=UTC → set initial time reference

  // 3. Start client-side clock interval
  setInterval(() => setCurrentTime(new Date()), 1000)
}, [])
```

#### On Timezone Change
```
// No API call needed!
// Client-side Intl.DateTimeFormat handles timezone conversion
const formatter = new Intl.DateTimeFormat('en-US', {
  timeZone: selectedTimezone,
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false
});
const display = formatter.format(currentTime);
```

### 3. Real-Time Update Mechanism

**Approach: Client-side setInterval (NOT server polling)**

```typescript
// In TimeDisplayWidget
useEffect(() => {
  const intervalId = setInterval(() => {
    setCurrentTime(new Date());
  }, 1000);

  return () => clearInterval(intervalId);  // Cleanup on unmount
}, []);
```

**Why client-side?**
- No network latency (instant updates)
- No server load from polling
- Browser handles timezone math via Intl API
- Server endpoint exists only for initial sync and drift correction

**Optional: Periodic drift correction**
```typescript
// Every 5 minutes, sync with server to correct drift
useEffect(() => {
  const syncId = setInterval(async () => {
    const res = await fetch(`/api/time/now?timezone=UTC`);
    const data = await res.json();
    // Compare server timestamp with local, adjust if >1s drift
  }, 300000);  // 5 minutes

  return () => clearInterval(syncId);
}, []);
```

### 4. Error Handling

| Scenario | Handling |
|----------|----------|
| `/api/time/zones` fails | Show error message, retry with exponential backoff |
| Invalid timezone selected | API returns 400, show validation error in UI |
| Clock interval drift | Optional 5-min server sync corrects accumulated drift |
| Component unmount | Clear all intervals to prevent memory leaks |
| Network offline | Clock continues ticking (client-side), timezone list from cache |

### 5. Integration with Dashboard

The TimeDisplayWidget is designed as a self-contained widget:

```typescript
// Dashboard just drops in the widget - no props required
function Dashboard() {
  return (
    <div className="dashboard-grid">
      <TimeDisplayWidget />    {/* Time widget */}
      <WeatherWidget />         {/* Weather widget - separate system */}
    </div>
  );
}
```

**Widget Independence**:
- TimeDisplayWidget manages its own state
- No shared state with WeatherWidget
- Each widget fetches its own data
- Dashboard only handles layout/grid

### 6. Future Extension Points

| Extension | How to Add |
|-----------|-----------|
| Multiple clocks | Render multiple LiveClock components with different timezone props |
| 12h/24h toggle | Add `format` prop to LiveClock, toggle in TimeDisplayWidget state |
| Alarm/timer | New component alongside LiveClock, shares timezone state |
| Favorites | Store preferred timezones in localStorage, pre-populate selector |
| Dark/light theme | CSS variables on TimeDisplayWidget container |
