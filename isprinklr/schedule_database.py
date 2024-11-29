import json
import logging
from typing import List, Optional

from isprinklr.paths import data_path
from isprinklr.schemas import Schedule, ScheduleList, SprinklerConfig
from isprinklr.schedule_util import validate_schedule, validate_schedule_list, get_scheduled_zones

logger = logging.getLogger(__name__)

class ScheduleDatabase:
    def __init__(self):
        """
        Initialize an empty ScheduleDatabase.
        """
        self.sprinklers: Optional[List[SprinklerConfig]] = None
        self.schedules: List[Schedule] = []
        self.active_schedule_id: Optional[int] = None
    
    @property
    def active_schedule(self) -> Optional[int]:
        return self.active_schedule_id

    def set_sprinklers(self, sprinklers: List[SprinklerConfig]):
        """
        Set the sprinkler configurations for the database.
        
        Args:
            sprinklers: List of valid sprinkler configurations
        """
        self.sprinklers = sprinklers

    def load_database(self):
        """
        Load the schedule database by reading and validating the schedule file.
        If the file doesn't exist or is invalid, an empty schedule list will be used.
        
        Raises:
            ValueError: If sprinklers have not been set
        """
        if self.sprinklers is None:
            raise ValueError("Sprinklers must be set before loading database")

        try:
            schedule_data = self.read_schedule_file()
            self.validate_schedule_data(schedule_data)
            self.schedules = schedule_data["schedules"]
            self.active_schedule_id = schedule_data["active_schedule"]
            logger.debug(f"Initial schedules loaded: {self.schedules}")
        except Exception as e:
            logger.error(f"Failed to load schedule database: {e}")
            self.schedules = []
            self.active_schedule_id = None

    def validate_schedule_data(self, data: dict) -> bool:
        """
        Validate the schedule data format and content.
        
        Args:
            data: Dictionary containing schedules and active_schedule
            
        Returns:
            bool: True if validation passes
            
        Raises:
            ValueError: If validation fails or if sprinklers have not been set
        """
        if self.sprinklers is None:
            raise ValueError("Sprinklers must be set before validating schedule data")

        if not isinstance(data, dict):
            raise ValueError("Invalid schedule data format")
        
        required_keys = {"schedules", "active_schedule"}
        if not all(key in data for key in required_keys):
            raise ValueError("Missing required keys in schedule data")
            
        if not isinstance(data["schedules"], list):
            raise ValueError("Schedules must be a list")
            
        if not isinstance(data["active_schedule"], int) and data["active_schedule"] is not None:
            raise ValueError("Active schedule must be an integer or None")
            
        # Validate all schedules using schedule_util
        try:
            validate_schedule_list(data["schedules"], self.sprinklers)
        except ValueError as e:
            raise ValueError(f"Invalid schedule data: {e}")

        # Verify active_schedule refers to a valid schedule
        if data["schedules"] and data["active_schedule"] is not None and data["active_schedule"] not in [s["sched_id"] for s in data["schedules"]]:
            raise ValueError("Active schedule ID does not exist")
            
        return True

    def read_schedule_file(self) -> dict:
        """
        Read the schedule file and parse its contents.
        
        Returns:
            dict: Schedule data containing schedules and active_schedule
            
        Raises:
            Exception: If file reading or parsing fails
        """
        try:
            with open(f"{data_path}/schedules.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("Schedule file not found, using empty schedule")
            return {"schedules": [], "active_schedule": None}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse schedule file: {e}")
            raise

    def write_schedule_file(self) -> bool:
        """
        Write the current schedules to the schedule file.
        
        Returns:
            bool: True if write was successful
            
        Raises:
            Exception: If writing fails
        """
        data = {
            "schedules": self.schedules,
            "active_schedule": self.active_schedule_id
        }
        try:
            with open(f"{data_path}/schedules.json", "w") as f:
                f.write(json.dumps(data, indent=2))
            logger.debug(f"Wrote schedules to file: {self.schedules}")
            return True
        except Exception as e:
            logger.error(f"Failed to write schedule file: {e}")
            raise

    def update_schedule(self, schedule: Schedule) -> Schedule:
        """
        Update an existing schedule.
        
        Args:
            schedule: Updated schedule data
            
        Returns:
            Schedule: The updated schedule
            
        Raises:
            ValueError: If schedule validation fails, schedule ID not found, or sprinklers not set
        """
        if self.sprinklers is None:
            raise ValueError("Sprinklers must be set before updating schedule")

        logger.debug(f"Before update, current schedules: {self.schedules}")
        logger.debug(f"Attempting to update schedule: {schedule}")

        # Validate the schedule
        try:
            validate_schedule(schedule["schedule_items"], self.sprinklers)
        except ValueError as e:
            logger.error(f"Failed to validate schedule: {e}")
            raise
        
        # Find and update existing schedule
        for i, s in enumerate(self.schedules):
            if s["sched_id"] == schedule["sched_id"]:
                logger.debug(f"Found schedule with ID {s['sched_id']} and name {s['schedule_name']}, updating")
                logger.debug(f"New schedule name: {schedule['schedule_name']}")
                self.schedules[i] = schedule
                self.write_schedule_file()
                return schedule
        
        raise ValueError(f"Schedule with ID {schedule['sched_id']} not found")

    def add_schedule(self, schedule: Schedule) -> Schedule:
        """
        Add a new schedule.
        
        Args:
            schedule: New schedule data
            
        Returns:
            Schedule: The added schedule
            
        Raises:
            ValueError: If schedule validation fails, ID already exists, or sprinklers not set
        """
        if self.sprinklers is None:
            raise ValueError("Sprinklers must be set before adding schedule")

        logger.debug(f"Before add, current schedules: {self.schedules}")
        logger.debug(f"Attempting to add schedule: {schedule}")

        # Validate the schedule
        try:
            validate_schedule(schedule["schedule_items"], self.sprinklers)
        except ValueError as e:
            logger.error(f"Failed to validate schedule: {e}")
            raise
        
        # Check if schedule ID already exists
        if any(s["sched_id"] == schedule["sched_id"] for s in self.schedules):
            raise ValueError(f"Schedule with ID {schedule['sched_id']} already exists")
        
        # Add new schedule
        self.schedules.append(schedule)
        self.write_schedule_file()
        return schedule

    def get_schedule(self, schedule_id: int) -> Optional[Schedule]:
        """
        Get a schedule by ID.
        
        Args:
            schedule_id: ID of the schedule to retrieve
            
        Returns:
            Optional[Schedule]: The schedule if found, None otherwise
            
        Raises:
            ValueError: If schedule not found
        """
        for schedule in self.schedules:
            if schedule["sched_id"] == schedule_id:
                return schedule
        raise ValueError(f"Schedule with ID {schedule_id} not found")

    def get_active_schedule(self) -> Optional[Schedule]:
        """
        Get the currently active schedule.
        
        Returns:
            Optional[Schedule]: The active schedule if one exists, None otherwise
            
        Raises:
            ValueError: If no active schedule or active schedule not found
        """
        if not self.active_schedule_id:
            raise ValueError("No active schedule")
        try:
            return self.get_schedule(self.active_schedule_id)
        except ValueError:
            raise
    