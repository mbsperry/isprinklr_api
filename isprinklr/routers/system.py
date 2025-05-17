import logging
import json
from fastapi import APIRouter, HTTPException

from isprinklr.system_status import system_status
from isprinklr.system_controller import system_controller
from isprinklr.schemas import ApiConfig
from isprinklr.paths import config_path

router = APIRouter(
    prefix="/api/system",
    tags=["system"]
)

logger = logging.getLogger(__name__)

@router.get("/last-sprinkler-run")
async def get_last_sprinkler_run():
    """Get information about the last manually run zone.

Returns:
* Dictionary containing:
  * zone (int): The zone number that was run
  * timestamp (float): Unix timestamp when the zone was run
  Or None if no zone has been run

Raises:
* HTTPException: If the last zone run status cannot be retrieved
    """
    try:
        return system_status.last_zone_run
    except Exception as exc:
        logger.error(f"Failed to get last zone run status: {exc}")
        raise HTTPException(status_code=500, detail="Failed to get last zone run status, see logs for details")

@router.get("/last-schedule-run") 
async def get_last_schedule_run():
    """Get information about the last schedule that was run.

Returns:
* Dictionary containing:
  * name (str): Name of the schedule that was run
  * timestamp (float): Unix timestamp when schedule was run
  * message (str): Status message (success, failure, canceled)
  Or None if no schedule has been run

Raises:
* HTTPException: If the last schedule run status cannot be retrieved
    """
    try:
        return system_status.last_schedule_run
    except Exception as exc:
        logger.error(f"Failed to get last schedule run status: {exc}")
        raise HTTPException(status_code=500, detail="Failed to get last schedule run status, see logs for details")

def get_api_config():
    """Read the current API configuration from api.conf
    
    Returns:
        dict: The current API configuration
        
    Raises:
        Exception: If the configuration file cannot be read
    """
    try:
        with open(f"{config_path}/api.conf", "r") as f:
            return json.load(f)
    except Exception as exc:
        logger.error(f"Failed to read API configuration: {exc}")
        raise Exception(f"Failed to read API configuration: {exc}")

def update_api_config(config: dict):
    """Update the API configuration in api.conf
    
    Args:
        config (dict): The new API configuration
        
    Returns:
        dict: The updated API configuration
        
    Raises:
        Exception: If the configuration file cannot be written
    """
    try:
        with open(f"{config_path}/api.conf", "w") as f:
            json.dump(config, f)
        return config
    except Exception as exc:
        logger.error(f"Failed to write API configuration: {exc}")
        raise Exception(f"Failed to write API configuration: {exc}")

@router.get("/status")
async def get_status():
    """Get the current system status including hardware connectivity check, active zones, and ESP32 controller details.

Returns:
* Dictionary containing:
  * systemStatus (str): Current system status ("active", "inactive", "error")
  * message (str | None): Status message or error description
  * active_zone (int | None): Currently active sprinkler zone
  * duration (int): Remaining duration in seconds for active zone, 0 if inactive
  * esp_status (dict | None): Detailed ESP32 controller status if available, containing:
    * status (str): Status of the ESP controller ("ok" or error state)
    * uptime_ms (int): Controller uptime in milliseconds
    * chip (dict): Chip information including model, revision, cores
    * memory (dict): Memory usage information including free heap space
    * network (dict): Network configuration including IP, connection type, MAC
    * reset_reason (str): Last reset reason
    * idf_version (str): ESP-IDF version
    * task (dict): Task-related information

Raises:
* HTTPException: If the system status cannot be retrieved
    """
    try:
        # Check hardware connection first
        system_controller.check_hunter_connection()
        # Then return current system status
        return system_status.get_status()
    except Exception as exc:
        logger.error(f"Failed to get system status: {exc}")
        raise HTTPException(status_code=500, detail="Failed to get system status, see logs for details")

@router.get("/config")
async def get_config():
    """Get the current API configuration
    
    Returns:
        dict: The current API configuration
        
    Raises:
        HTTPException: If the configuration cannot be retrieved
    """
    try:
        return get_api_config()
    except Exception as exc:
        logger.error(f"Failed to get API configuration: {exc}")
        raise HTTPException(status_code=500, detail="Failed to get API configuration, see logs for details")

@router.put("/config")
async def update_config(config: ApiConfig):
    """Update the API configuration
    
    Args:
        config (ApiConfig): The new API configuration
        
    Returns:
        dict: The updated API configuration
        
    Raises:
        HTTPException: If the configuration cannot be updated
    """
    try:
        # Convert the Pydantic model to a dict - the validators will have already run
        config_dict = config.model_dump()
        
        # Update the configuration
        updated_config = update_api_config(config_dict)
        
        # Update system status with new settings if applicable
        if 'schedule_on_off' in config_dict:
            schedule_on_off = config_dict['schedule_on_off'].lower() == "true"
            system_status.schedule_on_off = schedule_on_off
            logger.debug(f"Updated schedule_on_off to {schedule_on_off}")
        
        # Return the updated configuration
        return updated_config
    except ValueError as exc:
        # This captures validation errors from Pydantic
        logger.error(f"Validation error in API configuration: {exc}")
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(exc)}")
    except Exception as exc:
        logger.error(f"Failed to update API configuration: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to update API configuration: {str(exc)}")
