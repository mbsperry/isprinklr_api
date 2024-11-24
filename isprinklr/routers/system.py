from fastapi import APIRouter

from ..system import system_status

router = APIRouter(
    prefix="/api/system",
    tags=["system"]
)

@router.get("/status")
async def get_system_status():
    """
    Get the current system status including hardware connectivity check.
    
    The endpoint performs a hardware connectivity check and returns the current
    system state, any active zones, and relevant status messages.
    
    Returns:
        dict: System status containing:
            - systemStatus (str): Current state (inactive, active, error)
            - message (str | None): Optional status message describing error states
            - active_zone (int | None): Currently active sprinkler zone
            - duration (int): Duration in minutes for active zone, 0 if inactive
            
    Raises:
        HTTPException: If hardware communication fails
    """
    return system_status.get_status()
