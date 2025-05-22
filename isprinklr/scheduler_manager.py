"""
Scheduler Manager for managing and automating sprinkler schedules

This module provides functionality for:
1. Running schedules manually or automatically
2. Handling schedule execution in the background
3. Automated schedule execution using APScheduler
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from asyncio import CancelledError, create_task

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from isprinklr.system_status import system_status, schedule_database
from isprinklr.schedule_util import get_scheduled_zones
from isprinklr.system_controller import system_controller

logger = logging.getLogger(__name__)

# Create the scheduler as a module-level singleton
scheduler = BackgroundScheduler()

# Default schedule execution time (6:00 AM)
DEFAULT_SCHEDULE_HOUR = 4
DEFAULT_SCHEDULE_MINUTE = 0

async def run_schedule_background(schedule_name: str, zones: List[Dict[str, int]]) -> None:
    """Background task to run a sequence of zones.
    
    Args:
        schedule_name: Name of the schedule being run
        zones: List of dictionaries containing zone and duration
    """
    try:
        await system_controller.run_zone_sequence(zones)
        system_status.last_schedule_run = {
            "name": schedule_name,
            "message": "Success"
        }
    except CancelledError:
        logger.info("Schedule cancelled")
        system_status.last_schedule_run = {
            "name": schedule_name,
            "message": "Cancelled"
        }
    except Exception as exc:
        logger.error(f"Error running schedule: {exc}")
        system_status.last_schedule_run = {
            "name": schedule_name,
            "message": f"Error: {str(exc)}"
        }

async def run_schedule_helper(schedule_name: str) -> Tuple[List[Dict[str, int]], bool]:
    """Helper function to prepare zones for running a schedule.
    
    Args:
        schedule_name: Name of the schedule to run
        
    Returns:
        Tuple containing:
            - List of zones to run with their durations
            - Boolean indicating if there are no zones scheduled (True = no zones)
            
    Raises:
        ValueError: If schedule is not found
        RuntimeError: If system is already running
    """
    # Check if system is already running
    if system_status.active_zone:
        raise RuntimeError(f"System is already running zone {system_status.active_zone}")
    
    # Get the schedule
    schedule = schedule_database.get_schedule(schedule_name)
    
    # Get today's date in MMDDYY format
    today = datetime.now().strftime("%m%d%y")
    
    # Get zones scheduled for today
    zones = get_scheduled_zones(schedule["schedule_items"], today)
    
    return zones, not bool(zones)

async def run_active_schedule_helper() -> Tuple[str, List[Dict[str, int]], bool]:
    """Helper function to prepare zones for running the active schedule.
    
    Returns:
        Tuple containing:
            - Name of the active schedule
            - List of zones to run with their durations
            - Boolean indicating if there are no zones scheduled (True = no zones)
            
    Raises:
        ValueError: If no active schedule is set
        RuntimeError: If system is already running
    """
    # Get the active schedule
    schedule = schedule_database.get_active_schedule()
    schedule_name = schedule["schedule_name"]
    
    zones, no_zones = await run_schedule_helper(schedule_name)
    return schedule_name, zones, no_zones

async def run_schedule(schedule_name: str = None) -> Dict[str, Any]:
    """Run a schedule by name, or the active schedule if no name is provided.
    
    This is the main entry point for running schedules, handling all the error
    checking and zone preparation. It returns information about the execution.
    
    Args:
        schedule_name: Name of the schedule to run, or None to use active schedule
    
    Returns:
        Dict with:
            - message: Descriptive message about what happened
            - zones: List of zones that will be run (may be empty)
    
    Raises:
        ValueError: If schedule is not found or no active schedule is set
        RuntimeError: If system is already running
    """
    try:
        # Determine which schedule to run
        if schedule_name is None:
            # Use active schedule
            name, zones, no_zones = await run_active_schedule_helper()
            using_active = True
        else:
            # Use the specified schedule
            zones, no_zones = await run_schedule_helper(schedule_name)
            name = schedule_name
            using_active = False
        
        # Check if there are zones to run
        if no_zones:
            return {
                "message": "No zones scheduled for today",
                "zones": []
            }
        
        # Start running the schedule in the background
        create_task(run_schedule_background(name, zones))
        
        # Return success message
        if using_active:
            return {
                "message": "Started running active schedule",
                "zones": zones
            }
        else:
            return {
                "message": "Started running schedule",
                "zones": zones
            }
        
    except ValueError as e:
        # Re-raise with more specific message
        if schedule_name is None:
            raise ValueError("No active schedule set") from e
        else:
            raise ValueError(f"Schedule '{schedule_name}' not found") from e
    except RuntimeError as e:
        # System is already running
        raise

def automated_schedule_runner():
    """
    Minimal wrapper for run_schedule that:
    1. Checks if scheduling is enabled
    2. Handles APScheduler's need for a non-async function
    3. Handles errors appropriately for an automated context
    """
    logger.info("Automated scheduled job triggered")
    
    # Only run if scheduling is enabled
    if not system_status.schedule_on_off:
        logger.info("Scheduled job triggered but scheduling is disabled")
        return
    
    try:
        # Submit the async function to the event loop from our background thread
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(run_schedule(), loop)
        logger.info("Successfully scheduled sprinkler task")
    except Exception as e:
        logger.error(f"Error running automated schedule: {e}")


def setup_scheduler(hour: int = DEFAULT_SCHEDULE_HOUR, minute: int = DEFAULT_SCHEDULE_MINUTE):
    """
    Set up the APScheduler with a daily job to run the active schedule.
    
    Args:
        hour (int): Hour of day to run the schedule (24-hour format, default: 6)
        minute (int): Minute of hour to run the schedule (default: 0)
    """
    logger.info(f"Setting up scheduler to run daily at {hour:02d}:{minute:02d}")
    
    # Remove any existing jobs first (in case we're reconfiguring)
    scheduler.remove_all_jobs()
    
    # Add a job to run at the specified time daily
    scheduler.add_job(
        automated_schedule_runner,
        CronTrigger(hour=hour, minute=minute),
        id='daily_schedule_job',
        replace_existing=True,
        name='Run Daily Sprinkler Schedule'
    )
    
    # Start the scheduler if not already running
    if not scheduler.running:
        logger.info("Starting scheduler")
        scheduler.start()
    else:
        logger.info("Scheduler already running")


def update_scheduler_config(config: Dict[str, Any]) -> bool:
    """
    Update the scheduler configuration based on updated API settings.
    
    Args:
        config (Dict[str, Any]): API configuration dictionary
    
    Returns:
        bool: True if configuration was updated successfully
    """
    # Get schedule timing directly from SystemStatus
    # This ensures we're using the validated values that have already been applied
    hour = system_status.schedule_hour
    minute = system_status.schedule_minute
    
    # Reconfigure the scheduler
    setup_scheduler(hour, minute)
    return True


def shutdown_scheduler():
    """Shut down the scheduler"""
    if scheduler.running:
        logger.info("Shutting down scheduler")
        scheduler.shutdown()
    else:
        logger.info("Scheduler not running, no need to shut down")
