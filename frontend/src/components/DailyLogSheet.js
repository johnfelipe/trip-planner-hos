import React, { useRef, useEffect } from 'react';
import './DailyLogSheet.css';

/**
 * Draws a Driver's Daily Log sheet that closely matches the FMCSA paper log format.
 * Uses HTML Canvas to draw the graph grid with duty status lines.
 */

const DUTY_STATUSES = [
  { key: 'off_duty', label: '1. Off Duty', row: 0 },
  { key: 'sleeper_berth', label: '2. Sleeper Berth', row: 1 },
  { key: 'driving', label: '3. Driving', row: 2 },
  { key: 'on_duty_not_driving', label: '4. On Duty (not driving)', row: 3 },
];

const HOURS = Array.from({ length: 25 }, (_, i) => i); // 0-24

function DailyLogSheet({ log, tripData }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !log) return;
    drawLogSheet(canvasRef.current, log);
  }, [log]);

  const totalHours = log.totals || {};

  return (
    <div className="daily-log-sheet">
      <div className="log-header">
        <div className="log-title">
          <h3>Drivers Daily Log</h3>
          <span className="log-subtitle">(24 hours)</span>
        </div>
        <div className="log-day-info">
          <span className="day-badge">Day {log.day}</span>
        </div>
      </div>

      <div className="log-info-grid">
        <div className="log-info-row">
          <div className="info-field">
            <label>From:</label>
            <span>{log.start_location || 'N/A'}</span>
          </div>
          <div className="info-field">
            <label>To:</label>
            <span>{log.end_location || 'N/A'}</span>
          </div>
        </div>
        <div className="log-info-row">
          <div className="info-field">
            <label>Total Miles Driving Today:</label>
            <span>{log.total_miles?.toFixed(0) || 0}</span>
          </div>
          <div className="info-field">
            <label>Total Mileage Today:</label>
            <span>{log.total_miles?.toFixed(0) || 0}</span>
          </div>
        </div>
      </div>

      <div className="graph-container">
        <canvas
          ref={canvasRef}
          width={900}
          height={220}
          className="log-canvas"
        />
      </div>

      <div className="hours-summary">
        <h4>Total Hours</h4>
        <div className="hours-grid">
          <div className="hour-item">
            <span className="hour-label">Off Duty</span>
            <span className="hour-value">{(totalHours.off_duty || 0).toFixed(1)}</span>
          </div>
          <div className="hour-item">
            <span className="hour-label">Sleeper Berth</span>
            <span className="hour-value">{(totalHours.sleeper_berth || 0).toFixed(1)}</span>
          </div>
          <div className="hour-item">
            <span className="hour-label">Driving</span>
            <span className="hour-value">{(totalHours.driving || 0).toFixed(1)}</span>
          </div>
          <div className="hour-item">
            <span className="hour-label">On Duty (not driving)</span>
            <span className="hour-value">{(totalHours.on_duty_not_driving || 0).toFixed(1)}</span>
          </div>
          <div className="hour-item total">
            <span className="hour-label">Total</span>
            <span className="hour-value">
              {(
                (totalHours.off_duty || 0) +
                (totalHours.sleeper_berth || 0) +
                (totalHours.driving || 0) +
                (totalHours.on_duty_not_driving || 0)
              ).toFixed(1)}
            </span>
          </div>
        </div>
      </div>

      {log.entries && log.entries.length > 0 && (
        <div className="remarks-section">
          <h4>Remarks</h4>
          <div className="remarks-list">
            {log.entries
              .filter(e => e.remarks)
              .map((entry, idx) => (
                <div key={idx} className="remark-item">
                  <span className="remark-time">
                    {formatHour(entry.start_hour)} - {formatHour(entry.end_hour)}
                  </span>
                  <span className="remark-text">{entry.remarks}</span>
                  {entry.location && (
                    <span className="remark-location">{entry.location}</span>
                  )}
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

function formatHour(hour) {
  const h = Math.floor(hour);
  const m = Math.round((hour - h) * 60);
  const period = h >= 12 ? 'PM' : 'AM';
  const displayH = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${displayH}:${m.toString().padStart(2, '0')} ${period}`;
}

function drawLogSheet(canvas, log) {
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;

  // Clear
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);

  // Layout constants
  const leftMargin = 130;
  const rightMargin = 60;
  const topMargin = 30;
  const bottomMargin = 10;
  const gridWidth = width - leftMargin - rightMargin;
  const gridHeight = height - topMargin - bottomMargin;
  const rowHeight = gridHeight / 4;
  const hourWidth = gridWidth / 24;

  // Draw grid background
  ctx.fillStyle = '#fafafa';
  ctx.fillRect(leftMargin, topMargin, gridWidth, gridHeight);

  // Draw hour labels on top
  ctx.fillStyle = '#1a365d';
  ctx.font = 'bold 10px Arial';
  ctx.textAlign = 'center';

  for (let h = 0; h <= 24; h++) {
    const x = leftMargin + h * hourWidth;

    // Hour label
    if (h === 0) {
      ctx.fillText('Mid-', x, topMargin - 18);
      ctx.fillText('night', x, topMargin - 8);
    } else if (h === 12) {
      ctx.fillText('Noon', x, topMargin - 10);
    } else if (h === 24) {
      ctx.fillText('Mid-', x, topMargin - 18);
      ctx.fillText('night', x, topMargin - 8);
    } else {
      const displayH = h > 12 ? h - 12 : h;
      ctx.fillText(displayH.toString(), x, topMargin - 10);
    }

    // Vertical grid line
    ctx.beginPath();
    ctx.strokeStyle = h % 1 === 0 ? '#cbd5e0' : '#e2e8f0';
    ctx.lineWidth = h === 0 || h === 12 || h === 24 ? 1.5 : 0.5;
    ctx.moveTo(x, topMargin);
    ctx.lineTo(x, topMargin + gridHeight);
    ctx.stroke();
  }

  // Draw 15-minute subdivisions
  ctx.strokeStyle = '#e2e8f0';
  ctx.lineWidth = 0.3;
  for (let h = 0; h < 24; h++) {
    for (let q = 1; q < 4; q++) {
      const x = leftMargin + (h + q * 0.25) * hourWidth;
      ctx.beginPath();
      ctx.moveTo(x, topMargin);
      ctx.lineTo(x, topMargin + gridHeight);
      ctx.stroke();
    }
  }

  // Draw row labels and horizontal lines
  DUTY_STATUSES.forEach((status, i) => {
    const y = topMargin + i * rowHeight;

    // Horizontal line
    ctx.beginPath();
    ctx.strokeStyle = '#2d3748';
    ctx.lineWidth = i === 0 ? 1.5 : 1;
    ctx.moveTo(leftMargin, y);
    ctx.lineTo(leftMargin + gridWidth, y);
    ctx.stroke();

    // Row label
    ctx.fillStyle = '#2d3748';
    ctx.font = '11px Arial';
    ctx.textAlign = 'right';
    ctx.fillText(status.label, leftMargin - 8, y + rowHeight / 2 + 4);
  });

  // Bottom line
  ctx.beginPath();
  ctx.strokeStyle = '#2d3748';
  ctx.lineWidth = 1.5;
  ctx.moveTo(leftMargin, topMargin + gridHeight);
  ctx.lineTo(leftMargin + gridWidth, topMargin + gridHeight);
  ctx.stroke();

  // Draw "Total Hours" column on right
  ctx.fillStyle = '#1a365d';
  ctx.font = 'bold 9px Arial';
  ctx.textAlign = 'center';
  ctx.fillText('Total', leftMargin + gridWidth + 30, topMargin - 10);
  ctx.fillText('Hours', leftMargin + gridWidth + 30, topMargin);

  // Draw duty status lines from log entries
  if (!log.entries || log.entries.length === 0) return;

  const statusToRow = {
    'off_duty': 0,
    'sleeper_berth': 1,
    'driving': 2,
    'on_duty_not_driving': 3,
  };

  const statusColors = {
    'off_duty': '#38a169',
    'sleeper_berth': '#2b6cb0',
    'driving': '#e53e3e',
    'on_duty_not_driving': '#d69e2e',
  };

  // Draw filled areas and lines
  ctx.lineWidth = 3;
  let prevRow = null;
  let prevEndX = null;

  log.entries.forEach((entry, idx) => {
    const row = statusToRow[entry.status];
    if (row === undefined) return;

    const startX = leftMargin + entry.start_hour * hourWidth;
    const endX = leftMargin + Math.min(entry.end_hour, 24) * hourWidth;
    const y = topMargin + row * rowHeight + rowHeight / 2;

    const color = statusColors[entry.status] || '#718096';

    // Draw vertical line connecting to previous entry
    if (prevRow !== null && prevEndX !== null && prevRow !== row) {
      const prevY = topMargin + prevRow * rowHeight + rowHeight / 2;
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      ctx.moveTo(startX, prevY);
      ctx.lineTo(startX, y);
      ctx.stroke();
    }

    // Draw horizontal line for this entry
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5;
    ctx.moveTo(startX, y);
    ctx.lineTo(endX, y);
    ctx.stroke();

    // Light fill for the area
    ctx.fillStyle = color + '15';
    ctx.fillRect(startX, topMargin + row * rowHeight + 2, endX - startX, rowHeight - 4);

    prevRow = row;
    prevEndX = endX;
  });

  // Draw total hours for each row on right side
  const totals = {};
  log.entries.forEach(entry => {
    const duration = Math.min(entry.end_hour, 24) - entry.start_hour;
    if (duration > 0) {
      totals[entry.status] = (totals[entry.status] || 0) + duration;
    }
  });

  ctx.fillStyle = '#2d3748';
  ctx.font = 'bold 11px Arial';
  ctx.textAlign = 'center';
  DUTY_STATUSES.forEach((status, i) => {
    const y = topMargin + i * rowHeight + rowHeight / 2 + 4;
    const hours = totals[status.key] || 0;
    ctx.fillText(hours.toFixed(1), leftMargin + gridWidth + 30, y);
  });
}

export default DailyLogSheet;
