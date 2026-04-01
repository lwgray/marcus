import React from 'react';
import TimeDisplayWidget from './TimeDisplayWidget';

/**
 * Dashboard - Main dashboard layout containing all widgets.
 *
 * Each widget (TimeDisplayWidget, WeatherWidget) is independently functional
 * and manages its own state. The Dashboard only handles layout.
 */
const Dashboard: React.FC = () => {
  return (
    <div className="dashboard" data-testid="dashboard">
      <h1 className="dashboard__title">Dashboard</h1>
      <div className="dashboard__grid">
        <div className="dashboard__widget">
          <TimeDisplayWidget />
        </div>
        {/* WeatherWidget will be added by another task */}
      </div>
    </div>
  );
};

export default Dashboard;
