"""
Route calculation service using OSRM (Open Source Routing Machine).
Falls back to straight-line distance estimation if OSRM is unavailable.
"""

import math
import requests
from typing import Tuple


OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/driving"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def geocode_location(location: str) -> Tuple[float, float]:
    """
    Geocode a location string to (latitude, longitude) using Nominatim.
    """
    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                'q': location,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'us',
            },
            headers={'User-Agent': 'TripPlannerHOS/1.0'},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json()
        if results:
            return float(results[0]['lat']), float(results[0]['lon'])
    except (requests.RequestException, KeyError, IndexError, ValueError):
        pass
    return None, None


def get_route(
    origin_lat: float, origin_lng: float,
    destination_lat: float, destination_lng: float,
    waypoints: list = None,
) -> dict:
    """
    Get route from OSRM between origin and destination.

    Returns dict with:
    - distance_miles: total distance
    - duration_hours: estimated driving time
    - geometry: list of [lat, lng] points for the route
    - waypoint_distances: distances between waypoints
    """
    # Build coordinate string for OSRM (lng,lat format)
    coords = f"{origin_lng},{origin_lat}"
    if waypoints:
        for wp in waypoints:
            coords += f";{wp[1]},{wp[0]}"
    coords += f";{destination_lng},{destination_lat}"

    try:
        response = requests.get(
            f"{OSRM_BASE_URL}/{coords}",
            params={
                'overview': 'full',
                'geometries': 'geojson',
                'steps': 'true',
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if data.get('code') == 'Ok' and data.get('routes'):
            route = data['routes'][0]
            distance_meters = route['distance']
            duration_seconds = route['duration']
            geometry = route['geometry']['coordinates']

            # Convert to lat/lng points
            route_points = [
                {'lat': coord[1], 'lng': coord[0]}
                for coord in geometry
            ]

            # Simplify route to ~200 points for frontend
            if len(route_points) > 200:
                step = len(route_points) // 200
                route_points = route_points[::step] + [route_points[-1]]

            return {
                'distance_miles': distance_meters * 0.000621371,
                'duration_hours': duration_seconds / 3600,
                'route_points': route_points,
                'success': True,
            }
    except (requests.RequestException, KeyError, IndexError, ValueError):
        pass

    # Fallback: straight-line calculation
    distance_miles = haversine_distance(
        origin_lat, origin_lng, destination_lat, destination_lng
    )
    # Assume road distance is ~1.3x straight-line
    distance_miles *= 1.3
    duration_hours = distance_miles / 55.0  # Average 55 mph

    # Generate simple route points
    num_points = max(20, int(distance_miles / 10))
    route_points = []
    for i in range(num_points + 1):
        t = i / num_points
        lat = origin_lat + t * (destination_lat - origin_lat)
        lng = origin_lng + t * (destination_lng - origin_lng)
        route_points.append({'lat': lat, 'lng': lng})

    return {
        'distance_miles': distance_miles,
        'duration_hours': duration_hours,
        'route_points': route_points,
        'success': True,
        'fallback': True,
    }


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in miles between two coordinates using Haversine formula."""
    R = 3959  # Earth's radius in miles

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def get_full_route(
    current_location: str,
    pickup_location: str,
    dropoff_location: str,
) -> dict:
    """
    Get complete route from current -> pickup -> dropoff.
    """
    # Geocode all locations
    current_lat, current_lng = geocode_location(current_location)
    pickup_lat, pickup_lng = geocode_location(pickup_location)
    dropoff_lat, dropoff_lng = geocode_location(dropoff_location)

    errors = []
    if current_lat is None:
        errors.append(f"Could not geocode current location: {current_location}")
    if pickup_lat is None:
        errors.append(f"Could not geocode pickup location: {pickup_location}")
    if dropoff_lat is None:
        errors.append(f"Could not geocode dropoff location: {dropoff_location}")

    if errors:
        return {'success': False, 'errors': errors}

    # Get route from current to pickup
    leg1 = get_route(current_lat, current_lng, pickup_lat, pickup_lng)

    # Get route from pickup to dropoff (main haul)
    leg2 = get_route(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)

    # Combine routes
    all_points = leg1['route_points'] + leg2['route_points']
    total_distance = leg1['distance_miles'] + leg2['distance_miles']
    total_duration = leg1['duration_hours'] + leg2['duration_hours']

    return {
        'success': True,
        'total_distance_miles': total_distance,
        'total_duration_hours': total_duration,
        'route_points': all_points,
        'legs': [
            {
                'from': current_location,
                'to': pickup_location,
                'distance_miles': leg1['distance_miles'],
                'duration_hours': leg1['duration_hours'],
            },
            {
                'from': pickup_location,
                'to': dropoff_location,
                'distance_miles': leg2['distance_miles'],
                'duration_hours': leg2['duration_hours'],
            },
        ],
        'locations': {
            'current': {'lat': current_lat, 'lng': current_lng, 'name': current_location},
            'pickup': {'lat': pickup_lat, 'lng': pickup_lng, 'name': pickup_location},
            'dropoff': {'lat': dropoff_lat, 'lng': dropoff_lng, 'name': dropoff_location},
        },
    }
