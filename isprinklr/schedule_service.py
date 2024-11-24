import pandas as pd
import logging
from datetime import datetime

from isprinklr.paths import data_path
from isprinklr.schemas import ScheduleItem

logger = logging.getLogger(__name__)

class ScheduleService:
    def __init__(self, sprinklers: list[dict] = None):
        self.sprinklers = sprinklers if sprinklers is not None else []
        self.schedule = self.read_schedule() if sprinklers else []

    @staticmethod
    def validate_schedule(schedule: list[ScheduleItem], sprinklers: list[dict]):
        valid_days = {"M", "Tu", "W", "Th", "F", "Sa", "Su", "ALL", "NONE", "EO"}
        sprinkler_zones = [x["zone"] for x in sprinklers]
        # check that each zone is only used once
        if len(schedule) != len(set([x["zone"] for x in schedule])):
            logger.error(f"Duplicate zones in schedule: {schedule}")
            raise ValueError("Validation Error: Duplicate zones in schedule")
        for item in schedule:
            # Check if the zone is valid
            if item["zone"] not in sprinkler_zones:
                logger.error(f"Invalid zone in schedule: {item}")
                raise ValueError("Validation Error: Invalid zone")
            # Check if the duration is valid
            if item["duration"] < 0 or item["duration"] > 60:
                logger.error(f"Invalid duration in schedule: {item}")
                raise ValueError("Validation Error: Invalid duration")
            # Check if the day is valid
            days = item["day"].split(':')
            if not all(day in valid_days for day in days):
                logger.error(f"Invalid day in schedule: {item}")
                raise ValueError("Validation Error: Invalid day")
            if "ALL" in days or "NONE" in days or "EO" in days:
                if len(days) > 1:
                    logger.error(f"Invalid day definition in schedule. Cannot contain multiple day selector and specified days: {item}")
                    raise ValueError("Validation Error: Invalid day")
        return True

    def read_schedule(self):
        try:
            schedule_df = pd.read_csv(data_path + "/schedule.csv", usecols=["zone", "day", "duration"])
            schedule = schedule_df.to_dict("records")
            try:
                self.validate_schedule(schedule, self.sprinklers)
            except ValueError as e:
                logger.error(f"Schedule.csv contained invalid sprinkler definitions")
                schedule = []
        except Exception as e:
            logger.error(f"Failed to load schedule data: {e}")
            schedule = []
        logger.debug(f"Schedule: {schedule}")
        return schedule
    
    def update_schedule(self, schedule: list[ScheduleItem]):
        try:
            self.validate_schedule(schedule, self.sprinklers)
        except ValueError as e:
            logger.error(f"Invalid schedule: {schedule}")
            raise
        try:
            schedule_df = pd.DataFrame(schedule)
            schedule_df.to_csv(data_path + "/schedule.csv", index=False)
            self.schedule = schedule
            return True
        except Exception as e:
            logger.error(f"Failed to update schedule data: {e}")
            raise

    def get_scheduled_zones(self, date_str: str) -> list[dict]:
        """Get zones scheduled to run on the specified date.
        
        Args:
            date_str: Date string in MMDDYY format
            
        Returns:
            List of scheduled zones with their duration
        """
        try:
            date = datetime.strptime(date_str, "%m%d%y")
        except ValueError:
            logger.error(f"Invalid date format: {date_str}")
            return []

        # Map day of week (0-6, where 0 is Monday) to day abbreviation
        day_map = {0: "M", 1: "Tu", 2: "W", 3: "Th", 4: "F", 5: "Sa", 6: "Su"}
        current_day = day_map[date.weekday()]
        day_of_year = int(date.strftime("%j"))

        scheduled_zones = []
        for item in self.schedule:
            days = item["day"].upper().split(':')
            
            # Handle special day patterns
            if "ALL" in days:
                scheduled_zones.append({"zone": item["zone"], "duration": item["duration"]})
            elif "EO" in days and day_of_year % 2 != 0:
                scheduled_zones.append({"zone": item["zone"], "duration": item["duration"]})
            elif "NONE" in days:
                continue
            # Handle specific days
            elif current_day in days:
                scheduled_zones.append({"zone": item["zone"], "duration": item["duration"]})

        return scheduled_zones
