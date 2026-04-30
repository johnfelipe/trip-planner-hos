"""
FastAPI backend for ELD Trip Planner - FMCSA Hours of Service Compliance.
"""

import math
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests as http_requests

app = FastAPI(title="ELD Trip Planner API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# HOS Constants
# ============================================================

MAX_DRIVING_HOURS = 11.0
MAX_DUTY_WINDOW_HOURS = 14.0
MANDATORY_BREAK_AFTER_HOURS = 8.0
MANDATORY_BREAK_DURATION = 0.5
MIN_OFF_DUTY_HOURS = 10.0
MAX_CYCLE_HOURS = 70.0
RESTART_HOURS = 34.0
FUEL_INTERVAL_MILES = 1000.0
FUEL_STOP_DURATION = 0.5
PICKUP_DROPOFF_DURATION = 1.0
AVERAGE_SPEED_MPH = 55.0


# ============================================================
# Models
# ============================================================

class TripRequest(BaseModel):
    current_location: str
    pickup_location: str
    dropoff_location: str
    current_cycle_used: float = Field(default=0, ge=0, le=70)


# ============================================================
# Route Service
# ============================================================

OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/driving"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def geocode_location(location: str):
    try:
        response = http_requests.get(
            NOMINATIM_URL,
            params={'q': location, 'format': 'json', 'limit': 1, 'countrycodes': 'us'},
            headers={'User-Agent': 'TripPlannerHOS/1.0'},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json()
        if results:
            return float(results[0]['lat']), float(results[0]['lon'])
    except Exception:
        pass
    return None, None


def get_route(origin_lat, origin_lng, dest_lat, dest_lng):
    coords = f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
    try:
        response = http_requests.get(
            f"{OSRM_BASE_URL}/{coords}",
            params={'overview': 'full', 'geometries': 'geojson'},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if data.get('code') == 'Ok' and data.get('routes'):
            route = data['routes'][0]
            geometry = route['geometry']['coordinates']
            route_points = [{'lat': c[1], 'lng': c[0]} for c in geometry]
            if len(route_points) > 200:
                step = len(route_points) // 200
                route_points = route_points[::step] + [route_points[-1]]
            return {
                'distance_miles': route['distance'] * 0.000621371,
                'duration_hours': route['duration'] / 3600,
                'route_points': route_points,
                'success': True,
            }
    except Exception:
        pass

    distance_miles = haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng) * 1.3
    duration_hours = distance_miles / 55.0
    num_points = max(20, int(distance_miles / 10))
    route_points = []
    for i in range(num_points + 1):
        t = i / num_points
        route_points.append({
            'lat': origin_lat + t * (dest_lat - origin_lat),
            'lng': origin_lng + t * (dest_lng - origin_lng),
        })
    return {
        'distance_miles': distance_miles,
        'duration_hours': duration_hours,
        'route_points': route_points,
        'success': True,
    }


def haversine_distance(lat1, lng1, lat2, lng2):
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ============================================================
# HOS Rules Engine
# ============================================================

def calculate_trip_plan(total_distance_miles, current_cycle_used,
                        pickup_location="", dropoff_location="",
                        route_points=None):
    if route_points is None:
        route_points = []

    stops = []
    daily_logs = []

    current_driving_hours = 0.0
    current_duty_window_hours = 0.0
    current_cycle_hours = current_cycle_used
    hours_since_break = 0.0
    miles_since_fuel = 0.0
    total_miles_covered = 0.0
    current_day = 1
    current_hour_of_day = 6.0

    current_log = {
        'day': current_day, 'entries': [],
        'start_location': pickup_location, 'end_location': '',
        'total_miles': 0
    }

    # Pre-trip inspection
    current_log['entries'].append({
        'start_hour': current_hour_of_day,
        'end_hour': current_hour_of_day + 0.25,
        'status': 'on_duty_not_driving',
        'remarks': 'Pre-trip inspection', 'location': ''
    })
    current_hour_of_day += 0.25
    current_duty_window_hours += 0.25

    # Pickup
    stops.append({
        'location': pickup_location,
        'latitude': route_points[0]['lat'] if route_points else 0,
        'longitude': route_points[0]['lng'] if route_points else 0,
        'stop_type': 'pickup',
        'duration_hours': PICKUP_DROPOFF_DURATION,
        'mile_marker': 0,
    })
    current_log['entries'].append({
        'start_hour': current_hour_of_day,
        'end_hour': current_hour_of_day + PICKUP_DROPOFF_DURATION,
        'status': 'on_duty_not_driving',
        'remarks': 'Loading/Pickup', 'location': pickup_location
    })
    current_hour_of_day += PICKUP_DROPOFF_DURATION
    current_duty_window_hours += PICKUP_DROPOFF_DURATION

    remaining_miles = total_distance_miles
    trip_complete = False
    max_iterations = 500

    while not trip_complete and remaining_miles > 0 and max_iterations > 0:
        max_iterations -= 1

        available_drive_time = min(
            MAX_DRIVING_HOURS - current_driving_hours,
            MAX_DUTY_WINDOW_HOURS - current_duty_window_hours,
            MANDATORY_BREAK_AFTER_HOURS - hours_since_break,
            MAX_CYCLE_HOURS - current_cycle_hours,
            24.0 - current_hour_of_day,
        )

        miles_until_fuel = FUEL_INTERVAL_MILES - miles_since_fuel
        hours_until_fuel = miles_until_fuel / AVERAGE_SPEED_MPH
        drive_time_this_segment = min(available_drive_time, hours_until_fuel)
        miles_this_segment = drive_time_this_segment * AVERAGE_SPEED_MPH

        if miles_this_segment >= remaining_miles:
            miles_this_segment = remaining_miles
            drive_time_this_segment = miles_this_segment / AVERAGE_SPEED_MPH
            trip_complete = True

        if drive_time_this_segment <= 0.01:
            if (MANDATORY_BREAK_AFTER_HOURS - hours_since_break) <= 0.01:
                current_log['entries'].append({
                    'start_hour': round(current_hour_of_day, 2),
                    'end_hour': round(current_hour_of_day + MANDATORY_BREAK_DURATION, 2),
                    'status': 'off_duty',
                    'remarks': '30-min break', 'location': ''
                })
                _add_stop(stops, route_points, total_miles_covered,
                          total_distance_miles, 'rest', MANDATORY_BREAK_DURATION)
                current_hour_of_day += MANDATORY_BREAK_DURATION
                current_duty_window_hours += MANDATORY_BREAK_DURATION
                hours_since_break = 0.0
                continue

            elif ((MAX_DRIVING_HOURS - current_driving_hours) <= 0.01 or
                  (MAX_DUTY_WINDOW_HOURS - current_duty_window_hours) <= 0.01):
                remaining_today = 24.0 - current_hour_of_day
                if remaining_today > 0.01:
                    sleep_today = min(remaining_today, MIN_OFF_DUTY_HOURS)
                    current_log['entries'].append({
                        'start_hour': round(current_hour_of_day, 2),
                        'end_hour': round(current_hour_of_day + sleep_today, 2),
                        'status': 'sleeper_berth',
                        'remarks': 'Required 10-hr off duty', 'location': ''
                    })
                    current_log['end_location'] = f"Mile {total_miles_covered:.0f}"
                    current_log['total_miles'] = _calc_day_miles(current_log)
                    daily_logs.append(current_log)

                _add_stop(stops, route_points, total_miles_covered,
                          total_distance_miles, 'sleep', MIN_OFF_DUTY_HOURS)

                current_day += 1
                current_log = {
                    'day': current_day, 'entries': [],
                    'start_location': f"Mile {total_miles_covered:.0f}",
                    'end_location': '', 'total_miles': 0
                }

                off_in_new_day = MIN_OFF_DUTY_HOURS - remaining_today
                current_hour_of_day = max(off_in_new_day, 0)
                if off_in_new_day > 0.01:
                    current_log['entries'].append({
                        'start_hour': 0,
                        'end_hour': round(off_in_new_day, 2),
                        'status': 'sleeper_berth',
                        'remarks': 'Required 10-hr off duty (cont.)', 'location': ''
                    })

                current_driving_hours = 0.0
                current_duty_window_hours = 0.0
                hours_since_break = 0.0
                continue

            elif (MAX_CYCLE_HOURS - current_cycle_hours) <= 0.01:
                remaining_today = 24.0 - current_hour_of_day
                if remaining_today > 0.01:
                    sleep_today = min(remaining_today, RESTART_HOURS)
                    current_log['entries'].append({
                        'start_hour': round(current_hour_of_day, 2),
                        'end_hour': round(current_hour_of_day + sleep_today, 2),
                        'status': 'off_duty',
                        'remarks': '34-hr restart', 'location': ''
                    })
                    current_log['end_location'] = f"Mile {total_miles_covered:.0f}"
                    current_log['total_miles'] = _calc_day_miles(current_log)
                    daily_logs.append(current_log)

                _add_stop(stops, route_points, total_miles_covered,
                          total_distance_miles, 'sleep', RESTART_HOURS)

                remaining_restart = RESTART_HOURS - remaining_today
                while remaining_restart > 0:
                    current_day += 1
                    rest_log = {
                        'day': current_day, 'entries': [],
                        'start_location': f"Mile {total_miles_covered:.0f}",
                        'end_location': f"Mile {total_miles_covered:.0f}",
                        'total_miles': 0
                    }
                    hours_this_day = min(remaining_restart, 24.0)
                    rest_log['entries'].append({
                        'start_hour': 0,
                        'end_hour': round(hours_this_day, 2),
                        'status': 'off_duty',
                        'remarks': '34-hr restart (cont.)', 'location': ''
                    })
                    if remaining_restart >= 24.0:
                        daily_logs.append(rest_log)
                    else:
                        current_log = rest_log
                    remaining_restart -= 24.0

                current_hour_of_day = RESTART_HOURS % 24.0
                current_driving_hours = 0.0
                current_duty_window_hours = 0.0
                current_cycle_hours = 0.0
                hours_since_break = 0.0
                continue
            else:
                if (24.0 - current_hour_of_day) <= 0.01:
                    current_log['end_location'] = f"Mile {total_miles_covered:.0f}"
                    current_log['total_miles'] = _calc_day_miles(current_log)
                    daily_logs.append(current_log)
                    current_day += 1
                    current_log = {
                        'day': current_day, 'entries': [],
                        'start_location': f"Mile {total_miles_covered:.0f}",
                        'end_location': '', 'total_miles': 0
                    }
                    current_hour_of_day = 0.0
                continue

        # Drive
        current_log['entries'].append({
            'start_hour': round(current_hour_of_day, 2),
            'end_hour': round(current_hour_of_day + drive_time_this_segment, 2),
            'status': 'driving',
            'remarks': f"Driving ({miles_this_segment:.0f} mi)", 'location': ''
        })

        current_hour_of_day += drive_time_this_segment
        current_driving_hours += drive_time_this_segment
        current_duty_window_hours += drive_time_this_segment
        current_cycle_hours += drive_time_this_segment
        hours_since_break += drive_time_this_segment
        miles_since_fuel += miles_this_segment
        total_miles_covered += miles_this_segment
        remaining_miles -= miles_this_segment

        if miles_since_fuel >= FUEL_INTERVAL_MILES and not trip_complete:
            current_log['entries'].append({
                'start_hour': round(current_hour_of_day, 2),
                'end_hour': round(current_hour_of_day + FUEL_STOP_DURATION, 2),
                'status': 'on_duty_not_driving',
                'remarks': 'Fueling', 'location': ''
            })
            _add_stop(stops, route_points, total_miles_covered,
                      total_distance_miles, 'fuel', FUEL_STOP_DURATION)
            current_hour_of_day += FUEL_STOP_DURATION
            current_duty_window_hours += FUEL_STOP_DURATION
            current_cycle_hours += FUEL_STOP_DURATION
            miles_since_fuel = 0.0

    # Dropoff
    if current_hour_of_day + PICKUP_DROPOFF_DURATION > 24.0:
        remaining_today = 24.0 - current_hour_of_day
        if remaining_today > 0.01:
            current_log['entries'].append({
                'start_hour': round(current_hour_of_day, 2),
                'end_hour': 24.0,
                'status': 'on_duty_not_driving',
                'remarks': 'Unloading/Dropoff', 'location': dropoff_location
            })
        current_log['end_location'] = dropoff_location
        current_log['total_miles'] = _calc_day_miles(current_log)
        daily_logs.append(current_log)
        current_day += 1
        current_log = {
            'day': current_day, 'entries': [],
            'start_location': dropoff_location, 'end_location': dropoff_location,
            'total_miles': 0
        }
        remaining_dropoff = PICKUP_DROPOFF_DURATION - remaining_today
        current_log['entries'].append({
            'start_hour': 0,
            'end_hour': round(remaining_dropoff, 2),
            'status': 'on_duty_not_driving',
            'remarks': 'Unloading/Dropoff (cont.)', 'location': dropoff_location
        })
        current_hour_of_day = remaining_dropoff
    else:
        current_log['entries'].append({
            'start_hour': round(current_hour_of_day, 2),
            'end_hour': round(current_hour_of_day + PICKUP_DROPOFF_DURATION, 2),
            'status': 'on_duty_not_driving',
            'remarks': 'Unloading/Dropoff', 'location': dropoff_location
        })
        current_hour_of_day += PICKUP_DROPOFF_DURATION

    stops.append({
        'location': dropoff_location,
        'latitude': route_points[-1]['lat'] if route_points else 0,
        'longitude': route_points[-1]['lng'] if route_points else 0,
        'stop_type': 'dropoff',
        'duration_hours': PICKUP_DROPOFF_DURATION,
        'mile_marker': round(total_distance_miles, 1),
    })

    if current_hour_of_day < 23.99:
        current_log['entries'].append({
            'start_hour': round(current_hour_of_day, 2),
            'end_hour': 24.0,
            'status': 'off_duty',
            'remarks': 'Off duty', 'location': ''
        })

    current_log['end_location'] = dropoff_location
    current_log['total_miles'] = _calc_day_miles(current_log)
    daily_logs.append(current_log)

    return {
        'stops': stops,
        'daily_logs': daily_logs,
        'total_days': current_day,
        'total_miles': total_distance_miles,
    }


def _add_stop(stops, route_points, miles_covered, total_miles, stop_type, duration):
    coords = _get_coords_at_mile(route_points, miles_covered, total_miles)
    stops.append({
        'location': coords['name'],
        'latitude': coords['lat'],
        'longitude': coords['lng'],
        'stop_type': stop_type,
        'duration_hours': duration,
        'mile_marker': round(miles_covered, 1),
    })


def _get_coords_at_mile(route_points, miles_covered, total_miles):
    if not route_points or total_miles == 0:
        return {'lat': 0, 'lng': 0, 'name': f"Mile {miles_covered:.0f}"}
    fraction = min(miles_covered / total_miles, 1.0)
    index = fraction * (len(route_points) - 1)
    lower_idx = int(index)
    upper_idx = min(lower_idx + 1, len(route_points) - 1)
    t = index - lower_idx
    lat = route_points[lower_idx]['lat'] * (1 - t) + route_points[upper_idx]['lat'] * t
    lng = route_points[lower_idx]['lng'] * (1 - t) + route_points[upper_idx]['lng'] * t
    return {'lat': lat, 'lng': lng, 'name': f"Mile {miles_covered:.0f}"}


def _calc_day_miles(log):
    driving_hours = sum(
        e['end_hour'] - e['start_hour']
        for e in log['entries']
        if e['status'] == 'driving'
    )
    return round(driving_hours * AVERAGE_SPEED_MPH, 1)


def _format_daily_logs(daily_logs):
    formatted = []
    for log in daily_logs:
        totals = {}
        for entry in log['entries']:
            duration = entry['end_hour'] - entry['start_hour']
            if duration > 0:
                totals[entry['status']] = totals.get(entry['status'], 0) + duration
        formatted.append({
            'day': log['day'],
            'start_location': log.get('start_location', ''),
            'end_location': log.get('end_location', ''),
            'total_miles': log.get('total_miles', 0),
            'entries': log['entries'],
            'totals': {k: round(v, 2) for k, v in totals.items()},
        })
    return formatted


# ============================================================
# API Endpoints
# ============================================================

@app.get("/api/health/")
def health_check():
    return {"status": "ok"}


@app.post("/api/trip/plan/")
def plan_trip(request: TripRequest):
    current_location = request.current_location.strip()
    pickup_location = request.pickup_location.strip()
    dropoff_location = request.dropoff_location.strip()
    current_cycle_used = request.current_cycle_used

    errors = []
    if not current_location:
        errors.append("Current location is required")
    if not pickup_location:
        errors.append("Pickup location is required")
    if not dropoff_location:
        errors.append("Dropoff location is required")
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    # Geocode
    current_lat, current_lng = geocode_location(current_location)
    pickup_lat, pickup_lng = geocode_location(pickup_location)
    dropoff_lat, dropoff_lng = geocode_location(dropoff_location)

    if current_lat is None:
        errors.append(f"Could not geocode: {current_location}")
    if pickup_lat is None:
        errors.append(f"Could not geocode: {pickup_location}")
    if dropoff_lat is None:
        errors.append(f"Could not geocode: {dropoff_location}")
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    # Get routes
    leg1 = get_route(current_lat, current_lng, pickup_lat, pickup_lng)
    leg2 = get_route(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)

    all_points = leg1['route_points'] + leg2['route_points']
    total_distance = leg1['distance_miles'] + leg2['distance_miles']
    total_duration = leg1['duration_hours'] + leg2['duration_hours']

    # Calculate trip plan
    trip_plan = calculate_trip_plan(
        total_distance_miles=total_distance,
        current_cycle_used=current_cycle_used,
        pickup_location=pickup_location,
        dropoff_location=dropoff_location,
        route_points=all_points,
    )

    return {
        'route': {
            'total_distance_miles': round(total_distance, 1),
            'total_duration_hours': round(total_duration, 1),
            'points': all_points,
            'legs': [
                {'from': current_location, 'to': pickup_location,
                 'distance_miles': round(leg1['distance_miles'], 1),
                 'duration_hours': round(leg1['duration_hours'], 1)},
                {'from': pickup_location, 'to': dropoff_location,
                 'distance_miles': round(leg2['distance_miles'], 1),
                 'duration_hours': round(leg2['duration_hours'], 1)},
            ],
            'locations': {
                'current': {'lat': current_lat, 'lng': current_lng, 'name': current_location},
                'pickup': {'lat': pickup_lat, 'lng': pickup_lng, 'name': pickup_location},
                'dropoff': {'lat': dropoff_lat, 'lng': dropoff_lng, 'name': dropoff_location},
            },
        },
        'trip_plan': {
            'total_days': trip_plan['total_days'],
            'total_miles': round(trip_plan['total_miles'], 1),
            'stops': trip_plan['stops'],
            'daily_logs': _format_daily_logs(trip_plan['daily_logs']),
        },
    }
