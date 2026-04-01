import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import TimezoneSelector from '../components/TimezoneSelector';
import { TimezoneInfo } from '../types/time';

const mockTimezones: TimezoneInfo[] = [
  { name: 'UTC', utc_offset: '+00:00', region: 'Universal', display_name: 'UTC' },
  { name: 'America/New_York', utc_offset: '-05:00', region: 'Americas', display_name: 'New York' },
  { name: 'Europe/London', utc_offset: '+00:00', region: 'Europe', display_name: 'London' },
  { name: 'Asia/Tokyo', utc_offset: '+09:00', region: 'Asia', display_name: 'Tokyo' },
];

describe('TimezoneSelector', () => {
  it('renders the selector with timezone options', () => {
    render(
      <TimezoneSelector
        timezones={mockTimezones}
        selected="UTC"
        onChange={jest.fn()}
      />
    );
    const select = screen.getByTestId('timezone-select');
    expect(select).toBeInTheDocument();
  });

  it('groups timezones by region', () => {
    render(
      <TimezoneSelector
        timezones={mockTimezones}
        selected="UTC"
        onChange={jest.fn()}
      />
    );
    const optgroups = screen.getAllByRole('group');
    expect(optgroups.length).toBeGreaterThan(0);
  });

  it('shows the currently selected timezone', () => {
    render(
      <TimezoneSelector
        timezones={mockTimezones}
        selected="America/New_York"
        onChange={jest.fn()}
      />
    );
    const select = screen.getByTestId('timezone-select') as HTMLSelectElement;
    expect(select.value).toBe('America/New_York');
  });

  it('calls onChange when a new timezone is selected', () => {
    const handleChange = jest.fn();
    render(
      <TimezoneSelector
        timezones={mockTimezones}
        selected="UTC"
        onChange={handleChange}
      />
    );
    const select = screen.getByTestId('timezone-select');
    fireEvent.change(select, { target: { value: 'Asia/Tokyo' } });
    expect(handleChange).toHaveBeenCalledWith('Asia/Tokyo');
  });

  it('shows loading state when isLoading is true', () => {
    render(
      <TimezoneSelector
        timezones={[]}
        selected="UTC"
        onChange={jest.fn()}
        isLoading={true}
      />
    );
    const select = screen.getByTestId('timezone-select') as HTMLSelectElement;
    expect(select.disabled).toBe(true);
  });

  it('displays timezone offset in option text', () => {
    render(
      <TimezoneSelector
        timezones={mockTimezones}
        selected="UTC"
        onChange={jest.fn()}
      />
    );
    const options = screen.getAllByRole('option');
    const nyOption = options.find(o => o.textContent?.includes('New York'));
    expect(nyOption?.textContent).toContain('-05:00');
  });
});
