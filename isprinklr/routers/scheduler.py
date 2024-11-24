# Description: reads from a .csv file and starts sprinklers based on the schedule
# The program is run every morning at 4am by a cron job
# Needs to open the csv file and determine which sprinklers need to be run that day and for how long.
# Then it needs to start the sprinklers using the API defined in api.py and wait for them to finish.

import time, logging
import requests
from typing import Annotated
from fastapi import APIRouter, HTTPException

from ..schemas import ScheduleItem
from ..system import system_status

logger = logging.getLogger(__name__)

API_URL = "http://localhost:8080/api/"

day_abbr = {
        0: "Su",
        1: "M",
        2: "Tu",
        3: "W",
        4: "Th",
        5: "F",
        6: "Sa"
        }


router = APIRouter(
    prefix = "/api/scheduler",
    tags = ["scheduler"]
)

@router.get("/schedule")
async def get_schedule():
    return system_status.get_schedule()

@router.get("/on_off")
async def get_schedule_on_off():
    return {"schedule_on_off": system_status.schedule_on_off}

@router.put("/on_off")
async def update_schedule_on_off(schedule_on_off: bool):
    try:
        system_status.schedule_on_off = schedule_on_off
        return {"schedule_on_off": system_status.schedule_on_off}
    except Exception as exc:
        logger.error(f"Failed to update schedule on/off: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/schedule")
async def update_schedule(schedule: list[ScheduleItem]):
    try:
        system_status.update_schedule(schedule)
        return {"message": "Success", "schedule": system_status.get_schedule()}
    except ValueError as exc:
        logger.error(f"Failed to update schedule: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to update schedule: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")