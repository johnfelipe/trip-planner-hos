"""API views for trip planning."""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .route_service import get_full_route
from .hos_rules import calculate_trip_plan


@api_view(['POST'])
def plan_trip(request):
    """
    Plan a trip with HOS-compliant stops and daily logs.

    Expected POST body:
    {
        "current_location": "Dallas, TX",
        "pickup_location": "Houston, TX",
        "dropoff_location": "Los Angeles, CA",
        "current_cycle_used": 10
    }
    """
    current_location = request.data.get('current_location', '').strip()
    pickup_location = request.data.get('pickup_location', '').strip()
    dropoff_location = request.data.get('dropoff_location', '').strip()
    current_cycle_used = float(request.data.get('current_cycle_used', 0))

    # Validate inputs
    errors = []
    if not current_location:
        errors.append("Current location is required")
    if not pickup_location:
        errors.append("Pickup location is required")
    if not dropoff_location:
        errors.append("Dropoff location is required")
    if current_cycle_used < 0 or current_cycle_used > 70:
        errors.append("Current cycle used must be between 0 and 70 hours")

    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    # Get route information
    route_data = get_full_route(current_location, pickup_location, dropoff_location)

    if not route_data.get('success'):
        return Response(
            {'errors': route_data.get('errors', ['Route calculation failed'])},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Calculate trip plan with HOS rules
    trip_plan = calculate_trip_plan(
        total_distance_miles=route_data['total_distance_miles'],
        total_drive_time_hours=route_data['total_duration_hours'],
        current_cycle_used=current_cycle_used,
        pickup_location=pickup_location,
        dropoff_location=dropoff_location,
        route_points=route_data['route_points'],
    )

    # Format response
    response_data = {
        'route': {
            'total_distance_miles': round(route_data['total_distance_miles'], 1),
            'total_duration_hours': round(route_data['total_duration_hours'], 1),
            'points': route_data['route_points'],
            'legs': route_data['legs'],
            'locations': route_data['locations'],
        },
        'trip_plan': {
            'total_days': trip_plan['total_days'],
            'total_miles': round(trip_plan['total_miles'], 1),
            'stops': [
                {
                    'location': stop.location,
                    'latitude': stop.latitude,
                    'longitude': stop.longitude,
                    'stop_type': stop.stop_type,
                    'duration_hours': stop.duration_hours,
                    'mile_marker': round(stop.mile_marker, 1),
                }
                for stop in trip_plan['stops']
            ],
            'daily_logs': [
                {
                    'day': log.day,
                    'start_location': log.start_location,
                    'end_location': log.end_location,
                    'total_miles': round(log.total_miles_driving, 1),
                    'entries': [
                        {
                            'start_hour': round(entry.start_hour, 2),
                            'end_hour': round(entry.end_hour, 2),
                            'status': entry.status.value,
                            'remarks': entry.remarks,
                            'location': entry.location,
                        }
                        for entry in log.entries
                    ],
                    'totals': {
                        k.value: round(v, 2)
                        for k, v in log.total_hours.items()
                    },
                }
                for log in trip_plan['daily_logs']
            ],
        },
    }

    return Response(response_data)


@api_view(['GET'])
def health_check(request):
    """Health check endpoint."""
    return Response({'status': 'ok'})
