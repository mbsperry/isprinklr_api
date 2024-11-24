from typing_extensions import TypedDict
from pydantic import BaseModel

class Sprinkler(TypedDict):
    zone: int
    duration: int

class SprinklerConfig(TypedDict):
    zone: int
    name: str

class ScheduleItem(TypedDict):
    zone: int
    day: str
    duration: int

class ScheduleOnOff(BaseModel):
    schedule_on_off: bool
