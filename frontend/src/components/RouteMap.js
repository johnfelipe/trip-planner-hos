import React from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import './RouteMap.css';

// Custom marker icons
const createIcon = (color, label) => {
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      background: ${color};
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: 3px solid white;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 12px;
      font-weight: bold;
    ">${label}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

const stopTypeConfig = {
  pickup: { color: '#38a169', label: 'P', name: 'Pickup' },
  dropoff: { color: '#e53e3e', label: 'D', name: 'Drop-off' },
  fuel: { color: '#d69e2e', label: 'F', name: 'Fuel Stop' },
  rest: { color: '#805ad5', label: 'R', name: '30-min Break' },
  sleep: { color: '#2b6cb0', label: 'S', name: '10-hr Rest' },
};

function RouteMap({ data }) {
  if (!data || !data.route || !data.route.points) return null;

  const routePoints = data.route.points.map(p => [p.lat, p.lng]);
  const stops = data.trip_plan.stops;
  const locations = data.route.locations;

  // Calculate map bounds
  const lats = routePoints.map(p => p[0]);
  const lngs = routePoints.map(p => p[1]);
  const bounds = [
    [Math.min(...lats) - 0.5, Math.min(...lngs) - 0.5],
    [Math.max(...lats) + 0.5, Math.max(...lngs) + 0.5],
  ];

  return (
    <div className="route-map-container">
      <MapContainer
        bounds={bounds}
        style={{ height: '500px', width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Route line */}
        <Polyline
          positions={routePoints}
          color="#2b6cb0"
          weight={4}
          opacity={0.8}
        />

        {/* Current location marker */}
        {locations.current && (
          <Marker
            position={[locations.current.lat, locations.current.lng]}
            icon={createIcon('#4a5568', 'C')}
          >
            <Popup>
              <strong>Current Location</strong><br />
              {locations.current.name}
            </Popup>
          </Marker>
        )}

        {/* Stop markers */}
        {stops.map((stop, index) => {
          const config = stopTypeConfig[stop.stop_type] || { color: '#718096', label: '?', name: 'Stop' };
          return (
            <Marker
              key={index}
              position={[stop.latitude, stop.longitude]}
              icon={createIcon(config.color, config.label)}
            >
              <Popup>
                <strong>{config.name}</strong><br />
                {stop.location}<br />
                Duration: {stop.duration_hours}hr<br />
                Mile: {stop.mile_marker}
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      <div className="map-legend">
        <h4>Legend</h4>
        <div className="legend-items">
          <div className="legend-item">
            <span className="legend-dot" style={{ background: '#4a5568' }}>C</span>
            Current Location
          </div>
          {Object.entries(stopTypeConfig).map(([key, config]) => (
            <div key={key} className="legend-item">
              <span className="legend-dot" style={{ background: config.color }}>{config.label}</span>
              {config.name}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default RouteMap;
