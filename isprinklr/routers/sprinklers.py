import logging
from fastapi import APIRouter, HTTPException
from typing import List

from isprinklr.system_status import system_status
from isprinklr.system_controller import system_controller
from ..schemas import SprinklerCommand, SprinklerConfig

router = APIRouter(
    prefix="/api/sprinklers",
    tags=["sprinklers"]
)

logger = logging.getLogger(__name__)

@router.get("/")
async def get_sprinklers():
    """Get all configured sprinkler zones and their names.

Returns:
* List[SprinklerConfig]: A list of sprinkler configurations containing zone numbers and names

Raises:
* HTTPException: If sprinkler data cannot be loaded
    """
    if not system_status.sprinklers:
        raise HTTPException(status_code=500, detail="Failed to load sprinklers data, see logs for details")
    return system_status.sprinklers

@router.put("/")
async def update_sprinklers(sprinklers: List[SprinklerConfig]):
    """Update the configuration of multiple sprinkler zones.

Parameters:
* sprinklers (List[SprinklerConfig]): List of sprinkler configurations to update
  * zone (int): Zone number
  * name (str): Zone name

Returns:
* Dictionary containing:
  * message: Success message
  * zones: Updated sprinkler configurations

Raises:
* HTTPException: If the update fails due to invalid data or server error
    """
    try:
        new_sprinklers = system_status.update_sprinklers(sprinklers)
        return {"message": "Success", "zones": new_sprinklers}
    except ValueError as exc:
        logger.error(f"Failed to update sprinklers, invalid data: {exc}")
        raise HTTPException(status_code=400, detail=f"Failed to update sprinklers, invalid data: {str(exc)}")
    except Exception as exc:
        logger.error(f"Failed to update sprinklers: {exc}")
        raise HTTPException(status_code=500, detail="Failed to update sprinklers, see logs for details")

@router.post("/start")
async def start_sprinkler(sprinkler: SprinklerCommand):
    """Start a specific sprinkler zone for a given duration.

Parameters:
* sprinkler (SprinklerCommand): Command containing:
  * zone (int): Zone number to start
  * duration (int): Duration in seconds

Returns:
* Dictionary containing success message confirming the zone was started

Raises:
* HTTPException:
  * 400: If zone number is invalid or not found
  * 409: If system is already running another zone
  * 503: If hardware communication fails
  * 500: For other unexpected errors
    """
    logger.debug(f'Received: {sprinkler}')
    try:
        await system_controller.start_sprinkler(sprinkler)
        return {"message": f"Zone {sprinkler['zone']} started"}
    except ValueError as exc:
        logger.error(f"Failed to start sprinkler: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except IOError as exc:
        logger.error(f"Hardware communication error: {exc}")
        raise HTTPException(status_code=503, detail=f"Hardware communication error: {str(exc)}")
    except Exception as exc:
        if "system already active" in str(exc).lower():
            logger.error(f"System busy: {exc}")
            raise HTTPException(status_code=409, detail=str(exc))
        logger.error(f"Unexpected error starting sprinkler: {exc}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(exc)}")

@router.post("/stop")
async def stop_system():
    """Stop all running sprinkler zones.

Returns:
* Dictionary containing success message confirming the system was stopped

Raises:
* HTTPException: If the system cannot be stopped due to an error
    """
    try:
        await system_controller.stop_system()
        return {"message": "System stopped"}
    except Exception as exc:
        logger.error(f"Failed to stop system: {exc}")
        raise HTTPException(status_code=500, detail="Failed to stop system, see logs for details")
