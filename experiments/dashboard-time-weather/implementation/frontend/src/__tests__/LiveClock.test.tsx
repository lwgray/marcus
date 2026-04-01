import React from 'react';
import { render, screen } from '@testing-library/react';
import LiveClock from '../components/LiveClock';

describe('LiveClock', () => {
  const fixedDate = new Date('2026-03-31T15:30:45Z');

  it('renders the time display', () => {
    render(<LiveClock timezone="UTC" currentTime={fixedDate} />);
    const timeEl = screen.getByTestId('clock-time');
    expect(timeEl).toBeInTheDocument();
    expect(timeEl.textContent).toMatch(/\d{2}:\d{2}:\d{2}/);
  });

  it('renders the date display', () => {
    render(<LiveClock timezone="UTC" currentTime={fixedDate} />);
    const dateEl = screen.getByTestId('clock-date');
    expect(dateEl).toBeInTheDocument();
    expect(dateEl.textContent).toContain('2026');
  });

  it('renders the timezone abbreviation', () => {
    render(<LiveClock timezone="UTC" currentTime={fixedDate} />);
    const tzEl = screen.getByTestId('clock-timezone');
    expect(tzEl).toBeInTheDocument();
    expect(tzEl.textContent).toBeTruthy();
  });

  it('formats time for different timezones', () => {
    const { rerender } = render(
      <LiveClock timezone="UTC" currentTime={fixedDate} />
    );
    const utcTime = screen.getByTestId('clock-time').textContent;

    rerender(
      <LiveClock timezone="America/New_York" currentTime={fixedDate} />
    );
    const nyTime = screen.getByTestId('clock-time').textContent;

    // UTC and New York should show different times
    expect(utcTime).not.toEqual(nyTime);
  });

  it('updates when currentTime prop changes', () => {
    const time1 = new Date('2026-03-31T15:30:45Z');
    const time2 = new Date('2026-03-31T15:30:46Z');

    const { rerender } = render(
      <LiveClock timezone="UTC" currentTime={time1} />
    );
    const display1 = screen.getByTestId('clock-time').textContent;

    rerender(<LiveClock timezone="UTC" currentTime={time2} />);
    const display2 = screen.getByTestId('clock-time').textContent;

    expect(display1).not.toEqual(display2);
  });

  it('updates when timezone prop changes', () => {
    const { rerender } = render(
      <LiveClock timezone="UTC" currentTime={fixedDate} />
    );
    const tz1 = screen.getByTestId('clock-timezone').textContent;

    rerender(
      <LiveClock timezone="Asia/Tokyo" currentTime={fixedDate} />
    );
    const tz2 = screen.getByTestId('clock-timezone').textContent;

    expect(tz1).not.toEqual(tz2);
  });
});
