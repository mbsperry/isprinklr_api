import logging
from fastapi import APIRouter, HTTPException

from ..system import system_status

router = APIRouter(
    prefix="/api/system",
    tags=["system"]
)

logger = logging.getLogger(__name__)

@router.get("/status")
async def get_status():
    """Get the current system status including hardware connectivity check, active zones, remaining duration.

Returns:
* Dictionary containing:
  * systemStatus (str): Current system status ("active", "inactive", "error")
  * message (str | None): Status message or error description
  * active_zone (int | None): Currently active sprinkler zone
  * duration (int): Remaining duration in seconds for active zone, 0 if inactive

Raises:
* HTTPException: If the system status cannot be retrieved
    """
    try:
        return system_status.get_status()
    except Exception as exc:
        logger.error(f"Failed to get system status: {exc}")
        raise HTTPException(status_code=500, detail="Failed to get system status, see logs for details")
