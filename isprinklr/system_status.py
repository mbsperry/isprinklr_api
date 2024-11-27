import json, logging, time
from typing import Any, Optional, List

from .paths import config_path, data_path
import isprinklr.sprinkler_service as sprinkler_service
from .schedule_service import ScheduleService
from .schemas import ScheduleItem, SprinklerConfig

logger = logging.getLogger(__name__)

try:
    with open(config_path + "/api.conf", "r") as f:
        config = json.load(f)
        DOMAIN = config["domain"]
        SCHEDULE_ON_OFF=config.get("schedule_on_off", False) 
        if not isinstance(SCHEDULE_ON_OFF, bool):
            SCHEDULE_ON_OFF = SCHEDULE_ON_OFF.lower() in ["true", "yes", "on"]
        LOG_LEVEL=config.get("log_level", "ERROR")
        logger.setLevel(getattr(logging, LOG_LEVEL, "ERROR"))
        logger.debug("Starting API")
        logger.debug(f"Run schedule is set to: {SCHEDULE_ON_OFF}")
        logger.debug(f"Log level set to {LOG_LEVEL}")
except Exception as e:
    logger.critical(f"Failed to load api.conf: {e}")

class SystemStatus:
    def __init__(self):
        self._status: str = "inactive"
        self._status_message: Optional[str] = None
        self._active_zone: Optional[int] = None
        self._end_time: Optional[float] = None
        self._sprinklers: List[SprinklerConfig] = sprinkler_service.read_sprinklers(data_path)
        self._schedule_service: Any = ScheduleService(self._sprinklers)
        self._schedule_on_off: bool = False  # Initialize to False
        self._last_run: Optional[int] = None
        self._last_schedule_run: Optional[int] = None

    @property
    def last_run(self) -> Optional[int]:
        return self._last_run
    
    @property
    def last_schedule_run(self) -> Optional[int]:
        return self._last_schedule_run
    
    @property
    def schedule_on_off(self) -> bool:
        return self._schedule_on_off
    
    @schedule_on_off.setter
    def schedule_on_off(self, value: bool):
        self._schedule_on_off = value

    @property
    def active_zone(self) -> Optional[int]:
        return self._active_zone

    @property
    def sprinklers(self) -> List[SprinklerConfig]:
        return self._sprinklers

    @property
    def schedule(self) -> list:
        """Get the current schedule.
        
        Returns:
            list: Current schedule
        """
        return self._schedule_service.schedule

    def update_schedule(self, schedule: list[ScheduleItem]):
        """Update the schedule.
        
        Args:
            schedule: New schedule to set
            
        Returns:
            Updated schedule
        """
        return self._schedule_service.update_schedule(schedule)
    
    def update_status(self, status: str, message: Optional[str] = None, active_zone: Optional[int] = None, duration: Optional[int] = None):
        self._status = status
        self._status_message = message
        self._active_zone = active_zone
        self._end_time = time.time() + duration if status == "active" and duration is not None else None

    def get_status(self) -> dict:
        duration = 0
        if self._status == "active" and self._end_time is not None:
            duration = int(max(0, self._end_time - time.time()))

        logger.debug(f"System status: {self._status}, message: {self._status_message}, active zone: {self._active_zone}, duration: {duration}")
        return {
            "systemStatus": self._status,
            "message": self._status_message,
            "active_zone": self._active_zone,
            "duration": duration
        }
    
    def update_sprinklers(self, sprinklers: List[SprinklerConfig]) -> List[SprinklerConfig]:
        """Updates the sprinkler configurations.
        
        Args:
            sprinklers: List of SprinklerConfig objects containing zone number and name
            
        Returns:
            The updated list of sprinkler configurations
            
        Raises:
            ValueError: If validation fails (empty list, >12 sprinklers, duplicate zones/names)
            Exception: If writing to storage fails
        """
        try:
            sprinkler_service.write_sprinklers(data_path, sprinklers)
            self._sprinklers = sprinklers
            return sprinklers
        except Exception as e:
            logger.error(f"Failed to write sprinklers data: {e}")
            raise

# Create singleton instance
system_status = SystemStatus()
