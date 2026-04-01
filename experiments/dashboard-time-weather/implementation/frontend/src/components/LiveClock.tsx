import React from 'react';

interface LiveClockProps {
  /** IANA timezone identifier (e.g., "America/New_York") */
  timezone: string;
  /** Current time (updated every 1s by parent) */
  currentTime: Date;
  /** Whether to use 24-hour format. Defaults to true. */
  use24Hour?: boolean;
}

/**
 * LiveClock - Displays the current time formatted for a given timezone.
 *
 * Pure presentational component. The parent (TimeDisplayWidget) manages
 * the setInterval and passes currentTime as a prop every second.
 * Uses Intl.DateTimeFormat for timezone-aware formatting.
 */
const LiveClock: React.FC<LiveClockProps> = ({
  timezone,
  currentTime,
  use24Hour = true,
}) => {
  const timeFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: timezone,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: !use24Hour,
  });

  const dateFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: timezone,
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const tzNameFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: timezone,
    timeZoneName: 'short',
  });

  const timeDisplay = timeFormatter.format(currentTime);
  const dateDisplay = dateFormatter.format(currentTime);

  // Extract just the timezone abbreviation
  const tzParts = tzNameFormatter.formatToParts(currentTime);
  const tzAbbr = tzParts.find(p => p.type === 'timeZoneName')?.value ?? timezone;

  return (
    <div className="live-clock" data-testid="live-clock">
      <div className="live-clock__time" data-testid="clock-time">
        {timeDisplay}
      </div>
      <div className="live-clock__date" data-testid="clock-date">
        {dateDisplay}
      </div>
      <div className="live-clock__timezone" data-testid="clock-timezone">
        {tzAbbr}
      </div>
    </div>
  );
};

export default LiveClock;
