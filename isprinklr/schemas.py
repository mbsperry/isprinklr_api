from typing_extensions import TypedDict
from pydantic import BaseModel, Field, field_validator, IPvAnyAddress
from typing import List, Optional, ClassVar

class ApiConfig(BaseModel):
    ESP_controller_IP: str = Field(..., description="IP address of ESP controller")
    domain: str = Field(..., description="Domain address for the API server")
    dummy_mode: bool = Field(..., description="Whether to run in dummy mode")
    schedule_on_off: bool = Field(..., description="Whether schedules are enabled")
    log_level: str = Field(..., description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    USE_STRICT_CORS: bool = Field(..., description="Whether to use strict CORS settings")
    
    @field_validator('ESP_controller_IP')
    @classmethod
    def validate_ip(cls, v):
        try:
            # This will validate the IP format
            IPvAnyAddress(v)
            return v
        except:
            raise ValueError('Invalid IP address format')
    
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'WARN', 'ERROR', 'CRITICAL', 'FATAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {", ".join(valid_levels)}')
        return v.upper()  # Convert to uppercase for consistency

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
    schedule_name: str
    schedule_items: List[ScheduleItem]

class ScheduleList(TypedDict):
    schedules: List[Schedule]
    active_schedule: Optional[str]

class ScheduleOnOff(BaseModel):
    schedule_on_off: bool
