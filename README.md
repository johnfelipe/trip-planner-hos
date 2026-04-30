# ELD Trip Planner - FMCSA Hours of Service Compliance

**Live Demo:** https://build-tpczakxl.devinapps.com  
**API:** https://trip-planner-hos-api-jvfebtxf.fly.dev

A full-stack web application that takes trip details as inputs and outputs route instructions with HOS-compliant ELD (Electronic Logging Device) daily log sheets.

## Features

- **Trip Planning**: Input current location, pickup location, drop-off location, and current cycle hours
- **Route Mapping**: Interactive map showing the complete route with all stops marked (using OpenStreetMap/Leaflet)
- **HOS Compliance Engine**: Automatically calculates required stops based on FMCSA regulations
- **Daily Log Sheets**: Canvas-drawn log sheets mimicking the official FMCSA Driver's Daily Log format
- **Multi-day Support**: Generates multiple log sheets for trips spanning several days

## HOS Rules Implemented

Based on FMCSA Interstate Truck Driver's Guide to Hours of Service (April 2022):

| Rule | Limit |
|------|-------|
| 11-Hour Driving Limit | Max 11 hrs driving after 10 consecutive hrs off duty |
| 14-Hour Driving Window | Cannot drive beyond 14th hr after coming on duty |
| 30-Minute Rest Break | Required after 8 cumulative hours of driving |
| 70-Hour/8-Day Limit | Cannot drive after 70 hrs on duty in 8 consecutive days |
| 34-Hour Restart | Resets 70-hr limit after 34 consecutive hrs off duty |
| 10-Hour Off-Duty | Required between duty periods |

## Assumptions

- Property-carrying driver
- 70-hour/8-day cycle
- No adverse driving conditions
- Fueling at least once every 1,000 miles
- 1 hour for pickup and drop-off operations
- Average highway speed: 55 mph

## Tech Stack

- **Backend**: Django + Django REST Framework
- **Frontend**: React 18 + Leaflet (maps) + Canvas API (log sheets)
- **Routing**: OSRM (Open Source Routing Machine) API
- **Geocoding**: Nominatim (OpenStreetMap)

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

The app will be available at `http://localhost:3000`

## API Endpoints

### POST /api/trip/plan/

Plan a trip with HOS-compliant stops and daily logs.

**Request Body:**
```json
{
  "current_location": "Dallas, TX",
  "pickup_location": "Houston, TX",
  "dropoff_location": "Los Angeles, CA",
  "current_cycle_used": 10
}
```

**Response:**
- Route information (distance, duration, polyline points)
- Trip plan with stops (fuel, rest, sleep)
- Daily log sheets with duty status entries

### GET /api/health/

Health check endpoint.

## Project Structure

```
trip-planner-hos/
├── backend/
│   ├── api/
│   │   ├── hos_rules.py      # HOS rules engine
│   │   ├── route_service.py  # OSRM routing & geocoding
│   │   ├── views.py          # API views
│   │   └── urls.py           # API URLs
│   ├── trip_planner/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── TripForm.js        # Trip input form
│   │   │   ├── RouteMap.js        # Leaflet map component
│   │   │   ├── DailyLogSheet.js   # Canvas-drawn ELD log
│   │   │   └── TripSummary.js     # Trip overview
│   │   ├── App.js
│   │   └── index.js
│   └── package.json
└── README.md
```

## Daily Log Sheet

The application draws daily log sheets on an HTML Canvas that closely match the official FMCSA Driver's Daily Log format:

- 24-hour time grid with 15-minute subdivisions
- 4 duty status rows: Off Duty, Sleeper Berth, Driving, On Duty (Not Driving)
- Color-coded status lines with connecting vertical transitions
- Total hours per status displayed on the right
- Remarks section with time ranges and locations

## License

MIT
