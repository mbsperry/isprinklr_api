import json, logging, time, os # Added os
from typing import Any, Optional, List, Dict

from .paths import config_path, data_path
import isprinklr.sprinkler_service as sprinkler_service
from .schedule_database import ScheduleDatabase
from .schemas import SprinklerConfig

logger = logging.getLogger(__name__)

# Systemwide ScheduleDatabase singleton
schedule_database = ScheduleDatabase()

# Default configurations used if api.conf is missing, malformed, or keys are absent
DEFAULT_DOMAIN = "localhost"
DEFAULT_SCHEDULE_ON_OFF = False # Default to schedules being off
DEFAULT_LOG_LEVEL = "INFO"      # Default log level
DEFAULT_SCHEDULE_HOUR = 4       # Default to 4 AM
DEFAULT_SCHEDULE_MINUTE = 0     # Default to 0 minutes

# Initialize global config variables with defaults.
# These will be updated if api.conf is successfully read.
DOMAIN = DEFAULT_DOMAIN
SCHEDULE_ON_OFF = DEFAULT_SCHEDULE_ON_OFF
LOG_LEVEL = DEFAULT_LOG_LEVEL
SCHEDULE_HOUR = DEFAULT_SCHEDULE_HOUR
SCHEDULE_MINUTE = DEFAULT_SCHEDULE_MINUTE

try:
    api_conf_path = os.path.join(config_path, "api.conf")
    # main.py attempts to create a default api.conf if it's missing.
    # This block handles reading it, or falling back if it's still missing,
    # malformed, or keys are absent.
    with open(api_conf_path, "r") as f:
        config = json.load(f)
        
        # Load DOMAIN, falling back to default if key is missing or value is empty
        DOMAIN = config.get("domain", DEFAULT_DOMAIN)
        if not DOMAIN: # Handles cases like "domain": "" or "domain": null
            logger.warning(f"'domain' in '{api_conf_path}' is empty or null. Using default: '{DEFAULT_DOMAIN}'.")
            DOMAIN = DEFAULT_DOMAIN
            
        # Load SCHEDULE_ON_OFF, handling boolean or string representations
        raw_schedule_on_off = config.get("schedule_on_off", DEFAULT_SCHEDULE_ON_OFF)
        if isinstance(raw_schedule_on_off, bool):
            SCHEDULE_ON_OFF = raw_schedule_on_off
        else: # Attempt to parse from string
            SCHEDULE_ON_OFF = str(raw_schedule_on_off).lower() in ["true", "yes", "on"]
            
        # Load LOG_LEVEL, falling back to default if key is missing
        LOG_LEVEL = config.get("log_level", DEFAULT_LOG_LEVEL).upper()
        
        # Load schedule timing with validation, falling back to defaults if not provided or invalid
        schedule_hour = config.get("schedule_hour", DEFAULT_SCHEDULE_HOUR)
        schedule_minute = config.get("schedule_minute", DEFAULT_SCHEDULE_MINUTE)
        try:
            if isinstance(schedule_hour, int) and 0 <= schedule_hour <= 23:
                SCHEDULE_HOUR = schedule_hour
            else:
                logger.warning(f"Invalid schedule_hour in '{api_conf_path}': {schedule_hour}. Using default: {DEFAULT_SCHEDULE_HOUR}")
                SCHEDULE_HOUR = DEFAULT_SCHEDULE_HOUR
                
            if isinstance(schedule_minute, int) and 0 <= schedule_minute <= 59:
                SCHEDULE_MINUTE = schedule_minute
            else:
                logger.warning(f"Invalid schedule_minute in '{api_conf_path}': {schedule_minute}. Using default: {DEFAULT_SCHEDULE_MINUTE}")
                SCHEDULE_MINUTE = DEFAULT_SCHEDULE_MINUTE
        except Exception as e:
            logger.warning(f"Error processing schedule timing from '{api_conf_path}': {e}. Using defaults.")

