import time, logging
import requests
from fastapi import APIRouter, HTTPException

from ..system import system_status
from ..schemas import Sprinkler, SprinklerConfig

router = APIRouter(
    prefix = "/api/sprinklers",
    tags = ["sprinklers"]
)

logger = logging.getLogger(__name__)

@router.get("/")
async def get_sprinklers():
    if not system_status.get_sprinklers():
        raise HTTPException(status_code=500, detail="Failed to load sprinklers data, see logs for details")
    return system_status.get_sprinklers()

@router.put("/")
async def update_sprinklers(sprinklers: list[SprinklerConfig]):
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
async def start_sprinkler(sprinkler: Sprinkler):
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
    try:
        system_status.stop_system()
        return {"message": "System stopped"}
    except Exception as exc:
        logger.error(f"Failed to stop system: {exc}")
        raise HTTPException(status_code=500, detail="Failed to stop system, see logs for details")
