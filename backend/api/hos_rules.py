"""
FMCSA Hours of Service (HOS) Rules Engine for Property-Carrying Drivers.

Implements:
- 11-Hour Driving Limit
- 14-Hour Driving Window
- 30-Minute Rest Break (after 8 hours cumulative driving)
- 70-Hour/8-Day On-Duty Limit
- 34-Hour Restart
- 10-Hour Off-Duty requirement between shifts
- Fueling stop every 1,000 miles
- 1 hour for pickup and 1 hour for drop-off
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class DutyStatus(str, Enum):
    OFF_DUTY = "off_duty"
    SLEEPER_BERTH = "sleeper_berth"
    DRIVING = "driving"
    ON_DUTY_NOT_DRIVING = "on_duty_not_driving"


@dataclass
class LogEntry:
    start_hour: float  # Hour of day (0-24)
    end_hour: float
    status: DutyStatus
    location: str = ""
    remarks: str = ""


@dataclass
class DailyLog:
    day: int  # Day number of the trip (1-based)
    date: str = ""
    entries: List[LogEntry] = field(default_factory=list)
    total_miles_driving: float = 0.0
    start_location: str = ""
    end_location: str = ""

    @property
    def total_hours(self) -> dict:
        totals = {status: 0.0 for status in DutyStatus}
        for entry in self.entries:
            duration = entry.end_hour - entry.start_hour
            if duration > 0:
                totals[entry.status] += duration
        return totals


@dataclass
class TripStop:
    location: str
    latitude: float
    longitude: float
    stop_type: str  # 'fuel', 'rest', 'pickup', 'dropoff', 'sleep'
    duration_hours: float
    mile_marker: float
    cumulative_hours: float


@dataclass
class TripSegment:
    start_location: str
    end_location: str
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    distance_miles: float
    duration_hours: float
    segment_type: str  # 'drive', 'fuel', 'rest', 'pickup', 'dropoff', 'sleep'


# HOS Constants
MAX_DRIVING_HOURS = 11.0
MAX_DUTY_WINDOW_HOURS = 14.0
MANDATORY_BREAK_AFTER_HOURS = 8.0
MANDATORY_BREAK_DURATION = 0.5  # 30 minutes
MIN_OFF_DUTY_HOURS = 10.0
MAX_CYCLE_HOURS = 70.0
CYCLE_DAYS = 8
RESTART_HOURS = 34.0
FUEL_INTERVAL_MILES = 1000.0
FUEL_STOP_DURATION = 0.5  # 30 minutes for fueling
PICKUP_DROPOFF_DURATION = 1.0  # 1 hour each
AVERAGE_SPEED_MPH = 55.0  # Average highway speed


def calculate_trip_plan(
    total_distance_miles: float,
    total_drive_time_hours: float,
    current_cycle_used: float,
    pickup_location: str = "",
    dropoff_location: str = "",
    route_points: list = None,
) -> dict:
    """
    Calculate a complete trip plan with HOS-compliant stops.

    Returns dict with:
    - stops: list of TripStop
    - daily_logs: list of DailyLog
    - total_days: int
    - segments: list of route segments
    """
    if route_points is None:
        route_points = []

    stops = []
    daily_logs = []
    segments = []

    # State tracking
    current_driving_hours = 0.0
    current_duty_window_hours = 0.0
    current_cycle_hours = current_cycle_used
    hours_since_break = 0.0
    miles_since_fuel = 0.0
    total_miles_covered = 0.0
    current_day = 1
    current_hour_of_day = 6.0  # Start at 6:00 AM

    # Initialize first day log
    current_log = DailyLog(day=current_day, start_location=pickup_location)

    # Add pre-trip inspection (15 min on-duty not driving)
    pre_trip_duration = 0.25
    current_log.entries.append(LogEntry(
        start_hour=current_hour_of_day,
        end_hour=current_hour_of_day + pre_trip_duration,
        status=DutyStatus.ON_DUTY_NOT_DRIVING,
        remarks="Pre-trip inspection"
    ))
    current_hour_of_day += pre_trip_duration
    current_duty_window_hours += pre_trip_duration

    # Add pickup stop (1 hour on-duty not driving)
    stops.append(TripStop(
        location=pickup_location,
        latitude=route_points[0]['lat'] if route_points else 0,
        longitude=route_points[0]['lng'] if route_points else 0,
        stop_type='pickup',
        duration_hours=PICKUP_DROPOFF_DURATION,
        mile_marker=0,
        cumulative_hours=current_duty_window_hours
    ))
    current_log.entries.append(LogEntry(
        start_hour=current_hour_of_day,
        end_hour=current_hour_of_day + PICKUP_DROPOFF_DURATION,
        status=DutyStatus.ON_DUTY_NOT_DRIVING,
        location=pickup_location,
        remarks="Loading/Pickup"
    ))
    current_hour_of_day += PICKUP_DROPOFF_DURATION
    current_duty_window_hours += PICKUP_DROPOFF_DURATION

    remaining_miles = total_distance_miles
    trip_complete = False

    while not trip_complete and remaining_miles > 0:
        # Calculate available driving time before any limit is hit
        available_driving_until_11hr = MAX_DRIVING_HOURS - current_driving_hours
        available_driving_until_14hr = MAX_DUTY_WINDOW_HOURS - current_duty_window_hours
        available_driving_until_break = MANDATORY_BREAK_AFTER_HOURS - hours_since_break
        available_driving_until_cycle = MAX_CYCLE_HOURS - current_cycle_hours

        available_drive_time = min(
            available_driving_until_11hr,
            available_driving_until_14hr,
            available_driving_until_break,
            available_driving_until_cycle,
        )

        # Check if we need to handle end of day (drive until midnight max)
        hours_until_midnight = 24.0 - current_hour_of_day
        available_drive_time = min(available_drive_time, hours_until_midnight)

        # Check fuel stop needed
        miles_until_fuel = FUEL_INTERVAL_MILES - miles_since_fuel
        hours_until_fuel = miles_until_fuel / AVERAGE_SPEED_MPH

        drive_time_this_segment = min(available_drive_time, hours_until_fuel)
        miles_this_segment = drive_time_this_segment * AVERAGE_SPEED_MPH

        # Don't drive more than remaining
        if miles_this_segment >= remaining_miles:
            miles_this_segment = remaining_miles
            drive_time_this_segment = miles_this_segment / AVERAGE_SPEED_MPH
            trip_complete = True

        if drive_time_this_segment <= 0:
            # Need a break or reset
            if available_driving_until_break <= 0:
                # 30-minute break
                break_duration = MANDATORY_BREAK_DURATION
                current_log.entries.append(LogEntry(
                    start_hour=current_hour_of_day,
                    end_hour=current_hour_of_day + break_duration,
                    status=DutyStatus.OFF_DUTY,
                    remarks="30-min break"
                ))
                _add_stop(stops, route_points, total_miles_covered,
                          total_distance_miles, 'rest', break_duration,
                          current_duty_window_hours)
                current_hour_of_day += break_duration
                current_duty_window_hours += break_duration
                hours_since_break = 0.0
                continue

            elif available_driving_until_11hr <= 0 or available_driving_until_14hr <= 0:
                # 10-hour off-duty required
                off_duty_duration = MIN_OFF_DUTY_HOURS
                remaining_today = 24.0 - current_hour_of_day
                if remaining_today > 0:
                    sleep_today = min(remaining_today, off_duty_duration)
                    current_log.entries.append(LogEntry(
                        start_hour=current_hour_of_day,
                        end_hour=current_hour_of_day + sleep_today,
                        status=DutyStatus.SLEEPER_BERTH,
                        remarks="Required 10-hr off duty"
                    ))
                    current_log.end_location = _get_location_at_mile(
                        route_points, total_miles_covered, total_distance_miles)
                    current_log.total_miles_driving = _calc_day_miles(current_log)

                _add_stop(stops, route_points, total_miles_covered,
                          total_distance_miles, 'sleep', off_duty_duration,
                          current_duty_window_hours)

                # Start new day
                daily_logs.append(current_log)
                current_day += 1
                current_log = DailyLog(
                    day=current_day,
                    start_location=_get_location_at_mile(
                        route_points, total_miles_covered, total_distance_miles)
                )

                # Fill remaining off-duty into new day if needed
                off_in_new_day = off_duty_duration - remaining_today if remaining_today < off_duty_duration else 0
                current_hour_of_day = off_in_new_day if off_in_new_day > 0 else 6.0

                if off_in_new_day > 0:
                    current_log.entries.append(LogEntry(
                        start_hour=0,
                        end_hour=off_in_new_day,
                        status=DutyStatus.SLEEPER_BERTH,
                        remarks="Required 10-hr off duty (cont.)"
                    ))

                # Reset driving limits
                current_driving_hours = 0.0
                current_duty_window_hours = 0.0
                hours_since_break = 0.0
                continue

            elif available_driving_until_cycle <= 0:
                # 34-hour restart needed
                restart_duration = RESTART_HOURS
                remaining_today = 24.0 - current_hour_of_day
                if remaining_today > 0:
                    sleep_today = min(remaining_today, restart_duration)
                    current_log.entries.append(LogEntry(
                        start_hour=current_hour_of_day,
                        end_hour=current_hour_of_day + sleep_today,
                        status=DutyStatus.OFF_DUTY,
                        remarks="34-hr restart"
                    ))
                    current_log.end_location = _get_location_at_mile(
                        route_points, total_miles_covered, total_distance_miles)
                    current_log.total_miles_driving = _calc_day_miles(current_log)

                _add_stop(stops, route_points, total_miles_covered,
                          total_distance_miles, 'sleep', restart_duration,
                          current_duty_window_hours)

                # Handle multi-day restart
                daily_logs.append(current_log)
                remaining_restart = restart_duration - remaining_today

                while remaining_restart > 0:
                    current_day += 1
                    current_log = DailyLog(
                        day=current_day,
                        start_location=_get_location_at_mile(
                            route_points, total_miles_covered, total_distance_miles)
                    )
                    hours_this_day = min(remaining_restart, 24.0)
                    current_log.entries.append(LogEntry(
                        start_hour=0,
                        end_hour=hours_this_day,
                        status=DutyStatus.OFF_DUTY,
                        remarks="34-hr restart (cont.)"
                    ))
                    if remaining_restart >= 24.0:
                        daily_logs.append(current_log)
                    remaining_restart -= 24.0

                current_hour_of_day = max(0, restart_duration - (24.0 - (24.0 - remaining_today)))
                if current_hour_of_day >= 24:
                    current_hour_of_day -= 24.0

                # Reset everything
                current_driving_hours = 0.0
                current_duty_window_hours = 0.0
                current_cycle_hours = 0.0
                hours_since_break = 0.0
                continue
            else:
                # End of day boundary
                remaining_today = 24.0 - current_hour_of_day
                if remaining_today <= 0:
                    current_log.end_location = _get_location_at_mile(
                        route_points, total_miles_covered, total_distance_miles)
                    current_log.total_miles_driving = _calc_day_miles(current_log)
                    daily_logs.append(current_log)
                    current_day += 1
                    current_log = DailyLog(
                        day=current_day,
                        start_location=_get_location_at_mile(
                            route_points, total_miles_covered, total_distance_miles)
                    )
                    current_hour_of_day = 0.0
                continue

        # Drive this segment
        current_log.entries.append(LogEntry(
            start_hour=current_hour_of_day,
            end_hour=current_hour_of_day + drive_time_this_segment,
            status=DutyStatus.DRIVING,
            remarks=f"Driving ({miles_this_segment:.0f} mi)"
        ))

        current_hour_of_day += drive_time_this_segment
        current_driving_hours += drive_time_this_segment
        current_duty_window_hours += drive_time_this_segment
        current_cycle_hours += drive_time_this_segment
        hours_since_break += drive_time_this_segment
        miles_since_fuel += miles_this_segment
        total_miles_covered += miles_this_segment
        remaining_miles -= miles_this_segment

        # Add fuel stop if needed
        if miles_since_fuel >= FUEL_INTERVAL_MILES and not trip_complete:
            current_log.entries.append(LogEntry(
                start_hour=current_hour_of_day,
                end_hour=current_hour_of_day + FUEL_STOP_DURATION,
                status=DutyStatus.ON_DUTY_NOT_DRIVING,
                remarks="Fueling"
            ))
            _add_stop(stops, route_points, total_miles_covered,
                      total_distance_miles, 'fuel', FUEL_STOP_DURATION,
                      current_duty_window_hours)
            current_hour_of_day += FUEL_STOP_DURATION
            current_duty_window_hours += FUEL_STOP_DURATION
            current_cycle_hours += FUEL_STOP_DURATION
            miles_since_fuel = 0.0

    # Add dropoff (1 hour on-duty not driving)
    if current_hour_of_day + PICKUP_DROPOFF_DURATION > 24.0:
        # Need to handle day boundary
        remaining_today = 24.0 - current_hour_of_day
        if remaining_today > 0:
            current_log.entries.append(LogEntry(
                start_hour=current_hour_of_day,
                end_hour=24.0,
                status=DutyStatus.ON_DUTY_NOT_DRIVING,
                location=dropoff_location,
                remarks="Unloading/Dropoff"
            ))
        current_log.end_location = dropoff_location
        current_log.total_miles_driving = _calc_day_miles(current_log)
        daily_logs.append(current_log)
        current_day += 1
        current_log = DailyLog(day=current_day, start_location=dropoff_location)
        remaining_dropoff = PICKUP_DROPOFF_DURATION - remaining_today
        current_log.entries.append(LogEntry(
            start_hour=0,
            end_hour=remaining_dropoff,
            status=DutyStatus.ON_DUTY_NOT_DRIVING,
            location=dropoff_location,
            remarks="Unloading/Dropoff (cont.)"
        ))
        current_hour_of_day = remaining_dropoff
    else:
        current_log.entries.append(LogEntry(
            start_hour=current_hour_of_day,
            end_hour=current_hour_of_day + PICKUP_DROPOFF_DURATION,
            status=DutyStatus.ON_DUTY_NOT_DRIVING,
            location=dropoff_location,
            remarks="Unloading/Dropoff"
        ))
        current_hour_of_day += PICKUP_DROPOFF_DURATION

    stops.append(TripStop(
        location=dropoff_location,
        latitude=route_points[-1]['lat'] if route_points else 0,
        longitude=route_points[-1]['lng'] if route_points else 0,
        stop_type='dropoff',
        duration_hours=PICKUP_DROPOFF_DURATION,
        mile_marker=total_distance_miles,
        cumulative_hours=current_duty_window_hours
    ))

    # Fill rest of last day with off-duty
    if current_hour_of_day < 24.0:
        current_log.entries.append(LogEntry(
            start_hour=current_hour_of_day,
            end_hour=24.0,
            status=DutyStatus.OFF_DUTY,
            remarks="Off duty"
        ))

    current_log.end_location = dropoff_location
    current_log.total_miles_driving = _calc_day_miles(current_log)
    daily_logs.append(current_log)

    return {
        'stops': stops,
        'daily_logs': daily_logs,
        'total_days': current_day,
        'total_miles': total_distance_miles,
    }


def _add_stop(stops, route_points, miles_covered, total_miles, stop_type,
              duration, cumulative_hours):
    """Add a stop at the current position along the route."""
    location_info = _get_coords_at_mile(route_points, miles_covered, total_miles)
    stops.append(TripStop(
        location=location_info.get('name', f"Mile {miles_covered:.0f}"),
        latitude=location_info.get('lat', 0),
        longitude=location_info.get('lng', 0),
        stop_type=stop_type,
        duration_hours=duration,
        mile_marker=miles_covered,
        cumulative_hours=cumulative_hours
    ))


def _get_coords_at_mile(route_points, miles_covered, total_miles):
    """Interpolate coordinates at a given mile marker along the route."""
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


def _get_location_at_mile(route_points, miles_covered, total_miles):
    """Get a location name at a given mile marker."""
    return f"Mile {miles_covered:.0f}"


def _calc_day_miles(log: DailyLog) -> float:
    """Calculate total miles driven in a day based on driving hours."""
    driving_hours = sum(
        e.end_hour - e.start_hour
        for e in log.entries
        if e.status == DutyStatus.DRIVING
    )
    return driving_hours * AVERAGE_SPEED_MPH
