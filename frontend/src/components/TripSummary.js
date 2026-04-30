import React from 'react';
import './TripSummary.css';

function TripSummary({ data }) {
  if (!data) return null;

  const { route, trip_plan } = data;

  return (
    <div className="trip-summary">
      <h2>Trip Summary</h2>
      <div className="summary-cards">
        <div className="summary-card">
          <div className="card-value">{route.total_distance_miles.toFixed(0)}</div>
          <div className="card-label">Total Miles</div>
        </div>
        <div className="summary-card">
          <div className="card-value">{route.total_duration_hours.toFixed(1)}</div>
          <div className="card-label">Drive Hours</div>
        </div>
        <div className="summary-card">
          <div className="card-value">{trip_plan.total_days}</div>
          <div className="card-label">Total Days</div>
        </div>
        <div className="summary-card">
          <div className="card-value">{trip_plan.stops.length}</div>
          <div className="card-label">Stops</div>
        </div>
      </div>

      <div className="route-legs">
        <h3>Route Legs</h3>
        {route.legs.map((leg, idx) => (
          <div key={idx} className="leg-item">
            <span className="leg-from">{leg.from}</span>
            <span className="leg-arrow">&rarr;</span>
            <span className="leg-to">{leg.to}</span>
            <span className="leg-distance">{leg.distance_miles.toFixed(0)} mi</span>
            <span className="leg-duration">{leg.duration_hours.toFixed(1)} hrs</span>
          </div>
        ))}
      </div>

      <div className="stops-list">
        <h3>Planned Stops</h3>
        <div className="stops-table">
          <div className="stop-header">
            <span>Type</span>
            <span>Location</span>
            <span>Duration</span>
            <span>Mile Marker</span>
          </div>
          {trip_plan.stops.map((stop, idx) => (
            <div key={idx} className={`stop-row stop-${stop.stop_type}`}>
              <span className="stop-type-badge">{stop.stop_type.replace('_', ' ')}</span>
              <span className="stop-location">{stop.location}</span>
              <span className="stop-duration">{stop.duration_hours}hr</span>
              <span className="stop-mile">{stop.mile_marker}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default TripSummary;
