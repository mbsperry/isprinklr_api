# Description: Router for managing sprinkler schedules
# Provides endpoints for creating, reading, updating, and deleting schedules
# as well as managing the active schedule and schedule automation

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException

from ..schemas import Schedule, ScheduleItem
from isprinklr.system_status import system_status, schedule_database
from isprinklr.scheduler_manager import run_schedule as manager_run_schedule

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
        logger.info(f"Successfully set active schedule to '{schedule_name}'")
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
        logger.info(f"Successfully created schedule '{schedule['schedule_name']}' with {len(schedule['schedule_items'])} items")
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
        logger.info(f"Successfully updated schedule '{schedule['schedule_name']}': {updated_schedule}")
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
        logger.info(f"Successfully deleted schedule '{schedule_name}'")
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
        logger.info(f"Successfully {'enabled' if schedule_on_off else 'disabled'} automated scheduling")
        return {"schedule_on_off": system_status.schedule_on_off}
    except Exception as exc:
        logger.error(f"Failed to update schedule on/off: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/schedule/{schedule_name}/run")
async def run_schedule(schedule_name: str) -> Dict[str, Any]:
    """Run a specific schedule immediately.

    This endpoint will start running the specified schedule's zones that are scheduled for today.
    Each zone will run for its configured duration. The zones will run in the background and
    this endpoint will return immediately with the list of zones that will be run.

    Parameters:
        schedule_name (str): Name of the schedule to run

    Returns:
        Dict[str, Any]: Success message and list of zones that will be run

    Raises:
        HTTPException: If schedule is not found or if system is already running
    """
    try:
        # Use the scheduler_manager to handle all schedule execution
        result = await manager_run_schedule(schedule_name)
        logger.info(f"Successfully started schedule '{schedule_name}'")
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to run schedule: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/active/run")
async def run_active_schedule() -> Dict[str, Any]:
    """Run the active schedule immediately.

    This endpoint will start running the active schedule's zones that are scheduled for today.
    Each zone will run for its configured duration. The zones will run in the background and
    this endpoint will return immediately with the list of zones that will be run.

    Returns:
        Dict[str, Any]: Success message and list of zones that will be run

    Raises:
        HTTPException: If no active schedule is set, if system is already running,
                      or if other errors occur
    """
    try:
        # Use the scheduler_manager to handle all schedule execution
        # Pass None to run the active schedule
        result = await manager_run_schedule()
        logger.info("Successfully started active schedule")
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to run active schedule: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")
