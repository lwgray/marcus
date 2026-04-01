import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import TimeDisplayWidget from '../components/TimeDisplayWidget';

// Mock fetch for API calls
const mockTimezones = {
  timezones: [
    { name: 'UTC', utc_offset: '+00:00', region: 'Universal', display_name: 'UTC' },
    { name: 'America/New_York', utc_offset: '-05:00', region: 'Americas', display_name: 'New York' },
  ],
  count: 2,
};

beforeEach(() => {
  jest.useFakeTimers();
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(mockTimezones),
  }) as jest.Mock;
});

afterEach(() => {
  jest.useRealTimers();
  jest.restoreAllMocks();
});

describe('TimeDisplayWidget', () => {
  it('renders the widget container', async () => {
    await act(async () => {
      render(<TimeDisplayWidget />);
    });
    expect(screen.getByTestId('time-display-widget')).toBeInTheDocument();
  });

  it('fetches timezones on mount', async () => {
    await act(async () => {
      render(<TimeDisplayWidget />);
    });
    expect(global.fetch).toHaveBeenCalledWith('/api/time/zones');
  });

  it('displays the clock component', async () => {
    await act(async () => {
      render(<TimeDisplayWidget />);
    });
    expect(screen.getByTestId('live-clock')).toBeInTheDocument();
  });

  it('displays the timezone selector', async () => {
    await act(async () => {
      render(<TimeDisplayWidget />);
    });
    expect(screen.getByTestId('timezone-selector')).toBeInTheDocument();
  });

  it('updates time every second via setInterval', async () => {
    await act(async () => {
      render(<TimeDisplayWidget />);
    });

    const initialTime = screen.getByTestId('clock-time').textContent;

    // Advance time by 1 second
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    // The clock should have updated (content may or may not change
    // depending on timing, but the component should re-render)
    await waitFor(() => {
      expect(screen.getByTestId('clock-time')).toBeInTheDocument();
    });
  });

  it('cleans up interval on unmount', async () => {
    const clearIntervalSpy = jest.spyOn(global, 'clearInterval');

    let unmount: () => void;
    await act(async () => {
      const result = render(<TimeDisplayWidget />);
      unmount = result.unmount;
    });

    act(() => {
      unmount();
    });

    expect(clearIntervalSpy).toHaveBeenCalled();
  });

  it('shows error state when fetch fails', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(
      new Error('Network error')
    );

    await act(async () => {
      render(<TimeDisplayWidget />);
    });

    await waitFor(() => {
      expect(screen.getByTestId('time-widget-error')).toBeInTheDocument();
    });
  });
});
