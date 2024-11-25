import time, logging
import requests
from fastapi import APIRouter, HTTPException
from typing import List

from ..system import system_status
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
    if not system_status.get_sprinklers():
        raise HTTPException(status_code=500, detail="Failed to load sprinklers data, see logs for details")
    return system_status.get_sprinklers()

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
* HTTPException: If the sprinkler cannot be started due to invalid parameters or system error
    """
    logger.debug(f'Received: {sprinkler}')
    try:
        await system_status.start_sprinkler(sprinkler)
        return {"message": f"Zone {sprinkler['zone']} started"}
    except ValueError as exc:
        logger.error(f"Failed to start sprinkler: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to start sprinkler: {exc}")
        raise HTTPException(status_code=500, detail="Failed to start sprinkler, see logs for details")

@router.post("/stop")
async def stop_system():
    """Stop all running sprinkler zones.

Returns:
* Dictionary containing success message confirming the system was stopped

Raises:
* HTTPException: If the system cannot be stopped due to an error
    """
    try:
        await system_status.stop_system()
        return {"message": "System stopped"}
    except Exception as exc:
        logger.error(f"Failed to stop system: {exc}")
        raise HTTPException(status_code=500, detail="Failed to stop system, see logs for details")
