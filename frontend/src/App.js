import React, { useState } from 'react';
import TripForm from './components/TripForm';
import RouteMap from './components/RouteMap';
import DailyLogSheet from './components/DailyLogSheet';
import TripSummary from './components/TripSummary';
import './App.css';

function App() {
  const [tripData, setTripData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleTripSubmit = async (formData) => {
    setLoading(true);
    setError(null);
    setTripData(null);

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'https://trip-planner-hos-api-jvfebtxf.fly.dev';
      const response = await fetch(`${apiUrl}/api/trip/plan/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.errors?.join(', ') || 'Failed to plan trip');
      }

      const data = await response.json();
      setTripData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>ELD Trip Planner</h1>
          <p className="subtitle">FMCSA Hours of Service Compliance Tool</p>
        </div>
      </header>

      <main className="app-main">
        <section className="input-section">
          <TripForm onSubmit={handleTripSubmit} loading={loading} />
        </section>

        {error && (
          <div className="error-banner">
            <span className="error-icon">!</span>
            <p>{error}</p>
          </div>
        )}

        {loading && (
          <div className="loading-overlay">
            <div className="spinner"></div>
            <p>Calculating HOS-compliant route...</p>
          </div>
        )}

        {tripData && (
          <div className="results-section">
            <TripSummary data={tripData} />

            <section className="map-section">
              <h2>Route Map</h2>
              <RouteMap data={tripData} />
            </section>

            <section className="logs-section">
              <h2>Daily Log Sheets (ELD)</h2>
              <p className="logs-description">
                Each log sheet represents a 24-hour period following FMCSA regulations.
                Property-carrying driver | 70-hour/8-day cycle | No adverse conditions
              </p>
              {tripData.trip_plan.daily_logs.map((log, index) => (
                <DailyLogSheet key={index} log={log} tripData={tripData} />
              ))}
            </section>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>Based on FMCSA Hours of Service Regulations (49 CFR Part 395) - April 2022</p>
        <p>Property-carrying CMV | 70-hour/8-day cycle | No adverse driving conditions</p>
      </footer>
    </div>
  );
}

export default App;
