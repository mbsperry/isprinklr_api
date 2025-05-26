import logging, asyncio
from typing import Optional, List, Dict

import isprinklr.esp_controller as esp_controller
from .schemas import SprinklerCommand
from isprinklr.system_status import system_status

logger = logging.getLogger(__name__)

class SystemController:
    def __init__(self):
        self._timer_task: Optional[asyncio.Task] = None
        self._sequence_task: Optional[asyncio.Task] = None
        self._in_sequence: bool = False  # Flag to track if we're in a sequence

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
            # No raise here to avoid unhandled exceptions in tasks

    def check_hunter_connection(self) -> bool:
        """Check if the ESP controller hardware is responding.
        
        Returns:
            bool: True if connected, raises exception otherwise
            
        Raises:
            Exception: If hardware is not responding or connection error occurs
        """
        try:
            # test_awake now returns the full status data in normal mode, 
            # or a minimal status dict in dummy mode
            status_data = esp_controller.test_awake()
            
            # Store the status data in the system_status object
            system_status.esp_status_data = status_data
            
            logger.debug('ESP controller connected')
            logger.debug(f'ESP status data: {status_data}')
            
            # If the system was previously in an error state, clear the status message
            if system_status.get_status()["systemStatus"] == "error":
                system_status.update_status("inactive", None, None)
            return True
        except Exception as exc:
            logger.error(f"Caught error {str(exc)}")
            system_status.update_status("error", "ESP Controller error", None)
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
                if (esp_controller.start_zone(sprinkler['zone'], duration_minutes)):
                    logger.debug(f"Started zone {sprinkler['zone']} for {sprinkler['duration']} seconds: success")
                    system_status.update_status("active", None, sprinkler['zone'], sprinkler['duration'])
                    system_status.last_zone_run = sprinkler['zone']
                    
                    # Only create a timer task if we're not in a sequence
                    # This prevents the recursive dependency
                    if not self._in_sequence:
                        # Create and start new timer task - with proper naming and handling
                        self._timer_task = asyncio.create_task(
                            self._zone_timer(sprinkler['duration']), 
                            name=f"zone_timer_task_{sprinkler['zone']}"
                        )
                    return True
                else:
                    logger.error(f"Started zone {sprinkler['zone']} for {sprinkler['duration']} seconds: failed")
                    system_status.update_status("error", "Command Failed", None)
                    raise IOError("Command Failed")
            except IOError as exc:
                system_status.update_status("error", "ESP Controller error", None)
                raise
        else:
            logger.error(f"Failed to start zone {sprinkler['zone']}, system already active")
            raise Exception(f"Failed to start zone {sprinkler['zone']}, system already active. Active zone: {system_status.active_zone}")

    async def stop_system(self) -> bool:
        """Stop the currently running sprinkler and cancel any running sequence.
        
        Returns:
            True if the system was stopped successfully
            
        Raises:
            IOError: If hardware communication fails
            Exception: If system not active
        """
        try:
            # Cancel sequence task if running
            if self._sequence_task and not self._sequence_task.done():
                self._sequence_task.cancel()
                try:
                    await self._sequence_task
                except asyncio.CancelledError:
                    logger.debug("Zone sequence cancellation confirmed")
                    pass
                self._sequence_task = None
                self._in_sequence = False

            # Only check connection and stop hardware if a zone is active
            if system_status.active_zone:
                self.check_hunter_connection()
                if (esp_controller.stop_zone(system_status.active_zone)):
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
            else:
                logger.debug("No active zone to stop")
                return True

        except IOError as exc:
            system_status.update_status("error", "ESP Controller error", None)
            raise
        except Exception as exc:
            if system_status.active_zone:
                logger.error("Failed to stop zone, other error")
                raise
            return True

    async def run_zone_sequence(self, zones: List[Dict[str, int]]) -> bool:
        """Run a sequence of zones for specified durations.
        
        Args:
            zones: List of dictionaries containing:
                * zone (int): Zone number
                * duration (int): Duration in seconds
            
        Returns:
            True if all zones completed successfully
            
        Raises:
            asyncio.CancelledError: If sequence is cancelled
            Exception: If any zone fails or other errors occur
        """
        logger.debug(f"Running zone sequence: {zones}")
        try:
            # Create a new task for the sequence
            self._in_sequence = True  # Set flag to indicate we're in a sequence
            self._sequence_task = asyncio.create_task(self._run_sequence(zones))
            await self._sequence_task
            return True
        except asyncio.CancelledError:
            logger.info("Zone sequence cancelled")
            raise
        except Exception as e:
            logger.error(f"Error running zone sequence: {e}")
            raise
        finally:
            self._sequence_task = None
            self._in_sequence = False  # Reset flag when sequence is done

    async def _run_sequence(self, zones: List[Dict[str, int]]) -> None:
        """Internal method to run the zone sequence.
        
        Args:
            zones: List of dictionaries containing zone and duration
            
        Raises:
            Exception: If any zone fails
            asyncio.CancelledError: If sequence is cancelled
        """
        # Add padding between zones to avoid race conditions
        ZONE_TRANSITION_PADDING = 10  # seconds
        
        try:
            for zone in zones:
                logger.debug(f"Starting zone {zone['zone']} for {zone['duration']} seconds")
                try:
                    # Start the zone but _zone_timer() isn't' used in a sequence
                    await self.start_sprinkler(zone)
                    
                    try:
                        # Directly wait for the duration here
                        await asyncio.sleep(zone['duration'])
                        
                        # Add padding delay between zones
                        logger.debug(f"Adding {ZONE_TRANSITION_PADDING} seconds padding before next zone")
                        await asyncio.sleep(ZONE_TRANSITION_PADDING)
                        
                        # Stop the current zone before moving to the next one
                        await self.stop_system()
                    except asyncio.CancelledError:
                        logger.debug(f"Zone {zone['zone']} cancelled before completion")
                        raise
                except asyncio.CancelledError:
                    # Re-raise to properly handle sequence cancellation
                    raise
                except Exception as e:
                    logger.error(f"Error running zone {zone['zone']}: {e}")
                    raise
        except asyncio.CancelledError:
            # Ensure proper cleanup when cancelled
            if system_status.active_zone:
                await self.stop_system()
            raise
        except Exception as e:
            logger.error(f"Error in zone sequence: {e}")
            raise

system_controller = SystemController()
