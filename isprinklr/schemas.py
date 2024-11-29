from typing_extensions import TypedDict
from pydantic import BaseModel
from typing import List

class SprinklerCommand(TypedDict):
    zone: int
    duration: int

class SprinklerConfig(TypedDict):
    zone: int
    name: str

class ScheduleItem(TypedDict):
    zone: int
    day: str
    duration: int

class Schedule(TypedDict):
    sched_id: int
    schedule_name: str
    schedule_items: List[ScheduleItem]

class ScheduleList(TypedDict):
    schedules: List[Schedule]
    active_schedule: int

class ScheduleOnOff(BaseModel):
    schedule_on_off: bool
