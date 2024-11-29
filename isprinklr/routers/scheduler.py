# Description: reads from a .csv file and starts sprinklers based on the schedule
# The program is run every morning at 4am by a cron job
# Needs to open the csv file and determine which sprinklers need to be run that day and for how long.
# Then it needs to start the sprinklers using the API defined in api.py and wait for them to finish.

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

from ..schemas import Schedule, ScheduleItem
from isprinklr.system_status import system_status, schedule_database

logger = logging.getLogger(__name__)

API_URL = "http://localhost:8080/api/"

day_abbr = {
        0: "Su",
        1: "M",
        2: "Tu",
        3: "W",
        4: "Th",
        5: "F",
        6: "Sa"
        }

router = APIRouter(
    prefix="/api/scheduler",
    tags=["scheduler"]
)

@router.get("/schedule")
async def get_schedule() -> List[ScheduleItem]:
    """Get the current active schedule configuration.

    Returns:
        List[ScheduleItem]: List of schedule items from the active schedule, containing:
            * zone (int): Zone number
            * day (str): Day abbreviation ("Su", "M", "Tu", "W", "Th", "F", "Sa")
            * duration (int): Duration in seconds
            
    Raises:
        HTTPException: If no active schedule is set
    """
    try:
        active_schedule = schedule_database.get_active_schedule()
        return active_schedule["schedule_items"]
    except ValueError:
        return []

@router.get("/on_off")
async def get_schedule_on_off() -> Dict[str, bool]:
    """Get whether the automated schedule is currently enabled or disabled.

    Returns:
        Dict[str, bool]: Dictionary containing:
            * schedule_on_off (bool): Indicates if scheduling is enabled
    """
    return {"schedule_on_off": system_status.schedule_on_off}

@router.put("/on_off")
async def update_schedule_on_off(schedule_on_off: bool) -> Dict[str, bool]:
    """Enable or disable the automated schedule.

    Parameters:
        schedule_on_off (bool): True to enable scheduling, False to disable

    Returns:
        Dict[str, bool]: Dictionary containing:
            * schedule_on_off (bool): Updated schedule status

    Raises:
        HTTPException: If the update fails
    """
    try:
        system_status.schedule_on_off = schedule_on_off
        return {"schedule_on_off": system_status.schedule_on_off}
    except Exception as exc:
        logger.error(f"Failed to update schedule on/off: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/schedule")
async def update_schedule(schedule: Schedule) -> Dict[str, Any]:
    """Update a schedule in the database.

    Parameters:
        schedule (Schedule): Schedule data containing:
            * sched_id (int): Schedule ID
            * schedule_name (str): Name of the schedule
            * schedule_items (List[ScheduleItem]): List of schedule items containing:
                * zone (int): Zone number
                * day (str): Day abbreviation ("Su", "M", "Tu", "W", "Th", "F", "Sa")
                * duration (int): Duration in seconds

    Returns:
        Dict[str, Any]: Dictionary containing:
            * message (str): Success message
            * schedule (Schedule): Updated schedule configuration

    Raises:
        HTTPException: If the update fails due to invalid data or server error
    """
    try:
        updated_schedule = schedule_database.update_schedule(schedule)
        return {"message": "Success", "schedule": updated_schedule}
    except ValueError as exc:
        logger.error(f"Failed to update schedule: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to update schedule: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")
