# Description: Router for managing sprinkler schedules
# Provides endpoints for creating, reading, updating, and deleting schedules
# as well as managing the active schedule and schedule automation

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks

from ..schemas import Schedule, ScheduleItem
from isprinklr.system_status import system_status, schedule_database
from isprinklr.schedule_util import get_scheduled_zones
from isprinklr.system_controller import system_controller

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/scheduler",
    tags=["scheduler"]
)

@router.get("/schedules")
async def get_schedules() -> List[Schedule]:
    """Get all available schedules.

    Returns:
        List[Schedule]: List of all schedules in the database
    """
    return schedule_database.schedules

@router.get("/schedule/{schedule_name}")
async def get_schedule(schedule_name: str) -> Schedule:
    """Get a specific schedule by name.

    Parameters:
        schedule_name (str): Name of the schedule to retrieve

    Returns:
        Schedule: The requested schedule

    Raises:
        HTTPException: If schedule is not found
    """
    try:
        return schedule_database.get_schedule(schedule_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@router.get("/active")
async def get_active_schedule() -> Schedule:
    """Get the currently active schedule.

    Returns:
        Schedule: The active schedule

    Raises:
        HTTPException: If no active schedule is set
    """
    try:
        return schedule_database.get_active_schedule()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@router.put("/active/{schedule_name}")
async def set_active_schedule(schedule_name: str) -> Dict[str, Any]:
    """Set the active schedule.

    Parameters:
        schedule_name (str): Name of the schedule to set as active

    Returns:
        Dict[str, Any]: Success message and updated active schedule

    Raises:
        HTTPException: If schedule is not found
    """
    try:
        # Verify schedule exists before setting as active
        schedule = schedule_database.get_schedule(schedule_name)
        schedule_database.active_schedule = schedule_name
        schedule_database.write_schedule_file()
        return {"message": "Success", "active_schedule": schedule}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to set active schedule: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/schedule")
async def create_schedule(schedule: Schedule) -> Dict[str, Any]:
    """Create a new schedule.

    Parameters:
        schedule (Schedule): Schedule data containing:
            * schedule_name (str): Name of the schedule
            * schedule_items (List[ScheduleItem]): List of schedule items containing:
                * zone (int): Zone number
                * day (str): Day abbreviation ("Su", "M", "Tu", "W", "Th", "F", "Sa")
                * duration (int): Duration in seconds

    Returns:
        Dict[str, Any]: Success message and created schedule

    Raises:
        HTTPException: If creation fails due to invalid data or server error
    """
    try:
        created_schedule = schedule_database.add_schedule(schedule)
        return {"message": "Success", "schedule": created_schedule}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to create schedule: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/schedule")
async def update_schedule(schedule: Schedule) -> Dict[str, Any]:
    """Update an existing schedule.

    Parameters:
        schedule (Schedule): Schedule data containing:
            * schedule_name (str): Name of the schedule
            * schedule_items (List[ScheduleItem]): List of schedule items containing:
                * zone (int): Zone number
                * day (str): Day abbreviation ("Su", "M", "Tu", "W", "Th", "F", "Sa")
                * duration (int): Duration in seconds

    Returns:
        Dict[str, Any]: Success message and updated schedule

    Raises:
        HTTPException: If update fails due to invalid data or server error
    """
    try:
        updated_schedule = schedule_database.update_schedule(schedule)
        return {"message": "Success", "schedule": updated_schedule}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to update schedule: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/schedule/{schedule_name}")
async def delete_schedule(schedule_name: str) -> Dict[str, str]:
    """Delete a schedule by name.

    Parameters:
        schedule_name (str): Name of the schedule to delete

    Returns:
        Dict[str, str]: Success message

    Raises:
        HTTPException: If schedule is not found or deletion fails
    """
    try:
        schedule_database.delete_schedule(schedule_name)
        return {"message": "Success"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to delete schedule: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")

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

async def run_schedule_background(zones: List[Dict[str, int]]) -> None:
    """Background task to run a sequence of zones.
    
    Args:
        zones: List of dictionaries containing zone and duration
    """
    try:
        await system_controller.run_zone_sequence(zones)
    except Exception as exc:
        logger.error(f"Error running zone sequence in background: {exc}")

async def _run_schedule_helper(schedule: Schedule) -> Tuple[List[Dict[str, int]], bool]:
    """Helper function to handle the common logic for running a schedule.
    
    Args:
        schedule: The schedule to run
        
    Returns:
        Tuple containing:
            - List of zones to run with their durations
            - Boolean indicating if there are no zones scheduled (True = no zones)
            
    Raises:
        HTTPException: If system is already running
    """
    # Check if system is already running
    if system_status.active_zone:
        raise HTTPException(
            status_code=409,
            detail=f"System is already running zone {system_status.active_zone}"
        )
    
    # Get today's date in MMDDYY format
    today = datetime.now().strftime("%m%d%y")
    
    # Get zones scheduled for today
    zones = get_scheduled_zones(schedule["schedule_items"], today)
    
    return zones, not bool(zones)

@router.post("/schedule/{schedule_name}/run")
async def run_schedule(schedule_name: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Run a specific schedule immediately.

    This endpoint will start running the specified schedule's zones that are scheduled for today.
    Each zone will run for its configured duration. The zones will run in the background and
    this endpoint will return immediately with the list of zones that will be run.

    Parameters:
        schedule_name (str): Name of the schedule to run
        background_tasks: FastAPI background tasks handler

    Returns:
        Dict[str, Any]: Success message and list of zones that will be run

    Raises:
        HTTPException: If schedule is not found or if system is already running
    """
    try:
        # Get the schedule
        schedule = schedule_database.get_schedule(schedule_name)
        
        # Use helper to handle common schedule running logic
        zones, no_zones = await _run_schedule_helper(schedule)
        
        if no_zones:
            return {"message": "No zones scheduled for today", "zones": []}
        
        # Add the zone sequence execution to background tasks
        background_tasks.add_task(run_schedule_background, zones)
        
        return {
            "message": "Started running schedule",
            "zones": zones
        }
        
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to run schedule: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/active/run")
async def run_active_schedule(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Run the active schedule immediately.

    This endpoint will start running the active schedule's zones that are scheduled for today.
    Each zone will run for its configured duration. The zones will run in the background and
    this endpoint will return immediately with the list of zones that will be run.

    Parameters:
        background_tasks: FastAPI background tasks handler

    Returns:
        Dict[str, Any]: Success message and list of zones that will be run

    Raises:
        HTTPException: If no active schedule is set, if system is already running,
                      or if other errors occur
    """
    try:
        # Get the active schedule
        schedule = schedule_database.get_active_schedule()
        
        # Use helper to handle common schedule running logic
        zones, no_zones = await _run_schedule_helper(schedule)
        
        if no_zones:
            return {"message": "No zones scheduled for today", "zones": []}
        
        # Add the zone sequence execution to background tasks
        background_tasks.add_task(run_schedule_background, zones)
        
        return {
            "message": "Started running active schedule",
            "zones": zones
        }
        
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to run active schedule: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")