except FileNotFoundError:
    logger.warning(f"'{api_conf_path}' not found (or not created by main.py). "
                   f"Using default configurations: DOMAIN='{DEFAULT_DOMAIN}', "
                   f"SCHEDULE_ON_OFF={DEFAULT_SCHEDULE_ON_OFF}, LOG_LEVEL='{DEFAULT_LOG_LEVEL}'.")
    # Globals DOMAIN, SCHEDULE_ON_OFF, LOG_LEVEL retain their pre-defined defaults
except json.JSONDecodeError as e:
    logger.error(f"Error decoding JSON from '{api_conf_path}': {e}. "
                 f"Using default configurations.")
    # Globals retain defaults
except Exception as e: # Catch-all for other unexpected errors during config loading
    logger.critical(f"Unexpected error loading '{api_conf_path}': {e}. "
                    f"Using default configurations.")
    # Globals retain defaults

# Apply the determined log level to this module's logger
# (Root logger level is set in main.py's basicConfig)
try:
    # Ensure LOG_LEVEL is a valid level string before setting
    if LOG_LEVEL not in logging._nameToLevel:
        invalid_level = LOG_LEVEL
        LOG_LEVEL = DEFAULT_LOG_LEVEL # Fallback to a known good default
        logger.error(f"Invalid LOG_LEVEL string '{invalid_level}' from config or default. "
                     f"Defaulting logger level for '{__name__}' to '{LOG_LEVEL}'.")
    logger.setLevel(getattr(logging, LOG_LEVEL))
except AttributeError: # Should not happen if LOG_LEVEL is validated against _nameToLevel
    # This is an extra safeguard.
    LOG_LEVEL = DEFAULT_LOG_LEVEL
    logger.error(f"Failed to set log level with '{LOG_LEVEL}'. Defaulting to '{DEFAULT_LOG_LEVEL}'.")
    logger.setLevel(getattr(logging, DEFAULT_LOG_LEVEL))


# Log effective settings after attempting to load config
logger.info(f"Effective API Domain for CORS: {DOMAIN}")
logger.info(f"Effective initial Schedule ON/OFF state: {SCHEDULE_ON_OFF}")
logger.info(f"Effective Log Level for '{__name__}' logger: {LOG_LEVEL}")
logger.info(f"Effective schedule execution time: {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d}")


