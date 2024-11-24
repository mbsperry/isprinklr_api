from fastapi import APIRouter

from ..system import system_status

router = APIRouter(prefix="/api/system", tags=["system"])

@router.get("/status")
async def get_system_status():
    global system_status
    return system_status.get_status()