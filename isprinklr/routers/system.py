import logging
from fastapi import APIRouter, HTTPException

from isprinklr.system_status import system_status
from isprinklr.system_controller import system_controller
from isprinklr.schemas import ApiConfig

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
        dict: The current API configuration with the following fields:
            - ESP_controller_IP (str): IP address of ESP controller
            - domain (str): Domain address for the API server
            - dummy_mode (bool): Whether to run in dummy mode
            - schedule_on_off (bool): Whether schedules are enabled
            - log_level (str): Logging level
            - USE_STRICT_CORS (bool): Whether to use strict CORS settings
        
    Raises:
        HTTPException: If the configuration cannot be retrieved
    """
    try:
        return system_status.get_api_config()
    except Exception as exc:
        logger.error(f"Failed to get API configuration: {exc}")
        raise HTTPException(status_code=500, detail="Failed to get API configuration, see logs for details")

@router.put("/config")
async def update_config(config: ApiConfig):
    """Update the API configuration
    
    Args:
        config (ApiConfig): The new API configuration with the following fields:
            - ESP_controller_IP (str): IP address of ESP controller
            - domain (str): Domain address for the API server
            - dummy_mode (bool): Whether to run in dummy mode
            - schedule_on_off (bool): Whether schedules are enabled
            - log_level (str): Logging level
            - USE_STRICT_CORS (bool): Whether to use strict CORS settings
        
    Returns:
        dict: The updated API configuration
        
    Notes:
        Changes to domain and USE_STRICT_CORS will be
        saved to the configuration file but will not take effect
        until the API is restarted.
        
    Raises:
        HTTPException: If the configuration cannot be updated
    """
    try:
        # Convert the Pydantic model to a dict - the validators will have already run
        config_dict = config.model_dump()
        
        updated_config = system_status.update_api_config(config_dict)
        
        # Return the updated configuration
        return updated_config
    except ValueError as exc:
        # This captures validation errors from Pydantic
        logger.error(f"Validation error in API configuration: {exc}")
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(exc)}")
    except Exception as exc:
        logger.error(f"Failed to update API configuration: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to update API configuration: {str(exc)}")