class SystemStatus:
    """
    Manages the system state and configuration for the sprinkler system.
    
    The class is implemented as a singleton to ensure consistent system state
    across the application.
    """

    def __init__(self):
        self._status: str = "inactive"
        self._status_message: Optional[str] = None
        self._active_zone: Optional[int] = None
        self._end_time: Optional[float] = None
        self._sprinklers: List[SprinklerConfig] = sprinkler_service.read_sprinklers(data_path)
        # Initialize _schedule_on_off from the globally determined SCHEDULE_ON_OFF value
        self._schedule_on_off: bool = SCHEDULE_ON_OFF
        self._last_zone_run: Optional[Dict[str, Any]] = None
        self._last_schedule_run: Optional[Dict[str, Any]] = None
        self._esp_status_data: Optional[Dict[str, Any]] = None
        
        # Initialize schedule timing properties from global values
        self._schedule_hour: int = SCHEDULE_HOUR
        self._schedule_minute: int = SCHEDULE_MINUTE
        
        # Initialize schedule_database with sprinklers
        schedule_database.set_sprinklers(self._sprinklers)
        schedule_database.load_database()

    @property
    def last_zone_run(self) -> Optional[Dict[str, Any]]:
        """Get information about the last zone that was run.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing:
                - zone (int): The zone number that was run
                - timestamp (float): Unix timestamp when the zone was run
                Or None if no zone has been run
        """
        return self._last_zone_run
    
    @last_zone_run.setter 
    def last_zone_run(self, zone: int):
        """Set information about the last zone run.
        
        Args:
            zone (int): The zone number that was run
        """
        import time
        self._last_zone_run = {
            "zone": zone,
            "timestamp": time.time()
        }
    
    @property
    def last_schedule_run(self) -> Optional[Dict[str, Any]]:
        """Get information about the last schedule that was run.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing:
                - name (str): Name of the schedule that was run
                - timestamp (float): Unix timestamp when schedule was run
                - message (str): Status message about the schedule run
                Or None if no schedule has been run
        """
        return self._last_schedule_run
    
    @last_schedule_run.setter
    def last_schedule_run(self, data: Dict[str, Any]):
        """Set information about the last schedule run.
        
        Args:
            data (dict): Dictionary containing:
                - name (str): Name of the schedule that was run
                - message (str): Status message about the schedule run
        """
        import time
        self._last_schedule_run = {
            "name": data["name"],
            "timestamp": time.time(),
            "message": data["message"]
        }
    
    @property
    def schedule_on_off(self) -> bool:
        return self._schedule_on_off
    
    @schedule_on_off.setter
    def schedule_on_off(self, value: bool):
        self._schedule_on_off = value
        
    @property
    def schedule_hour(self) -> int:
        return self._schedule_hour
    
    @schedule_hour.setter
    def schedule_hour(self, value: int):
        if not (0 <= value <= 23):
            raise ValueError("Hour must be between 0 and 23")
        self._schedule_hour = value
        
    @property
    def schedule_minute(self) -> int:
        return self._schedule_minute
    
    @schedule_minute.setter
    def schedule_minute(self, value: int):
        if not (0 <= value <= 59):
            raise ValueError("Minute must be between 0 and 59")
        self._schedule_minute = value

    @property
    def active_zone(self) -> Optional[int]:
        return self._active_zone

    @property
    def sprinklers(self) -> List[SprinklerConfig]:
        return self._sprinklers

    def update_status(self, status: str, message: Optional[str] = None, active_zone: Optional[int] = None, duration: Optional[int] = None):
        """
        Update the system status.
        
        Args:
            status (str): New status to set ('active' or 'inactive')
            message (Optional[str]): Optional status message
            active_zone (Optional[int]): Zone number that is active, or None
            duration (Optional[int]): Duration in seconds for the active status, or None    
        """
        self._status = status
        self._status_message = message
        self._active_zone = active_zone
        self._end_time = time.time() + duration if status == "active" and duration is not None else None

    @property
    def esp_status_data(self) -> Optional[Dict[str, Any]]:
        """Get the current ESP controller status data.
        
        Returns:
            Optional[Dict[str, Any]]: The full ESP controller status data, or None if not available
        """
        return self._esp_status_data
    
    @esp_status_data.setter
    def esp_status_data(self, data: Dict[str, Any]):
        """Set the ESP controller status data.
        
        Args:
            data (Dict[str, Any]): The ESP controller status data
        """
        self._esp_status_data = data
    
    def get_status(self) -> dict:
        """
        Get the current system status.
        
        Returns:
            dict: Dictionary containing current status information:
                - systemStatus (str): Current status ('active' or 'inactive')
                - message (Optional[str]): Current status message
                - active_zone (Optional[int]): Currently active zone number
                - duration (int): Remaining duration in seconds if active
                - esp_status (Optional[Dict]): ESP controller detailed status information
        """
        duration = 0
        if self._status == "active" and self._end_time is not None:
            duration = int(max(0, self._end_time - time.time()))

        logger.debug(f"System status: {self._status}, message: {self._status_message}, active zone: {self._active_zone}, duration: {duration}")
        
        status_data = {
            "systemStatus": self._status,
            "message": self._status_message,
            "active_zone": self._active_zone,
            "duration": duration
        }
        
        # Include ESP controller status if available
        if self._esp_status_data:
            status_data["esp_status"] = self._esp_status_data
            
        return status_data
    
    def update_sprinklers(self, sprinklers: List[SprinklerConfig]) -> List[SprinklerConfig]:
        """
        Updates the sprinkler configurations.
        
        Args:
            sprinklers (List[SprinklerConfig]): List of sprinkler configurations to set.
                Each config must contain zone number and name.
            
        Returns:
            List[SprinklerConfig]: The updated list of sprinkler configurations
            
        Raises:
            ValueError: If validation fails (empty list, >12 sprinklers, duplicate zones/names)
            Exception: If writing to storage fails
        """
        try:
            sprinkler_service.write_sprinklers(data_path, sprinklers)
            self._sprinklers = sprinklers
            schedule_database.set_sprinklers(sprinklers)
            return sprinklers
        except Exception as e:
            logger.error(f"Failed to write sprinklers data: {e}")
            raise
    
    def get_api_config(self) -> dict:
        """Read the current API configuration from api.conf
        
        Returns:
            dict: The current API configuration
            
        Raises:
            Exception: If the configuration file cannot be read
        """
        try:
            with open(f"{config_path}/api.conf", "r") as f:
                return json.load(f)
        except Exception as exc:
            logger.error(f"Failed to read API configuration: {exc}")
            raise Exception(f"Failed to read API configuration: {exc}")

    def update_api_config(self, config: dict) -> dict:
        """Update the API configuration in api.conf
        
        Args:
            config (dict): The new API configuration with fields like:
                ESP_controller_IP, domain, dummy_mode, schedule_on_off, 
                log_level, USE_STRICT_CORS
            
        Returns:
            dict: The updated API configuration
            
        Notes:
            Changes to domain and USE_STRICT_CORS will be
            saved to the configuration file but will not take effect
            until the API is restarted.
            
        Raises:
            Exception: If the configuration file cannot be written
        """
        try:
            # Write the configuration to file
            with open(f"{config_path}/api.conf", "w") as f:
                json.dump(config, f)
            
            # Update internal state and global variables
            global DOMAIN, SCHEDULE_ON_OFF, LOG_LEVEL
            
            # Update schedule_on_off both in SystemStatus instance and global variable
            if 'schedule_on_off' in config:
                self._schedule_on_off = config['schedule_on_off']
                SCHEDULE_ON_OFF = config['schedule_on_off']
                logger.debug(f"Updated schedule_on_off to {config['schedule_on_off']}")
                
            # Update schedule time properties
            if 'schedule_hour' in config:
                try:
                    self.schedule_hour = config['schedule_hour']
                    logger.debug(f"Updated schedule_hour to {config['schedule_hour']}")
                except ValueError as e:
                    logger.warning(f"Invalid schedule_hour value: {e}")
                    
            if 'schedule_minute' in config:
                try:
                    self.schedule_minute = config['schedule_minute']
                    logger.debug(f"Updated schedule_minute to {config['schedule_minute']}")
                except ValueError as e:
                    logger.warning(f"Invalid schedule_minute value: {e}")
            
            # Check if scheduler configuration has been updated
            schedule_config_modified = False
            for key in ['schedule_hour', 'schedule_minute', 'schedule_on_off']:
                if key in config:
                    schedule_config_modified = True
                    break
            
            # If scheduler-related settings have changed, update the scheduler configuration
            if schedule_config_modified:
                try:
                    # Import here to avoid circular imports
                    from .scheduler_manager import update_scheduler_config
                    update_scheduler_config(config)
                    logger.info("Updated scheduler configuration")
                except Exception as e:
                    logger.error(f"Failed to update scheduler configuration: {e}")
            
            # Update domain for CORS
            if 'domain' in config:
                DOMAIN = config['domain']
                logger.debug(f"Updated DOMAIN to {config['domain']}")
            
            # Update log level
            if 'log_level' in config:
                new_log_level = config['log_level'].upper()
                # Validate log level before setting
                if new_log_level in logging._nameToLevel:
                    LOG_LEVEL = new_log_level
                    logger.setLevel(getattr(logging, LOG_LEVEL))
                    logger.debug(f"Updated LOG_LEVEL to {LOG_LEVEL}")
                else:
                    logger.warning(f"Invalid log level: {new_log_level}, ignoring")
            
            return config
        except Exception as exc:
            logger.error(f"Failed to write API configuration: {exc}")
            raise Exception(f"Failed to write API configuration: {exc}")

# Create singleton instance
system_status = SystemStatus()
