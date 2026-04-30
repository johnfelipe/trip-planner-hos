import React, { useState } from 'react';
import './TripForm.css';

function TripForm({ onSubmit, loading }) {
  const [formData, setFormData] = useState({
    current_location: '',
    pickup_location: '',
    dropoff_location: '',
    current_cycle_used: 0,
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'current_cycle_used' ? parseFloat(value) || 0 : value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form className="trip-form" onSubmit={handleSubmit}>
      <h2>Trip Details</h2>
      <div className="form-grid">
        <div className="form-group">
          <label htmlFor="current_location">
            <span className="label-icon">📍</span>
            Current Location
          </label>
          <input
            type="text"
            id="current_location"
            name="current_location"
            value={formData.current_location}
            onChange={handleChange}
            placeholder="e.g., Dallas, TX"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="pickup_location">
            <span className="label-icon">📦</span>
            Pickup Location
          </label>
          <input
            type="text"
            id="pickup_location"
            name="pickup_location"
            value={formData.pickup_location}
            onChange={handleChange}
            placeholder="e.g., Houston, TX"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="dropoff_location">
            <span className="label-icon">🏁</span>
            Drop-off Location
          </label>
          <input
            type="text"
            id="dropoff_location"
            name="dropoff_location"
            value={formData.dropoff_location}
            onChange={handleChange}
            placeholder="e.g., Los Angeles, CA"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="current_cycle_used">
            <span className="label-icon">⏱️</span>
            Current Cycle Used (Hours)
          </label>
          <input
            type="number"
            id="current_cycle_used"
            name="current_cycle_used"
            value={formData.current_cycle_used}
            onChange={handleChange}
            min="0"
            max="70"
            step="0.5"
          />
          <span className="help-text">Hours used in current 70-hour/8-day cycle (0-70)</span>
        </div>
      </div>

      <button type="submit" className="submit-btn" disabled={loading}>
        {loading ? 'Planning Route...' : 'Plan Trip'}
      </button>

      <div className="assumptions-note">
        <strong>Assumptions:</strong> Property-carrying driver | 70hr/8-day cycle |
        No adverse conditions | Fuel every 1,000 mi | 1 hr pickup/drop-off
      </div>
    </form>
  );
}

export default TripForm;
