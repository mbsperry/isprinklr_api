import logging
from datetime import datetime
from typing import List

from isprinklr.schemas import ScheduleItem, SprinklerConfig

logger = logging.getLogger(__name__)

def validate_schedule(schedule: list[ScheduleItem], sprinklers: list[SprinklerConfig]) -> bool:
    """
    Validate a sprinkler schedule against constraints.

    Args:
        schedule (list[ScheduleItem]): List of schedule items containing:
            * zone (int): Zone number.
            * day (str): Day abbreviation or pattern ("M", "Tu", "W", "Th", "F", "Sa", "Su", "ALL", "NONE", "EO").
            * duration (int): Duration in seconds.
        sprinklers (list[dict]): List of available sprinkler configurations with "zone" as a key.

    Raises:
        ValueError: If any validation constraint is violated, such as:
            - Duplicate zones in the schedule.
            - Invalid zone numbers not present in the available sprinkler configurations.
            - Invalid duration (must be between 0 and 7200 seconds).
            - Invalid day definitions or patterns.

    Returns:
        bool: True if the schedule passes all validation checks.
    """
    valid_days = {"M", "Tu", "W", "Th", "F", "Sa", "Su", "ALL", "NONE", "EO"}
    sprinkler_zones = [x["zone"] for x in sprinklers]
    # check that each zone is only used once
    if len(schedule) != len(set([x["zone"] for x in schedule])):
        logger.error(f"Duplicate zones in schedule: {schedule}")
        raise ValueError("Validation Error: Duplicate zones in schedule")
    for item in schedule:
        # Check if the zone is valid
        if item["zone"] not in sprinkler_zones:
            logger.error(f"Invalid zone in schedule: {item}")
            raise ValueError("Validation Error: Invalid zone")
        # Check if the duration is valid (in seconds)
        # Max duration is 2 hours (7200 seconds)
        if item["duration"] < 0 or item["duration"] > 7200:
            logger.error(f"Invalid duration in schedule: {item}")
            raise ValueError("Validation Error: Invalid duration (must be between 0 and 7200 seconds)")
        # Check if the day is valid
        days = item["day"].split(':')
        if not all(day in valid_days for day in days):
            logger.error(f"Invalid day in schedule: {item}")
            raise ValueError("Validation Error: Invalid day")
        if "ALL" in days or "NONE" in days or "EO" in days:
            if len(days) > 1:
                logger.error(f"Invalid day definition in schedule. Cannot contain multiple day selector and specified days: {item}")
                raise ValueError("Validation Error: Invalid day")
    return True

def validate_schedule_list(schedules: List[dict], sprinklers: List[SprinklerConfig]) -> bool:
    """
    Validate a list of schedules.

    Args:
        schedules (List[dict]): List of schedules, each containing:
            * sched_id (int): Unique schedule ID
            * schedule_name (str): Name of the schedule
            * schedule_items (List[ScheduleItem]): List of schedule items
        sprinklers (List[SprinklerConfig]): List of available sprinkler configurations

    Raises:
        ValueError: If any validation constraint is violated:
            - Duplicate schedule IDs
            - Duplicate schedule names
            - Missing or empty schedule names
            - Invalid schedule items

    Returns:
        bool: True if all schedules pass validation
    """
    # Check for duplicate schedule IDs
    schedule_ids = [s["sched_id"] for s in schedules]
    if len(schedule_ids) != len(set(schedule_ids)):
        raise ValueError("Validation Error: Duplicate schedule IDs")

    # Check for duplicate schedule names
    schedule_names = [s["schedule_name"] for s in schedules]
    if len(schedule_names) != len(set(schedule_names)):
        raise ValueError("Validation Error: Duplicate schedule names")

    # Validate each schedule's items
    for schedule in schedules:
        if not schedule.get("schedule_name"):
            raise ValueError("Validation Error: Schedule name is required")
        validate_schedule(schedule["schedule_items"], sprinklers)
    
    return True

def get_scheduled_zones(schedule: List[ScheduleItem], date_str: str) -> List[SprinklerConfig]:
    """Get zones scheduled to run on the specified date.
    
    Args:
        schedule (List[ScheduleItem]): List of schedule items
        date_str: Date string in MMDDYY format
        
    Returns:
        List of scheduled zones with their duration (in seconds)
    """
    try:
        date = datetime.strptime(date_str, "%m%d%y")
    except ValueError:
        logger.error(f"Invalid date format: {date_str}")
        return []

    # Map day of week (0-6, where 0 is Monday) to day abbreviation
    day_map = {0: "M", 1: "Tu", 2: "W", 3: "Th", 4: "F", 5: "Sa", 6: "Su"}
    current_day = day_map[date.weekday()]
    day_of_year = int(date.strftime("%j"))

    scheduled_zones = []
    for item in schedule:
        days = item["day"].upper().split(':')
        
        # Handle special day patterns
        if "ALL" in days:
            scheduled_zones.append({"zone": item["zone"], "duration": item["duration"]})
        elif "EO" in days and day_of_year % 2 != 0:
            scheduled_zones.append({"zone": item["zone"], "duration": item["duration"]})
        elif "NONE" in days:
            continue
        # Handle specific days
        elif current_day in days:
            scheduled_zones.append({"zone": item["zone"], "duration": item["duration"]})

    return scheduled_zones
