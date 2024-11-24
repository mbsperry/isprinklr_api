import json, logging, asyncio, time
from dataclasses import dataclass, field
from typing import Any, Optional, List
from fastapi import BackgroundTasks

from .paths import config_path, data_path

import isprinklr.sprinkler_service as sprinkler_service
import isprinklr.sprinklr_serial as hunterserial
from .schedule_service import ScheduleService
from .schemas import ScheduleItem, SprinklerCommand, SprinklerConfig

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

# TODO: Add error handling for initialization of SystemStatus

class SystemStatus:
    def __init__(self):
        self._status: str = "inactive"
        self._status_message: Optional[str] = None
        self._active_zone: Optional[int] = None
        self._end_time: Optional[float] = None
        self._sprinklers: List[SprinklerConfig] = sprinkler_service.read_sprinklers(data_path)
        self._schedule_service: Any = ScheduleService(self._sprinklers)
        self._schedule_on_off: bool = SCHEDULE_ON_OFF
        self._last_run: Optional[int] = None
        self._last_schedule_run: Optional[int] = None
        self._timer_task: Optional[asyncio.Task] = None

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

    # Duration is now in seconds
    async def _zone_timer(self, duration: int):
        try:
            await asyncio.sleep(duration)  # Duration is already in seconds
            # Stop the zone when timer completes
            await self.stop_system()
        except asyncio.CancelledError:
            logger.debug("Zone timer cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in zone timer: {e}")
            self._update_status("error", str(e), None)
            raise
    
    def _update_status(self, status: str, message: Optional[str] = None, active_zone: Optional[int] = None, duration: Optional[int] = None):
        self._status = status
        self._status_message = message
        self._active_zone = active_zone
        self._end_time = time.time() + duration if status == "active" and duration is not None else None

    def check_hunter_connection(self) -> bool:
        try:
            if (hunterserial.test_awake()):
                logger.debug('Arduino connected')
                # If the system was previously in an error state, clear the status message
                if self._status == "error":
                    self._update_status("inactive", None, None)
                return True
            else:
                logger.error('Arduino not responding')
                self._update_status("error", "Arduino not responding", None)
                raise Exception("I/O: Arduino not responding")
        except Exception as exc:
            logger.error(f"Caught error {str(exc)}")
            self._update_status("error", "Serial Port error", None)
            raise

    def get_status(self) -> dict:
        # No need to handle exception here, let the caller handle it
        self.check_hunter_connection()

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

    def get_sprinklers(self) -> List[SprinklerConfig]:
        return self._sprinklers
    
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
    
    async def start_sprinkler(self, sprinkler: SprinklerCommand) -> bool:
        """Start a sprinkler for a specified duration.
        
        Args:
            sprinkler: SprinklerCommand object containing zone number and duration (in seconds)
            
        Returns:
            True if the sprinkler was started successfully
            
        Raises:
            ValueError: If the zone number is not found in configured sprinklers
            IOError: If there's a communication error with the hardware
            Exception: If the system is already running a sprinkler
        """
        # No need to handle exception here, let the caller handle it
        self.check_hunter_connection()
        if not any(s['zone'] == sprinkler['zone'] for s in self._sprinklers):
            raise ValueError(f"Zone {sprinkler['zone']} not found")

        if not self._active_zone:
            try:
                # Convert seconds to minutes for the hardware interface
                duration_minutes = int(sprinkler['duration'] // 60)
                if (hunterserial.start_zone(sprinkler['zone'], duration_minutes)):
                    logger.debug(f"Started zone {sprinkler['zone']} for {sprinkler['duration']} seconds: success")
                    self._update_status("active", None, sprinkler['zone'], sprinkler['duration'])
                    
                    
                    # Create and start new timer task
                    self._timer_task = asyncio.create_task(self._zone_timer(sprinkler['duration']))
                    return True
                else:
                    logger.error(f"Started zone {sprinkler['zone']} for {sprinkler['duration']} seconds: failed")
                    self._update_status("error", "Command Failed", None)
                    # raise an IOError
                    raise IOError("Command Failed")
            except IOError as exc:
                self._update_status("error", "Serial Port error", None)
                raise
        else:
            logger.error(f"Failed to start zone {sprinkler['zone']}, system already active")
            raise Exception(f"Failed to start zone {sprinkler['zone']}, system already active. Active zone: {self._active_zone}")
    
    async def stop_system(self) -> bool:
        """Stop the currently running sprinkler and deactivate the system.
        
        Returns:
            True if the system was stopped successfully
            
        Raises:
            IOError: If there's a communication error with the hardware
            Exception: If the system is not currently active
        """
        # No need to handle exception here, let the caller handle it
        self.check_hunter_connection()
        if self._active_zone:
            try:
                if (hunterserial.stop_zone(self._active_zone)):
                    logger.debug(f"Stopped zone {self._active_zone}")
                    # Cancel any running timer
                    if self._timer_task and not self._timer_task.done():
                        self._timer_task.cancel()
                        try:
                            await self._timer_task
                        except asyncio.CancelledError:
                            logger.debug("Zone timer cancellation confirmed")
                            pass
                    self._timer_task = None
                    self._update_status("inactive", None, None)
                    return True
                else:
                    logger.error(f"Failed to stop zone {self._active_zone}")
                    raise IOError("Command Failed")
            except IOError as exc:
                self._update_status("error", "Serial Port error", None)
                raise
        else:
            logger.error("Failed to stop zone, system is not active")
            raise Exception("Failed to stop zone, system is not active")
        
    def get_schedule(self) -> list:
        return self._schedule_service.schedule
    
    def update_schedule(self, schedule: list[ScheduleItem]):
        return self._schedule_service.update_schedule(schedule)

    async def run_zone_sequence(self, zone_sequence: list[list]) -> bool:
        """Run a sequence of zones for specified durations.
        
        Args:
            zone_sequence: List of [zone, duration] pairs to run sequentially (duration in seconds)
            
        Returns:
            True if all zones completed successfully, False otherwise
        """
        try:
            for zone, duration in zone_sequence:
                logger.debug(f"Starting zone {zone} for {duration} seconds")
                sprinkler = {"zone": zone, "duration": duration}
                await self.start_sprinkler(sprinkler)
                await asyncio.sleep(duration)  # Duration already in seconds
                try:
                    await self.stop_system()
                except Exception as e:
                    logger.error(f"Error running zone sequence: {e}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error running zone sequence: {e}")
            return False

system_status = SystemStatus()
