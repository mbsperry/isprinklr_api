import logging, asyncio
from typing import Optional

import isprinklr.sprinklr_serial as hunterserial
from .schemas import SprinklerCommand
from . import system_status

logger = logging.getLogger(__name__)

class SystemController:
    def __init__(self):
        self._timer_task: Optional[asyncio.Task] = None

    async def _zone_timer(self, duration: int):
        try:
            await asyncio.sleep(duration)
            await self.stop_system()
        except asyncio.CancelledError:
            logger.debug("Zone timer cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in zone timer: {e}")
            system_status.update_status("error", str(e), None)
            raise

    def check_hunter_connection(self) -> bool:
        """Check if the Hunter controller hardware is responding.
        
        Returns:
            bool: True if connected, raises exception otherwise
            
        Raises:
            Exception: If hardware is not responding or serial error occurs
        """
        try:
            if (hunterserial.test_awake()):
                logger.debug('Arduino connected')
                # If the system was previously in an error state, clear the status message
                if system_status.get_status()["systemStatus"] == "error":
                    system_status.update_status("inactive", None, None)
                return True
            else:
                logger.error('Arduino not responding')
                system_status.update_status("error", "Arduino not responding", None)
                raise Exception("I/O: Arduino not responding")
        except Exception as exc:
            logger.error(f"Caught error {str(exc)}")
            system_status.update_status("error", "Serial Port error", None)
            raise

    async def start_sprinkler(self, sprinkler: SprinklerCommand) -> bool:
        """Start a sprinkler for a specified duration.
        
        Args:
            sprinkler: SprinklerCommand object containing zone number and duration (in seconds)
            
        Returns:
            True if the sprinkler was started successfully
            
        Raises:
            ValueError: If zone not found
            IOError: If hardware communication fails
            Exception: If system already active
        """
        self.check_hunter_connection()
        if not any(s['zone'] == sprinkler['zone'] for s in system_status.sprinklers):
            raise ValueError(f"Zone {sprinkler['zone']} not found")

        if not system_status.active_zone:
            try:
                # Convert seconds to minutes for the hardware interface
                duration_minutes = int(sprinkler['duration'] // 60)
                if (hunterserial.start_zone(sprinkler['zone'], duration_minutes)):
                    logger.debug(f"Started zone {sprinkler['zone']} for {sprinkler['duration']} seconds: success")
                    system_status.update_status("active", None, sprinkler['zone'], sprinkler['duration'])
                    
                    # Create and start new timer task
                    self._timer_task = asyncio.create_task(self._zone_timer(sprinkler['duration']))
                    return True
                else:
                    logger.error(f"Started zone {sprinkler['zone']} for {sprinkler['duration']} seconds: failed")
                    system_status.update_status("error", "Command Failed", None)
                    raise IOError("Command Failed")
            except IOError as exc:
                system_status.update_status("error", "Serial Port error", None)
                raise
        else:
            logger.error(f"Failed to start zone {sprinkler['zone']}, system already active")
            raise Exception(f"Failed to start zone {sprinkler['zone']}, system already active. Active zone: {system_status.active_zone}")

    async def stop_system(self) -> bool:
        """Stop the currently running sprinkler.
        
        Returns:
            True if the system was stopped successfully
            
        Raises:
            IOError: If hardware communication fails
            Exception: If system not active
        """
        self.check_hunter_connection()
        if system_status.active_zone:
            try:
                if (hunterserial.stop_zone(system_status.active_zone)):
                    logger.debug(f"Stopped zone {system_status.active_zone}")
                    # Cancel any running timer
                    if self._timer_task and not self._timer_task.done():
                        self._timer_task.cancel()
                        try:
                            await self._timer_task
                        except asyncio.CancelledError:
                            logger.debug("Zone timer cancellation confirmed")
                            pass
                    self._timer_task = None
                    system_status.update_status("inactive", None, None)
                    return True
                else:
                    logger.error(f"Failed to stop zone {system_status.active_zone}")
                    system_status.update_status("error", "Command Failed", None)
                    raise IOError("Command Failed")
            except IOError as exc:
                system_status.update_status("error", "Serial Port error", None)
                raise
        else:
            logger.error("Failed to stop zone, system is not active")
            raise Exception("Failed to stop zone, system is not active")

    async def run_zone_sequence(self, zone_sequence: list[list]) -> bool:
        """Run a sequence of zones for specified durations.
        
        Args:
            zone_sequence: List of [zone, duration] pairs to run sequentially
            
        Returns:
            True if all zones completed successfully
        """
        try:
            for zone, duration in zone_sequence:
                logger.debug(f"Starting zone {zone} for {duration} seconds")
                sprinkler = {"zone": zone, "duration": duration}
                await self.start_sprinkler(sprinkler)
                await asyncio.sleep(duration)
                try:
                    await self.stop_system()
                except Exception as e:
                    logger.error(f"Error running zone sequence: {e}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error running zone sequence: {e}")
            return False

system_controller = SystemController()
